from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest

from app.core.calculation.wear_cycle_seed import (
    SeedExportError,
    SeedInitializationStatus,
    build_seed_package,
    initialize_seed_if_empty,
    metadata_fingerprints,
    normalized_dataset_is_empty,
    write_seed_package,
)
from app.core.calculation.wear_cycle_types import MetadataInterval
from app.core.database import DatabaseManager


def _metadata():
    from decimal import Decimal

    return {
        ("EAL", "EAL"): (
            MetadataInterval("28", "UP", Decimal("100"), Decimal("200"), "EAL UP"),
        ),
        ("EAL", "LMC"): (
            MetadataInterval("28", "UP", Decimal("300"), Decimal("400"), "LMC UP"),
        ),
        ("TML", "TML"): (
            MetadataInterval("28", "UP", Decimal("500"), Decimal("600"), "TML UP"),
            MetadataInterval("29", "UP", Decimal("601"), Decimal("700"), "TML UP"),
        ),
    }


def _fingerprints():
    return {"EAL": "eal-fingerprint", "TML": "tml-fingerprint"}


def _package():
    timestamp = "2026-08-07T12:00:00Z"
    identities = (
        ("EAL", "EAL", 100.0, 200.0, 10.5),
        ("EAL", "LMC", 300.0, 400.0, 10.4),
        ("TML", "TML", 500.0, 600.0, 10.3),
    )
    cycles = []
    records = []
    for line_group, line_class, from_m, to_m, average in identities:
        cycles.append({
            "line_group": line_group,
            "line_class": line_class,
            "cycle_date": "2026-05-28",
            "source_type": "sync",
            "acquisition_date_from": None,
            "acquisition_date_to": None,
            "completeness_state": "complete",
            "source_lineage": ["approved-development.db"],
            "created_at": timestamp,
            "updated_at": timestamp,
        })
        records.append({
            "line_group": line_group,
            "line_class": line_class,
            "cycle_date": "2026-05-28",
            "tension_length": "28",
            "track": "UP",
            "from_m": from_m,
            "to_m": to_m,
            "avg_wear_min": average,
            "wear_percentage": 0.0,
            "measurement_sd": None,
            "source_lineage": ["approved-development.db"],
            "created_at": timestamp,
            "updated_at": timestamp,
        })
    return {
        "schema": "wear-cycle-v1",
        "package_id": "approved-development-seed",
        "exported_at": timestamp,
        "source_workstation": "development",
        "metadata_fingerprint": _fingerprints(),
        "cycles": cycles,
        "records": records,
        "segments": [],
        "conflict_decisions": [],
        "tombstones": [{
            "line_group": "TML",
            "line_class": "TML",
            "cycle_date": "2026-06-28",
            "tension_length": "29",
            "deleted_at": timestamp,
            "source_package_id": "approved-development-seed",
        }],
    }


def _create_database(path: Path) -> None:
    DatabaseManager.reset_instance()
    manager = DatabaseManager(str(path))
    manager.close()
    DatabaseManager.reset_instance()


