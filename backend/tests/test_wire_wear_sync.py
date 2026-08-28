import os
from contextlib import closing
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.calculation.wear_cycle_repository import save_analysis_cycle
from app.core.calculation.wear_cycle_types import (
    AggregatedWearRecord,
    BusinessKey,
    CyclePreview,
    MetadataInterval,
    SegmentCoverage,
)
from app.core.database import DatabaseManager
from app.main import app


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "sync-api.db"
    os.environ["TOV640_TEST_DB_PATH"] = str(db_path)
    DatabaseManager.reset_instance()
    DatabaseManager(str(db_path)).close()
    with TestClient(app) as test_client:
        yield test_client
    DatabaseManager.reset_instance()
    os.environ.pop("TOV640_TEST_DB_PATH", None)


def _preview():
    record = AggregatedWearRecord(
        BusinessKey("EAL", date(2026, 5, 28), "28", "EAL"), "UP",
        Decimal("100"), Decimal("200"), 11.4, 10.0, None, False, (), (),
    )
    segment = SegmentCoverage(
        "U1", True, 100.0, (), ("source.xlsx",), (date(2026, 5, 28),),
    )
    return CyclePreview(
        "EAL", date(2026, 5, 28), (record,), (segment,), (), (), (), True,
        datetime(2026, 5, 28, tzinfo=timezone.utc), "EAL",
    )


def _metadata():
    return (MetadataInterval("28", "UP", Decimal("100"), Decimal("200"), "EAL UP"),)


def test_sync_json_preview_apply_api_creates_pre_apply_backup(tmp_path, monkeypatch):
    import app.api.endpoints.wear_records as endpoint

    db_path = tmp_path / "api-sync.db"
    os.environ["TOV640_TEST_DB_PATH"] = str(db_path)
    DatabaseManager.reset_instance()
    before_files = {path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file()}
    try:
        db = DatabaseManager(str(db_path))
        with db.get_connection() as conn:
            save_analysis_cycle(conn, _preview(), expected_data_version=0)
        monkeypatch.setattr(endpoint, "_load_cycle_metadata", lambda *_identity: _metadata())
        monkeypatch.setattr(
            endpoint, "_cycle_metadata_fingerprints",
            lambda: {"EAL": "same", "TML": "same"}, raising=False,
        )

        with TestClient(app) as client:
            exported = client.get("/api/calculation/wear-records/sync.json?source_workstation=Machine-A")
            package = exported.json()
            package["package_id"] = "remote-package"
            package["records"][0]["cycle_date"] = "2026-06-28"
            package["records"][0]["updated_at"] = "2026-08-01T00:00:00Z"
            package["cycles"][0]["cycle_date"] = "2026-06-28"
            package["cycles"][0]["updated_at"] = "2026-08-01T00:00:00Z"
            package["segments"] = []
            package["conflict_decisions"] = []
            preview = client.post("/api/calculation/wear-records/sync/preview", json=package)
            body = preview.json()
            applied = client.post("/api/calculation/wear-records/sync/apply", json={
                "source_package": body["source_package"],
                "preview_digest": body["preview_digest"],
                "expected_data_version": body["expected_data_version"],
            })
    finally:
        DatabaseManager.reset_instance()
        os.environ.pop("TOV640_TEST_DB_PATH", None)

    assert exported.status_code == 200
    assert package["schema"] == "wear-cycle-v1"
    assert preview.status_code == 200
    assert body["actions"][0]["action"] == "create"
    assert body["actions"][0]["status"] == "new"
    assert applied.status_code == 200
    backup_path = Path(applied.json()["backup_path"])
    assert backup_path.parent == tmp_path / "backups"
    assert backup_path.exists()
    with closing(sqlite3.connect(backup_path)) as backup_conn:
        rows = backup_conn.execute(
            """
            SELECT line_group, line_class, cycle_date, tension_length
            FROM wire_wear_cycle_records
            ORDER BY cycle_date
            """
        ).fetchall()
        assert rows == [("EAL", "EAL", "2026-05-28", "28")]
    after_files = {path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file()}
    created_files = after_files - before_files
    assert [
        path for path in created_files
        if "-wire-wear-backup-" in path.name.lower()
    ] == [backup_path.relative_to(tmp_path)]


def test_sync_api_rejects_legacy_schema_and_stale_apply(client, monkeypatch):
    import app.api.endpoints.wear_records as endpoint

    monkeypatch.setattr(endpoint, "_load_cycle_metadata", lambda *_identity: _metadata())
    monkeypatch.setattr(
        endpoint, "_cycle_metadata_fingerprints",
        lambda: {"EAL": "same", "TML": "same"}, raising=False,
    )
    legacy = client.post("/api/calculation/wear-records/sync/preview", json={"schema": "tov640-wire-wear-sync"})
    stale = client.post("/api/calculation/wear-records/sync/apply", json={
        "source_package": {"schema": "wear-cycle-v1"},
        "preview_digest": "digest",
        "expected_data_version": -1,
    })

    assert legacy.status_code == 422
    assert "wear-cycle-v1" in str(legacy.json())
    assert stale.status_code == 409
