import json
import sqlite3
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.core.database import DatabaseManager


def test_wire_wear_records_table_exists(tmp_path):
    db = DatabaseManager(str(tmp_path / "wear_records.db"))
    try:
        with db.get_connection() as conn:
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(wire_wear_records)").fetchall()
            }
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert {
        "record_id",
        "line_group",
        "line_class",
        "track",
        "section",
        "cycle_date",
        "tension_length",
        "from_m",
        "to_m",
        "avg_wear_min",
        "sd",
        "wear_percentage",
        "source_file_names",
        "saved_by",
        "created_at",
        "updated_at",
    }.issubset(columns)


def test_complete_cycle_schema_fresh_database_has_normalized_tables_indexes_and_foreign_keys(tmp_path):
    db = DatabaseManager(str(tmp_path / "complete_cycle_schema.db"))
    try:
        with db.get_connection() as conn:
            expected_columns = {
                "wire_wear_cycles": {
                    "cycle_id",
                    "line_group",
                    "line_class",
                    "cycle_date",
                    "source_type",
                    "acquisition_date_from",
                    "acquisition_date_to",
                    "completeness_state",
                    "source_lineage",
                    "created_at",
                    "updated_at",
                },
                "wire_wear_cycle_segments": {
                    "segment_id",
                    "cycle_id",
                    "segment_name",
                    "is_present",
                    "coverage_percentage",
                    "diagnostic_gaps",
                    "source_file_names",
                    "acquisition_date_from",
                    "acquisition_date_to",
                },
                "wire_wear_cycle_records": {
                    "record_id",
                    "cycle_id",
                    "line_group",
                    "line_class",
                    "cycle_date",
                    "tension_length",
                    "track",
                    "from_m",
                    "to_m",
                    "avg_wear_min",
                    "wear_percentage",
                    "measurement_sd",
                    "physical_intervals",
                    "source_lineage",
                    "created_at",
                    "updated_at",
                },
                "wire_wear_conflict_decisions": {
                    "decision_id",
                    "cycle_id",
                    "measurement_identity",
                    "source_values",
                    "selected_wear_min",
                    "accepted_at",
                },
                "wire_wear_deletion_tombstones": {
                    "tombstone_id",
                    "line_group",
                    "line_class",
                    "cycle_date",
                    "tension_length",
                    "deleted_at",
                    "source_package_id",
                },
            }

            actual_columns = {
                table: {
                    row["name"]
                    for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
                }
                for table in expected_columns
            }
            index_columns = {
                name: [
                    row["name"]
                    for row in conn.execute(f"PRAGMA index_info({name})").fetchall()
                ]
                for name in (
                    "ux_wire_wear_cycle_identity",
                    "idx_wire_wear_cycle_tl_history",
                    "ux_wire_wear_parent_cycle",
                )
            }
            cascade_foreign_keys = {
                table: {
                    (row["from"], row["table"], row["to"], row["on_delete"])
                    for row in conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
                }
                for table in (
                    "wire_wear_cycle_segments",
                    "wire_wear_cycle_records",
                    "wire_wear_conflict_decisions",
                )
            }
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert actual_columns == expected_columns
    assert index_columns == {
        "ux_wire_wear_cycle_identity": [
            "line_group", "line_class", "cycle_date", "tension_length"
        ],
        "idx_wire_wear_cycle_tl_history": [
            "line_group", "line_class", "tension_length", "cycle_date"
        ],
        "ux_wire_wear_parent_cycle": ["line_group", "line_class", "cycle_date"],
    }
    for foreign_keys in cascade_foreign_keys.values():
        assert ("cycle_id", "wire_wear_cycles", "cycle_id", "CASCADE") in foreign_keys


def test_migration_1_5_upgrades_interim_table_destructively_without_backup(tmp_path, monkeypatch):
    db_path = tmp_path / "interim_cycle_schema.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE wire_wear_cycle_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_group TEXT NOT NULL,
                cycle_date TEXT NOT NULL,
                tension_length TEXT NOT NULL,
                track TEXT NOT NULL,
                from_m REAL NOT NULL,
                to_m REAL NOT NULL,
                avg_wear_min REAL NOT NULL,
                wear_percentage REAL NOT NULL,
                sd REAL NOT NULL DEFAULT 0,
                source_type TEXT NOT NULL DEFAULT 'analysis',
                source_file_names TEXT,
                saved_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(line_group, cycle_date, tension_length)
            );
            CREATE INDEX idx_wire_wear_cycle_date ON wire_wear_cycle_records(cycle_date);
            CREATE TRIGGER trg_wire_wear_cycle_updated_at
            AFTER UPDATE ON wire_wear_cycle_records
            BEGIN
                UPDATE wire_wear_cycle_records
                SET updated_at = CURRENT_TIMESTAMP
                WHERE record_id = NEW.record_id;
            END;
            INSERT INTO wire_wear_cycle_records (
                line_group, cycle_date, tension_length, track, from_m, to_m,
                avg_wear_min, wear_percentage, sd
            ) VALUES ('EAL', '2026-05-01', 'H01', 'UP', 0, 100, 12.1, 4.5, 0.1);
            """
        )
        conn.commit()
    finally:
        conn.close()

    original_connect = sqlite3.connect

    class BackupTrackingConnection(sqlite3.Connection):
        backup_calls = 0

        def backup(self, *args, **kwargs):
            type(self).backup_calls += 1
            return super().backup(*args, **kwargs)

    def tracking_connect(*args, **kwargs):
        return original_connect(*args, factory=BackupTrackingConnection, **kwargs)

    monkeypatch.setattr("app.core.database.sqlite3.connect", tracking_connect)

    db = DatabaseManager(str(db_path))
    try:
        with db.get_connection() as migrated:
            columns = {
                row["name"]
                for row in migrated.execute("PRAGMA table_info(wire_wear_cycle_records)").fetchall()
            }
            record_count = migrated.execute(
                "SELECT COUNT(*) AS count FROM wire_wear_cycle_records"
            ).fetchone()["count"]
            retired_objects = migrated.execute(
                """
                SELECT name FROM sqlite_master
                WHERE name IN ('idx_wire_wear_cycle_date', 'trg_wire_wear_cycle_updated_at')
                   OR lower(name) LIKE '%backup%'
                   OR lower(name) LIKE '%legacy%'
                """
            ).fetchall()
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert "cycle_id" in columns
    assert "measurement_sd" in columns
    assert "sd" not in columns
    assert record_count == 0
    assert retired_objects == []
    assert BackupTrackingConnection.backup_calls == 0
    assert set(tmp_path.iterdir()) == {db_path}


def test_migration_1_5_rolls_back_interim_upgrade_when_late_schema_statement_fails(
    tmp_path, monkeypatch
):
    import io

    import pytest

    from app.core import database as database_module

    db_path = tmp_path / "atomic_interim_cycle_schema.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE wire_wear_cycle_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_group TEXT NOT NULL,
                cycle_date TEXT NOT NULL,
                tension_length TEXT NOT NULL,
                track TEXT NOT NULL,
                from_m REAL NOT NULL,
                to_m REAL NOT NULL,
                avg_wear_min REAL NOT NULL,
                wear_percentage REAL NOT NULL,
                sd REAL NOT NULL DEFAULT 0
            );
            INSERT INTO wire_wear_cycle_records (
                line_group, cycle_date, tension_length, track, from_m, to_m,
                avg_wear_min, wear_percentage, sd
            ) VALUES ('EAL', '2026-05-01', 'H01', 'UP', 0, 100, 12.1, 4.5, 0.1);
            """
        )
        conn.commit()
    finally:
        conn.close()

    schema_path = database_module.Path(database_module.__file__).parent / "schema.sql"
    failing_schema = schema_path.read_text(encoding="utf-8") + """
        CREATE TABLE late_schema_marker (id INTEGER PRIMARY KEY);
        INSERT INTO missing_late_schema_table (id) VALUES (1);
    """
    original_open = open

    def failing_schema_open(path, *args, **kwargs):
        if database_module.Path(path) == schema_path:
            return io.StringIO(failing_schema)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(database_module, "open", failing_schema_open, raising=False)

    try:
        with pytest.raises(sqlite3.OperationalError, match="missing_late_schema_table"):
            DatabaseManager(str(db_path))
    finally:
        DatabaseManager.reset_instance()

    conn = sqlite3.connect(db_path)
    try:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(wire_wear_cycle_records)")
        }
        row = conn.execute(
            "SELECT line_group, tension_length, sd FROM wire_wear_cycle_records"
        ).fetchone()
        marker = conn.execute(
            "SELECT name FROM sqlite_master WHERE name = 'late_schema_marker'"
        ).fetchone()
    finally:
        conn.close()

    assert "sd" in columns
    assert "cycle_id" not in columns
    assert row == ("EAL", "H01", 0.1)
    assert marker is None


