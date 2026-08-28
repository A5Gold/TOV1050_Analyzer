import os

from fastapi.testclient import TestClient

from app.core.database import DatabaseManager
from app.main import app


def test_diagnostics_api_returns_active_database_path_and_packaging(tmp_path):
    db_path = tmp_path / "diagnostics.db"
    os.environ["DB_PATH"] = str(db_path)
    DatabaseManager.reset_instance()

    try:
        response = TestClient(app).get("/api/diagnostics")
    finally:
        DatabaseManager.reset_instance()
        os.environ.pop("DB_PATH", None)

    assert response.status_code == 200
    body = response.json()
    assert body["database_path"] == str(db_path)
    assert body["database_directory"] == str(tmp_path)
    assert body["packaging"]["recommended_target"] == "dir"
    assert body["packaging"]["single_exe_note"]