def _connect(path: Path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _apply_package(path: Path, package: dict | None = None) -> None:
    from app.core.calculation.wear_cycle_io import apply_sync_import, preview_sync_import

    with _connect(path) as conn:
        source = package or _package()
        preview = preview_sync_import(
            conn, source, _metadata(), metadata_fingerprint=_fingerprints()
        )
        apply_sync_import(
            conn,
            source_package=preview.source_package,
            preview_digest=preview.preview_digest,
            expected_data_version=preview.expected_data_version,
            metadata=_metadata(),
            metadata_fingerprint=_fingerprints(),
            db_path=path,
        )


def _seed_source(path: Path) -> None:
    _create_database(path)
    _apply_package(path)
    with _connect(path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO system_metadata (key, value) VALUES (?, ?)",
            ("unrelated-analysis-marker", "must-not-export"),
        )
        conn.commit()


def test_seed_export_contains_only_normalized_records_tombstones_and_required_cycles(tmp_path):
    source_path = tmp_path / "development" / "analysis.db"
    _seed_source(source_path)

    with _connect(source_path) as conn:
        package = build_seed_package(
            conn,
            metadata_fingerprint=_fingerprints(),
            package_id="seed-export",
        )

    assert set(package) == {
        "schema", "package_id", "exported_at", "source_workstation",
        "metadata_fingerprint", "cycles", "records", "segments",
        "conflict_decisions", "tombstones",
    }
    assert package["schema"] == "wear-cycle-v1"
    assert package["metadata_fingerprint"] == _fingerprints()
    assert package["segments"] == []
    assert package["conflict_decisions"] == []
    assert {(row["line_group"], row["line_class"]) for row in package["records"]} == {
        ("EAL", "EAL"), ("EAL", "LMC"), ("TML", "TML"),
    }
    assert len(package["cycles"]) == len(package["records"]) == 3
    assert len(package["tombstones"]) == 1
    assert "must-not-export" not in json.dumps(package)


def test_seed_export_rejects_incomplete_required_identities(tmp_path):
    path = tmp_path / "development" / "analysis.db"
    _create_database(path)
    incomplete = _package()
    incomplete["cycles"] = incomplete["cycles"][:1]
    incomplete["records"] = incomplete["records"][:1]
    incomplete["tombstones"] = []
    _apply_package(path, incomplete)

    with _connect(path) as conn, pytest.raises(
        SeedExportError,
        match="EAL/LMC, TML/TML",
    ):
        build_seed_package(conn, metadata_fingerprint=_fingerprints())


def test_metadata_fingerprints_require_both_canonical_files(tmp_path):
    (tmp_path / "EAL metadata.xlsx").write_bytes(b"eal")

    with pytest.raises(SeedExportError, match="missing: TML"):
        metadata_fingerprints(tmp_path)


@pytest.mark.parametrize("local_state", ["cycle", "record", "tombstone"])
def test_normalized_dataset_empty_check_is_conservative(tmp_path, local_state):
    path = tmp_path / local_state / "analysis.db"
    _create_database(path)
    conn = _connect(path)
    try:
        assert normalized_dataset_is_empty(conn)
        if local_state == "cycle":
            conn.execute(
                """
                INSERT INTO wire_wear_cycles (
                    line_group, line_class, cycle_date, source_type,
                    completeness_state, source_lineage, created_at, updated_at
                ) VALUES ('EAL', 'EAL', '2026-05-28', 'manual', 'incomplete', '[]', ?, ?)
                """,
                ("2026-08-07T12:00:00Z", "2026-08-07T12:00:00Z"),
            )
        elif local_state == "record":
            conn.close()
            _apply_package(path, {**_package(), "tombstones": []})
            conn = _connect(path)
        else:
            conn.execute(
                """
                INSERT INTO wire_wear_deletion_tombstones (
                    line_group, line_class, cycle_date, tension_length,
                    deleted_at, source_package_id
                ) VALUES ('EAL', 'EAL', '2026-05-28', '28', ?, 'local')
                """,
                ("2026-08-07T12:00:00Z",),
            )
        conn.commit()
        assert not normalized_dataset_is_empty(conn)
    finally:
        conn.close()


def test_empty_database_applies_seed_once_and_reopen_skips(tmp_path):
    source_path = tmp_path / "development" / "analysis.db"
    target_path = tmp_path / "portable" / "data" / "analysis.db"
    seed_path = tmp_path / "config" / "wire-wear-seed.json"
    _seed_source(source_path)
    _create_database(target_path)
    with _connect(source_path) as source:
        write_seed_package(
            source,
            seed_path,
            metadata_fingerprint=_fingerprints(),
            package_id="portable-seed",
        )

    with _connect(target_path) as target:
        applied = initialize_seed_if_empty(
            target,
            seed_path,
            _metadata(),
            metadata_fingerprint=_fingerprints(),
            db_path=target_path,
        )
        first_version = applied.data_version
        reopened = initialize_seed_if_empty(
            target,
            seed_path,
            _metadata(),
            metadata_fingerprint=_fingerprints(),
            db_path=target_path,
        )
        identities = target.execute(
            "SELECT line_group, line_class FROM wire_wear_cycle_records ORDER BY line_group, line_class"
        ).fetchall()
        tombstones = target.execute(
            "SELECT COUNT(*) FROM wire_wear_deletion_tombstones"
        ).fetchone()[0]

    assert applied.status is SeedInitializationStatus.APPLIED
    assert applied.created == 3
    assert applied.deleted == 1
    assert Path(applied.backup_path).parent == target_path.parent / "backups"
    assert reopened.status is SeedInitializationStatus.SKIPPED_NON_EMPTY
    assert reopened.data_version == first_version
    assert [tuple(row) for row in identities] == [
        ("EAL", "EAL"), ("EAL", "LMC"), ("TML", "TML"),
    ]
    assert tombstones == 1


def test_non_empty_database_never_overwrites_local_records(tmp_path):
    target_path = tmp_path / "portable" / "analysis.db"
    seed_path = tmp_path / "config" / "wire-wear-seed.json"
    _create_database(target_path)
    local = _package()
    local["records"][0]["avg_wear_min"] = 9.25
    local["records"] = local["records"][:1]
    local["cycles"] = local["cycles"][:1]
    local["tombstones"] = []
    _apply_package(target_path, local)
    seed_path.parent.mkdir(parents=True)
    seed_path.write_text(json.dumps(_package()), encoding="utf-8")

    with _connect(target_path) as target:
        result = initialize_seed_if_empty(
            target,
            seed_path,
            _metadata(),
            metadata_fingerprint=_fingerprints(),
            db_path=target_path,
        )
        rows = target.execute(
            "SELECT line_class, avg_wear_min FROM wire_wear_cycle_records"
        ).fetchall()

    assert result.status is SeedInitializationStatus.SKIPPED_NON_EMPTY
    assert [tuple(row) for row in rows] == [("EAL", 9.25)]


def test_malformed_seed_fails_without_breaking_empty_database(tmp_path):
    target_path = tmp_path / "portable" / "analysis.db"
    seed_path = tmp_path / "config" / "wire-wear-seed.json"
    _create_database(target_path)
    seed_path.parent.mkdir(parents=True)
    seed_path.write_text("{not-json", encoding="utf-8")

    with _connect(target_path) as target:
        result = initialize_seed_if_empty(
            target,
            seed_path,
            _metadata(),
            metadata_fingerprint=_fingerprints(),
            db_path=target_path,
        )
        assert target.execute("SELECT 1").fetchone()[0] == 1
        assert normalized_dataset_is_empty(target)

    assert result.status is SeedInitializationStatus.FAILED
    assert "SeedLoadError" in result.error
    assert result.data_version == 0


def test_failed_seed_apply_rolls_back_all_normalized_state(tmp_path, monkeypatch):
    import app.core.calculation.wear_cycle_io as sync

    target_path = tmp_path / "portable" / "analysis.db"
    seed_path = tmp_path / "config" / "wire-wear-seed.json"
    _create_database(target_path)
    seed_path.parent.mkdir(parents=True)
    seed_path.write_text(json.dumps(_package()), encoding="utf-8")
    original_apply = sync._apply_action
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("seed apply failed")
        return original_apply(*args, **kwargs)

    monkeypatch.setattr(sync, "_apply_action", fail_second)
    with _connect(target_path) as target:
        result = initialize_seed_if_empty(
            target,
            seed_path,
            _metadata(),
            metadata_fingerprint=_fingerprints(),
            db_path=target_path,
        )
        counts = tuple(
            target.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "wire_wear_cycles",
                "wire_wear_cycle_records",
                "wire_wear_deletion_tombstones",
            )
        )

    assert result.status is SeedInitializationStatus.FAILED
    assert "seed apply failed" in result.error
    assert counts == (0, 0, 0)
    assert result.data_version == 0


