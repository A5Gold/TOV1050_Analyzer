"""Regression coverage for the user-maintained wide Excel report enrichment."""
import hashlib
import json

import pandas as pd
import pytest
from openpyxl import Workbook

from app.core.tov1050_metadata import TOV1050MetadataManager
from app.core.tov1050_capabilities import MetadataCapabilityError
from app.core.tov1050_wide_enrichment import WideExcelEnrichmentProvider


HEADERS = ['Landmark FromM', 'Landmark ToM', 'Landmark', 'Overlap FromM',
           'Overlap ToM', 'Overlap', 'Tension Length', 'Track Type',
           'Track Type FromM', 'Track Type ToM', 'Interval Closed']


def workbook(tmp_path, rows=None, *, drl=False):
    path = tmp_path / ('DRL metadata.xlsx' if drl else 'TWL metadata.xlsx')
    book = Workbook()
    book.remove(book.active)
    boundaries = book.create_sheet('Exception Boundarys')
    boundaries.append(['Line', 'Class', 'UT Track FromM', 'UT Track ToM',
                       'PL Track FromM', 'PL Track ToM'] if drl else
                      ['Line', 'Class', 'UP Track FromM', 'UP Track ToM',
                       'DN Track FromM', 'DN Track ToM'])
    boundaries.append(['DRL' if drl else 'TWL', 'Open', 0, 1000, 1000, 2000])
    sheet = book.create_sheet('DRL UT' if drl else 'TWL UT')
    sheet.append(HEADERS)
    for row in rows if rows is not None else [
        [500, 500, 'Point landmark', 0, 0, 'N', '1', 'Tangent', 0, 1000, 'both'],
        [800, 850, 'Range landmark', 0, 10, 'N', '1', None, None, None, 'neither'],
        [None, None, None, 10, 10, 'Y', '2,1', None, None, None, 'both'],
        [None, None, None, 10, 20, 'N', '2', None, None, None, 'neither'],
        [None, None, None, 20, 20, 'N', '2', None, None, None, 'both'],
        [None, None, None, 20, 30, None, None, None, None, None, 'neither'],
    ]:
        sheet.append(row)
    if drl:
        sheet = book.create_sheet('DRL PL')
        sheet.append(HEADERS)
        sheet.append([None, None, None, 1000, 2000, 'N', 'PL-TL', 'Curve', 1000, 2000, 'both'])
    book.save(path)
    return TOV1050MetadataManager(path)


def test_wide_atoms_keep_exact_endpoints_and_no_tl_unknown(tmp_path):
    manager = workbook(tmp_path)
    provider = manager.approved_interval_provider()
    assert isinstance(provider, WideExcelEnrichmentProvider)
    at = lambda x: manager.enrichment_evidence(x, 'TWL', 'Mainline', 'UT')
    assert at(0)['Tension Length'] == '1'
    assert at(9.99999)['Overlap'] == 'N'
    assert at(10)['Tension Length'] == '1 / 2'
    assert at(10)['Overlap'] == 'Y'
    assert at(10.00001)['Tension Length'] == '2'
    assert at(20)['Tension Length'] == '2'
    assert at(25)['Overlap'] is None
    assert at(25)['overlap_status'] == 'unknown'
    assert at(30)['tl_status'] == 'outside_coverage'
    frame = pd.DataFrame({'Chainage': [10, 0, 10.00001, 25, float('nan')]})
    manager.map_approved_enrichment(frame, 'TWL', 'Mainline', 'UT')
    assert frame['Tension Length'].tolist() == ['1 / 2', '1', '2', None, None]
    assert manager.get_overlap_intervals('TWL', 'Mainline', 'UT').index[1].closed == 'neither'
    provider.verify_sources()
    manager.config_path.write_bytes(b'changed')
    with pytest.raises(MetadataCapabilityError, match='changed.*import again'):
        provider.verify_sources()