def test_complete_cycle_schema_ddl_matches_python_migration():
    from app.core import database as database_module

    def normalized_ddl(sql):
        without_identifier_quotes = (
            sql.replace("IF NOT EXISTS", "")
            .replace('"', "")
            .replace("`", "")
            .replace("[", "")
            .replace("]", "")
        )
        return " ".join(without_identifier_quotes.split())

    schema_sql = (
        database_module.Path(database_module.__file__).parent / "schema.sql"
    ).read_text(encoding="utf-8")
    schema_conn = sqlite3.connect(":memory:")
    migration_conn = sqlite3.connect(":memory:")
    schema_conn.row_factory = sqlite3.Row
    migration_conn.row_factory = sqlite3.Row
    try:
        schema_conn.execute("PRAGMA foreign_keys = ON")
        migration_conn.execute("PRAGMA foreign_keys = ON")
        schema_conn.executescript(schema_sql)
        manager = object.__new__(DatabaseManager)
        manager._apply_wire_wear_cycle_records_migration(migration_conn)

        tables = (
            "wire_wear_cycles",
            "wire_wear_cycle_segments",
            "wire_wear_cycle_records",
            "wire_wear_conflict_decisions",
            "wire_wear_deletion_tombstones",
        )
        for table in tables:
            schema_columns = [tuple(row) for row in schema_conn.execute(f"PRAGMA table_info({table})")]
            migration_columns = [
                tuple(row) for row in migration_conn.execute(f"PRAGMA table_info({table})")
            ]
            schema_foreign_keys = [
                tuple(row) for row in schema_conn.execute(f"PRAGMA foreign_key_list({table})")
            ]
            migration_foreign_keys = [
                tuple(row) for row in migration_conn.execute(f"PRAGMA foreign_key_list({table})")
            ]
            schema_indexes = {
                row["name"]: (
                    row["unique"],
                    tuple(
                        column["name"]
                        for column in schema_conn.execute(f"PRAGMA index_info({row['name']})")
                    ),
                )
                for row in schema_conn.execute(f"PRAGMA index_list({table})")
            }
            migration_indexes = {
                row["name"]: (
                    row["unique"],
                    tuple(
                        column["name"]
                        for column in migration_conn.execute(
                            f"PRAGMA index_info({row['name']})"
                        )
                    ),
                )
                for row in migration_conn.execute(f"PRAGMA index_list({table})")
            }
            schema_table_sql = schema_conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table,),
            ).fetchone()["sql"]
            migration_table_sql = migration_conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table,),
            ).fetchone()["sql"]

            assert migration_columns == schema_columns
            assert migration_foreign_keys == schema_foreign_keys
            assert migration_indexes == schema_indexes
            assert normalized_ddl(migration_table_sql) == normalized_ddl(schema_table_sql)
    finally:
        schema_conn.close()
        migration_conn.close()


def test_migration_1_5_is_idempotent_and_preserves_final_records(tmp_path):
    db = DatabaseManager(str(tmp_path / "idempotent_cycle_schema.db"))
    try:
        with db.get_connection() as conn:
            cycle_id = conn.execute(
                """
                INSERT INTO wire_wear_cycles (
                    line_group, line_class, cycle_date, source_type, completeness_state
                ) VALUES ('EAL', 'EAL', '2026-05-01', 'analysis', 'complete')
                """
            ).lastrowid
            conn.execute(
                """
                INSERT INTO wire_wear_cycle_records (
                    cycle_id, line_group, line_class, cycle_date, tension_length, track,
                    from_m, to_m, avg_wear_min, wear_percentage
                ) VALUES (?, 'EAL', 'EAL', '2026-05-01', 'H01', 'UP', 0, 100, 12.1, 4.5)
                """,
                (cycle_id,),
            )

            db._apply_wire_wear_cycle_records_migration(conn)
            db._apply_wire_wear_cycle_records_migration(conn)

            record_count = conn.execute(
                "SELECT COUNT(*) AS count FROM wire_wear_cycle_records"
            ).fetchone()["count"]
            migration_count = conn.execute(
                "SELECT COUNT(*) AS count FROM schema_migrations WHERE version = '1.5'"
            ).fetchone()["count"]
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert record_count == 1
    assert migration_count == 1


def test_migration_1_7_initializes_line_class_metadata(tmp_path):
    db = DatabaseManager(str(tmp_path / "complete_cycle_metadata.db"))
    try:
        with db.get_connection() as conn:
            metadata = {
                row["key"]: row["value"]
                for row in conn.execute(
                    """
                    SELECT key, value FROM system_metadata
                    WHERE key IN ('schema_version', 'last_migration', 'wire_wear_data_version')
                    """
                ).fetchall()
            }
            migration = conn.execute(
                "SELECT description FROM schema_migrations WHERE version = '1.7'"
            ).fetchone()
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert metadata == {
        "schema_version": "1.7",
        "last_migration": "1.7",
        "wire_wear_data_version": "0",
    }
    assert migration is not None
    assert "line_class" in migration["description"]


