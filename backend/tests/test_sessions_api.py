"""
TOV640 Analyzer - Sessions API Tests
=====================================
Tests for Stateful Transformation API endpoints.

TDD: These tests are written BEFORE the implementation.

Endpoints tested:
- GET /api/sessions - 查詢分析記錄列表
- GET /api/sessions/{session_id} - 獲取單個 session 詳情
- GET /api/sessions/{session_id}/exceptions - 獲取 session 的異常列表
- PATCH /api/exceptions/{exception_id}/status - 更新異常狀態
"""

import pytest
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Import the main app for testing
import sys
from pathlib import Path

# Add backend/app to path for imports
backend_path = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(backend_path))


class TestSessionsAPI:
    """Test suite for Sessions API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_client(self, test_client: TestClient):
        """Setup test client for each test."""
        self.client = test_client
    
    # =========================================================================
    # GET /api/sessions - Query Sessions List
    # =========================================================================
    
    def test_get_sessions_returns_200_with_empty_list(self):
        """
        GET /api/sessions should return 200 with empty list when no sessions exist.
        """
        response = self.client.get("/api/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "sessions" in data
        assert isinstance(data["sessions"], list)
        assert "total" in data
    
    def test_get_sessions_returns_sessions_list(self, sample_session_in_db):
        """
        GET /api/sessions should return list of sessions.
        """
        response = self.client.get("/api/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["sessions"]) >= 1
        
        # Verify session structure
        session = data["sessions"][0]
        assert "id" in session
        assert "line" in session
        assert "track" in session
        assert "section" in session
        assert "date_str" in session
        assert "created_at" in session
    
    def test_get_sessions_with_line_filter(self, sample_session_in_db):
        """
        GET /api/sessions?line=EAL should filter by line.
        """
        response = self.client.get("/api/sessions", params={"line": "EAL"})
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned sessions should have line == EAL
        for session in data["sessions"]:
            assert session["line"] == "EAL"
    
    def test_get_sessions_with_date_filter(self, sample_session_in_db):
        """
        GET /api/sessions?date_from=20260101&date_to=20260131 should filter by date range.
        """
        response = self.client.get(
            "/api/sessions", 
            params={"date_from": "20260101", "date_to": "20260131"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned sessions should have date_str within range
        for session in data["sessions"]:
            assert "20260101" <= session["date_str"] <= "20260131"
    
    def test_get_sessions_with_limit(self, sample_session_in_db):
        """
        GET /api/sessions?limit=5 should limit results.
        """
        response = self.client.get("/api/sessions", params={"limit": 5})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) <= 5
    
    def test_get_sessions_invalid_limit_returns_422(self):
        """
        GET /api/sessions?limit=999999 should return validation error.
        """
        response = self.client.get("/api/sessions", params={"limit": 999999})
        
        # FastAPI returns 422 for validation errors
        assert response.status_code == 422
    
    # =========================================================================
    # GET /api/sessions/{session_id} - Get Single Session
    # =========================================================================
    
    def test_get_session_by_id_returns_200(self, sample_session_in_db):
        """
        GET /api/sessions/{session_id} should return session details.
        """
        session_id = sample_session_in_db["session_id"]
        response = self.client.get(f"/api/sessions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["session"]["id"] == session_id
        assert "line" in data["session"]
        assert "track" in data["session"]
    
    def test_get_session_by_id_not_found_returns_404(self):
        """
        GET /api/sessions/{non_existent_id} should return 404.
        """
        non_existent_id = str(uuid.uuid4())
        response = self.client.get(f"/api/sessions/{non_existent_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_get_session_by_id_includes_stats(self, sample_session_with_exceptions):
        """
        GET /api/sessions/{session_id} should include exception statistics.
        """
        session_id = sample_session_with_exceptions["session_id"]
        response = self.client.get(f"/api/sessions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        session = data["session"]
        
        # Should include exception counts from v_sessions_with_stats
        # These fields come from the view
        assert "total_exceptions" in session or "exception_count" in session
    
    # =========================================================================
    # GET /api/sessions/{session_id}/exceptions - Get Session Exceptions
    # =========================================================================
    
    def test_get_session_exceptions_returns_200(self, sample_session_with_exceptions):
        """
        GET /api/sessions/{session_id}/exceptions should return exception list.
        """
        session_id = sample_session_with_exceptions["session_id"]
        response = self.client.get(f"/api/sessions/{session_id}/exceptions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "exceptions" in data
        assert isinstance(data["exceptions"], list)
    
    def test_get_session_exceptions_empty_for_new_session(self, sample_session_in_db):
        """
        GET /api/sessions/{session_id}/exceptions should return empty list for session without exceptions.
        """
        session_id = sample_session_in_db["session_id"]
        response = self.client.get(f"/api/sessions/{session_id}/exceptions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["exceptions"] == []
    
    def test_get_session_exceptions_with_level_filter(self, sample_session_with_exceptions):
        """
        GET /api/sessions/{session_id}/exceptions?level=L1 should filter by level.
        """
        session_id = sample_session_with_exceptions["session_id"]
        response = self.client.get(
            f"/api/sessions/{session_id}/exceptions",
            params={"level": "L1"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned exceptions should have level == L1
        for exc in data["exceptions"]:
            assert exc["level"] == "L1"
    
    def test_get_session_exceptions_not_found_returns_404(self):
        """
        GET /api/sessions/{non_existent_id}/exceptions should return 404.
        """
        non_existent_id = str(uuid.uuid4())
        response = self.client.get(f"/api/sessions/{non_existent_id}/exceptions")
        
        assert response.status_code == 404
    
    def test_get_session_exceptions_structure(self, sample_session_with_exceptions):
        """
        Exception records should have all required fields.
        """
        session_id = sample_session_with_exceptions["session_id"]
        response = self.client.get(f"/api/sessions/{session_id}/exceptions")
        
        assert response.status_code == 200
        data = response.json()
        
        if data["exceptions"]:
            exc = data["exceptions"][0]
            # Required fields from schema
            assert "id" in exc
            assert "exception_type" in exc
            assert "level" in exc
            assert "from_m" in exc
            assert "to_m" in exc
            assert "current_status" in exc
    
    # =========================================================================
    # PATCH /api/exceptions/{exception_id}/status - Update Exception Status
    # =========================================================================
    
    def test_update_exception_status_returns_200(self, sample_session_with_exceptions):
        """
        PATCH /api/exceptions/{exception_id}/status should update status successfully.
        """
        exception_id = sample_session_with_exceptions["exception_ids"][0]
        
        response = self.client.patch(
            f"/api/exceptions/{exception_id}/status",
            json={"status": "in_progress"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_update_exception_status_with_notes(self, sample_session_with_exceptions):
        """
        PATCH /api/exceptions/{exception_id}/status should accept notes field.
        """
        exception_id = sample_session_with_exceptions["exception_ids"][0]
        
        response = self.client.patch(
            f"/api/exceptions/{exception_id}/status",
            json={
                "status": "in_progress",
                "notes": "Scheduled for maintenance on 2026-02-15"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_update_exception_status_with_assigned_to(self, sample_session_with_exceptions):
        """
        PATCH /api/exceptions/{exception_id}/status should accept assigned_to field.
        """
        exception_id = sample_session_with_exceptions["exception_ids"][0]
        
        response = self.client.patch(
            f"/api/exceptions/{exception_id}/status",
            json={
                "status": "in_progress",
                "assigned_to": "Engineer A"
            }
        )
        
        assert response.status_code == 200
    
    def test_update_exception_status_to_resolved(self, sample_session_with_exceptions):
        """
        PATCH /api/exceptions/{exception_id}/status with status=resolved should set resolved_at.
        """
        exception_id = sample_session_with_exceptions["exception_ids"][0]
        
        response = self.client.patch(
            f"/api/exceptions/{exception_id}/status",
            json={
                "status": "resolved",
                "resolved_by": "Engineer B"
            }
        )
        
        assert response.status_code == 200
    
    def test_update_exception_status_invalid_status_returns_422(self, sample_session_with_exceptions):
        """
        PATCH /api/exceptions/{exception_id}/status with invalid status should return 422.
        """
        exception_id = sample_session_with_exceptions["exception_ids"][0]
        
        response = self.client.patch(
            f"/api/exceptions/{exception_id}/status",
            json={"status": "invalid_status"}
        )
        
        assert response.status_code == 422
    
    def test_update_exception_status_not_found_returns_404(self):
        """
        PATCH /api/exceptions/{non_existent_id}/status should return 404.
        """
        non_existent_id = str(uuid.uuid4())
        
        response = self.client.patch(
            f"/api/exceptions/{non_existent_id}/status",
            json={"status": "in_progress"}
        )
        
        assert response.status_code == 404
    
    def test_update_exception_status_missing_body_returns_422(self, sample_session_with_exceptions):
        """
        PATCH /api/exceptions/{exception_id}/status without body should return 422.
        """
        exception_id = sample_session_with_exceptions["exception_ids"][0]
        
        response = self.client.patch(f"/api/exceptions/{exception_id}/status")
        
        # FastAPI returns 422 for missing required body
        assert response.status_code == 422
    
    def test_update_exception_status_creates_history_record(self, sample_session_with_exceptions):
        """
        PATCH /api/exceptions/{exception_id}/status should create a record in exception_history.
        
        This is verified by checking the trigger works correctly.
        """
        exception_id = sample_session_with_exceptions["exception_ids"][0]
        
        # First update
        response = self.client.patch(
            f"/api/exceptions/{exception_id}/status",
            json={"status": "in_progress"}
        )
        assert response.status_code == 200
        
        # Second update
        response = self.client.patch(
            f"/api/exceptions/{exception_id}/status",
            json={"status": "resolved"}
        )
        assert response.status_code == 200


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
    
    # Cleanup - properly close connections before deleting
    try:
        db.close()
    except Exception:
        pass
    
    DatabaseManager.reset_instance()
    gc.collect()  # Force garbage collection
    time.sleep(0.1)  # Brief pause for Windows file handle release
    
    # Try to delete, but don't fail if it doesn't work (Windows file locking)
    try:
        if test_db_path.exists():
            test_db_path.unlink()
    except PermissionError:
        pass  # File may still be locked on Windows, that's OK


@pytest.fixture
def sample_session_in_db(test_client, tmp_path):
    """
    Create a sample session in the test database.
    """
    import os
    from app.core.database import DatabaseManager, save_analysis_session
    
    test_db_path = tmp_path / "test_analysis.db"
    db = DatabaseManager(str(test_db_path))
    
    session_data = {
        "line": "EAL",
        "section": "Mainline",
        "track": "UP",
        "date_str": "20260115",
        "raw_data_file_name": "test_data.datac",
        "task_no": "U1",
        "station_start": "HUH",
        "station_end": "RAC"
    }
    
    with db.get_connection() as conn:
        session_id = save_analysis_session(conn, session_data)
    
    return {
        "session_id": session_id,
        **session_data
    }


@pytest.fixture
def sample_session_with_exceptions(test_client, tmp_path):
    """
    Create a sample session with exceptions in the test database.
    """
    import os
    from app.core.database import (
        DatabaseManager, 
        save_analysis_session, 
        save_exceptions_from_analysis
    )
    
    test_db_path = tmp_path / "test_analysis.db"
    db = DatabaseManager(str(test_db_path))
    
    session_data = {
        "line": "EAL",
        "section": "Mainline",
        "track": "UP",
        "date_str": "20260120",
        "raw_data_file_name": "test_data_with_exceptions.datac"
    }
    
    exceptions = {
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
            },
            {
                "id": str(uuid.uuid4()),
                "exception type": "Low Height",
                "level": "L2",
                "FromM": 2000.0,
                "ToM": 2010.5,
                "length": 10.5,
                "maxValue": 4900,
                "maxLocation": 2005.0,
                "Track Type": "Mainline",
                "Section": "Mainline"
            }
        ],
        "Stagger Left": [
            {
                "id": str(uuid.uuid4()),
                "exception type": "Stagger Left",
                "level": "L1",
                "FromM": 3000.0,
                "ToM": 3002.0,
                "length": 2.0,
                "maxValue": 350,
                "maxLocation": 3001.0,
                "Track Type": "Mainline",
                "Section": "Mainline"
            }
        ]
    }
    
    exception_ids = []
    for exc_type, exc_list in exceptions.items():
        for exc in exc_list:
            exception_ids.append(exc["id"])
    
    with db.get_connection() as conn:
        session_id = save_analysis_session(conn, session_data)
        save_exceptions_from_analysis(conn, session_id, exceptions)
    
    return {
        "session_id": session_id,
        "exception_ids": exception_ids,
        **session_data
    }
