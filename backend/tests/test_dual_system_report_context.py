"""Identity and capability boundaries shared by report-consuming modules."""
import io
import zipfile
from dataclasses import replace

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.api.endpoints import calculation, version_difference
from app.core.calculation.excel_parser import ChartDataRecord, WireWearRecord, parse_exception_report
from app.core.calculation.stagger_selector import _normalize_track
from app.core.calculation.stagger_metadata import require_stagger_configuration, StaggerConfigurationUnavailable
from app.core.calculation.trend_analyzer import analyze_trend
from app.core.calculation.wear_records import normalize_line_group, WireWearValidationError
from app.core.report_context import (
    ReportContext, ReportContextError, normalize_report_row, read_report_context,
    ensure_compatible_scopes, validate_algorithm_compatibility,
    load_report_preflight,
)
from app.main import app


client = TestClient(app)


def workbook_bytes(*, line='AEL', track='UT', section='Mainline', algorithm='', mode='',
                   chart_line=None, include_wear=True, summary_line=None):
    summary = {'ID': 'W1', 'Run Date': '2026-06-03', 'Line': summary_line or line,
               'Track': track, 'Section': section, 'Task No': 'U3',
               'Stn Start': 'SHR', 'Stn End': 'AWE', 'Exception Type': 'Wire Wear',
               'Level': 'L2', 'FromM': 100., 'ToM': 102., 'MaxValue': 9.8,
               'MaxLocation': 101., 'Tension Length': None}
    chart = [{'task_run_date': '20260603', 'line': chart_line or line, 'track': track,
              'Section': section, 'task_no': 'U3', 'station_start': 'SHR', 'station_end': 'AWE',
              'Chainage': 100 + index * .25, 'wear_min': 9.8,
              **{f'{metric}{channel}': 9.8 + index * .001 for metric in ('wear', 'height', 'stagger') for channel in range(1, 5)}}
             for index in range(110)]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame([summary]).to_excel(writer, sheet_name='Summary', index=False)
        if include_wear:
            # Old templates omit identity on Wire Wear. Summary is authoritative
            # for this candidate even when no approved TL is available.
            pd.DataFrame([{key: value for key, value in summary.items()
                           if key not in {'Line', 'Track', 'Section', 'Task No', 'Stn Start', 'Stn End'}}]).to_excel(writer, sheet_name='Wire Wear', index=False)
        pd.DataFrame(chart).to_excel(writer, sheet_name='ChartData', index=False)
        if algorithm or mode:
            pd.DataFrame([['aggregation_version', algorithm], ['chart_data_mode', mode]],
                         columns=['Key', 'Value']).to_excel(writer, sheet_name='_Metadata', index=False)
    return output.getvalue()


def chart(date='2026-06-03', **kwargs):
    values = dict(task_run_date=date, line='AEL', track='UT', section='Mainline', task_no='U3',
                  station_start='SHR', station_end='AWE', tension_length='', chainage=101.,
                  wear_min=9.8, track_type='Tangent', overlap=None, branch='Mainline')
    values.update(kwargs)
    return ChartDataRecord(**values)


def candidate(**kwargs):
    values = dict(run_date='2026-06-03', exception_id='W1', tension_length='', from_m=100., to_m=102.,
                  max_value=9.8, level='L2', action=None, line='AEL', track='UT', section='Mainline',
                  task_no='U3', station_start='SHR', station_end='AWE', branch='Mainline')
    values.update(kwargs)
    return WireWearRecord(**values)


@pytest.mark.parametrize('line,section,parent,branch', [('LMC','LMC','EAL','LMC'), ('TKS','TKS','TKL','TKS'), ('DRL','Mainline','DRL','UT')])
def test_source_aliases_preserve_source_line(line, section, parent, branch):
    context = normalize_report_row({'Line': line, 'Section': section, 'Track': 'DT'})
    assert (context.line, context.branch, context.direction, context.source_line) == (parent, branch, 'DOWN', line)