def test_portable_databases_and_development_database_remain_isolated(tmp_path):
    source_path = tmp_path / "development" / "analysis.db"
    first_path = tmp_path / "portable-a" / "data" / "analysis.db"
    second_path = tmp_path / "portable-b" / "data" / "analysis.db"
    seed_path = tmp_path / "resources" / "config" / "wire-wear-seed.json"
    _seed_source(source_path)
    _create_database(first_path)
    _create_database(second_path)
    with _connect(source_path) as source:
        write_seed_package(source, seed_path, metadata_fingerprint=_fingerprints())
    for target_path in (first_path, second_path):
        with _connect(target_path) as target:
            result = initialize_seed_if_empty(
                target,
                seed_path,
                _metadata(),
                metadata_fingerprint=_fingerprints(),
                db_path=target_path,
            )
            assert result.status is SeedInitializationStatus.APPLIED

    with _connect(first_path) as first:
        first.execute(
            "UPDATE wire_wear_cycle_records SET avg_wear_min = 8.0 WHERE line_class = 'LMC'"
        )
        first.commit()
    values = []
    for path in (source_path, first_path, second_path):
        with _connect(path) as conn:
            values.append(conn.execute(
                "SELECT avg_wear_min FROM wire_wear_cycle_records WHERE line_class = 'LMC'"
            ).fetchone()[0])

    assert values == [10.4, 8.0, 10.4]


def test_cli_exports_read_only_database_with_metadata_fingerprints(tmp_path, capsys):
    source_path = tmp_path / "development" / "analysis.db"
    config_dir = tmp_path / "config"
    output_path = config_dir / "wire-wear-seed.json"
    _seed_source(source_path)
    config_dir.mkdir(parents=True)
    (config_dir / "EAL metadata.xlsx").write_bytes(b"eal metadata")
    (config_dir / "TML metadata.xlsx").write_bytes(b"tml metadata")
    script_path = Path(__file__).parents[1] / "scripts" / "generate_wear_cycle_seed.py"
    spec = importlib.util.spec_from_file_location("generate_wear_cycle_seed", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    result = module.main([
        "--database", str(source_path),
        "--config-dir", str(config_dir),
        "--output", str(output_path),
        "--source-workstation", "seed-test",
    ])
    package = json.loads(output_path.read_text(encoding="utf-8"))

    assert result == 0
    assert "Wire Wear seed written" in capsys.readouterr().out
    assert package["source_workstation"] == "seed-test"
    assert package["metadata_fingerprint"] == {
        "EAL": sha256(b"eal metadata").hexdigest(),
        "TML": sha256(b"tml metadata").hexdigest(),
    }
