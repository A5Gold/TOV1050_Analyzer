import gc
import io
import weakref
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.api.endpoints import analysis as api


def test_median_snapshot_cannot_request_raw_or_export_frontend_payload(monkeypatch):
    frame = pd.DataFrame({'Chainage': [9142.], 'height1': [5000.], 'group_id': [0]})
    state = {'analysis_mode': 'median', 'analysis_revision': 'r', 'analysis_df': frame,
             'results': {}, 'params': {'line': 'TWL'}, 'aggregation_metadata': {'algorithm': 'test'}}
    monkeypatch.setattr(api, 'ANALYSIS_SESSIONS', {'a': state})
    observed = []
    def export(results, chart_df, **kwargs):
        import io
        observed.append((results, chart_df, kwargs))
        return io.BytesIO(b'excel')
    monkeypatch.setattr(api, 'export_analysis_report', export)
    with TestClient(app) as client:
        assert client.get('/api/analyze/chart-data', params={'client_session_id': 'a',
            'analysis_revision': 'r', 'chart_data_mode': 'raw'}).status_code == 409
        assert client.get('/api/analyze/chart-data', params={'client_session_id': 'a',
            'analysis_revision': 'r', 'chart_data_mode': 'chainage_median'}).status_code == 200
        response = client.post('/api/export/report/generate', json={'client_session_id': 'a',
            'params': {'line': 'TWL', 'session': 'Mainline'}, 'exceptions': {'fake': []}, 'chart_data': {'height1': [1]}})
        assert response.status_code == 200
        assert observed[0][0] is state['results'] and observed[0][1] is frame
        assert observed[0][2]['metadata']['algorithm'] == 'test'


@pytest.mark.parametrize('capabilities', [None, {'capabilities': {}},
    {'enrichment_version': 'wide-excel-enrichment-2026-11-05-v1'}])
def test_tov1050_report_routes_use_median_but_raw_csv_reloads_source(monkeypatch, tmp_path, capabilities):
    raw = pd.DataFrame({'Chainage': [100., 100., 101.], 'height1': [1., 5., 9.]})
    median = raw.iloc[[0, 2]].copy()
    results = {'High Height': pd.DataFrame({'maxLocation': [100.], 'maxValue': [5.]})}
    params = {'line': 'TWL', 'track': 'UT', 'section': 'Mainline', 'session': 'Mainline',
              'date_str': '20260907', 'station_start': 'CEN', 'station_end': 'TSW'}
    state = {'analysis_mode': 'median', 'analysis_revision': 'r', 'analysis_df': median,
             'source_path': 'source.csv', 'results': results, 'params': params,
             'aggregation_metadata': {'detection_algorithm': 'cleaned_raw_signed_stagger_v1',
                                      'detection_data_mode': 'cleaned_raw',
                                      'detection_points': 3, 'representative_points': 2}}
    state['metadata_capabilities'] = capabilities
    monkeypatch.setattr(api, 'ANALYSIS_SESSIONS', {'tab': state})
    monkeypatch.setattr(api, 'LAST_ANALYSIS_SNAPSHOT', state)
    monkeypatch.setattr(api, 'LAST_ANALYSIS_RESULTS', results)
    monkeypatch.setattr(api, 'LAST_ANALYSIS_PARAMS', params)
    monkeypatch.setattr(api, 'LAST_METADATA_CAPABILITIES', capabilities)
    reloads, observed = [], []
    def reload(snapshot):
        reloads.append(snapshot)
        return raw
    def export(actual_results, chart_df=None, metadata=None, output_path=None, **kwargs):
        observed.append((actual_results, chart_df, metadata))
        if output_path:
            Path(output_path).write_bytes(b'excel')
        return io.BytesIO(b'excel')
    monkeypatch.setattr(api, '_reload_cleaned_source', reload)
    monkeypatch.setattr(api, 'export_analysis_report', export)
    with TestClient(app) as client:
        response = client.post('/api/export/report/generate', json={
            'client_session_id': 'tab', 'params': params, 'exceptions': {},
            'chart_data': {'Chainage': [100.]}})
        assert response.status_code == 200, response.text
        assert client.get('/api/export/report').status_code == 200
        raw_response = client.post('/api/export/raw/generate', json={
            'client_session_id': 'tab', 'params': params})
        assert raw_response.status_code == 200, raw_response.text
        assert raw_response.content.decode('utf-8').count('\n') == len(raw) + 1
    job = SimpleNamespace(path=None, filename=None)
    context = SimpleNamespace(progress=lambda *args: None, output_path=lambda: tmp_path / 'job.xlsx',
                              check_cancelled=lambda: None, job=job)
    api._export_job_work(state, 'chainage_median')(context)
    assert len(observed) == 3
    assert all(item[0] is results and item[1] is median for item in observed)
    assert all(item[2]['detection_data_mode'] == 'cleaned_raw'
               and item[2]['export_data_mode'] == 'chainage_median'
               and item[2]['raw_row_count'] == 3
               and item[2]['chart_row_count'] == 2 for item in observed)
    assert reloads == [state]
    expected = capabilities.get('enrichment_version', 'tov640-first-nonempty-v1') if capabilities else None
    assert all(item[2].get('enrichment_version') == expected for item in observed)


