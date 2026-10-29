import gc
import weakref

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