def test_landmark_points_buffer_once_and_explicit_ranges_stay_exact(tmp_path):
    manager = workbook(tmp_path)
    at = lambda x: manager.enrichment_evidence(x, 'TWL', 'Mainline', 'UT')
    for x in (400, 500, 600):
        assert at(x)['Landmark'] == 'Point landmark'
    assert at(399.99999)['Landmark'] is None
    assert at(600.00001)['Landmark'] is None
    for _ in range(2):  # Cached contexts must not expand [400,600] a second time.
        assert at(300)['Landmark'] is None
    assert at(800)['Landmark'] == 'Range landmark'
    assert at(850)['Landmark'] == 'Range landmark'
    assert at(799.999)['Landmark'] is None
    assert at(850.001)['Landmark'] is None


def test_multiple_landmarks_list_all_names_and_are_independent_from_tl_rows(tmp_path):
    rows = [[100, 200, 'A', None, None, None, None, 'Tangent', 0, 1000, None],
            [150, 250, 'B', None, None, None, None, None, None, None, None],
            [160, 180, 'A', None, None, None, None, None, None, None, None]]
    manager = workbook(tmp_path, rows)
    evidence = manager.enrichment_evidence(175, 'TWL', 'Mainline', 'UT')
    assert evidence['Landmark'] == 'A / B'
    assert evidence['landmark_status'] == 'matched'
    assert evidence['landmark_candidates'] == ['A', 'B']
    assert evidence['Tension Length'] is None
    mapped=manager.map_approved_enrichment(pd.DataFrame({'Chainage':[125.,175.,225.,300.]}),'TWL','Mainline','UT')
    assert mapped['Landmark'].tolist()==['A','A / B','B',None]


@pytest.mark.parametrize('column,value,message', [
    (3, float('inf'), 'finite ordered'), (4, -1, 'finite ordered'),
    (10, 'invalid', 'Interval Closed'), (5, 'Y', 'disagrees'),
    (0, None, 'finite ordered'), (2, None, 'name is required'),
])
def test_malformed_wide_values_do_not_silently_disappear(tmp_path, column, value, message):
    row = [500, 500, 'Point landmark', 0, 0, 'N', '1', 'Tangent', 0, 1000, 'both']
    # Excel cannot encode inf; use its literal representation, which the parser rejects.
    row[column] = 'inf' if value == float('inf') else value
    manager = workbook(tmp_path, [row])
    with pytest.raises(MetadataCapabilityError, match=message):
        manager.enrichment_evidence(0, 'TWL', 'Mainline', 'UT')


def test_drl_pl_uses_its_own_track_class_and_tl_sheet(tmp_path):
    manager = workbook(tmp_path, drl=True)
    assert manager._wide_context('DRL', 'PL', 'UT') == ('DRL', 'PL')
    assert manager.get_track_type_intervals('DRL', 'PL', 'UT')['Track Type'].tolist() == ['Curve']
    assert manager.get_exception_boundaries('DRL', 'UT', 'PL').index[0].left == 1000
    assert manager.get_exception_boundaries('DRL', 'UT', 'Mainline').index[0].left == 0
    assert manager.enrichment_evidence(1500, 'DRL', 'PL', 'UT')['Tension Length'] == 'PL-TL'
    assert manager.enrichment_evidence(1500, 'DRL', 'Mainline', 'UT')['Tension Length'] is None


def test_legacy_point_layout_keeps_existing_sidecar_fallback(tmp_path):
    manager = workbook(tmp_path)
    book = __import__('openpyxl').load_workbook(manager.config_path)
    book.remove(book['TWL UT'])
    sheet = book.create_sheet('TWL UT')
    sheet.append(['Track Type', 'Track Type FromM', 'Track Type ToM', None,
                  'Bracket FromM', 'Tension Length', 'Bracket'])
    sheet.append(['Tangent', 0, 1000, None, 0, '1', '1-001'])
    book.save(manager.config_path)
    from app.core.tov1050_approved_intervals import ApprovedIntervalProvider, VERSION
    provider = manager.approved_interval_provider()
    assert isinstance(provider, ApprovedIntervalProvider)
    assert manager.enrichment_evidence(5, 'TWL', 'Mainline', 'UT')['Tension Length'] is None
    lineage = dict(closed='both', approval_id='test', source_ids=['workbook'])
    document = dict(schema_version=VERSION, chainage_unit='m',
        sources={'workbook': dict(path=manager.config_path.name,
            sha256=hashlib.sha256(manager.config_path.read_bytes()).hexdigest())},
        approvals={'test': dict(approved_by='test', approved_at='2026-11-05', scope='test')},
        contexts=[dict(line='TWL', session='Mainline', direction='UT',
            tension_lengths=[dict(from_m=0, to_m=10, tension_length='legacy', wire_role='contact', **lineage)])])
    manager.config_path.with_suffix('.approved-intervals.json').write_text(json.dumps(document), encoding='utf-8')
    manager = TOV1050MetadataManager(manager.config_path)
    assert manager.enrichment_evidence(5, 'TWL', 'Mainline', 'UT')['Tension Length'] == 'legacy'