@pytest.mark.parametrize(
    "existing_line_class_scope", [None, "parent", "all_with_legacy_unique"]
)
def test_migration_1_7_preserves_normalized_graph_and_is_idempotent(
    tmp_path, existing_line_class_scope
):
    db_path = tmp_path / "pre_line_class.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE system_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE schema_migrations (
                version TEXT PRIMARY KEY,
                description TEXT,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO system_metadata (key, value) VALUES
                ('schema_version', '1.6'),
                ('last_migration', '1.6'),
                ('wire_wear_data_version', '37');

            CREATE TABLE wire_wear_cycles (
                cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_group TEXT NOT NULL,
                cycle_date TEXT NOT NULL,
                source_type TEXT NOT NULL,
                acquisition_date_from TEXT,
                acquisition_date_to TEXT,
                completeness_state TEXT NOT NULL,
                source_lineage TEXT NOT NULL DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(line_group, cycle_date)
            );
            CREATE TABLE wire_wear_cycle_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                line_group TEXT NOT NULL,
                cycle_date TEXT NOT NULL,
                tension_length TEXT NOT NULL,
                track TEXT NOT NULL,
                from_m REAL NOT NULL,
                to_m REAL NOT NULL,
                avg_wear_min REAL NOT NULL,
                wear_percentage REAL NOT NULL,
                measurement_sd REAL,
                physical_intervals TEXT NOT NULL DEFAULT '[]',
                source_lineage TEXT NOT NULL DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(line_group, cycle_date, tension_length),
                FOREIGN KEY (cycle_id) REFERENCES wire_wear_cycles(cycle_id) ON DELETE CASCADE
            );
            CREATE TABLE wire_wear_cycle_segments (
                segment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                segment_name TEXT NOT NULL,
                is_present INTEGER NOT NULL,
                coverage_percentage REAL NOT NULL,
                diagnostic_gaps TEXT NOT NULL DEFAULT '[]',
                source_file_names TEXT NOT NULL DEFAULT '[]',
                acquisition_date_from TEXT,
                acquisition_date_to TEXT,
                UNIQUE(cycle_id, segment_name),
                FOREIGN KEY (cycle_id) REFERENCES wire_wear_cycles(cycle_id) ON DELETE CASCADE
            );
            CREATE TABLE wire_wear_conflict_decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                measurement_identity TEXT NOT NULL,
                source_values TEXT NOT NULL,
                selected_wear_min REAL NOT NULL,
                accepted_at DATETIME NOT NULL,
                UNIQUE(cycle_id, measurement_identity),
                FOREIGN KEY (cycle_id) REFERENCES wire_wear_cycles(cycle_id) ON DELETE CASCADE
            );
            CREATE TABLE wire_wear_deletion_tombstones (
                tombstone_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_group TEXT NOT NULL,
                cycle_date TEXT NOT NULL,
                tension_length TEXT NOT NULL,
                deleted_at DATETIME NOT NULL,
                source_package_id TEXT,
                UNIQUE(line_group, cycle_date, tension_length)
            );

            INSERT INTO wire_wear_cycles VALUES (
                41, 'EAL', '2026-05-28', 'analysis', '2026-05-27', '2026-05-28',
                'complete', '["source-a.xlsx"]', '2026-06-01 01:02:03', '2026-06-02 04:05:06'
            );
            INSERT INTO wire_wear_cycle_records VALUES (
                73, 41, 'EAL', '2026-05-28', '28', 'UP', 100, 200, 11.25, 9.5,
                0.2, '[{"track":"UP","from_m":100,"to_m":200}]',
                '["source-a.xlsx"]', '2026-06-01 01:02:03', '2026-06-02 04:05:06'
            );
            INSERT INTO wire_wear_cycle_segments VALUES (
                11, 41, 'U1', 1, 100, '[]', '["source-a.xlsx"]',
                '2026-05-27', '2026-05-28'
            );
            INSERT INTO wire_wear_conflict_decisions VALUES (
                19, 41, 'measurement-28', '[["a.xlsx",11.3],["b.xlsx",11.25]]',
                11.25, '2026-06-02 04:05:06'
            );
            INSERT INTO wire_wear_deletion_tombstones VALUES (
                23, 'TML', '2026-04-01', 'T01', '2026-06-03 07:08:09', 'package-1'
            );
            """
        )
        if existing_line_class_scope is not None:
            conn.execute("ALTER TABLE wire_wear_cycles ADD COLUMN line_class TEXT")
            conn.execute("UPDATE wire_wear_cycles SET line_class = 'LMC'")
        if existing_line_class_scope == "all_with_legacy_unique":
            conn.execute("ALTER TABLE wire_wear_cycle_records ADD COLUMN line_class TEXT")
            conn.execute("UPDATE wire_wear_cycle_records SET line_class = 'LMC'")
            conn.execute("ALTER TABLE wire_wear_deletion_tombstones ADD COLUMN line_class TEXT")
            conn.execute(
                "UPDATE wire_wear_deletion_tombstones "
                "SET line_class = CASE WHEN line_group = 'TML' THEN 'TML' ELSE 'EAL' END"
            )
            conn.execute(
                "CREATE UNIQUE INDEX ux_partial_cycles ON wire_wear_cycles"
                "(line_group, line_class, cycle_date)"
            )
            conn.execute(
                "CREATE UNIQUE INDEX ux_partial_records ON wire_wear_cycle_records"
                "(line_group, line_class, cycle_date, tension_length)"
            )
            conn.execute(
                "CREATE UNIQUE INDEX ux_partial_tombstones ON wire_wear_deletion_tombstones"
                "(line_group, line_class, cycle_date, tension_length)"
            )
        conn.commit()
    finally:
        conn.close()

    db = DatabaseManager(str(db_path))
    try:
        with db.get_connection() as migrated:
            db._apply_wire_wear_cycle_records_migration(migrated)
            cycle = dict(migrated.execute("SELECT * FROM wire_wear_cycles").fetchone())
            record = dict(migrated.execute("SELECT * FROM wire_wear_cycle_records").fetchone())
            segment = dict(migrated.execute("SELECT * FROM wire_wear_cycle_segments").fetchone())
            decision = dict(migrated.execute("SELECT * FROM wire_wear_conflict_decisions").fetchone())
            tombstone = dict(
                migrated.execute("SELECT * FROM wire_wear_deletion_tombstones").fetchone()
            )
            data_version = migrated.execute(
                "SELECT value FROM system_metadata WHERE key = 'wire_wear_data_version'"
            ).fetchone()["value"]
            migration_count = migrated.execute(
                "SELECT COUNT(*) AS count FROM schema_migrations WHERE version = '1.7'"
            ).fetchone()["count"]
            record_unique_shapes = {
                tuple(
                    row["name"]
                    for row in migrated.execute(
                        f"PRAGMA index_info({index['name']})"
                    ).fetchall()
                )
                for index in migrated.execute(
                    "PRAGMA index_list(wire_wear_cycle_records)"
                ).fetchall()
                if index["unique"]
            }
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert cycle == {
        "cycle_id": 41,
        "line_group": "EAL",
        "line_class": "LMC" if existing_line_class_scope else "EAL",
        "cycle_date": "2026-05-28",
        "source_type": "analysis",
        "acquisition_date_from": "2026-05-27",
        "acquisition_date_to": "2026-05-28",
        "completeness_state": "complete",
        "source_lineage": '["source-a.xlsx"]',
        "created_at": "2026-06-01 01:02:03",
        "updated_at": "2026-06-02 04:05:06",
    }
    assert record["record_id"] == 73
    assert record["cycle_id"] == 41
    assert record["line_class"] == ("LMC" if existing_line_class_scope else "EAL")
    assert record["source_lineage"] == '["source-a.xlsx"]'
    assert record["created_at"] == "2026-06-01 01:02:03"
    assert record["updated_at"] == "2026-06-02 04:05:06"
    assert segment["segment_id"] == 11 and segment["cycle_id"] == 41
    assert decision["decision_id"] == 19 and decision["cycle_id"] == 41
    assert tombstone["tombstone_id"] == 23
    assert tombstone["line_class"] == "TML"
    assert data_version == "37"
    assert migration_count == 1
    assert ("line_group", "line_class", "cycle_date", "tension_length") in record_unique_shapes
    assert ("line_group", "cycle_date", "tension_length") not in record_unique_shapes


def test_wire_wear_records_migration_upgrades_legacy_table(tmp_path):
    db_path = tmp_path / "legacy_wire_wear.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE wire_wear_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_group TEXT NOT NULL,
                track TEXT NOT NULL,
                section TEXT NOT NULL,
                cycle_date TEXT NOT NULL,
                tension_length TEXT NOT NULL,
                from_m REAL NOT NULL,
                to_m REAL NOT NULL,
                avg_wear_min REAL NOT NULL,
                sd REAL NOT NULL DEFAULT 0,
                wear_percentage REAL NOT NULL,
                source_file_names TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(line_group, track, section, cycle_date, tension_length)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO wire_wear_records (
                line_group, track, section, cycle_date, tension_length,
                from_m, to_m, avg_wear_min, sd, wear_percentage
            ) VALUES ('EAL', 'UP', 'LMC', '2026-02-01', 'H46', 0, 50, 12.4, 0.1, 6.5)
            """
        )
        conn.commit()
    finally:
        conn.close()

    db = DatabaseManager(str(db_path))
    try:
        with db.get_connection() as migrated:
            columns = {
                row["name"]
                for row in migrated.execute("PRAGMA table_info(wire_wear_records)").fetchall()
            }
            row = migrated.execute("SELECT * FROM wire_wear_records WHERE tension_length = 'H46'").fetchone()
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert "line_class" in columns
    assert "saved_by" in columns
    assert row["line_group"] == "EAL"
    assert row["line_class"] == "LMC"


def test_wire_wear_records_migration_handles_minimal_incomplete_table(tmp_path):
    db_path = tmp_path / "minimal_legacy_wire_wear.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE wire_wear_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_date TEXT,
                tension_length TEXT,
                from_m REAL,
                to_m REAL,
                avg_wear_min REAL,
                wear_percentage REAL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO wire_wear_records (
                cycle_date, tension_length, from_m, to_m, avg_wear_min, wear_percentage
            ) VALUES ('2026-02-01', 'H01', 0, 50, 12.4, 6.5)
            """
        )
        conn.commit()
    finally:
        conn.close()

    db = DatabaseManager(str(db_path))
    try:
        with db.get_connection() as migrated:
            row = migrated.execute("SELECT * FROM wire_wear_records WHERE tension_length = 'H01'").fetchone()
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert row["line_group"] == "EAL"
    assert row["line_class"] == "EAL"
    assert row["track"] == ""
    assert row["section"] == "Mainline"


def test_wire_wear_records_migration_preserves_collision_source_rows(tmp_path):
    db_path = tmp_path / "collision_legacy_wire_wear.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE wire_wear_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_group TEXT NOT NULL,
                track TEXT NOT NULL,
                section TEXT NOT NULL,
                cycle_date TEXT NOT NULL,
                tension_length TEXT NOT NULL,
                from_m REAL NOT NULL,
                to_m REAL NOT NULL,
                avg_wear_min REAL NOT NULL,
                wear_percentage REAL NOT NULL
            )
            """
        )
        for avg_wear_min in (12.4, 12.1):
            conn.execute(
                """
                INSERT INTO wire_wear_records (
                    line_group, track, section, cycle_date, tension_length,
                    from_m, to_m, avg_wear_min, wear_percentage
                ) VALUES ('EAL', 'UP', 'Mainline', '2026-02-01', 'H01', 0, 50, ?, 6.5)
                """,
                (avg_wear_min,),
            )
        conn.commit()
    finally:
        conn.close()

    db = DatabaseManager(str(db_path))
    try:
        with db.get_connection() as migrated:
            migrated_count = migrated.execute("SELECT COUNT(*) AS count FROM wire_wear_records").fetchone()["count"]
            preserved_count = migrated.execute(
                "SELECT COUNT(*) AS count FROM wire_wear_records_migration_conflicts"
            ).fetchone()["count"]
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert migrated_count == 1
    assert preserved_count == 2


def test_save_wire_wear_records_maps_lmc_to_eal_group(tmp_path):
    from app.core.calculation.wear_records import (
        WireWearRecordInput,
        WireWearSaveRequest,
        query_wire_wear_records,
        save_wire_wear_records,
    )

    db = DatabaseManager(str(tmp_path / "wear_records_save.db"))
    try:
        request = WireWearSaveRequest(
            line_group="EAL",
            line_class="LMC",
            track="UP",
            section="LMC",
            cycle_date="2026-02-01",
            source_file_names=["cycle.xlsx"],
            saved_by="tester",
            records=[
                WireWearRecordInput(
                    tension_length="H46",
                    from_m=100.0,
                    to_m=200.0,
                    avg_wear_min=12.4,
                    sd=0.2,
                    wear_percentage=6.5,
                )
            ],
        )
        with db.get_connection() as conn:
            result = save_wire_wear_records(conn, request, overwrite=False)
            records = query_wire_wear_records(conn, {"line_group": "EAL"})
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert result.saved_count == 1
    assert result.updated_count == 0
    assert records[0]["line_group"] == "EAL"
    assert records[0]["line_class"] == "LMC"
    assert records[0]["source_file_names"] == ["cycle.xlsx"]
    assert records[0]["saved_by"] == "tester"


