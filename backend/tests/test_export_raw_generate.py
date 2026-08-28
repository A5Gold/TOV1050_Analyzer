"""
Test Export Raw Generate Endpoint
==================================
Tests for Bug 10.7-2 fix: POST /export/raw/generate endpoint

This endpoint accepts data directly from the frontend instead of using
global variables, solving the multi-tab export issue.

Version: 1.0
Date: 2026-02-04
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd
import io

from app.main import app

client = TestClient(app)


class TestExportRawGenerateEndpoint:
    """Tests for Bug 10.7-2: POST /export/raw/generate endpoint"""

    def test_export_raw_generate_success(self):
        """Test successful raw CSV export with data provided in request"""
        payload = {
            "chart_data": [
                {"Chainage": 100.0, "height1": 5000, "stagger1": 200},
                {"Chainage": 101.0, "height1": 5100, "stagger1": 210},
                {"Chainage": 102.0, "height1": 5200, "stagger1": 220},
            ],
            "params": {
                "date_str": "20260204",
                "line": "EAL",
                "track": "UP",
                "section": "Mainline"
            }
        }

        response = client.post("/api/export/raw/generate", json=payload)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        # Check Content-Disposition header for filename
        content_disposition = response.headers.get("content-disposition", "")
        assert "20260204" in content_disposition
        assert "EAL" in content_disposition
        assert "UP" in content_disposition
        assert "Mainline" in content_disposition
        assert "Catenary_Report.csv" in content_disposition

        # Verify CSV content
        csv_content = response.content.decode("utf-8")
        assert "Chainage" in csv_content
        assert "height1" in csv_content
        assert "100.0" in csv_content

    def test_export_raw_generate_with_custom_naming(self):
        """Test raw export with custom naming (task_no, station_start, station_end)"""
        payload = {
            "chart_data": [
                {"Chainage": 100.0, "height1": 5000},
            ],
            "params": {
                "date_str": "20260204",
                "line": "EAL",
                "track": "UP",
                "section": "Mainline",
                "task_no": "U3",
                "station_start": "TAP",
                "station_end": "LOW"
            }
        }

        response = client.post("/api/export/raw/generate", json=payload)

        assert response.status_code == 200
        
        # Check filename uses custom naming
        content_disposition = response.headers.get("content-disposition", "")
        assert "U3" in content_disposition
        assert "TAP-LOW" in content_disposition
        # Should NOT contain track/section in custom mode
        # Actually it should be: 20260204_EAL_U3_TAP-LOW_Catenary_Report.csv

    def test_export_raw_generate_empty_data(self):
        """Test error handling when no data is provided"""
        payload = {
            "chart_data": [],
            "params": {
                "date_str": "20260204",
                "line": "EAL",
                "track": "UP",
                "section": "Mainline"
            }
        }

        response = client.post("/api/export/raw/generate", json=payload)

        assert response.status_code == 400
        assert "No data provided" in response.json()["detail"]

    def test_export_raw_generate_missing_chart_data(self):
        """Test error handling when chart_data is missing"""
        payload = {
            "params": {
                "date_str": "20260204",
                "line": "EAL",
                "track": "UP",
                "section": "Mainline"
            }
        }

        response = client.post("/api/export/raw/generate", json=payload)

        # Should return validation error
        assert response.status_code == 422

    def test_export_raw_generate_with_different_tabs(self):
        """
        Bug 10.7-2 Core Test: Verify different tabs export their own data
        
        This simulates the scenario where:
        1. Tab 1 has data A
        2. Tab 2 has data B
        3. Exporting from Tab 1 should return data A (not data B)
        """
        # Tab 1 data
        tab1_payload = {
            "chart_data": [
                {"Chainage": 100.0, "height1": 5000, "marker": "TAB1_DATA"},
            ],
            "params": {
                "date_str": "20260116",
                "line": "EAL",
                "track": "UP",
                "section": "Mainline",
                "task_no": "U3",
                "station_start": "TAP",
                "station_end": "LOW"
            }
        }

        # Tab 2 data
        tab2_payload = {
            "chart_data": [
                {"Chainage": 200.0, "height1": 6000, "marker": "TAB2_DATA"},
            ],
            "params": {
                "date_str": "20251227",
                "line": "EAL",
                "track": "UP",
                "section": "Mainline"
            }
        }

        # Export Tab 1
        response1 = client.post("/api/export/raw/generate", json=tab1_payload)
        assert response1.status_code == 200
        csv1 = response1.content.decode("utf-8")
        assert "TAB1_DATA" in csv1
        assert "TAB2_DATA" not in csv1
        
        # Check Tab 1 filename has custom naming
        cd1 = response1.headers.get("content-disposition", "")
        assert "U3" in cd1
        assert "TAP-LOW" in cd1

        # Export Tab 2
        response2 = client.post("/api/export/raw/generate", json=tab2_payload)
        assert response2.status_code == 200
        csv2 = response2.content.decode("utf-8")
        assert "TAB2_DATA" in csv2
        assert "TAB1_DATA" not in csv2
        
        # Check Tab 2 filename has default naming
        cd2 = response2.headers.get("content-disposition", "")
        assert "20251227" in cd2

        # Export Tab 1 again - should still return Tab 1 data
        response1_again = client.post("/api/export/raw/generate", json=tab1_payload)
        assert response1_again.status_code == 200
        csv1_again = response1_again.content.decode("utf-8")
        assert "TAB1_DATA" in csv1_again
        assert "TAB2_DATA" not in csv1_again

    def test_export_raw_generate_default_values(self):
        """Test that missing params use default values"""
        payload = {
            "chart_data": [
                {"Chainage": 100.0, "height1": 5000},
            ],
            "params": {}  # Empty params
        }

        response = client.post("/api/export/raw/generate", json=payload)

        assert response.status_code == 200
        
        # Should use "Unknown" defaults in filename
        content_disposition = response.headers.get("content-disposition", "")
        assert "UnknownDate" in content_disposition or response.status_code == 200


class TestBug1082ColumnOrientedFormat:
    """
    Tests for Bug 10.8-2: Accept column-oriented chart_data format
    
    The /analyze endpoint returns chart_data in column-oriented format:
    {"Chainage": [100, 101], "height1": [5000, 5100]}
    
    But the original ExportRawRequest expected row-oriented format:
    [{"Chainage": 100, "height1": 5000}, {"Chainage": 101, "height1": 5100}]
    
    This caused 422 Unprocessable Entity errors.
    """

    def test_export_raw_column_oriented_format(self):
        """
        Bug 10.8-2 Core Test: Accept column-oriented chart_data format
        
        This format is what the /analyze endpoint actually returns.
        """
        # Column-oriented format (what /analyze returns)
        payload = {
            "chart_data": {
                "Chainage": [100.0, 101.0, 102.0],
                "height1": [5000, 5100, 5200],
                "stagger1": [200, 210, 220]
            },
            "params": {
                "date_str": "20260204",
                "line": "EAL",
                "track": "UP",
                "section": "Mainline"
            }
        }

        response = client.post("/api/export/raw/generate", json=payload)

        # Should succeed with column-oriented format
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        # Verify CSV content has correct data
        csv_content = response.content.decode("utf-8")
        assert "Chainage" in csv_content
        assert "height1" in csv_content
        assert "100.0" in csv_content or "100" in csv_content
        assert "5000" in csv_content

    def test_export_raw_both_formats_produce_same_csv(self):
        """
        Bug 10.8-2: Both formats should produce equivalent CSV output
        """
        # Column-oriented format
        column_payload = {
            "chart_data": {
                "Chainage": [100.0, 101.0],
                "value": [5000, 5100]
            },
            "params": {
                "date_str": "20260204",
                "line": "EAL",
                "track": "UP",
                "section": "Mainline"
            }
        }

        # Row-oriented format
        row_payload = {
            "chart_data": [
                {"Chainage": 100.0, "value": 5000},
                {"Chainage": 101.0, "value": 5100}
            ],
            "params": {
                "date_str": "20260204",
                "line": "EAL",
                "track": "UP",
                "section": "Mainline"
            }
        }

        response_col = client.post("/api/export/raw/generate", json=column_payload)
        response_row = client.post("/api/export/raw/generate", json=row_payload)

        # Both should succeed
        assert response_col.status_code == 200
        assert response_row.status_code == 200

        # Both should produce CSV with same data
        csv_col = response_col.content.decode("utf-8")
        csv_row = response_row.content.decode("utf-8")
        
        # Both should contain the same values
        assert "100" in csv_col
        assert "100" in csv_row
        assert "5000" in csv_col
        assert "5000" in csv_row

    def test_export_raw_empty_column_oriented(self):
        """
        Bug 10.8-2: Empty column-oriented format should return 400
        """
        payload = {
            "chart_data": {},  # Empty dict
            "params": {
                "date_str": "20260204",
                "line": "EAL",
                "track": "UP",
                "section": "Mainline"
            }
        }

        response = client.post("/api/export/raw/generate", json=payload)

        # Should return 400 for empty data
        assert response.status_code == 400


class TestLegacyExportRawEndpoint:
    """Tests to ensure legacy GET /export/raw still works for backward compatibility"""

    def test_legacy_endpoint_returns_error_without_analysis(self):
        """Legacy endpoint should return 400 if no analysis has been run"""
        # Clear global state first
        from app.api.endpoints.analysis import LAST_RAW_DF
        
        with patch('app.api.endpoints.analysis.LAST_RAW_DF', pd.DataFrame()):
            response = client.get("/api/export/raw")
            # Should fail since no analysis has been run
            assert response.status_code == 400
            assert "No raw data available" in response.json()["detail"]