def test_reader_uses_summary_candidate_metadata_with_empty_tl_and_arbitrary_filename():
    wire, data = parse_exception_report(workbook_bytes(), filename='renamed.xlsx')
    record = wire[0]
    assert record.tension_length == ''
    assert (record.line, record.track, record.section, record.task_no, record.station_start, record.station_end) == ('AEL', 'UT', 'Mainline', 'U3', 'SHR', 'AWE')
    assert data[0].line == 'AEL'


def test_reader_preserves_original_lmc_source_on_candidate_and_chartdata():
    wire, data = parse_exception_report(workbook_bytes(line='LMC', section='LMC', track='UP'))
    for record in (wire[0], data[0]):
        assert (record.line, record.branch, record.source_line) == ('EAL', 'LMC', 'LMC')


@pytest.mark.parametrize('suffix', ['', '_MedianSample'])
def test_old_and_new_report_filenames_are_accepted(suffix):
    data = workbook_bytes()
    book = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        context = read_report_context(book, f'20260603_AEL_UT_MAINLINE_SHR_AWE_Exception_Report{suffix}.xlsx')
    finally:
        book.close()
    assert context.scope == ('AEL', 'Mainline', 'UP')


def test_reader_rejects_summary_chart_identity_conflict():
    with pytest.raises(ReportContextError, match='incompatible line'):
        parse_exception_report(workbook_bytes(chart_line='TWL'))


@pytest.mark.parametrize('track', ['DT', 'DN', 'DOWN'])
def test_stagger_down_direction(track):
    assert _normalize_track(track) == 'down'


@pytest.mark.parametrize('track', ['', None, 'UNKNOWN'])
def test_stagger_missing_or_unknown_direction_rejected(track):
    with pytest.raises(ValueError):
        _normalize_track(track)


def test_lmc_cannot_inherit_mainline_stagger_profile():
    with pytest.raises(StaggerConfigurationUnavailable) as failure:
        require_stagger_configuration('EAL', 'LMC', 'UP')
    assert failure.value.detail()['context']['branch'] == 'LMC'