@pytest.mark.parametrize('line', ['EAL', 'TML'])
def test_tov640_report_keeps_full_frame(line, monkeypatch):
    raw = pd.DataFrame({'Chainage': [100., 100., 101.], 'height1': [1., 5., 9.]})
    state = {'analysis_mode': 'median', 'analysis_df': raw.iloc[:2],
             'source_path': 'source.datac', 'params': {'line': line}}
    monkeypatch.setattr(api, '_reload_cleaned_source', lambda snapshot: raw)
    assert api._report_chart_frame(state) is raw
    assert api._report_chart_metadata(state, raw)['export_data_mode'] == 'cleaned_raw'


def test_missing_tov1050_median_never_falls_back_to_raw(monkeypatch):
    state = {'analysis_mode': 'median', 'source_path': 'source.csv',
             'raw_df': pd.DataFrame({'Chainage': [1.]}), 'params': {'line': 'TWL'}}
    monkeypatch.setattr(api, '_reload_cleaned_source', lambda snapshot: pytest.fail('raw fallback'))
    with pytest.raises(HTTPException) as error:
        api._report_chart_frame(state)
    assert error.value.status_code == 410


def test_raw_overview_all_report_routes_and_csv_are_guarded(monkeypatch):
    state = {'analysis_mode': 'raw_overview', 'analysis_revision': 'r', 'source_path': 'x',
             'params': {}, 'results': {}, 'overview_payload': {'Chainage': [1]},
             'overview_resolution': {'strategy': 'raw'}}
    monkeypatch.setattr(api, 'ANALYSIS_SESSIONS', {'a': state})
    monkeypatch.setattr(api, 'LAST_ANALYSIS_SNAPSHOT', state)
    with TestClient(app) as client:
        assert client.get('/api/export/report').status_code == 403
        assert client.get('/api/export/raw').status_code == 403
        for path, body in [('/api/export/report/jobs', {'client_session_id': 'a', 'analysis_revision': 'r'}),
                           ('/api/export/report/generate', {'client_session_id': 'a', 'exceptions': {}, 'params': {}}),
                           ('/api/export/raw/generate', {'client_session_id': 'a', 'params': {}})]:
            assert client.post(path, json=body).status_code == 403
        overview = client.get('/api/analyze/chart-data', params={'client_session_id': 'a',
            'analysis_revision': 'r', 'chart_data_mode': 'raw'})
        assert overview.status_code == 200 and overview.json()['chart_data']['Chainage'] == [1]


def test_overview_source_digest_change_rejected(tmp_path):
    source = tmp_path / 'test.csv'
    source.write_text('old')
    state = {'source_path': str(source), 'source_sha256': api._file_digest(source), 'params': {}}
    source.write_text('changed')
    with pytest.raises(HTTPException) as error:
        api._reload_overview_source(state)
    assert error.value.status_code == 409


def test_reduction_does_not_retain_raw_frame():
    from app.core.chainage_reduction import reduce_chainage
    raw = pd.DataFrame({'Chainage': [1., 1., 2.], 'height1': [4., 8., 9.]})
    reference = weakref.ref(raw)
    representative, metadata = reduce_chainage(raw)
    del raw
    gc.collect()
    assert reference() is None
    assert len(representative) == 2 and metadata['raw_points'] == 3
