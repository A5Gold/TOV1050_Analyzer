import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from pathlib import Path
from app.main import app
from app.api.endpoints import analysis as analysis_endpoint

client = TestClient(app)

REFERENCE_SAMPLE = (
    Path(__file__).resolve().parents[2]
    / "docs" / "TOV1050_Migration" / "Raw data" / "AEL"
    / "20260822_AEL_UT_SHO_AWE.csv"
)
REFERENCE_CONFIG = Path(__file__).resolve().parents[2] / "config"

class TestAnalysisAPI:
    """Tests for Story 1.5: Dashboard Visualization Data Contract"""

    @pytest.fixture
    def mock_components(self):
        """Mock all core components used in the endpoint"""
        with patch('app.api.endpoints.analysis.DataLoader') as MockLoader, \
             patch('app.api.endpoints.analysis.MetadataManager') as MockMeta, \
             patch('app.api.endpoints.analysis.ExceptionDetector') as MockDetector, \
             patch('pathlib.Path.exists') as MockExists:
            
            # Setup mocks
            MockExists.return_value = True # Assume all files exist
            
            # Mock Data
            mock_df = pd.DataFrame({
                'Chainage': [100.0, 101.0, 102.0],
                'height1': [4500, 5000, 5500],
                'stagger1': [200, 300, 400],
                'wear1': [10, 11, 12]
            })
            MockLoader.return_value.load_data.return_value = mock_df
            
            # Mock Analysis Results
            mock_exceptions = {
                'Low Height': pd.DataFrame([{
                    'id': 'LH1', 'FromM': 100, 'ToM': 101, 
                    'level': 'L1', 'maxValue': 4500, 'maxLocation': 100.5
                }])
            }
            mock_boundaries = pd.DataFrame([{
                'Class': 'Mainline', 'FromM': 0, 'ToM': 1000
            }])
            
            MockDetector.return_value.analyze.return_value = (mock_exceptions, mock_boundaries)
            
            yield {
                'loader': MockLoader,
                'detector': MockDetector
            }

    def test_analyze_endpoint_success(self, mock_components):
        """Test happy path for /analyze -> Verifies AC1, AC2, AC3 data structure"""
        payload = {
            "file_path": "dummy.datac",
            "line": "EAL",
            "section": "Mainline",
            "track": "UP",
            "date_str": "20251212"
        }
        
        response = client.post("/api/analyze", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        
        # AC1: Chart Data (Column-oriented)
        assert 'chart_data' in data
        chart_data = data['chart_data']
        assert 'Chainage' in chart_data
        assert 'height1' in chart_data
        assert isinstance(chart_data['Chainage'], list)
        assert len(chart_data['Chainage']) == 3
        
        # AC2/AC3: Exceptions (Records)
        assert 'exceptions' in data
        exceptions = data['exceptions']
        assert 'Low Height' in exceptions
        assert len(exceptions['Low Height']) == 1
        assert exceptions['Low Height'][0]['level'] == 'L1'
        
        # Boundaries
        assert 'boundaries' in data
        assert len(data['boundaries']) == 1

    def test_file_not_found(self):
        """Test error handling"""
        # Patch exists to return False
        with patch('pathlib.Path.exists', return_value=False):
            payload = {
                "file_path": "non_existent.datac",
                "line": "EAL",
                "section": "Mainline",
                "track": "UP",
                "date_str": "20251212"
            }
            response = client.post("/api/analyze", json=payload)
            assert response.status_code == 404

    def test_missing_chainage_returns_400(self):
        """Test: Missing Chainage column returns 400 with helpful error message."""
        with patch('app.api.endpoints.analysis.DataLoader') as MockLoader, \
             patch('pathlib.Path.exists') as MockExists:
            
            MockExists.return_value = True
            
            # Mock DataFrame without Chainage (missing KM column)
            mock_df = pd.DataFrame({
                'LOCATION': [100.50, 100.55],
                'Line': ['EAL', 'EAL'],
                'Track': ['UP', 'UP'],
                'stagger1': [10, 15],
                'height1': [5300, 5301]
            })
            MockLoader.return_value.load_data.return_value = mock_df
            
            payload = {
                "file_path": "bad_file.datac",
                "line": "EAL",
                "section": "Mainline",
                "track": "UP",
                "date_str": "20251212"
            }
            response = client.post("/api/analyze", json=payload)
            
            assert response.status_code == 400
            data = response.json()
            assert 'KM' in data['detail']  # Error message should mention missing column

    def test_empty_dataframe_returns_400(self):
        """Test: Empty DataFrame returns 400 with helpful error message."""
        with patch('app.api.endpoints.analysis.DataLoader') as MockLoader, \
             patch('pathlib.Path.exists') as MockExists:
            
            MockExists.return_value = True
            
            # Mock empty DataFrame
            mock_df = pd.DataFrame()
            MockLoader.return_value.load_data.return_value = mock_df
            
            payload = {
                "file_path": "empty_file.datac",
                "line": "EAL",
                "section": "Mainline",
                "track": "UP",
                "date_str": "20251212"
            }
            response = client.post("/api/analyze", json=payload)
            
            assert response.status_code == 400
            data = response.json()
            assert 'empty' in data['detail'].lower()


def test_tov1050_reference_sample_contract(monkeypatch):
    """The real TOV1050 sample exercises CSV cleaning, metadata and exports."""
    monkeypatch.setattr(analysis_endpoint, "CONFIG_DIR", REFERENCE_CONFIG)

    response = client.post(
        "/api/analyze",
        json={
            "file_path": str(REFERENCE_SAMPLE),
            "line": "AEL",
            "section": "Mainline",
            "session": "Mainline",
            "track": "UT",
            "date_str": "20260822",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    summary = payload["cleaning_summary"]
    assert summary["raw_row_count"] == 476
    assert summary["retained_row_count"] == 276
    assert summary["trimmed_leading_count"] == 100
    assert summary["trimmed_trailing_count"] == 100
    assert summary["io_value_count"] == 3309
    assert payload["params"]["session"] == "Mainline"
    assert payload["params"]["station_start"] == "SHO"
    assert payload["params"]["station_end"] == "AWE"
    assert payload["chart_data"]["Chainage"]

    export = client.get("/api/export/report")
    assert export.status_code == 200
    assert "20260822_AEL_UT_MAINLINE_SHO_AWE_Exception_Report.xlsx" in export.headers["content-disposition"]


def test_tov1050_analysis_ignores_noncanonical_input_basename(monkeypatch):
    """Operational CSV basenames must not override complete form context."""
    monkeypatch.setattr(analysis_endpoint, "CONFIG_DIR", REFERENCE_CONFIG)
    monkeypatch.setattr(
        analysis_endpoint,
        "parse_input_filename",
        lambda _path: (_ for _ in ()).throw(ValueError("non-canonical basename")),
    )

    response = client.post(
        "/api/analyze",
        json={
            "file_path": str(REFERENCE_SAMPLE),
            "line": "AEL",
            "section": "Mainline",
            "session": "Mainline",
            "track": "UT",
            "date_str": "20260822",
            "station_start": "SHO",
            "station_end": "AWE",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["params"]["station_start"] == "SHO"


@pytest.mark.parametrize(
    ("field", "value"),
    [("session", "TKS"), ("track", "SIDE")],
)
def test_tov1050_rejects_invalid_session_or_direction(monkeypatch, field, value):
    monkeypatch.setattr(analysis_endpoint, "CONFIG_DIR", REFERENCE_CONFIG)
    payload = {
        "file_path": str(REFERENCE_SAMPLE),
        "line": "AEL",
        "section": "Mainline",
        "session": "Mainline",
        "track": "UT",
        "date_str": "20260822",
    }
    payload[field] = value

    response = client.post("/api/analyze", json=payload)

    assert response.status_code == 400


@pytest.mark.parametrize("suffix", [".csv", ".datac"])
def test_selected_context_overrides_source_labels_in_analysis_and_all_exports(tmp_path, suffix):
    """Real parsers/detector/exporters must use form context, never file labels."""
    import io
    from openpyxl import load_workbook
    path = tmp_path / ("operational" + suffix)
    if suffix == ".csv":
        source = pd.read_csv(REFERENCE_SAMPLE)
        source["Line"] = "ORANGE LINE"
        source["HeightWire1 [mm]"] = 3500.123456
        source.to_csv(path, index=False)
    else:
        pd.DataFrame({
            "LINE": ["GREEN LINE"] * 80, "TRACK": ["DN"] * 80,
            "KM": [48] * 80, "LOCATION": [430.2 + i * .1 for i in range(80)],
            "WHGT1c": [-1799.876544] * 80, "STG1c": [0] * 80, "RWH1mm": [10] * 80,
        }).to_csv(path, index=False, sep=";")
    session_id = "context-override" + suffix
    response = client.post("/api/analyze", json={
        "file_path": str(path), "line": " ael ", "section": "Mainline", "track": "ut",
        "date_str": "20261023", "station_start": "SHO", "station_end": "AWE",
        "client_session_id": session_id,
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["params"]["line"] == "AEL" and payload["params"]["track"] == "UT"
    exceptions = [row for rows in payload["exceptions"].values() for row in rows]
    assert exceptions
    assert all(row["line"] == "AEL" and row["track"] == "UT" for row in exceptions)
    frame = analysis_endpoint.ANALYSIS_SESSIONS[session_id]["raw_df"]
    assert set(frame.Line) == set(frame.line) == {"AEL"}
    assert set(frame.Track) == set(frame.track) == {"UT"}
    assert set(frame.source_line) == {"ORANGE LINE" if suffix == ".csv" else "GREEN LINE"}
    if suffix == ".datac":
        assert set(frame.source_track) == {"DN"}
    export_payload = dict(params=payload["params"], exceptions=payload["exceptions"],
                          chart_data={}, client_session_id=session_id)
    for report in (client.get("/api/export/report"), client.post("/api/export/report/generate", json=export_payload)):
        assert report.status_code == 200, report.text
        assert "AEL_UT_" in report.headers["content-disposition"]
        book = load_workbook(io.BytesIO(report.content), read_only=True)
        for sheet in book:
            if sheet.title == "_Metadata":
                continue
            rows = iter(sheet.values)
            headers = next(rows)
            for row in rows:
                assert row[headers.index("line" if sheet.title == "ChartData" else "Line")] == "AEL"
                assert row[headers.index("track" if sheet.title == "ChartData" else "Track")] == "UT"
        book.close()
    raw = client.post("/api/export/raw/generate", json=export_payload)
    assert raw.status_code == 200
    exported = pd.read_csv(io.BytesIO(raw.content))
    assert set(exported.line) == {"AEL"} and set(exported.track) == {"UT"}
    pd.testing.assert_series_equal(exported.height1, frame.height1, check_names=False, atol=1e-9, rtol=0)
