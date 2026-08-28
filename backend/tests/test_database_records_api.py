"""
TOV640 Analyzer - Database Records API Tests
=============================================
Tests for Database Record module API endpoints.

TDD: These tests are written BEFORE the implementation.

Endpoints tested:
Sub-module 1: Exception Records (Single Run)
- POST   /api/database/exception-records        - Save exception records
- GET    /api/database/exception-records        - Query exception records
- DELETE /api/database/exception-records/{id}   - Delete single record
- GET    /api/database/exception-records/export - Export to Excel

Sub-module 2: Repeated Exception Records
- POST   /api/database/repeated-records                - Save repeated records
- GET    /api/database/repeated-records                - Query repeated records
- PATCH  /api/database/repeated-records/{record_id}   - Update workflow fields
- DELETE /api/database/repeated-records/{record_id}   - Delete record
- GET    /api/database/repeated-records/export        - Export to Excel
"""

import pytest
import uuid
import io
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import sys
from pathlib import Path

# Add backend/app to path for imports
backend_path = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(backend_path))


@pytest.mark.skip(reason="Sub-module 1 is deprecated")
class TestExceptionRecordsAPI:
    """Test suite for Sub-module 1: Exception Records API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_client(self, test_client: TestClient):
        """Setup test client for each test."""
        self.client = test_client
    
    # =========================================================================
    # POST /api/database/exception-records - Save Exception Records
    # =========================================================================
    
    def test_save_exception_records_returns_200(self):
        """
        POST /api/database/exception-records should save records and return success.
        """
        request_data = {
            "line": "EAL",
            "track": "UP",
            "section": "Mainline",
            "date_str": "20260130",
            "exceptions": {
                "Low Height": [
                    {
                        "id": str(uuid.uuid4()),
                        "exception type": "Low Height",
                        "level": "L1",
                        "FromM": 1000.5,
                        "ToM": 1005.2,
                        "length": 4.7,
                        "maxValue": 4850,
                        "maxLocation": 1002.3,
                        "Track Type": "Mainline",
                        "Section": "Mainline"
                    }
                ]
            }
        }
        
        response = self.client.post("/api/database/exception-records", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "saved_count" in data
        assert data["saved_count"] >= 1
    
    def test_save_exception_records_with_optional_fields(self):
        """
        POST /api/database/exception-records should accept optional fields.
        """
        request_data = {
            "line": "EAL",
            "track": "UP",
            "section": "Mainline",
            "date_str": "20260130",
            "task_no": "U1",
            "station_start": "HUH",
            "station_end": "RAC",
            "saved_by": "TestUser",
            "exceptions": {
                "Low Height": [
                    {
                        "id": str(uuid.uuid4()),
                        "exception type": "Low Height",
                        "level": "L2",
                        "FromM": 2000.0,
                        "ToM": 2010.0,
                        "Section": "Mainline"
                    }
                ]
            }
        }
        
        response = self.client.post("/api/database/exception-records", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_save_exception_records_empty_returns_400(self):
        """
        POST /api/database/exception-records with empty exceptions should return 400.
        """
        request_data = {
            "line": "EAL",
            "track": "UP",
            "section": "Mainline",
            "date_str": "20260130",
            "exceptions": {}
        }
        
        response = self.client.post("/api/database/exception-records", json=request_data)
        
        assert response.status_code == 400
    
    def test_save_exception_records_missing_required_returns_422(self):
        """
        POST /api/database/exception-records without required fields should return 422.
        """
        request_data = {
            "line": "EAL",
            # Missing: track, section, date_str, exceptions
        }
        
        response = self.client.post("/api/database/exception-records", json=request_data)
        
        assert response.status_code == 422
    
    # =========================================================================
    # GET /api/database/exception-records - Query Exception Records
    # =========================================================================
    
    def test_get_exception_records_returns_200(self, saved_exception_records):
        """
        GET /api/database/exception-records should return list of records.
        """
        response = self.client.get("/api/database/exception-records")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "records" in data
        assert "total" in data
        assert isinstance(data["records"], list)
    
    def test_get_exception_records_with_line_filter(self, saved_exception_records):
        """
        GET /api/database/exception-records?line=EAL should filter by line.
        """
        response = self.client.get("/api/database/exception-records", params={"line": "EAL"})
        
        assert response.status_code == 200
        data = response.json()
        
        for record in data["records"]:
            assert record["line"] == "EAL"
    
    def test_get_exception_records_with_level_filter(self, saved_exception_records):
        """
        GET /api/database/exception-records?level=L1 should filter by level.
        """
        response = self.client.get("/api/database/exception-records", params={"level": "L1"})
        
        assert response.status_code == 200
        data = response.json()
        
        for record in data["records"]:
            assert record["level"] == "L1"
    
    def test_get_exception_records_with_date_range(self, saved_exception_records):
        """
        GET /api/database/exception-records?date_from=20260101&date_to=20260131 should filter by date.
        """
        response = self.client.get(
            "/api/database/exception-records",
            params={"date_from": "20260101", "date_to": "20260131"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for record in data["records"]:
            assert "20260101" <= record["date_str"] <= "20260131"
    
    def test_get_exception_records_with_limit(self, saved_exception_records):
        """
        GET /api/database/exception-records?limit=5 should limit results.
        """
        response = self.client.get("/api/database/exception-records", params={"limit": 5})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["records"]) <= 5
    
    def test_get_exception_records_structure(self, saved_exception_records):
        """
        Exception records should have all required fields.
        """
        response = self.client.get("/api/database/exception-records")
        
        assert response.status_code == 200
        data = response.json()
        
        if data["records"]:
            record = data["records"][0]
            # Required fields
            assert "id" in record
            assert "exception_type" in record
            assert "level" in record
            assert "from_m" in record
            assert "to_m" in record
            assert "line" in record
            assert "track" in record
            assert "date_str" in record
            assert "saved_at" in record
    
    # =========================================================================
    # DELETE /api/database/exception-records/{id} - Delete Exception Record
    # =========================================================================
    
    def test_delete_exception_record_returns_200(self, saved_exception_records):
        """
        DELETE /api/database/exception-records/{id} should delete record successfully.
        """
        record_id = saved_exception_records["record_ids"][0]
        
        response = self.client.delete(f"/api/database/exception-records/{record_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_delete_exception_record_not_found_returns_404(self):
        """
        DELETE /api/database/exception-records/{non_existent_id} should return 404.
        """
        non_existent_id = str(uuid.uuid4())
        
        response = self.client.delete(f"/api/database/exception-records/{non_existent_id}")
        
        assert response.status_code == 404
    
    def test_delete_exception_record_actually_removes(self, saved_exception_records):
        """
        After DELETE, record should no longer exist in GET results.
        """
        record_id = saved_exception_records["record_ids"][0]
        
        # Delete
        self.client.delete(f"/api/database/exception-records/{record_id}")
        
        # Verify removed
        response = self.client.get("/api/database/exception-records")
        data = response.json()
        
        record_ids = [r["id"] for r in data["records"]]
        assert record_id not in record_ids
    
    # =========================================================================
    # GET /api/database/exception-records/export - Export to Excel
    # =========================================================================
    
    def test_export_exception_records_returns_excel(self, saved_exception_records):
        """
        GET /api/database/exception-records/export should return Excel file.
        """
        response = self.client.get("/api/database/exception-records/export")
        
        assert response.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
    
    def test_export_exception_records_with_filters(self, saved_exception_records):
        """
        GET /api/database/exception-records/export?line=EAL should export filtered records.
        """
        response = self.client.get(
            "/api/database/exception-records/export",
            params={"line": "EAL", "level": "L1"}
        )
        
        assert response.status_code == 200
        # Verify it's a valid Excel file (has content)
        assert len(response.content) > 0
    
    def test_export_exception_records_empty_returns_200(self):
        """
        GET /api/database/exception-records/export with no matching records should still return 200.
        """
        response = self.client.get(
            "/api/database/exception-records/export",
            params={"line": "NonExistent"}
        )
        
        # Should return 200 with empty Excel, not error
        assert response.status_code == 200


class TestRepeatedRecordsAPI:
    """Test suite for Sub-module 2: Repeated Exception Records API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_client(self, test_client: TestClient):
        """Setup test client for each test."""
        self.client = test_client
    
    # =========================================================================
    # POST /api/database/repeated-records - Save Repeated Records
    # =========================================================================
    
    def test_save_repeated_records_returns_200(self):
        """
        POST /api/database/repeated-records should save records and return success.
        """
        request_data = {
            "line": "EAL",
            "track": "UP",
            "date_str": "20260130",
            "repeated_exceptions": [
                {
                    "id": str(uuid.uuid4()),
                    "exception type": "Low Height",
                    "level": "L1",
                    "FromM": 1000.5,
                    "ToM": 1005.2,
                    "length": 4.7,
                    "maxValue": 4850,
                    "Previous 1": str(uuid.uuid4()),
                    "Previous 2": str(uuid.uuid4()),
                    "action": "Keep monitoring",
                    "Section": "Mainline"
                }
            ]
        }
        
        response = self.client.post("/api/database/repeated-records", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "saved_count" in data
    
    def test_save_repeated_records_filters_mock_data(self):
        """
        POST /api/database/repeated-records should filter out mock data (id starts with 'mock-').
        """
        request_data = {
            "line": "EAL",
            "track": "UP",
            "date_str": "20260130",
            "repeated_exceptions": [
                {
                    "id": "mock-test-001",  # Should be filtered
                    "exception type": "Low Height",
                    "level": "L1",
                    "FromM": 1000.0,
                    "ToM": 1005.0,
                    "Section": "Mainline"
                },
                {
                    "id": str(uuid.uuid4()),  # Real data
                    "exception type": "Low Height",
                    "level": "L2",
                    "FromM": 2000.0,
                    "ToM": 2005.0,
                    "Section": "Mainline"
                }
            ]
        }
        
        response = self.client.post("/api/database/repeated-records", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["saved_count"] == 1  # Only real data saved
        assert "filtered_mock_count" in data
        assert data["filtered_mock_count"] == 1
    
    def test_save_repeated_records_only_mock_returns_400(self):
        """
        POST /api/database/repeated-records with only mock data should return 400.
        """
        request_data = {
            "line": "EAL",
            "track": "UP",
            "date_str": "20260130",
            "repeated_exceptions": [
                {
                    "id": "mock-test-001",
                    "exception type": "Low Height",
                    "level": "L1",
                    "FromM": 1000.0,
                    "ToM": 1005.0,
                    "Section": "Mainline"
                }
            ]
        }
        
        response = self.client.post("/api/database/repeated-records", json=request_data)
        
        assert response.status_code == 400
    
    def test_save_repeated_records_with_workflow_fields(self):
        """
        POST /api/database/repeated-records should accept workflow fields.
        """
        request_data = {
            "line": "EAL",
            "track": "UP",
            "date_str": "20260130",
            "repeated_exceptions": [
                {
                    "id": str(uuid.uuid4()),
                    "exception type": "Low Height",
                    "level": "L1",
                    "FromM": 1000.0,
                    "ToM": 1005.0,
                    "action": "Verify on site",
                    "check_date": "2026-02-15",
                    "checked_by": "Engineer A",
                    "check_result": "Pass",
                    "remarks": "No issue found",
                    "Section": "Mainline"
                }
            ]
        }
        
        response = self.client.post("/api/database/repeated-records", json=request_data)
        
        assert response.status_code == 200
    
    # =========================================================================
    # GET /api/database/repeated-records - Query Repeated Records
    # =========================================================================
    
    def test_get_repeated_records_returns_200(self, saved_repeated_records):
        """
        GET /api/database/repeated-records should return list of records.
        """
        response = self.client.get("/api/database/repeated-records")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "records" in data
        assert "total" in data
        assert "section_counts" in data

    def test_get_repeated_records_reports_full_total_beyond_limit(
        self,
        sectioned_repeated_records,
    ):
        response = self.client.get(
            "/api/database/repeated-records",
            params={"line": "EAL", "limit": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["records"]) == 2
        assert data["total"] == 8
        assert data["section_counts"] == {
            "all": 8,
            "mainline": 2,
            "rac": 1,
            "low_s1": 2,
            "lmc": 1,
            "unknown": 2,
        }

    def test_get_repeated_records_preserves_maximum_limit_contract(self):
        response = self.client.get(
            "/api/database/repeated-records",
            params={"limit": 5001},
        )

        assert response.status_code == 422

    def test_active_section_filters_records_but_not_navigation_counts(
        self,
        sectioned_repeated_records,
    ):
        response = self.client.get(
            "/api/database/repeated-records",
            params={"line": "EAL", "section": "LOW S1", "limit": 1, "offset": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["records"]) == 1
        assert data["total"] == 2
        assert data["section_counts"] == {
            "all": 8,
            "mainline": 2,
            "rac": 1,
            "low_s1": 2,
            "lmc": 1,
            "unknown": 2,
        }

    def test_all_endpoint_filters_share_total_scope(self, sectioned_repeated_records):
        response = self.client.get(
            "/api/database/repeated-records",
            params={
                "line": "EAL",
                "track": "UP",
                "section": "LMC",
                "level": "L2",
                "action": "Calculation",
                "exception_type": "High Height",
                "task_number": "TASK-E",
                "date_type": "task_run_date",
                "date_from": "2026-05-01",
                "date_to": "2026-05-31",
                "chainage_from": 505,
                "chainage_to": 510,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert [record["exception_id"] for record in data["records"]] == ["api-lmc"]
        assert data["section_counts"]["all"] == 1
        assert data["section_counts"]["lmc"] == 1
    
    def test_get_repeated_records_with_action_filter(self, saved_repeated_records):
        """
        GET /api/database/repeated-records?action=Keep monitoring should filter by action.
        """
        response = self.client.get(
            "/api/database/repeated-records",
            params={"action": "Keep monitoring"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for record in data["records"]:
            assert record["action"] == "Keep monitoring"
    
    def test_get_repeated_records_structure(self, saved_repeated_records):
        """
        Repeated records should have all required fields including workflow fields.
        """
        response = self.client.get("/api/database/repeated-records")
        
        assert response.status_code == 200
        data = response.json()
        
        if data["records"]:
            record = data["records"][0]
            # Required fields
            assert "record_id" in record
            assert "exception_id" in record
            assert "exception_type" in record
            assert "level" in record
            assert "line" in record
            assert "track" in record
            # Workflow fields
            assert "action" in record or record.get("action") is None
            assert "check_date" in record or record.get("check_date") is None
    
    # =========================================================================
    # PATCH /api/database/repeated-records/{record_id} - Update Workflow
    # =========================================================================
    
    def test_update_repeated_record_returns_200(self, saved_repeated_records):
        """
        PATCH /api/database/repeated-records/{record_id} should update workflow fields.
        """
        record_id = saved_repeated_records["record_ids"][0]
        
        response = self.client.patch(
            f"/api/database/repeated-records/{record_id}",
            json={"action": "Verify on site"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_update_repeated_record_multiple_fields(self, saved_repeated_records):
        """
        PATCH /api/database/repeated-records/{record_id} should update multiple workflow fields.
        """
        record_id = saved_repeated_records["record_ids"][0]
        
        response = self.client.patch(
            f"/api/database/repeated-records/{record_id}",
            json={
                "action": "Calculation",
                "check_date": "2026-02-20",
                "checked_by": "Engineer B",
                "check_result": "Fail",
                "remarks": "Need adjustment"
            }
        )
        
        assert response.status_code == 200
    
    def test_update_repeated_record_not_found_returns_404(self):
        """
        PATCH /api/database/repeated-records/{non_existent_id} should return 404.
        """
        response = self.client.patch(
            "/api/database/repeated-records/99999",
            json={"action": "Test"}
        )
        
        assert response.status_code == 404
    
    def test_update_repeated_record_empty_body_returns_400(self, saved_repeated_records):
        """
        PATCH /api/database/repeated-records/{record_id} with empty body should return 400.
        """
        record_id = saved_repeated_records["record_ids"][0]
        
        response = self.client.patch(
            f"/api/database/repeated-records/{record_id}",
            json={}
        )
        
        assert response.status_code == 400
    
    # =========================================================================
    # DELETE /api/database/repeated-records/{record_id} - Delete Record
    # =========================================================================
    
    def test_delete_repeated_record_returns_200(self, saved_repeated_records):
        """
        DELETE /api/database/repeated-records/{record_id} should delete successfully.
        """
        record_id = saved_repeated_records["record_ids"][0]
        
        response = self.client.delete(f"/api/database/repeated-records/{record_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_delete_repeated_record_not_found_returns_404(self):
        """
        DELETE /api/database/repeated-records/{non_existent_id} should return 404.
        """
        response = self.client.delete("/api/database/repeated-records/99999")
        
        assert response.status_code == 404
    
    # =========================================================================
    # GET /api/database/repeated-records/export - Export to Excel
    # =========================================================================
    
    def test_export_repeated_records_returns_excel(self, saved_repeated_records):
        """
        GET /api/database/repeated-records/export should return Excel file.
        """
        response = self.client.get("/api/database/repeated-records/export")
        
        assert response.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
        assert "Content-Disposition" in response.headers
    
    def test_export_repeated_records_filename(self, saved_repeated_records):
        """
        Export filename should contain 'Follow_up_Action'.
        """
        response = self.client.get("/api/database/repeated-records/export")
        
        assert response.status_code == 200
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "Follow" in content_disposition or "Repeated" in content_disposition


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_client(tmp_path):
    """
    Create a test client with a temporary database.
    """
    import os
    import gc
    import time
    
    # Set up temporary database path
    test_db_path = tmp_path / "test_analysis.db"
    os.environ['TOV640_TEST_DB_PATH'] = str(test_db_path)
    
    # Reset DatabaseManager singleton for testing
    from app.core.database import DatabaseManager
    DatabaseManager.reset_instance()
    
    # Re-initialize with test path
    db = DatabaseManager(str(test_db_path))
    
    # Import and create test client
    from app.main import app
    from fastapi.testclient import TestClient
    
    with TestClient(app) as client:
        yield client
    
    # Cleanup
    try:
        db.close()
    except Exception:
        pass
    
    DatabaseManager.reset_instance()
    gc.collect()
    time.sleep(0.1)
    
    try:
        if test_db_path.exists():
            test_db_path.unlink()
    except PermissionError:
        pass


@pytest.fixture
def saved_exception_records(test_client, tmp_path):
    """
    Create sample exception records in the test database.
    """
    from app.core.database import DatabaseManager, save_exception_records_batch
    
    test_db_path = tmp_path / "test_analysis.db"
    db = DatabaseManager(str(test_db_path))
    
    exceptions = [
        {
            "id": str(uuid.uuid4()),
            "exception type": "Low Height",
            "level": "L1",
            "FromM": 1000.5,
            "ToM": 1005.2,
            "length": 4.7,
            "maxValue": 4850,
            "maxLocation": 1002.3,
            "Track Type": "Mainline",
            "Section": "Mainline"
        },
        {
            "id": str(uuid.uuid4()),
            "exception type": "Stagger Left",
            "level": "L2",
            "FromM": 2000.0,
            "ToM": 2010.0,
            "length": 10.0,
            "maxValue": 350,
            "maxLocation": 2005.0,
            "Track Type": "Mainline",
            "Section": "Mainline"
        }
    ]
    
    record_ids = [exc["id"] for exc in exceptions]
    
    with db.get_connection() as conn:
        save_exception_records_batch(
            conn,
            line="EAL",
            track="UP",
            section="Mainline",
            date_str="20260115",
            exceptions=exceptions
        )
    
    return {
        "record_ids": record_ids,
        "line": "EAL",
        "track": "UP",
        "date_str": "20260115"
    }


@pytest.fixture
def saved_repeated_records(test_client, tmp_path):
    """
    Create sample repeated exception records in the test database.
    """
    from app.core.database import DatabaseManager, save_repeated_records_batch
    
    test_db_path = tmp_path / "test_analysis.db"
    db = DatabaseManager(str(test_db_path))
    
    repeated_exceptions = [
        {
            "id": str(uuid.uuid4()),
            "exception type": "Low Height",
            "level": "L1",
            "FromM": 1000.5,
            "ToM": 1005.2,
            "length": 4.7,
            "maxValue": 4850,
            "Previous 1": str(uuid.uuid4()),
            "action": "Keep monitoring",
            "Section": "Mainline"
        },
        {
            "id": str(uuid.uuid4()),
            "exception type": "Stagger Left",
            "level": "L2",
            "FromM": 2000.0,
            "ToM": 2010.0,
            "length": 10.0,
            "maxValue": 350,
            "Previous 1": str(uuid.uuid4()),
            "action": "Calculation",
            "Section": "Mainline"
        }
    ]
    
    with db.get_connection() as conn:
        result = save_repeated_records_batch(
            conn,
            line="EAL",
            track="UP",
            date_str="20260120",
            repeated_exceptions=repeated_exceptions
        )
    
    # Get record IDs from database
    with db.get_connection() as conn:
        cursor = conn.execute("SELECT record_id FROM saved_repeated_exceptions ORDER BY record_id")
        record_ids = [row[0] for row in cursor.fetchall()]
    
    return {
        "record_ids": record_ids,
        "line": "EAL",
        "track": "UP",
        "date_str": "20260120"
    }


def test_check_1_year_rejects_invalid_date_filter(test_client):
    response = test_client.post(
        "/api/database/repeated-records/check-1-year",
        json={
            "line": "EAL",
            "track": "UP",
            "date_from": "not-a-date",
            "exceptions": [{"id": "x", "action": "Pending"}],
        },
    )
    assert response.status_code == 422
    assert "date_from" in response.json()["detail"]


def test_check_1_year_rejects_empty_effective_window(test_client):
    response = test_client.post(
        "/api/database/repeated-records/check-1-year",
        json={
            "line": "EAL",
            "track": "UP",
            "date_from": "20200101",
            "date_to": "20200131",
            "current_date": "20260101",
            "exceptions": [{"id": "x", "action": "Pending"}],
        },
    )
    assert response.status_code == 422
    assert "effective 365-day window" in response.json()["detail"]


def test_check_1_year_returns_machine_readable_reason_for_skipped_rows(test_client):
    response = test_client.post(
        "/api/database/repeated-records/check-1-year",
        json={
            "line": "EAL",
            "track": "UP",
            "current_date": "20260101",
            "exceptions": [{
                "id": "skip-current-action",
                "action": "Calculation",
                "exception type": "Low Height",
                "level": "L1",
                "maxLocation": 100.0,
                "Section": "Mainline",
            }],
        },
    )

    assert response.status_code == 200
    row = response.json()["exceptions"][0]
    assert row["check_1_year_status"] == "skipped"
    assert row["check_1_year_reason"] == "current_action_not_pending"


def test_save_approved_review_link_is_idempotent_and_version_guarded(test_client, saved_repeated_records):
    from app.core.database import DatabaseManager

    db = DatabaseManager()
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT record_id, exception_id, last_updated, reoccurrence_id FROM saved_repeated_exceptions ORDER BY record_id LIMIT 1"
        ).fetchone()
        target_id = row["record_id"]
        target_version = str(row["last_updated"] or "")
        current_id = "approved-current-1"

    payload = {
        "line": "EAL",
        "track": "UP",
        "date_str": "20260220",
        "repeated_exceptions": [{"id": current_id, "exception type": "Low Height", "level": "L1", "FromM": 1, "ToM": 2}],
        "approved_recurrence_links": [{
            "exception_id": current_id,
            "target_record_id": target_id,
            "target_version": target_version,
        }],
    }
    first = test_client.post("/api/database/repeated-records", json=payload)
    assert first.status_code == 200, first.text
    with db.get_connection() as conn:
        refreshed_version = str(conn.execute("SELECT last_updated FROM saved_repeated_exceptions WHERE record_id = ?", (target_id,)).fetchone()["last_updated"] or "")
    retry_payload = dict(payload)
    retry_payload["approved_recurrence_links"] = [{**payload["approved_recurrence_links"][0], "target_version": refreshed_version}]
    second = test_client.post("/api/database/repeated-records", json=retry_payload)
    assert second.status_code == 200, second.text

    with db.get_connection() as conn:
        row = conn.execute("SELECT reoccurrence_id FROM saved_repeated_exceptions WHERE record_id = ?", (target_id,)).fetchone()
        assert row["reoccurrence_id"].split(", ").count(current_id) == 1

    stale = dict(payload)
    stale["approved_recurrence_links"] = [{**payload["approved_recurrence_links"][0], "target_version": "stale-version"}]
    conflict = test_client.post("/api/database/repeated-records", json=stale)
    assert conflict.status_code == 409


@pytest.fixture
def sectioned_repeated_records(test_client, tmp_path):
    """Create a bounded dataset for full totals and section navigation counts."""
    from app.core.database import DatabaseManager, save_repeated_records_batch

    db = DatabaseManager(str(tmp_path / "test_analysis.db"))
    records = [
        ("api-main-1", "EAL", "UP", "Mainline", "L1", "Low Height", "Pending", 100, 120, "TASK-A", "20260110"),
        ("api-main-2", "EAL", "UP", "Mainline", "L2", "Stagger Left", "Keep monitoring", 200, 220, "TASK-B", "20260210"),
        ("api-rac", "EAL", "DN", "RAC", "L1", "Low Height", "Pending", 300, 320, "TASK-C", "20260310"),
        ("api-low", "EAL", "UP", "LOW", "L1", "Low Height", "Pending", 400, 420, "TASK-D", "20260410"),
        ("api-low-s1", "EAL", "UP", "LOW S1", "L1", "Low Height", "Pending", 450, 470, "TASK-D2", "20260420"),
        ("api-lmc", "EAL", "UP", "LMC", "L2", "High Height", "Calculation", 500, 520, "TASK-E", "20260510"),
        ("api-null", "EAL", "UP", None, "L1", "Low Height", "Pending", 600, 620, "TASK-F", "20260610"),
        ("api-unknown", "EAL", "UP", "Depot", "L1", "Low Height", "Pending", 700, 720, "TASK-G", "20260710"),
        ("api-tml", "TML", "UP", "Mainline", "L1", "Low Height", "Pending", 800, 820, "TASK-H", "20260810"),
    ]

    with db.get_connection() as conn:
        for (
            exception_id,
            line,
            track,
            section,
            level,
            exception_type,
            action,
            from_m,
            to_m,
            task_no,
            task_run_date,
        ) in records:
            save_repeated_records_batch(
                conn,
                line=line,
                track=track,
                date_str=task_run_date,
                task_run_date=task_run_date,
                task_no=task_no,
                repeated_exceptions=[{
                    "id": exception_id,
                    "exception type": exception_type,
                    "level": level,
                    "FromM": from_m,
                    "ToM": to_m,
                    "action": action,
                    "Section": section,
                }],
            )

    return records


# =============================================================================
# Phase 10.10 - Bug 1.3: Distinct Values API (TDD)
# =============================================================================

class TestDistinctValuesAPI:
    """Test GET /api/database/repeated-records/distinct-values endpoint."""

    @pytest.fixture(autouse=True)
    def setup_client(self, test_client):
        self.client = test_client

    def test_get_distinct_values_returns_200(self, saved_repeated_records):
        """Should return 200 with a list of distinct values."""
        response = self.client.get(
            "/api/database/repeated-records/distinct-values",
            params={"field": "task_no"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["values"], list)

    def test_get_distinct_values_with_line_filter(self, saved_repeated_records):
        """Should filter by line when provided."""
        response = self.client.get(
            "/api/database/repeated-records/distinct-values",
            params={"field": "line"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "EAL" in data["values"]

    def test_get_distinct_values_invalid_field_returns_400(self):
        """Should return 400 for invalid/unsafe field names."""
        response = self.client.get(
            "/api/database/repeated-records/distinct-values",
            params={"field": "DROP TABLE; --"}
        )
        assert response.status_code == 400

    def test_get_distinct_values_missing_field_returns_422(self):
        """Should return 422 when field parameter is missing."""
        response = self.client.get(
            "/api/database/repeated-records/distinct-values"
        )
        assert response.status_code == 422