def test_save_wire_wear_records_detects_duplicate_without_overwrite(tmp_path):
    from app.core.calculation.wear_records import (
        WireWearRecordInput,
        WireWearSaveRequest,
        save_wire_wear_records,
    )

    db = DatabaseManager(str(tmp_path / "wear_records_duplicate.db"))
    try:
        request = WireWearSaveRequest(
            line_group="TML",
            line_class="TML",
            track="UP",
            section="Mainline",
            cycle_date="2026-02-01",
            source_file_names=[],
            records=[
                WireWearRecordInput("H01", 0.0, 50.0, 12.8, 0.1, 3.2),
            ],
        )
        with db.get_connection() as conn:
            first = save_wire_wear_records(conn, request, overwrite=False)
            second = save_wire_wear_records(conn, request, overwrite=False)
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert first.saved_count == 1
    assert second.saved_count == 0
    assert second.duplicate_count == 1
    assert second.duplicates[0]["tension_length"] == "H01"


def test_save_wire_wear_records_overwrites_duplicates(tmp_path):
    from app.core.calculation.wear_records import (
        WireWearRecordInput,
        WireWearSaveRequest,
        query_wire_wear_records,
        save_wire_wear_records,
    )

    db = DatabaseManager(str(tmp_path / "wear_records_overwrite.db"))
    try:
        request = WireWearSaveRequest(
            line_group="EAL",
            line_class="EAL",
            track="UP",
            section="Mainline",
            cycle_date="2026/02/01",
            source_file_names=["old.xlsx"],
            records=[WireWearRecordInput("H01", 0.0, 50.0, 12.8, 0.1, 3.2)],
        )
        replacement = WireWearSaveRequest(
            line_group="EAL",
            line_class="EAL",
            track="UP",
            section="Mainline",
            cycle_date="20260201",
            source_file_names=["new.xlsx"],
            records=[WireWearRecordInput("H01", 0.0, 50.0, 12.0, 0.2, 8.0)],
        )
        with db.get_connection() as conn:
            save_wire_wear_records(conn, request, overwrite=False)
            result = save_wire_wear_records(conn, replacement, overwrite=True)
            records = query_wire_wear_records(conn, {"tension_length": "H01"})
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert result.saved_count == 0
    assert result.updated_count == 1
    assert result.duplicate_count == 1
    assert records[0]["cycle_date"] == "2026-02-01"
    assert records[0]["wear_percentage"] == 8.0
    assert records[0]["source_file_names"] == ["new.xlsx"]


def _seed_rate_records(conn: sqlite3.Connection) -> None:
    from app.core.calculation.wear_records import (
        WireWearRecordInput,
        WireWearSaveRequest,
        save_wire_wear_records,
    )

    save_wire_wear_records(
        conn,
        WireWearSaveRequest(
            line_group="EAL",
            line_class="EAL",
            track="UP",
            section="Mainline",
            cycle_date="2024-01-01",
            source_file_names=[],
            records=[
                WireWearRecordInput("H01", 0.0, 50.0, 12.8, 0.1, 3.0),
                WireWearRecordInput("H02", 50.0, 100.0, 12.6, 0.1, 5.0),
            ],
        ),
        overwrite=False,
    )
    save_wire_wear_records(
        conn,
        WireWearSaveRequest(
            line_group="EAL",
            line_class="EAL",
            track="UP",
            section="Mainline",
            cycle_date="2025-01-01",
            source_file_names=[],
            records=[
                WireWearRecordInput("H01", 0.0, 50.0, 12.7, 0.1, 4.0),
                WireWearRecordInput("H02", 50.0, 100.0, 12.2, 0.1, 9.0),
            ],
        ),
        overwrite=False,
    )
    save_wire_wear_records(
        conn,
        WireWearSaveRequest(
            line_group="EAL",
            line_class="LMC",
            track="UP",
            section="LMC",
            cycle_date="2024-01-01",
            source_file_names=[],
            records=[
                WireWearRecordInput("H01", 0.0, 50.0, 12.9, 0.1, 1.0),
                WireWearRecordInput("H02", 50.0, 100.0, 12.8, 0.1, 3.0),
            ],
        ),
        overwrite=False,
    )
    save_wire_wear_records(
        conn,
        WireWearSaveRequest(
            line_group="EAL",
            line_class="LMC",
            track="UP",
            section="LMC",
            cycle_date="2025-01-01",
            source_file_names=[],
            records=[
                WireWearRecordInput("H01", 0.0, 50.0, 12.7, 0.1, 4.0),
                WireWearRecordInput("H02", 50.0, 100.0, 12.2, 0.1, 9.0),
            ],
        ),
        overwrite=False,
    )


def test_dashboard_summary_splits_lmc_under_eal(tmp_path):
    from app.core.calculation.wear_records import build_dashboard_summary

    db = DatabaseManager(str(tmp_path / "wear_dashboard.db"))
    try:
        with db.get_connection() as conn:
            _seed_rate_records(conn)
            summary = build_dashboard_summary(conn)
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert "EAL" in summary
    assert "TML" in summary
    assert summary["EAL"]["top_max_rate"][0]["tension_length"] == "H02"
    assert summary["EAL"]["top_max_rate"][0]["wear_percent_per_year"] > 3.9
    assert summary["EAL"]["top_current_wear"][0]["tension_length"] == "H02"
    assert summary["TML"]["top_max_rate"] == []


def test_projection_summary_buckets_next_30_years(tmp_path):
    from app.core.calculation.wear_records import build_projection_summary

    db = DatabaseManager(str(tmp_path / "wear_projection.db"))
    try:
        with db.get_connection() as conn:
            _seed_rate_records(conn)
            projection = build_projection_summary(conn, threshold_percentage=20.0, years=30)
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert projection["threshold_percentage"] == 20.0
    assert projection["years"] == 30
    assert projection["line_groups"]["EAL"]["records"]
    assert projection["line_groups"]["EAL"]["year_buckets"]
    assert sum(bucket["count"] for bucket in projection["line_groups"]["EAL"]["year_buckets"]) >= 1


def test_projection_summary_anchors_projected_year_to_latest_cycle_date(tmp_path):
    from app.core.calculation.wear_records import (
        WireWearRecordInput,
        WireWearSaveRequest,
        build_projection_summary,
        save_wire_wear_records,
    )

    db = DatabaseManager(str(tmp_path / "wear_projection_anchor.db"))
    try:
        with db.get_connection() as conn:
            save_wire_wear_records(
                conn,
                WireWearSaveRequest(
                    line_group="EAL",
                    line_class="EAL",
                    track="UP",
                    section="Mainline",
                    cycle_date="2023-01-01",
                    source_file_names=[],
                    records=[WireWearRecordInput("H77", 0.0, 50.0, 12.0, 0.1, 10.0)],
                ),
            )
            save_wire_wear_records(
                conn,
                WireWearSaveRequest(
                    line_group="EAL",
                    line_class="EAL",
                    track="UP",
                    section="Mainline",
                    cycle_date="2024-01-01",
                    source_file_names=[],
                    records=[WireWearRecordInput("H77", 0.0, 50.0, 11.0, 0.1, 15.0)],
                ),
            )
            projection = build_projection_summary(conn, threshold_percentage=20.0, years=30)
    finally:
        db.close()
        DatabaseManager.reset_instance()

    projected = next(
        row
        for row in projection["line_groups"]["EAL"]["records"]
        if row["tension_length"] == "H77"
    )
    assert projected["projected_year"] == 2025


def test_rate_dashboard_projection_keep_track_section_and_class_separate(tmp_path):
    from app.core.calculation.wear_records import (
        WireWearRecordInput,
        WireWearSaveRequest,
        build_dashboard_summary,
        build_projection_summary,
        save_wire_wear_records,
    )

    db = DatabaseManager(str(tmp_path / "wear_identity_rates.db"))
    try:
        with db.get_connection() as conn:
            for cycle_date, eal_up, eal_dn, lmc_up in (
                ("2024-01-01", 1.0, 2.0, 5.0),
                ("2025-01-01", 11.0, 4.0, 6.0),
            ):
                save_wire_wear_records(
                    conn,
                    WireWearSaveRequest(
                        line_group="EAL",
                        line_class="EAL",
                        track="UP",
                        section="Mainline",
                        cycle_date=cycle_date,
                        source_file_names=[],
                        records=[WireWearRecordInput("H99", 0.0, 50.0, 12.0, 0.1, eal_up)],
                    ),
                )
                save_wire_wear_records(
                    conn,
                    WireWearSaveRequest(
                        line_group="EAL",
                        line_class="EAL",
                        track="DN",
                        section="Mainline",
                        cycle_date=cycle_date,
                        source_file_names=[],
                        records=[WireWearRecordInput("H99", 50.0, 100.0, 12.0, 0.1, eal_dn)],
                    ),
                )
                save_wire_wear_records(
                    conn,
                    WireWearSaveRequest(
                        line_group="EAL",
                        line_class="LMC",
                        track="UP",
                        section="LMC",
                        cycle_date=cycle_date,
                        source_file_names=[],
                        records=[WireWearRecordInput("H99", 100.0, 150.0, 12.0, 0.1, lmc_up)],
                    ),
                )

            dashboard = build_dashboard_summary(conn)
            projection = build_projection_summary(conn, threshold_percentage=20.0, years=30)
    finally:
        db.close()
        DatabaseManager.reset_instance()

    dashboard_rows = [
        row
        for row in dashboard["EAL"]["top_current_wear"]
        if row["tension_length"] == "H99"
    ]
    projection_rows = [
        row
        for row in projection["line_groups"]["EAL"]["records"]
        if row["tension_length"] == "H99"
    ]

    dashboard_identities = {
        (row["line_group"], row["line_class"], row["track"], row["section"], row["tension_length"])
        for row in dashboard_rows
    }
    projection_identities = {
        (row["line_group"], row["line_class"], row["track"], row["section"], row["tension_length"])
        for row in projection_rows
    }

    assert dashboard_identities == {
        ("EAL", "EAL", "UP", "Mainline", "H99"),
        ("EAL", "EAL", "DN", "Mainline", "H99"),
        ("EAL", "LMC", "UP", "LMC", "H99"),
    }
    assert projection_identities == dashboard_identities
    assert {
        (row["line_class"], row["track"], row["section"]): row["record_count"]
        for row in projection_rows
    } == {
        ("EAL", "UP", "Mainline"): 2,
        ("EAL", "DN", "Mainline"): 2,
        ("LMC", "UP", "LMC"): 2,
    }