def test_ael_stagger_reports_capability_before_loading_chartdata(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Unsupported profile decoded ChartData')
    monkeypatch.setattr(calculation.pd, 'read_excel', forbidden)
    response = client.post('/api/calculation/stagger', files={'file': ('renamed.xlsx', workbook_bytes())})
    assert response.status_code == 422
    detail = response.json()['detail']
    assert detail['code'] == 'STAGGER_CONFIG_UNAVAILABLE'
    assert detail['context'] == {'line': 'AEL', 'branch': 'Mainline', 'direction': 'UP'}


def test_stagger_preflight_does_not_even_open_chartdata_xml(monkeypatch):
    content = workbook_bytes()
    original_open = zipfile.ZipFile.open

    def guarded_open(archive, name, *args, **kwargs):
        filename = name.filename if isinstance(name, zipfile.ZipInfo) else name
        if filename == 'xl/worksheets/sheet3.xml':
            pytest.fail('Capability preflight opened ChartData XML')
        return original_open(archive, name, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, 'open', guarded_open)
    response = client.post('/api/calculation/stagger', files={'file': ('renamed.xlsx', content)})
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'STAGGER_CONFIG_UNAVAILABLE'


def test_trend_preserves_candidate_context_and_matches_across_different_tasks_dates():
    current = chart()
    previous = chart('2026-05-03', task_no='U1', station_start='OTHER', station_end='OLD', wear_min=10.)
    for records in ({'2026-06-03': [current], '2026-05-03': [previous]},
                    {'2026-05-03': [previous], '2026-06-03': [current]}):
        result = analyze_trend([candidate()], records)[0]
        assert result.line == 'AEL'
        assert (result.track, result.section, result.task_no, result.station_start, result.station_end) == ('UT', 'Mainline', 'U3', 'SHR', 'AWE')
        assert result.record_points == [9.8, 10.]
        assert result.algorithm_status == 'unknown'


@pytest.mark.parametrize('changes', [{'line': 'TWL'}, {'track': 'DT'}, {'line': 'EAL','branch': 'LMC','section':'LMC'}])
def test_trend_rejects_mixed_identity(changes):
    with pytest.raises(ReportContextError):
        analyze_trend([candidate()], {'2026-06-03': [chart(), chart(**changes)]})


def test_trend_does_not_mix_same_tl_across_sections_or_empty_tl_spans():
    result = analyze_trend([candidate(tension_length='T01')], {'2026-06-03': [
        chart(tension_length='T01'), chart(tension_length='T01', section='Other', wear_min=1.),
        chart(chainage=200., wear_min=2.),
    ]})[0]
    assert result.record_points == [9.8]


def test_trend_same_day_task_or_source_cannot_replace_candidates_own_measurement():
    own = candidate(source_id='own')
    records = [chart(source_id='own'), chart(source_id='other', wear_min=1.),
               chart(source_id='own', task_no='U1', wear_min=2.)]
    result = analyze_trend([own], {'2026-06-03': records})[0]
    assert result.record_points == [9.8]


def test_trend_rejects_ambiguous_historical_acquisitions():
    with pytest.raises(ReportContextError) as failure:
        analyze_trend([candidate()], {'2026-06-03': [chart()], '2026-05-03': [
            chart('2026-05-03', task_no='U1'), chart('2026-05-03', task_no='U2')]})
    assert failure.value.code == 'AMBIGUOUS_REPORT_ACQUISITION'


def test_trend_composite_tl_uses_compatible_physical_span():
    result = analyze_trend([candidate(tension_length='T01, T02')], {'2026-06-03': [
        chart(tension_length='T01', section='MAINLINE'), chart(tension_length='OTHER', wear_min=1.)]})[0]
    assert result.record_points == [9.8]


@pytest.mark.parametrize('line,section,track,code', [
    ('TWL','Mainline','UT','INCOMPATIBLE_REPORT_SCOPE'),
    ('AEL','Mainline','DT','INCOMPATIBLE_REPORT_SCOPE'),
    ('AEL','Other','UT','INCOMPATIBLE_REPORT_SECTION'),
])
def test_version_rejects_incompatible_report_identity(line, section, track, code):
    response = client.post('/api/analyze/version-difference', files={
        'latest': ('latest.xlsx', workbook_bytes()),
        'previous_1': ('previous.xlsx', workbook_bytes(line=line, section=section, track=track)),
    })
    assert response.status_code == 422
    assert response.json()['detail']['code'] == code


def test_version_rejects_explicit_algorithm_mismatch():
    response = client.post('/api/analyze/version-difference', files={
        'latest': ('latest.xlsx', workbook_bytes(algorithm='same_chainage_median_sample_v1', mode='chainage_median')),
        'previous_1': ('previous.xlsx', workbook_bytes(algorithm='raw_v1', mode='raw')),
    })
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'INCOMPATIBLE_REPORT_ALGORITHM'


def test_trend_rejects_explicit_algorithm_mismatch():
    with pytest.raises(ReportContextError) as failure:
        analyze_trend([candidate()], {'2026-06-03': [chart(algorithm='median_v1')],
                                      '2026-05-03': [chart('2026-05-03', algorithm='mean_v1')]})
    assert failure.value.code == 'INCOMPATIBLE_REPORT_ALGORITHM'


@pytest.mark.parametrize('group,kind', [('AEL','AEL'), ('UNKNOWN',''), ('TML','EAL'), ('TML','LMC'), ('','')])
def test_wear_unknown_or_conflicting_identity_never_defaults_to_eal(group, kind):
    with pytest.raises(WireWearValidationError):
        normalize_line_group(group, kind)
