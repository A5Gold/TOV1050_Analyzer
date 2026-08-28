"""Backup-aware application service for staged wire-wear changes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import sqlite3
from typing import Sequence
from uuid import uuid4

from .wear_cycle_repository import ChangeSet, apply_change_set
from .wear_cycle_types import MetadataInterval


DEFAULT_BACKUP_RETENTION = 10


class BackupCreationError(RuntimeError):
    """Raised when a required pre-write SQLite backup cannot be completed."""


class ChangeSetOrigin(str, Enum):
    MANUAL = "manual"
    WORKBOOK = "workbook"


@dataclass(frozen=True)
class BackupAwareChangeSetResult:
    added: int
    edited: int
    deleted: int
    data_version: int
    backup_path: str | None


def _backup_pattern(db_path: Path) -> str:
    return f"{db_path.stem}-wire-wear-backup-*.db"


def _prune_automatic_backups(
    backup_dir: Path,
    db_path: Path,
    retention: int,
) -> None:
    backups = sorted(
        backup_dir.glob(_backup_pattern(db_path)),
        key=lambda path: path.name,
        reverse=True,
    )
    for expired in backups[retention:]:
        expired.unlink(missing_ok=True)


def create_sqlite_backup(
    conn: sqlite3.Connection,
    db_path: Path | str,
    *,
    retention: int = DEFAULT_BACKUP_RETENTION,
    now: datetime | None = None,
) -> str:
    """Create and retain a service-owned SQLite backup before mutation."""
    if retention < 1:
        raise ValueError("backup retention must be at least 1")

    source_path = Path(db_path)
    backup_dir = source_path.parent / "backups"
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    timestamp = current.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_dir / (
        f"{source_path.stem}-wire-wear-backup-{timestamp}-{uuid4().hex[:8]}.db"
    )

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_conn = sqlite3.connect(str(backup_path))
        try:
            conn.backup(backup_conn)
        finally:
            backup_conn.close()
        _prune_automatic_backups(backup_dir, source_path, retention)
    except Exception as exc:
        try:
            backup_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise BackupCreationError(f"failed to create SQLite backup: {exc}") from exc

    return str(backup_path)


def apply_change_set_with_backup(
    conn: sqlite3.Connection,
    change_set: ChangeSet,
    metadata: Sequence[MetadataInterval],
    *,
    db_path: Path | str,
    origin: ChangeSetOrigin | str,
    now: datetime | None = None,
    expected_data_version: int | None = None,
    backup_retention: int = DEFAULT_BACKUP_RETENTION,
) -> BackupAwareChangeSetResult:
    """Apply one staged change set, backing up workbook-originated batches."""
    normalized_origin = ChangeSetOrigin(origin)
    backup_path = None
    if normalized_origin is ChangeSetOrigin.WORKBOOK:
        backup_path = create_sqlite_backup(
            conn,
            db_path,
            retention=backup_retention,
            now=now,
        )

    result = apply_change_set(
        conn,
        change_set,
        metadata,
        now=now,
        expected_data_version=expected_data_version,
    )
    return BackupAwareChangeSetResult(
        added=result.added,
        edited=result.edited,
        deleted=result.deleted,
        data_version=result.data_version,
        backup_path=backup_path,
    )
