"""Developer seed export and empty-database initialization for Wire Wear."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import logging
from pathlib import Path
import sqlite3
from typing import Mapping
from uuid import uuid4

from .wear_cycle_io import (
    SyncMetadata,
    apply_sync_import,
    build_sync_package,
    preview_sync_import,
)
from .wear_cycle_repository import current_data_version


logger = logging.getLogger(__name__)

SEED_FILENAME = "wire-wear-seed.json"
SEED_SOURCE_WORKSTATION = "TOV640 Analyzer development seed"
REQUIRED_IDENTITIES = frozenset({("EAL", "EAL"), ("EAL", "LMC"), ("TML", "TML")})


class SeedExportError(ValueError):
    """Raised when development state cannot produce an approved complete seed."""


class SeedLoadError(ValueError):
    """Raised when a seed asset cannot be decoded."""


class SeedInitializationStatus(str, Enum):
    APPLIED = "applied"
    SKIPPED_NON_EMPTY = "skipped_non_empty"
    SKIPPED_MISSING = "skipped_missing"
    FAILED = "failed"


@dataclass(frozen=True)
class SeedInitializationResult:
    status: SeedInitializationStatus
    data_version: int | None
    created: int = 0
    updated: int = 0
    deleted: int = 0
    backup_path: str | None = None
    error: str | None = None


def metadata_fingerprints(config_dir: Path | str) -> dict[str, str]:
    """Fingerprint the canonical metadata files used by normalized identities."""
    root = Path(config_dir)
    fingerprints = {
        line_group: sha256(path.read_bytes()).hexdigest()
        for line_group in ("EAL", "TML")
        if (path := root / f"{line_group} metadata.xlsx").is_file()
    }
    missing = sorted({"EAL", "TML"} - set(fingerprints))
    if missing:
        raise SeedExportError(
            f"metadata files required for seed export are missing: {', '.join(missing)}"
        )
    return fingerprints


def build_seed_package(
    conn: sqlite3.Connection,
    *,
    metadata_fingerprint: Mapping[str, str],
    source_workstation: str = SEED_SOURCE_WORKSTATION,
    package_id: str | None = None,
) -> dict:
    """Export only committed normalized records, tombstones, and required parents."""
    package = build_sync_package(
        conn,
        source_workstation=source_workstation,
        metadata_fingerprint=metadata_fingerprint,
        package_id=package_id,
    )
    record_identities = {
        (record["line_group"], record["line_class"])
        for record in package["records"]
    }
    missing_identities = sorted(REQUIRED_IDENTITIES - record_identities)
    if missing_identities:
        missing = ", ".join(f"{line}/{line_class}" for line, line_class in missing_identities)
        raise SeedExportError(f"seed export is missing required identities: {missing}")
    record_cycles = {
        (record["line_group"], record["line_class"], record["cycle_date"])
        for record in package["records"]
    }
    package["cycles"] = [
        cycle
        for cycle in package["cycles"]
        if (cycle["line_group"], cycle["line_class"], cycle["cycle_date"])
        in record_cycles
    ]
    package["segments"] = []
    package["conflict_decisions"] = []
    return package


def write_seed_package(
    conn: sqlite3.Connection,
    output_path: Path | str,
    *,
    metadata_fingerprint: Mapping[str, str],
    source_workstation: str = SEED_SOURCE_WORKSTATION,
    package_id: str | None = None,
) -> Path:
    """Atomically write a deterministic JSON representation of the seed package."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    package = build_seed_package(
        conn,
        metadata_fingerprint=metadata_fingerprint,
        source_workstation=source_workstation,
        package_id=package_id,
    )
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(package, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def load_seed_package(seed_path: Path | str) -> object:
    """Read a seed asset while preserving validation responsibility in sync core."""
    path = Path(seed_path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SeedLoadError(f"unable to load Wire Wear seed {path}: {exc}") from exc


def normalized_dataset_is_empty(conn: sqlite3.Connection) -> bool:
    """Treat any normalized cycle, record, or tombstone state as user-owned data."""
    row = conn.execute(
        """
        SELECT
            EXISTS(SELECT 1 FROM wire_wear_cycles LIMIT 1)
            OR EXISTS(SELECT 1 FROM wire_wear_cycle_records LIMIT 1)
            OR EXISTS(SELECT 1 FROM wire_wear_deletion_tombstones LIMIT 1)
        """
    ).fetchone()
    return not bool(row[0])


def _safe_data_version(conn: sqlite3.Connection) -> int | None:
    try:
        return current_data_version(conn)
    except Exception:
        return None


def initialize_seed_if_empty(
    conn: sqlite3.Connection,
    seed_path: Path | str,
    metadata: SyncMetadata,
    *,
    metadata_fingerprint: Mapping[str, str],
    db_path: Path | str | None = None,
) -> SeedInitializationResult:
    """Apply a valid seed to an empty normalized dataset without blocking startup."""
    try:
        if not normalized_dataset_is_empty(conn):
            return SeedInitializationResult(
                SeedInitializationStatus.SKIPPED_NON_EMPTY,
                current_data_version(conn),
            )

        path = Path(seed_path)
        if not path.is_file():
            logger.info("Wire Wear seed not found; initialization skipped: %s", path)
            return SeedInitializationResult(
                SeedInitializationStatus.SKIPPED_MISSING,
                current_data_version(conn),
            )

        package = load_seed_package(path)
        preview = preview_sync_import(
            conn,
            package,
            metadata,
            metadata_fingerprint=metadata_fingerprint,
        )
        applied = apply_sync_import(
            conn,
            source_package=preview.source_package,
            preview_digest=preview.preview_digest,
            expected_data_version=preview.expected_data_version,
            metadata=metadata,
            metadata_fingerprint=metadata_fingerprint,
            db_path=db_path,
        )
        logger.info(
            "Wire Wear seed applied: created=%s deleted=%s version=%s",
            applied["created"],
            applied["deleted"],
            applied["data_version"],
        )
        return SeedInitializationResult(
            SeedInitializationStatus.APPLIED,
            applied["data_version"],
            created=applied["created"],
            updated=applied["updated"],
            deleted=applied["deleted"],
            backup_path=applied["backup_path"],
        )
    except Exception as exc:
        logger.error("Wire Wear seed initialization failed: %s", exc, exc_info=True)
        return SeedInitializationResult(
            SeedInitializationStatus.FAILED,
            _safe_data_version(conn),
            error=f"{type(exc).__name__}: {exc}",
        )
