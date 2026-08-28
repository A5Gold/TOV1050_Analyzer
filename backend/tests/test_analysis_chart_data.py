import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd
from app.main import app

client = TestClient(app)

class TestAnalysisChartData:
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