def test_wide_schema_and_direction_errors_are_explicit(tmp_path):
    manager = workbook(tmp_path)
    with pytest.raises(MetadataCapabilityError, match='missing wide enrichment sheet TWL DT'):
        manager.enrichment_evidence(5, 'TWL', 'Mainline', 'DT')
    book = __import__('openpyxl').load_workbook(manager.config_path)
    book['TWL UT'].cell(1, 11).value = 'Missing closure'
    book.save(manager.config_path)
    with pytest.raises(MetadataCapabilityError, match='incomplete wide enrichment columns: Interval Closed'):
        TOV1050MetadataManager(manager.config_path).approved_interval_provider()


def test_wide_capabilities_describe_listed_scopes_and_preserve_wear_gate(tmp_path, monkeypatch):
    manager = workbook(tmp_path)
    monkeypatch.setattr(manager, 'get_all_thresholds', lambda: pd.DataFrame({'threshold': [9.1]}))
    result = manager.get_capabilities('TWL', 'Mainline', 'UT')
    assert result['enrichment_source'] == 'wide_excel'
    assert result['enrichment_version'] == WideExcelEnrichmentProvider.version
    assert result['overlap_state'] == 'listed_tl_set'
    assert result['capabilities']['tension_length_intervals']['count'] == 5
    assert result['capabilities']['landmark_intervals']['count'] == 2
    with pytest.raises(MetadataCapabilityError, match='cannot authorize wear lookup'):
        manager.require_tension_length_intervals('TWL', 'UT', 'Mainline')


def test_corrected_bracket_positions_keep_explicit_classification_and_lineage(tmp_path):
    manager = workbook(tmp_path)
    book = __import__('openpyxl').load_workbook(manager.config_path)
    points = book.create_sheet('TWL UT Brackets')
    points.append(['Bracket FromM', 'Tension Length', 'Bracket', 'classification',
                   'wire_role', 'original_workbook', 'source_sheet', 'source_excel_row',
                   'source_bracket', 'component_index'])
    points.append([123, '1', '1-BWA', 'termination', 'contact', 'mapping.xlsx',
                   'TWL UT', 42, 'Original BWA', 2])
    points.append([125, '1', 'Unknown', None, None, None, None, None, None, None])
    provenance = book.create_sheet('__provenance__')
    provenance.append(['source_sheet', 'source_row', 'classification', 'components_json'])
    provenance.append(['TWL UT', 42, 'termination', json.dumps([
        {'from_m': 100, 'candidate_bracket': '1-BWA'}])])
    book.save(manager.config_path)
    manager = TOV1050MetadataManager(manager.config_path)
    frame = manager._point_frame('TWL', 'Mainline', 'UT')
    point = frame.iloc[0]
    assert point.chainage_m == 123
    assert point.classification == 'termination'
    assert point.wire_role == 'contact'
    assert point.source_workbook == 'mapping.xlsx'
    assert point.source_sheet == 'TWL UT'
    assert point.source_excel_row == 42
    assert point.source_bracket == 'Original BWA'
    assert point.component_index == 2
    assert frame.iloc[1].classification == 'unclassified'
    assert manager.get_bracket_points('TWL', 'Mainline', 'UT').bracket.tolist() == ['1-BWA']
