from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3

import pytest

from app.core.calculation.wear_cycle_application import (
    BackupCreationError,
    ChangeSetOrigin,
    apply_change_set_with_backup,
    create_sqlite_backup,
)
from app.core.calculation.wear_cycle_repository import (
    AddOperation,
    ChangeOperationError,
    ChangeSet,
    StaleDataVersionError,
    get_wire_wear_data_version,
)
from app.core.calculation.wear_cycle_types import BusinessKey, MetadataInterval
from app.core.database import DatabaseManager


@pytest.fixture()
def wire_wear_database(tmp_path):
    db_path = tmp_path / "data" / "analysis.db"
    db = DatabaseManager(str(db_path))
    try:
        yield db, db_path
    finally:
        db.close()
        DatabaseManager.reset_instance()


def _metadata():
    return (
        MetadataInterval(
            "28",
            "UP",
            Decimal("100"),
            Decimal("200"),
            "EAL UP",
        ),
    )


def _add_operation(*, tension_length="28", avg_wear_min=11.4):
    return AddOperation(
        BusinessKey("EAL", date(2026, 5, 28), tension_length, "EAL"),
        avg_wear_min,
    )


def _record_count(conn):
    return conn.execute("SELECT COUNT(*) FROM wire_wear_cycle_records").fetchone()[0]


def _data_version(conn):
    return get_wire_wear_data_version(conn)


def test_workbook_apply_creates_backup_before_mutation_and_returns_result(
    wire_wear_database,
):
    db, db_path = wire_wear_database

    with db.get_connection() as conn:
        result = apply_change_set_with_backup(
            conn,
            ChangeSet((_add_operation(),)),
            _metadata(),
            db_path=db_path,
            origin=ChangeSetOrigin.WORKBOOK,
            now=datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc),
        )

        assert result.added == 1
        assert result.edited == 0
        assert result.deleted == 0
        assert result.data_version == 1
        assert result.backup_path is not None
        assert _record_count(conn) == 1

    backup_path = Path(result.backup_path)
    assert backup_path.parent == db_path.parent / "backups"
    assert backup_path.exists()
    with closing(sqlite3.connect(backup_path)) as backup_conn:
        assert _record_count(backup_conn) == 0
        assert _data_version(backup_conn) == 0


def test_backup_failure_stops_apply_without_mutation(
    wire_wear_database, monkeypatch
):
    import app.core.calculation.wear_cycle_application as application

    db, db_path = wire_wear_database

    def fail_backup(*_args, **_kwargs):
        raise BackupCreationError("backup unavailable")

    monkeypatch.setattr(application, "create_sqlite_backup", fail_backup)

    with db.get_connection() as conn:
        with pytest.raises(BackupCreationError, match="backup unavailable"):
            apply_change_set_with_backup(
                conn,
                ChangeSet((_add_operation(),)),
                _metadata(),
                db_path=db_path,
                origin=ChangeSetOrigin.WORKBOOK,
            )

        assert _record_count(conn) == 0
        assert _data_version(conn) == 0


def test_failed_change_set_rolls_back_and_keeps_readable_backup(
    wire_wear_database,
):
    db, db_path = wire_wear_database
    change_set = ChangeSet(
        (
            _add_operation(),
            _add_operation(tension_length="unknown", avg_wear_min=10.8),
        )
    )

    with db.get_connection() as conn:
        before = set((db_path.parent / "backups").glob("*.db"))
        with pytest.raises(ChangeOperationError):
            apply_change_set_with_backup(
                conn,
                change_set,
                _metadata(),
                db_path=db_path,
                origin=ChangeSetOrigin.WORKBOOK,
            )

        assert _record_count(conn) == 0
        assert _data_version(conn) == 0

    backups = set((db_path.parent / "backups").glob("*.db")) - before
    assert len(backups) == 1
    with closing(sqlite3.connect(backups.pop())) as backup_conn:
        assert _record_count(backup_conn) == 0


def test_manual_apply_does_not_create_backup(wire_wear_database):
    db, db_path = wire_wear_database

    with db.get_connection() as conn:
        result = apply_change_set_with_backup(
            conn,
            ChangeSet((_add_operation(),)),
            _metadata(),
            db_path=db_path,
            origin=ChangeSetOrigin.MANUAL,
        )

    assert result.backup_path is None
    assert not (db_path.parent / "backups").exists()


def test_stale_workbook_apply_keeps_backup_without_mutating_live_database(
    wire_wear_database,
):
    db, db_path = wire_wear_database

    with db.get_connection() as conn:
        apply_change_set_with_backup(
            conn,
            ChangeSet((_add_operation(),)),
            _metadata(),
            db_path=db_path,
            origin=ChangeSetOrigin.MANUAL,
            expected_data_version=0,
        )
        before_records = _record_count(conn)
        before_version = _data_version(conn)

        with pytest.raises(
            StaleDataVersionError,
            match="wire wear data changed since the candidate preview",
        ):
            apply_change_set_with_backup(
                conn,
                ChangeSet((_add_operation(avg_wear_min=10.8),)),
                _metadata(),
                db_path=db_path,
                origin=ChangeSetOrigin.WORKBOOK,
                expected_data_version=0,
            )

        assert _record_count(conn) == before_records == 1
        assert _data_version(conn) == before_version == 1

    backups = list((db_path.parent / "backups").glob("*.db"))
    assert len(backups) == 1
    with closing(sqlite3.connect(backups[0])) as backup_conn:
        assert _record_count(backup_conn) == before_records
        assert _data_version(backup_conn) == before_version


def test_automatic_backup_retention_keeps_latest_ten_and_user_files(
    wire_wear_database,
):
    db, db_path = wire_wear_database
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True)
    user_export = backup_dir / "wire-wear-export-user-owned.json"
    user_export.write_text("{}", encoding="utf-8")
    start = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)

    with db.get_connection() as conn:
        created = [
            create_sqlite_backup(
                conn,
                db_path,
                now=start + timedelta(seconds=index),
            )
            for index in range(12)
        ]

    retained = sorted(backup_dir.glob("analysis-wire-wear-backup-*.db"))
    assert len(retained) == 10
    assert set(retained) == {Path(path) for path in created[-10:]}
    assert user_export.exists()