def test_workbench_history_averages_raw_rows_by_line_date_and_tension_length(tmp_path):
    from app.core.calculation.wear_records import (
        WireWearRecordInput,
        WireWearSaveRequest,
        build_workbench_summary,
        save_wire_wear_records,
    )

    db = DatabaseManager(str(tmp_path / "wear_workbench_history.db"))
    try:
        with db.get_connection() as conn:
            for line_class, track, section, avg_wear_min, wear_percentage in (
                ("EAL", "UP", "Mainline", 12.0, 6.0),
                ("LMC", "DN", "LMC", 10.0, 8.0),
            ):
                save_wire_wear_records(
                    conn,
                    WireWearSaveRequest(
                        line_group="EAL",
                        line_class=line_class,
                        track=track,
                        section=section,
                        cycle_date="2026-02-01",
                        source_file_names=[],
                        records=[WireWearRecordInput("X1", 0.0, 10.0, avg_wear_min, 0.1, wear_percentage)],
                    ),
                    overwrite=False,
                )

            summary = build_workbench_summary(conn, {"line_group": "EAL"})
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert summary["line_group"] == "EAL"
    assert summary["tension_lengths"] == ["X1"]
    assert summary["history_rows"] == [{"cycle_date": "2026-02-01", "values": {"X1": 11.0}}]
    assert len(summary["detail_records"]["X1"]) == 2


def test_workbench_latest_summary_uses_aggregated_time_series(tmp_path):
    from app.core.calculation.wear_records import (
        WireWearRecordInput,
        WireWearSaveRequest,
        build_workbench_summary,
        save_wire_wear_records,
    )

    db = DatabaseManager(str(tmp_path / "wear_workbench_summary.db"))
    try:
        with db.get_connection() as conn:
            for cycle_date, row_a, row_b in (
                ("2024-01-01", (12.0, 10.0), (10.0, 14.0)),
                ("2025-01-01", (11.0, 14.0), (9.0, 18.0)),
            ):
                for line_class, track, section, values in (
                    ("EAL", "UP", "Mainline", row_a),
                    ("LMC", "DN", "LMC", row_b),
                ):
                    save_wire_wear_records(
                        conn,
                        WireWearSaveRequest(
                            line_group="EAL",
                            line_class=line_class,
                            track=track,
                            section=section,
                            cycle_date=cycle_date,
                            source_file_names=[],
                            records=[WireWearRecordInput("X9", 0.0, 10.0, values[0], 0.1, values[1])],
                        ),
                        overwrite=False,
                    )

            summary = build_workbench_summary(conn, {"line_group": "EAL"})
    finally:
        db.close()
        DatabaseManager.reset_instance()

    metric_rows = {row["metric"]: row["values"] for row in summary["latest_summary_rows"]}
    assert metric_rows["Latest Wear %"]["X9"] == "16.00 %"
    assert metric_rows["Wear % Rate per year"]["X9"].endswith(" % /year")
    assert metric_rows["Wear mm Rate per year"]["X9"].endswith(" mm /year")
    assert metric_rows["20% Wear Projection year"]["X9"] in {"2026", "2027"}
    assert metric_rows["33% Wear Projection year"]["X9"] in {"2029", "2030"}


def test_update_wire_wear_record_updates_only_allowed_fields(tmp_path):
    from app.core.calculation.wear_records import (
        WireWearRecordInput,
        WireWearSaveRequest,
        query_wire_wear_records,
        save_wire_wear_records,
        update_wire_wear_record,
    )

    db = DatabaseManager(str(tmp_path / "wear_update.db"))
    try:
        with db.get_connection() as conn:
            save_wire_wear_records(
                conn,
                WireWearSaveRequest(
                    line_group="EAL",
                    line_class="EAL",
                    track="UP",
                    section="Mainline",
                    cycle_date="2026-02-01",
                    source_file_names=[],
                    records=[WireWearRecordInput("X1", 0.0, 10.0, 12.0, 0.1, 6.0)],
                ),
            )
            record_id = query_wire_wear_records(conn, {"line_group": "EAL"})[0]["record_id"]
            updated = update_wire_wear_record(conn, record_id, {"avg_wear_min": 11.5, "wear_percentage": 8.0})
            rows = query_wire_wear_records(conn, {"line_group": "EAL"})
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert updated is True
    assert rows[0]["avg_wear_min"] == 11.5
    assert rows[0]["wear_percentage"] == 8.0


def test_delete_wire_wear_record_removes_one_row(tmp_path):
    from app.core.calculation.wear_records import (
        WireWearRecordInput,
        WireWearSaveRequest,
        delete_wire_wear_record,
        query_wire_wear_records,
        save_wire_wear_records,
    )

    db = DatabaseManager(str(tmp_path / "wear_delete.db"))
    try:
        with db.get_connection() as conn:
            save_wire_wear_records(
                conn,
                WireWearSaveRequest(
                    line_group="EAL",
                    line_class="EAL",
                    track="UP",
                    section="Mainline",
                    cycle_date="2026-02-01",
                    source_file_names=[],
                    records=[
                        WireWearRecordInput("X1", 0.0, 10.0, 12.0, 0.1, 6.0),
                        WireWearRecordInput("X2", 10.0, 20.0, 11.0, 0.1, 9.0),
                    ],
                ),
            )
            rows = query_wire_wear_records(conn, {"line_group": "EAL"})
            deleted = delete_wire_wear_record(conn, rows[0]["record_id"])
            remaining = query_wire_wear_records(conn, {"line_group": "EAL"})
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert deleted is True
    assert len(remaining) == 1
    assert remaining[0]["tension_length"] == "X2"


def _cycle_key(line_group="EAL", cycle_date="2026-05-28", tension_length="28"):
    from app.core.calculation.wear_cycle_types import BusinessKey

    return BusinessKey(line_group, date.fromisoformat(cycle_date), tension_length)


def _metadata(*rows):
    from app.core.calculation.wear_cycle_types import MetadataInterval

    return tuple(
        MetadataInterval(tl, track, Decimal(str(start)), Decimal(str(end)), sheet)
        for tl, track, start, end, sheet in rows
    )


def _preview(
    *,
    line_group="EAL",
    cycle_date="2026-05-28",
    records=None,
    can_save=True,
    conflicts=(),
    segments=None,
    blocking_reasons=None,
):
    from app.core.calculation.wear_cycle_types import (
        AggregatedWearRecord,
        CyclePreview,
        SegmentCoverage,
    )

    if records is None:
        records = (
            AggregatedWearRecord(
                _cycle_key(line_group, cycle_date, "28"),
                "Siding",
                Decimal("111361"),
                Decimal("112486.5"),
                11.45,
                8.96,
                0.75,
                bool(conflicts),
                tuple(item.conflict_id for item in conflicts),
                ("u1.xlsx", "d1.xlsx"),
            ),
        )
    if segments is None:
        segments = (
            SegmentCoverage(
                "U1",
                True,
                80.0,
                ("TL29",),
                ("u1.xlsx",),
                (date(2026, 5, 27), date(2026, 5, 28)),
            ),
        )
    if blocking_reasons is None:
        blocking_reasons = () if can_save else ("unknown_segment",)
    return CyclePreview(
        line_group,
        date.fromisoformat(cycle_date),
        tuple(records),
        tuple(segments),
        tuple(conflicts),
        (),
        tuple(blocking_reasons),
        can_save,
        datetime(2026, 5, 28, 12, tzinfo=timezone.utc),
    )


