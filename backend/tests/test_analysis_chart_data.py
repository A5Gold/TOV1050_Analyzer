import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd
from app.main import app
import app.api.endpoints.analysis as analysis_endpoint

client = TestClient(app)

class TestAnalysisChartData:
    def test_chart_data_uses_client_session_snapshot(self, monkeypatch):
        first = pd.DataFrame({'Chainage': [100.0], 'height1': [1.0]})
        second = pd.DataFrame({'Chainage': [900.0], 'height1': [9.0]})
        monkeypatch.setattr(analysis_endpoint, 'ANALYSIS_SESSIONS', {
            'tab-a': {'raw_df': first, 'source_path': r'C:\\data\\first.csv'},
            'tab-b': {'raw_df': second, 'source_path': r'C:\\data\\second.csv'},
        })

        response_a = client.get('/api/analyze/chart-data', params={
            'client_session_id': 'tab-a', 'from_m': 0, 'to_m': 1000, 'max_points': 500,
        })
        response_b = client.get('/api/analyze/chart-data', params={
            'client_session_id': 'tab-b', 'from_m': 0, 'to_m': 1000, 'max_points': 500,
        })

        assert response_a.status_code == 200
        assert response_b.status_code == 200
        assert response_a.json()['chart_data']['Chainage'] == [100.0]
        assert response_b.json()['chart_data']['Chainage'] == [900.0]

    @patch('app.api.endpoints.analysis.DataLoader')
    @patch('app.api.endpoints.analysis.MetadataManager')
    @patch('app.api.endpoints.analysis.ExceptionDetector')
    @patch('pathlib.Path.exists')
    def test_chart_data_includes_metadata_and_computed(self, mock_exists, MockDetector, MockMeta, MockLoader):
        mock_exists.return_value = True
        
        # Mock DataFrame
        df = pd.DataFrame({
            'Chainage': [100, 101],
            'height1': [5000, 5000],
            'stagger1': [200, 200],
            'wear1': [10, 10],
            'stg_max': [200, 200], # Computed
            'stg_min': [-200, -200], # Computed
            'Track Type': ['Tangent', 'Tangent'], # Metadata
            'Class': ['MOL', 'MOL'] # Metadata
        })
        
        mock_loader_instance = MockLoader.return_value
        mock_loader_instance.load_data.return_value = df
        
        mock_detector_instance = MockDetector.return_value
        mock_detector_instance.analyze.return_value = ({}, pd.DataFrame()) # Empty results
        
        payload = {
            "file_path": "test.datac",
            "line": "EAL",
            "section": "Mainline",
            "track": "UP",
            "date_str": "20260209",
            "task_no": "T1",
            "station_start": "A",
            "station_end": "B"
        }
        
        response = client.post("/api/analyze", json=payload)
        
        assert response.status_code == 200
        res = response.json()
        chart_data = res["chart_data"]
        
        # Check for new columns
        assert "Track Type" in chart_data
        assert "Class" in chart_data
        assert "stg_max" in chart_data
        assert "stg_min" in chart_data
        
        # Check Task Run Data injection
        assert "task_no" in chart_data
        assert chart_data["task_no"] == ["T1", "T1"]
        assert "station_start" in chart_data
        assert chart_data["station_start"] == ["A", "A"]

    @patch('app.api.endpoints.analysis.TOV1050DataLoader')
    @patch('app.api.endpoints.analysis.DataLoader')
    @patch('pathlib.Path.exists')
    def test_chart_data_reload_is_scoped_to_requested_file(self, mock_exists, MockLoader, MockTovLoader, monkeypatch):
        mock_exists.return_value = True
        cached = pd.DataFrame({'Chainage': [100.0], 'height1': [1.0]})
        requested = pd.DataFrame({'Chainage': [900.0], 'height1': [9.0]})
        monkeypatch.setattr(analysis_endpoint, 'LAST_RAW_DF', cached)
        monkeypatch.setattr(analysis_endpoint, 'LAST_ANALYSIS_SOURCE_PATH', r'C:\data\first.csv')
        MockTovLoader.return_value.load_data.return_value = requested

        response = client.get(
            '/api/analyze/chart-data',
            params={
                'file_path': r'C:\data\second.csv',
                'line': 'AEL',
                'from_m': 0,
                'to_m': 1000,
                'max_points': 500,
            },
        )

        assert response.status_code == 200
        assert response.json()['chart_data']['Chainage'] == [900.0]
        MockTovLoader.return_value.load_data.assert_called_once()