def test_save_analysis_cycle_persists_complete_cycle_and_conflict_audit_once(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        get_wire_wear_data_version,
        list_committed_records,
        save_analysis_cycle,
    )
    from app.core.calculation.wear_cycle_types import ConflictPreview

    conflict = ConflictPreview(
        "conflict-1",
        "stable:m1",
        (("u1.xlsx", 11.45), ("overlap.xlsx", 11.55)),
        11.45,
        True,
    )
    db = DatabaseManager(str(tmp_path / "analysis_cycle.db"))
    try:
        with db.get_connection() as conn:
            save_analysis_cycle(conn, _preview(conflicts=(conflict,)))
            records = list_committed_records(conn, line_group="EAL")
            parent = conn.execute("SELECT * FROM wire_wear_cycles").fetchone()
            segment = conn.execute("SELECT * FROM wire_wear_cycle_segments").fetchone()
            audit = conn.execute("SELECT * FROM wire_wear_conflict_decisions").fetchone()
            version = get_wire_wear_data_version(conn)
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert len(records) == 1
    assert parent["source_type"] == "analysis"
    assert parent["completeness_state"] == "complete"
    assert json.loads(parent["source_lineage"]) == ["d1.xlsx", "u1.xlsx"]
    assert segment["coverage_percentage"] == 80.0
    assert json.loads(audit["source_values"]) == [["u1.xlsx", 11.45], ["overlap.xlsx", 11.55]]
    assert audit["selected_wear_min"] == 11.45
    assert audit["accepted_at"]
    assert version == 1


def test_normalized_identity_allows_eal_and_lmc_same_cycle_date_and_tl(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        list_committed_records,
        save_analysis_cycle,
    )

    eal = _preview()
    lmc_record = replace(
        eal.records[0],
        key=replace(eal.records[0].key, line_class="LMC"),
        avg_wear_min=10.25,
    )
    lmc = replace(eal, records=(lmc_record,), line_class="LMC")
    db = DatabaseManager(str(tmp_path / "line_class_identity.db"))
    try:
        with db.get_connection() as conn:
            save_analysis_cycle(conn, eal)
            save_analysis_cycle(conn, lmc)
            eal_rows = list_committed_records(
                conn, line_group="EAL", line_class="EAL"
            )
            lmc_rows = list_committed_records(
                conn, line_group="EAL", line_class="LMC"
            )
            parents = conn.execute(
                """
                SELECT line_group, line_class, cycle_date
                FROM wire_wear_cycles
                ORDER BY line_class
                """
            ).fetchall()
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert [(row["line_class"], row["avg_wear_min"]) for row in eal_rows] == [
        ("EAL", 11.45)
    ]
    assert [(row["line_class"], row["avg_wear_min"]) for row in lmc_rows] == [
        ("LMC", 10.25)
    ]
    assert [tuple(row) for row in parents] == [
        ("EAL", "EAL", "2026-05-28"),
        ("EAL", "LMC", "2026-05-28"),
    ]


def test_save_analysis_cycle_persists_missing_segment_as_incomplete(tmp_path):
    from app.core.calculation.wear_cycle_repository import save_analysis_cycle

    complete = _preview()
    missing_segment = replace(
        complete.segments[0],
        segment_name="D2",
        is_present=False,
        coverage_percentage=0,
        diagnostic_gaps=(),
        source_file_names=(),
        acquisition_dates=(),
    )
    preview = _preview(
        can_save=False,
        segments=(complete.segments[0], missing_segment),
        blocking_reasons=("segment_missing",),
    )
    db = DatabaseManager(str(tmp_path / "partial_analysis_cycle.db"))
    try:
        with db.get_connection() as conn:
            saved = save_analysis_cycle(conn, preview)
            parent = conn.execute("SELECT completeness_state FROM wire_wear_cycles").fetchone()
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert saved.completeness_state == "incomplete"
    assert parent["completeness_state"] == "incomplete"
    assert saved.segments[0]["is_present"] == 0


@pytest.mark.parametrize("invalid_preview", [_preview(can_save=False)])
def test_save_analysis_cycle_rejects_hard_blocked_or_duplicate_preview(tmp_path, invalid_preview):
    from app.core.calculation.wear_cycle_repository import (
        WearCycleRepositoryError,
        get_wire_wear_data_version,
        save_analysis_cycle,
    )

    db = DatabaseManager(str(tmp_path / "analysis_reject.db"))
    try:
        with db.get_connection() as conn:
            with pytest.raises(WearCycleRepositoryError, match="cannot be saved"):
                save_analysis_cycle(conn, invalid_preview)
            duplicate_record_preview = _preview(
                records=(_preview().records[0], _preview().records[0])
            )
            with pytest.raises(WearCycleRepositoryError, match="duplicate"):
                save_analysis_cycle(conn, duplicate_record_preview)
            save_analysis_cycle(conn, _preview())
            with pytest.raises(WearCycleRepositoryError, match="duplicate"):
                save_analysis_cycle(conn, _preview())
            counts = tuple(
                conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "wire_wear_cycles",
                    "wire_wear_cycle_segments",
                    "wire_wear_cycle_records",
                )
            )
            version = get_wire_wear_data_version(conn)
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert counts == (1, 1, 1)
    assert version == 1


def test_save_analysis_cycle_rolls_back_parent_segments_records_and_version(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        get_wire_wear_data_version,
        save_analysis_cycle,
    )

    db = DatabaseManager(str(tmp_path / "analysis_rollback.db"))
    try:
        with db.get_connection() as conn:
            conn.execute(
                """
                CREATE TRIGGER reject_cycle_record BEFORE INSERT ON wire_wear_cycle_records
                BEGIN SELECT RAISE(ABORT, 'forced record failure'); END
                """
            )
            conn.commit()
            with pytest.raises(sqlite3.IntegrityError, match="forced record failure"):
                save_analysis_cycle(conn, _preview())
            counts = tuple(
                conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "wire_wear_cycles",
                    "wire_wear_cycle_segments",
                    "wire_wear_cycle_records",
                    "wire_wear_conflict_decisions",
                )
            )
            version = get_wire_wear_data_version(conn)
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert counts == (0, 0, 0, 0)
    assert version == 0


def test_save_analysis_cycle_rejects_stale_data_version_inside_transaction(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        WearCycleRepositoryError,
        get_wire_wear_data_version,
        save_analysis_cycle,
    )

    db = DatabaseManager(str(tmp_path / "analysis_stale_version.db"))
    try:
        with db.get_connection() as conn:
            with pytest.raises(WearCycleRepositoryError, match="data version") as raised:
                save_analysis_cycle(conn, _preview(), expected_data_version=1)
            counts = tuple(
                conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "wire_wear_cycles",
                    "wire_wear_cycle_segments",
                    "wire_wear_cycle_records",
                    "wire_wear_conflict_decisions",
                )
            )
            version = get_wire_wear_data_version(conn)
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert type(raised.value).__name__ == "StaleDataVersionError"
    assert counts == (0, 0, 0, 0)
    assert version == 0


def test_apply_change_set_resolves_manual_metadata_and_bumps_version_once(tmp_path):
    from app.core.calculation.wear_calculator import calculate_wear_percentage
    from app.core.calculation.wear_cycle_repository import (
        AddOperation,
        ChangeSet,
        apply_change_set,
        list_committed_records,
    )

    metadata = _metadata(
        ("28", "UP", 111361, 111633, "EAL UP"),
        ("28", "DN", 111633, 112486.5, "EAL DN"),
        ("29", "UP", 112486.5, 113000, "EAL UP"),
    )
    changes = ChangeSet((
        AddOperation(_cycle_key(tension_length="28"), 11.4),
        AddOperation(_cycle_key(tension_length="29"), 11.2),
    ))
    now = datetime(2026, 6, 1, 8, 30, tzinfo=timezone.utc)
    db = DatabaseManager(str(tmp_path / "manual_add.db"))
    try:
        with db.get_connection() as conn:
            result = apply_change_set(conn, changes, metadata, now=now)
            rows = list_committed_records(conn, line_group="EAL")
            parent = conn.execute("SELECT * FROM wire_wear_cycles").fetchone()
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert result.added == 2 and result.edited == 0 and result.deleted == 0
    assert result.data_version == 1
    assert rows[0]["track"] == "Siding"
    assert (rows[0]["from_m"], rows[0]["to_m"]) == (111361.0, 112486.5)
    assert rows[0]["wear_percentage"] == calculate_wear_percentage(11.4)
    assert rows[0]["measurement_sd"] is None
    assert parent["source_type"] == "manual"
    assert parent["completeness_state"] == "incomplete"


def test_apply_change_set_rolls_back_all_operations_on_optimistic_edit_failure(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        AddOperation,
        ChangeOperationError,
        ChangeSet,
        EditOperation,
        apply_change_set,
        get_wire_wear_data_version,
        list_committed_records,
    )

    metadata = _metadata(
        ("28", "UP", 1, 2, "EAL UP"),
        ("29", "UP", 2, 3, "EAL UP"),
    )
    db = DatabaseManager(str(tmp_path / "optimistic_edit.db"))
    try:
        with db.get_connection() as conn:
            apply_change_set(
                conn,
                ChangeSet((
                    AddOperation(_cycle_key(tension_length="28"), 11.4),
                    AddOperation(_cycle_key(tension_length="29"), 11.3),
                )),
                metadata,
                now=datetime(2026, 6, 1, tzinfo=timezone.utc),
            )
            rows = list_committed_records(conn, line_group="EAL")
            with pytest.raises(ChangeOperationError) as exc_info:
                apply_change_set(
                    conn,
                    ChangeSet((
                        EditOperation(_cycle_key(tension_length="28"), 10.9, rows[0]["updated_at"]),
                        EditOperation(_cycle_key(tension_length="29"), 10.8, "stale"),
                    )),
                    metadata,
                    now=datetime(2026, 6, 2, tzinfo=timezone.utc),
                )
            after = list_committed_records(conn, line_group="EAL")
            version = get_wire_wear_data_version(conn)
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert exc_info.value.operation_index == 1
    assert [row["avg_wear_min"] for row in after] == [11.4, 11.3]
    assert version == 1


def test_edit_preserves_complete_parent_and_delete_operations_keep_unique_tombstones(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        ChangeSet,
        DeleteCellOperation,
        DeleteRowOperation,
        EditOperation,
        apply_change_set,
        list_committed_records,
        save_analysis_cycle,
    )
    first = _preview().records[0]
    second = replace(
        first,
        key=_cycle_key(tension_length="29"),
        track="UP",
        from_m=Decimal("112486.5"),
        to_m=Decimal("113000"),
    )
    metadata = _metadata(
        ("28", "UP", 111361, 111633, "EAL UP"),
        ("28", "DN", 111633, 112486.5, "EAL DN"),
        ("29", "UP", 112486.5, 113000, "EAL UP"),
    )
    db = DatabaseManager(str(tmp_path / "delete_ops.db"))
    try:
        with db.get_connection() as conn:
            save_analysis_cycle(conn, _preview(records=(first, second)))
            rows = list_committed_records(conn, line_group="EAL")
            edited = apply_change_set(
                conn,
                ChangeSet((EditOperation(_cycle_key(tension_length="28"), 11.1, rows[0]["updated_at"]),)),
                metadata,
                now=datetime(2026, 6, 1, tzinfo=timezone.utc),
            )
            completeness_after_edit = conn.execute(
                "SELECT completeness_state FROM wire_wear_cycles"
            ).fetchone()[0]
            rows = list_committed_records(conn, line_group="EAL")
            edited_measurement_sd = rows[0]["measurement_sd"]
            deleted_cell = apply_change_set(
                conn,
                ChangeSet((DeleteCellOperation(_cycle_key(tension_length="28"), rows[0]["updated_at"]),)),
                metadata,
                now=datetime(2026, 6, 2, tzinfo=timezone.utc),
            )
            deleted_row = apply_change_set(
                conn,
                ChangeSet((DeleteRowOperation("EAL", date(2026, 5, 28)),)),
                metadata,
                now=datetime(2026, 6, 3, tzinfo=timezone.utc),
            )
            parent_count = conn.execute("SELECT COUNT(*) FROM wire_wear_cycles").fetchone()[0]
            tombstones = conn.execute(
                "SELECT tension_length FROM wire_wear_deletion_tombstones ORDER BY tension_length"
            ).fetchall()
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert edited.edited == 1
    assert completeness_after_edit == "complete"
    assert edited_measurement_sd is None
    assert deleted_cell.deleted == 1
    assert deleted_row.deleted == 1
    assert parent_count == 0
    assert [row[0] for row in tombstones] == ["28", "29"]


def test_tombstone_recreation_requires_strictly_newer_change(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        AddOperation,
        ChangeOperationError,
        ChangeSet,
        DeleteCellOperation,
        apply_change_set,
        list_committed_records,
    )

    metadata = _metadata(("28", "UP", 1, 2, "EAL UP"))
    deleted_at = datetime(2026, 6, 2, tzinfo=timezone.utc)
    db = DatabaseManager(str(tmp_path / "tombstone_precedence.db"))
    try:
        with db.get_connection() as conn:
            apply_change_set(
                conn,
                ChangeSet((AddOperation(_cycle_key(), 11.4),)),
                metadata,
                now=datetime(2026, 6, 1, tzinfo=timezone.utc),
            )
            record = list_committed_records(conn, line_group="EAL")[0]
            with pytest.raises(ChangeOperationError, match="changed or does not exist"):
                apply_change_set(
                    conn,
                    ChangeSet((DeleteCellOperation(_cycle_key(), "stale"),)),
                    metadata,
                    now=deleted_at,
                )
            apply_change_set(
                conn,
                ChangeSet((DeleteCellOperation(_cycle_key(), record["updated_at"]),)),
                metadata,
                now=deleted_at,
            )
            with pytest.raises(ChangeOperationError, match="tombstone"):
                apply_change_set(
                    conn,
                    ChangeSet((AddOperation(_cycle_key(), 11.2),)),
                    metadata,
                    now=deleted_at,
                )
            recreated = apply_change_set(
                conn,
                ChangeSet((AddOperation(_cycle_key(), 11.2),)),
                metadata,
                now=datetime(2026, 6, 2, 0, 0, 1, tzinfo=timezone.utc),
            )
            tombstones_after_recreate = conn.execute(
                "SELECT COUNT(*) FROM wire_wear_deletion_tombstones"
            ).fetchone()[0]
            recreated_record = list_committed_records(conn, line_group="EAL")[0]
            apply_change_set(
                conn,
                ChangeSet((DeleteCellOperation(_cycle_key(), recreated_record["updated_at"]),)),
                metadata,
                now=datetime(2026, 6, 3, tzinfo=timezone.utc),
            )
            tombstone_count = conn.execute(
                "SELECT COUNT(*) FROM wire_wear_deletion_tombstones"
            ).fetchone()[0]
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert recreated.added == 1
    assert recreated.data_version == 3
    assert tombstones_after_recreate == 0
    assert tombstone_count == 1


def test_build_workbench_derives_historical_sd_without_overwriting_measurement_sd(tmp_path):
    from app.core.calculation.wear_cycle_repository import build_workbench, save_analysis_cycle

    first = _preview(cycle_date="2026-05-01")
    second_record = replace(
        first.records[0],
        key=_cycle_key(cycle_date="2026-05-12"),
        avg_wear_min=11.50,
        measurement_sd=0.25,
    )
    second = _preview(cycle_date="2026-05-12", records=(second_record,))
    db = DatabaseManager(str(tmp_path / "workbench_sd.db"))
    try:
        with db.get_connection() as conn:
            save_analysis_cycle(conn, first)
            save_analysis_cycle(conn, second)
            workbench = build_workbench(conn, "EAL", " 28 ", date(2026, 5, 1), date(2026, 5, 31))
            stored = conn.execute(
                "SELECT measurement_sd FROM wire_wear_cycle_records ORDER BY cycle_date"
            ).fetchall()
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert [row["cycle_date"] for row in workbench["records"]] == ["2026-05-01", "2026-05-12"]
    assert round(workbench["records"][0]["historical_sd"], 3) == 0.035
    assert [row[0] for row in stored] == [0.75, 0.25]


def test_build_workbench_filters_line_date_and_orders_by_canonical_range(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        AddOperation,
        ChangeSet,
        apply_change_set,
        build_workbench,
    )

    metadata = _metadata(
        ("X10", "UP", 200, 300, "EAL UP"),
        ("X2", "UP", 100, 200, "EAL UP"),
        ("X20", "UP", 300, 400, "TML UP"),
    )
    db = DatabaseManager(str(tmp_path / "workbench_filter.db"))
    try:
        with db.get_connection() as conn:
            apply_change_set(
                conn,
                ChangeSet((
                    AddOperation(_cycle_key(tension_length="X10"), 11.4),
                    AddOperation(_cycle_key(tension_length="X2"), 11.3),
                    AddOperation(_cycle_key("TML", "2026-05-28", "X20"), 11.2),
                )),
                metadata,
                now=datetime(2026, 6, 1, tzinfo=timezone.utc),
            )
            rows = build_workbench(
                conn,
                "EAL",
                "x",
                date(2026, 5, 1),
                date(2026, 5, 31),
            )["records"]
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert [row["tension_length"] for row in rows] == ["X2", "X10"]


def test_save_analysis_cycle_returns_saved_cycle_and_typed_domain_errors(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        DuplicateBusinessKeyError,
        IncompleteCycleError,
        SavedCycle,
        save_analysis_cycle,
    )

    db = DatabaseManager(str(tmp_path / "typed_cycle_save.db"))
    try:
        with db.get_connection() as conn:
            with pytest.raises(IncompleteCycleError) as incomplete:
                save_analysis_cycle(conn, _preview(can_save=False))

            duplicate_preview = _preview(
                records=(_preview().records[0], _preview().records[0])
            )
            with pytest.raises(DuplicateBusinessKeyError):
                save_analysis_cycle(conn, duplicate_preview)

            saved = save_analysis_cycle(conn, _preview())
            with pytest.raises(DuplicateBusinessKeyError):
                save_analysis_cycle(conn, _preview())
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert incomplete.value.blocking_reasons == ("unknown_segment",)
    assert isinstance(saved, SavedCycle)
    assert saved.line_group == "EAL"
    assert saved.cycle_date == date(2026, 5, 28)
    assert saved.completeness_state == "complete"
    assert len(saved.records) == 1
    assert saved.data_version == 1


def test_change_operation_error_exposes_stable_detail(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        AddOperation,
        ChangeOperationError,
        ChangeSet,
        EditOperation,
        StaleRecordError,
        apply_change_set,
    )

    metadata = _metadata(("28", "UP", 1, 2, "EAL UP"))
    db = DatabaseManager(str(tmp_path / "change_detail.db"))
    try:
        with db.get_connection() as conn:
            apply_change_set(
                conn,
                ChangeSet((AddOperation(_cycle_key(), 11.4),)),
                metadata,
                now=datetime(2026, 6, 1, tzinfo=timezone.utc),
            )
            with pytest.raises(ChangeOperationError) as exc_info:
                apply_change_set(
                    conn,
                    ChangeSet((EditOperation(_cycle_key(), 11.2, "stale"),)),
                    metadata,
                    now=datetime(2026, 6, 2, tzinfo=timezone.utc),
                )
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert exc_info.value.operation_index == 0
    assert exc_info.value.detail == "record was changed or does not exist"
    assert isinstance(exc_info.value.cause, StaleRecordError)


def test_build_workbench_returns_columns_matrix_and_latest_summary(tmp_path):
    from app.core.calculation.wear_cycle_repository import build_workbench, save_analysis_cycle
    from app.core.calculation.wear_cycle_types import PhysicalInterval

    first_28 = replace(
        _preview(cycle_date="2026-05-01").records[0],
        intervals=(
            PhysicalInterval("UP", Decimal("111361"), Decimal("111800")),
            PhysicalInterval("DN", Decimal("112000"), Decimal("112700")),
        ),
    )
    first_29 = replace(
        first_28,
        key=_cycle_key(cycle_date="2026-05-01", tension_length="29"),
        track="UP",
        from_m=Decimal("112486.5"),
        to_m=Decimal("113000"),
        avg_wear_min=11.8,
        wear_percentage=6.0,
    )
    second_28 = replace(
        first_28,
        key=_cycle_key(cycle_date="2026-06-01"),
        avg_wear_min=11.2,
        wear_percentage=10.0,
    )
    db = DatabaseManager(str(tmp_path / "full_workbench.db"))
    try:
        with db.get_connection() as conn:
            save_analysis_cycle(
                conn,
                _preview(cycle_date="2026-05-01", records=(first_28, first_29)),
            )
            save_analysis_cycle(
                conn,
                _preview(cycle_date="2026-06-01", records=(second_28,)),
            )
            workbench = build_workbench(conn, "EAL")
            summary = build_workbench(conn, "EAL", summary_only=True)
            selected = build_workbench(
                conn, "EAL", selected_tension_length="29"
            )
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert [column["tension_length"] for column in workbench["columns"]] == ["28", "29"]
    assert workbench["columns"][0]["interval_count"] == 2
    assert workbench["columns"][0]["physical_intervals"] == [
        {"track": "UP", "from_m": 111361.0, "to_m": 111800.0},
        {"track": "DN", "from_m": 112000.0, "to_m": 112700.0},
    ]
    assert workbench["matrix_rows"] == [
        {"cycle_date": "2026-05-01", "values": {"28": 11.45, "29": 11.8}},
        {"cycle_date": "2026-06-01", "values": {"28": 11.2, "29": None}},
    ]
    summaries = {row["tension_length"]: row for row in workbench["latest_summary"]}
    assert summaries["28"]["latest_cycle_date"] == "2026-06-01"
    assert summaries["28"]["latest_avg_wear_min"] == 11.2
    assert summaries["28"]["latest_wear_percentage"] == 10.0
    assert summaries["28"]["historical_sd"] == pytest.approx(0.1767766953)
    assert summaries["29"]["historical_sd"] is None
    assert summary["summary_only"] is True
    assert summary["records"] == []
    assert summary["matrix_rows"] == []
    assert len(summary["latest_summary"]) == 2
    assert [column["tension_length"] for column in selected["columns"]] == ["29"]
    assert {record["tension_length"] for record in selected["records"]} == {"29"}


def test_failed_change_set_rolls_back_new_parent_and_tombstone(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        AddOperation,
        ChangeOperationError,
        ChangeSet,
        DeleteCellOperation,
        EditOperation,
        apply_change_set,
        current_data_version,
        list_committed_records,
        save_analysis_cycle,
    )

    first = _preview().records[0]
    second = replace(
        first,
        key=_cycle_key(tension_length="29"),
        from_m=Decimal("2"),
        to_m=Decimal("3"),
    )
    metadata = _metadata(
        ("28", "UP", 1, 2, "EAL UP"),
        ("29", "UP", 2, 3, "EAL UP"),
        ("30", "UP", 3, 4, "EAL UP"),
    )
    db = DatabaseManager(str(tmp_path / "parent_tombstone_rollback.db"))
    try:
        with db.get_connection() as conn:
            save_analysis_cycle(conn, _preview(records=(first, second)))
            before = list_committed_records(conn, line_group="EAL")
            before_version = current_data_version(conn)
            with pytest.raises(ChangeOperationError) as exc_info:
                apply_change_set(
                    conn,
                    ChangeSet((
                        AddOperation(_cycle_key(cycle_date="2026-06-01", tension_length="30"), 11.0),
                        DeleteCellOperation(_cycle_key(tension_length="28"), before[0]["updated_at"]),
                        EditOperation(_cycle_key(tension_length="29"), 10.9, "stale"),
                    )),
                    metadata,
                    now=datetime(2026, 6, 2, tzinfo=timezone.utc),
                )
            after = list_committed_records(conn, line_group="EAL")
            parent_dates = [
                row[0]
                for row in conn.execute(
                    "SELECT cycle_date FROM wire_wear_cycles ORDER BY cycle_date"
                ).fetchall()
            ]
            tombstone_count = conn.execute(
                "SELECT COUNT(*) FROM wire_wear_deletion_tombstones"
            ).fetchone()[0]
            after_version = current_data_version(conn)
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert exc_info.value.operation_index == 2
    assert after == before
    assert parent_dates == ["2026-05-28"]
    assert tombstone_count == 0
    assert after_version == before_version


def test_manual_metadata_resolution_is_isolated_by_line_group(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        AddOperation,
        ChangeSet,
        apply_change_set,
        list_committed_records,
    )

    metadata = _metadata(
        ("28", "UP", 1, 2, "EAL UP"),
        ("28", "DN", 100, 200, "TML DN"),
    )
    db = DatabaseManager(str(tmp_path / "line_metadata.db"))
    try:
        with db.get_connection() as conn:
            apply_change_set(
                conn,
                ChangeSet((
                    AddOperation(_cycle_key("EAL", "2026-06-01", "28"), 11.4),
                    AddOperation(_cycle_key("TML", "2026-06-01", "28"), 11.2),
                )),
                metadata,
                now=datetime(2026, 6, 2, tzinfo=timezone.utc),
            )
            rows = list_committed_records(conn)
    finally:
        db.close()
        DatabaseManager.reset_instance()

    by_line = {row["line_group"]: row for row in rows}
    assert (by_line["EAL"]["track"], by_line["EAL"]["from_m"], by_line["EAL"]["to_m"]) == (
        "UP", 1.0, 2.0,
    )
    assert (by_line["TML"]["track"], by_line["TML"]["from_m"], by_line["TML"]["to_m"]) == (
        "DN", 100.0, 200.0,
    )


def test_public_data_version_helpers_only_change_wire_wear_key(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        bump_data_version,
        current_data_version,
    )

    db = DatabaseManager(str(tmp_path / "data_version.db"))
    try:
        with db.get_connection() as conn:
            schema_version = conn.execute(
                "SELECT value FROM system_metadata WHERE key = 'schema_version'"
            ).fetchone()[0]
            assert current_data_version(conn) == 0
            assert bump_data_version(conn) == 1
            assert bump_data_version(conn) == 2
            metadata = {
                row["key"]: row["value"]
                for row in conn.execute("SELECT key, value FROM system_metadata").fetchall()
            }
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert metadata["wire_wear_data_version"] == "2"
    assert metadata["schema_version"] == schema_version


def test_latest_complete_uploaded_cycle_ignores_newer_manual_cycle(tmp_path):
    from app.core.calculation.wear_cycle_repository import (
        AddOperation,
        ChangeSet,
        apply_change_set,
        get_latest_complete_uploaded_cycle,
        save_analysis_cycle,
    )

    metadata = _metadata(("28", "UP", 1, 2, "EAL UP"))
    db = DatabaseManager(str(tmp_path / "latest_complete.db"))
    try:
        with db.get_connection() as conn:
            saved = save_analysis_cycle(conn, _preview(cycle_date="2026-05-28"))
            apply_change_set(
                conn,
                ChangeSet((AddOperation(_cycle_key(cycle_date="2026-06-15"), 11.2),)),
                metadata,
                now=datetime(2026, 6, 16, tzinfo=timezone.utc),
            )
            latest = get_latest_complete_uploaded_cycle(conn, "EAL")
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert latest is not None
    assert latest.cycle_id == saved.cycle_id
    assert latest.cycle_date == date(2026, 5, 28)


def test_wear_records_does_not_expose_interim_cycle_facade():
    from app.core.calculation import wear_records

    interim_symbols = (
        "query_wire_wear_cycle_records",
        "save_wire_wear_cycle_records",
        "recalculate_cycle_sd_for_tension_length",
    )

    assert not [name for name in interim_symbols if hasattr(wear_records, name)]
