"""Atomic persistence and workbench queries for complete wire-wear cycles."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import math
import sqlite3
from statistics import stdev
from typing import Iterable, Iterator, Sequence, TypeAlias

from .wear_calculator import calculate_wear_percentage
from .wear_cycle_analytics import _history_points, fit_tl_trend
from .wear_cycle_metadata import (
    metadata_sources,
    natural_key,
    normalize_cycle_date,
    normalize_line_identity,
    normalize_line_group,
    normalize_tension_length,
    resolve_canonical_tl,
)
from .wear_cycle_types import (
    BusinessKey,
    CanonicalTensionLength,
    CyclePreview,
    MetadataInterval,
)


class WearCycleRepositoryError(ValueError):
    """Raised when a cycle persistence request violates repository rules."""


class IncompleteCycleError(WearCycleRepositoryError):
    """Raised when an analysis preview is not eligible to be saved."""

    def __init__(self, blocking_reasons: Iterable[str]):
        self.blocking_reasons = tuple(blocking_reasons)
        detail = ", ".join(self.blocking_reasons) or "unknown reason"
        super().__init__(f"cycle preview cannot be saved: {detail}")


class DuplicateBusinessKeyError(WearCycleRepositoryError):
    """Raised when a committed cycle business key already exists."""


class StaleRecordError(WearCycleRepositoryError):
    """Raised when optimistic concurrency does not match a committed record."""


class StaleDataVersionError(WearCycleRepositoryError):
    """Raised when the committed wear data changed before an atomic save."""


class ChangeOperationError(WearCycleRepositoryError):
    """Identify the operation that caused an atomic change set to fail."""

    def __init__(self, operation_index: int, operation: object, cause: Exception):
        self.operation_index = operation_index
        self.operation = operation
        self.cause = cause
        self.detail = str(cause)
        super().__init__(f"change operation {operation_index} failed: {self.detail}")


@dataclass(frozen=True)
class AddOperation:
    key: BusinessKey
    avg_wear_min: float


@dataclass(frozen=True)
class EditOperation:
    key: BusinessKey
    avg_wear_min: float
    expected_updated_at: str


@dataclass(frozen=True)
class DeleteCellOperation:
    key: BusinessKey
    expected_updated_at: str


@dataclass(frozen=True)
class DeleteRowOperation:
    line_group: str
    cycle_date: date
    line_class: str | None = None


ChangeOperation: TypeAlias = (
    AddOperation | EditOperation | DeleteCellOperation | DeleteRowOperation
)


@dataclass(frozen=True)
class ChangeSet:
    operations: tuple[ChangeOperation, ...]

    def __init__(self, operations: Iterable[ChangeOperation]):
        object.__setattr__(self, "operations", tuple(operations))


@dataclass(frozen=True)
class ChangeSetResult:
    added: int
    edited: int
    deleted: int
    data_version: int


@dataclass(frozen=True)
class SavedCycle:
    cycle_id: int
    line_group: str
    line_class: str
    cycle_date: date
    source_type: str
    completeness_state: str
    acquisition_date_from: str | None
    acquisition_date_to: str | None
    source_lineage: tuple[str, ...]
    records: tuple[dict[str, object], ...]
    segments: tuple[dict[str, object], ...]
    conflict_decisions: tuple[dict[str, object], ...]
    data_version: int


def _timestamp(value: datetime | None) -> tuple[datetime, str]:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    return current, current.isoformat(timespec="microseconds")


def _parse_timestamp(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise WearCycleRepositoryError("timestamp cannot be empty")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WearCycleRepositoryError(f"invalid timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@contextmanager
def _immediate_transaction(conn: sqlite3.Connection) -> Iterator[None]:
    if conn.in_transaction:
        raise WearCycleRepositoryError(
            "cycle repository transaction requires an idle connection"
        )
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()


def current_data_version(conn: sqlite3.Connection) -> int:
    """Return the complete-cycle data version, initializing it when absent."""
    row = conn.execute(
        "SELECT value FROM system_metadata WHERE key = 'wire_wear_data_version'"
    ).fetchone()
    if row is None:
        return 0
    try:
        return int(row["value"])
    except (KeyError, TypeError, ValueError):
        return int(row[0])


def bump_data_version(conn: sqlite3.Connection) -> int:
    conn.execute(
        """
        INSERT OR IGNORE INTO system_metadata (key, value, description)
        VALUES ('wire_wear_data_version', '0', 'Wire wear data version for sync')
        """
    )
    conn.execute(
        """
        UPDATE system_metadata
        SET value = CAST(value AS INTEGER) + 1
        WHERE key = 'wire_wear_data_version'
        """
    )
    return current_data_version(conn)


get_wire_wear_data_version = current_data_version
_bump_data_version = bump_data_version


def _key_parts(key: BusinessKey) -> tuple[str, str, str, str]:
    line_group, line_class = normalize_line_identity(key.line_group, key.line_class)
    return (
        line_group,
        line_class,
        normalize_cycle_date(key.cycle_date).isoformat(),
        normalize_tension_length(key.tension_length),
    )


def _json(values: Iterable[object]) -> str:
    return json.dumps(list(values), ensure_ascii=True, separators=(",", ":"))


def _interval_payload(intervals) -> list[dict[str, object]]:
    return [
        {"track": item.track, "from_m": float(item.from_m), "to_m": float(item.to_m)}
        for item in intervals
    ]


def _source_lineage(preview: CyclePreview) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                source
                for record in preview.records
                for source in record.source_lineage
            },
            key=natural_key,
        )
    )


def _acquisition_range(preview: CyclePreview) -> tuple[str | None, str | None]:
    dates = sorted(
        {
            acquisition_date
            for segment in preview.segments
            for acquisition_date in segment.acquisition_dates
        }
    )
    if not dates:
        return None, None
    return dates[0].isoformat(), dates[-1].isoformat()


def _validate_preview(preview: CyclePreview) -> tuple[tuple[str, str, str, str], ...]:
    hard_blocking_reasons = tuple(
        reason for reason in preview.blocking_reasons if reason != "segment_missing"
    )
    if hard_blocking_reasons:
        raise IncompleteCycleError(hard_blocking_reasons)
    if not any(segment.is_present for segment in preview.segments):
        raise IncompleteCycleError(("segment_missing",))
    if not preview.records:
        raise WearCycleRepositoryError("cycle preview has no records")
    line_group, line_class = normalize_line_identity(preview.line_group, preview.line_class)
    cycle_date = normalize_cycle_date(preview.cycle_date)
    keys = tuple(_key_parts(record.key) for record in preview.records)
    if any(
        key[0] != line_group or key[1] != line_class or key[2] != cycle_date.isoformat()
        for key in keys
    ):
        raise WearCycleRepositoryError("preview record key does not match its cycle")
    if len(set(keys)) != len(keys):
        raise DuplicateBusinessKeyError("duplicate business key in cycle preview")
    if any(not conflict.is_accepted for conflict in preview.conflicts):
        raise IncompleteCycleError(("conflict_not_accepted",))
    return keys


def save_analysis_cycle(
    conn: sqlite3.Connection,
    preview: CyclePreview,
    expected_data_version: int | None = None,
) -> SavedCycle:
    """Persist one valid analysis preview in a single immediate transaction."""
    keys = _validate_preview(preview)
    _, accepted_at = _timestamp(None)
    line_group, line_class = normalize_line_identity(preview.line_group, preview.line_class)
    cycle_date = normalize_cycle_date(preview.cycle_date).isoformat()
    acquisition_from, acquisition_to = _acquisition_range(preview)
    lineage = _source_lineage(preview)
    completeness_state = (
        "complete"
        if preview.segments and all(segment.is_present for segment in preview.segments)
        else "incomplete"
    )

    with _immediate_transaction(conn):
        if (
            expected_data_version is not None
            and current_data_version(conn) != expected_data_version
        ):
            raise StaleDataVersionError(
                "wear data version changed; reload and retry"
            )
        for key in keys:
            if conn.execute(
                """
                SELECT 1 FROM wire_wear_cycle_records
                WHERE line_group = ? AND line_class = ? AND cycle_date = ? AND tension_length = ?
                """,
                key,
            ).fetchone():
                raise DuplicateBusinessKeyError(f"duplicate business key: {key}")

        conn.execute(
            """
            INSERT INTO wire_wear_cycles (
                line_group, line_class, cycle_date, source_type,
                acquisition_date_from, acquisition_date_to,
                completeness_state, source_lineage, created_at, updated_at
            ) VALUES (?, ?, ?, 'analysis', ?, ?, ?, ?, ?, ?)
            ON CONFLICT(line_group, line_class, cycle_date) DO UPDATE SET
                source_type = 'analysis',
                acquisition_date_from = excluded.acquisition_date_from,
                acquisition_date_to = excluded.acquisition_date_to,
                completeness_state = excluded.completeness_state,
                source_lineage = excluded.source_lineage,
                updated_at = excluded.updated_at
            """,
            (
                line_group,
                line_class,
                cycle_date,
                acquisition_from,
                acquisition_to,
                completeness_state,
                _json(lineage),
                accepted_at,
                accepted_at,
            ),
        )
        cycle_id = conn.execute(
            "SELECT cycle_id FROM wire_wear_cycles WHERE line_group = ? AND line_class = ? AND cycle_date = ?",
            (line_group, line_class, cycle_date),
        ).fetchone()["cycle_id"]

        for segment in preview.segments:
            acquisition_dates = sorted(segment.acquisition_dates)
            conn.execute(
                """
                INSERT INTO wire_wear_cycle_segments (
                    cycle_id, segment_name, is_present, coverage_percentage,
                    diagnostic_gaps, source_file_names,
                    acquisition_date_from, acquisition_date_to
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cycle_id,
                    segment.segment_name,
                    int(segment.is_present),
                    segment.coverage_percentage,
                    _json(segment.diagnostic_gaps),
                    _json(segment.source_file_names),
                    acquisition_dates[0].isoformat() if acquisition_dates else None,
                    acquisition_dates[-1].isoformat() if acquisition_dates else None,
                ),
            )

        for record in preview.records:
            key_line, key_class, key_date, tension_length = _key_parts(record.key)
            conn.execute(
                """
                INSERT INTO wire_wear_cycle_records (
                    cycle_id, line_group, line_class, cycle_date, tension_length,
                    track, from_m, to_m, avg_wear_min, wear_percentage,
                    measurement_sd, physical_intervals, source_lineage, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cycle_id,
                    key_line,
                    key_class,
                    key_date,
                    tension_length,
                    record.track,
                    float(record.from_m),
                    float(record.to_m),
                    float(record.avg_wear_min),
                    float(record.wear_percentage),
                    record.measurement_sd,
                    _json(_interval_payload(record.intervals)),
                    _json(record.source_lineage),
                    accepted_at,
                    accepted_at,
                ),
            )

        for conflict in preview.conflicts:
            conn.execute(
                """
                INSERT INTO wire_wear_conflict_decisions (
                    cycle_id, measurement_identity, source_values,
                    selected_wear_min, accepted_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    cycle_id,
                    conflict.measurement_identity,
                    _json(conflict.source_values),
                    conflict.selected_wear_min,
                    accepted_at,
                ),
            )
        data_version = bump_data_version(conn)
    return _saved_cycle(conn, cycle_id, data_version)


def _saved_cycle(
    conn: sqlite3.Connection, cycle_id: int, data_version: int | None = None
) -> SavedCycle:
    parent = conn.execute(
        "SELECT * FROM wire_wear_cycles WHERE cycle_id = ?", (cycle_id,)
    ).fetchone()
    if parent is None:
        raise WearCycleRepositoryError(f"saved cycle does not exist: {cycle_id}")
    records = tuple(
        _decode_record(row)
        for row in conn.execute(
            """
            SELECT records.*, cycles.source_type, cycles.completeness_state
            FROM wire_wear_cycle_records AS records
            JOIN wire_wear_cycles AS cycles ON cycles.cycle_id = records.cycle_id
            WHERE records.cycle_id = ?
            ORDER BY records.from_m, records.to_m, records.tension_length
            """,
            (cycle_id,),
        ).fetchall()
    )
    segments: list[dict[str, object]] = []
    for row in conn.execute(
        "SELECT * FROM wire_wear_cycle_segments WHERE cycle_id = ? ORDER BY segment_name",
        (cycle_id,),
    ).fetchall():
        item = dict(row)
        item["diagnostic_gaps"] = tuple(json.loads(item["diagnostic_gaps"] or "[]"))
        item["source_file_names"] = tuple(json.loads(item["source_file_names"] or "[]"))
        segments.append(item)
    decisions: list[dict[str, object]] = []
    for row in conn.execute(
        """
        SELECT * FROM wire_wear_conflict_decisions
        WHERE cycle_id = ? ORDER BY measurement_identity
        """,
        (cycle_id,),
    ).fetchall():
        item = dict(row)
        item["source_values"] = tuple(
            tuple(value) for value in json.loads(item["source_values"] or "[]")
        )
        decisions.append(item)
    return SavedCycle(
        cycle_id=int(parent["cycle_id"]),
        line_group=str(parent["line_group"]),
        line_class=str(parent["line_class"]),
        cycle_date=normalize_cycle_date(parent["cycle_date"]),
        source_type=str(parent["source_type"]),
        completeness_state=str(parent["completeness_state"]),
        acquisition_date_from=parent["acquisition_date_from"],
        acquisition_date_to=parent["acquisition_date_to"],
        source_lineage=tuple(json.loads(parent["source_lineage"] or "[]")),
        records=records,
        segments=tuple(segments),
        conflict_decisions=tuple(decisions),
        data_version=(
            current_data_version(conn) if data_version is None else data_version
        ),
    )


def get_latest_complete_uploaded_cycle(
    conn: sqlite3.Connection,
    line_group: str | None = None,
    line_class: str | None = None,
) -> SavedCycle | None:
    """Return the newest complete cycle without considering manual-only parents."""
    where = ["completeness_state = 'complete'"]
    params: list[object] = []
    if line_group is not None:
        line, normalized_class = normalize_line_identity(line_group, line_class)
        where.extend(("line_group = ?", "line_class = ?"))
        params.extend((line, normalized_class))
    row = conn.execute(
        f"""
        SELECT cycle_id FROM wire_wear_cycles
        WHERE {' AND '.join(where)}
        ORDER BY cycle_date DESC, updated_at DESC, cycle_id DESC
        LIMIT 1
        """,
        params,
    ).fetchone()
    return None if row is None else _saved_cycle(conn, int(row["cycle_id"]))


def _canonical_for_key(
    key: BusinessKey, metadata: Sequence[MetadataInterval]
) -> tuple[tuple[str, str, str, str], CanonicalTensionLength]:
    parts = _key_parts(key)
    allowed_sheets = {
        sheet_name for _, _, sheet_name in metadata_sources(parts[0], parts[1])
    }
    relevant = tuple(
        interval
        for interval in metadata
        if normalize_tension_length(interval.tension_length) == parts[3]
        and interval.sheet_name in allowed_sheets
    )
    return parts, resolve_canonical_tl(parts[0], parts[3], relevant, line_class=parts[1])


def _validated_average(value: float) -> float:
    average = float(value)
    if not math.isfinite(average):
        raise WearCycleRepositoryError("average wear must be finite")
    return average


def _ensure_manual_parent(
    conn: sqlite3.Connection,
    line_group: str,
    line_class: str,
    cycle_date: str,
    timestamp: str,
) -> int:
    conn.execute(
        """
        INSERT INTO wire_wear_cycles (
            line_group, line_class, cycle_date, source_type, completeness_state,
            source_lineage, created_at, updated_at
        ) VALUES (?, ?, ?, 'manual', 'incomplete', '[]', ?, ?)
        ON CONFLICT(line_group, line_class, cycle_date) DO UPDATE SET updated_at = excluded.updated_at
        """,
        (line_group, line_class, cycle_date, timestamp, timestamp),
    )
    return int(
        conn.execute(
            "SELECT cycle_id FROM wire_wear_cycles WHERE line_group = ? AND line_class = ? AND cycle_date = ?",
            (line_group, line_class, cycle_date),
        ).fetchone()["cycle_id"]
    )


def _tombstone_allows_change(
    conn: sqlite3.Connection,
    key: tuple[str, str, str, str],
    change_time: datetime,
) -> None:
    row = conn.execute(
        """
        SELECT deleted_at FROM wire_wear_deletion_tombstones
        WHERE line_group = ? AND line_class = ? AND cycle_date = ? AND tension_length = ?
        """,
        key,
    ).fetchone()
    if row is None:
        return
    if change_time <= _parse_timestamp(row["deleted_at"]):
        raise WearCycleRepositoryError("change is not newer than tombstone")
    conn.execute(
        """
        DELETE FROM wire_wear_deletion_tombstones
        WHERE line_group = ? AND line_class = ? AND cycle_date = ? AND tension_length = ?
        """,
        key,
    )


def _add_record(
    conn: sqlite3.Connection,
    operation: AddOperation,
    metadata: Sequence[MetadataInterval],
    change_time: datetime,
    timestamp: str,
) -> None:
    key, canonical = _canonical_for_key(operation.key, metadata)
    if conn.execute(
        """
        SELECT 1 FROM wire_wear_cycle_records
        WHERE line_group = ? AND line_class = ? AND cycle_date = ? AND tension_length = ?
        """,
        key,
    ).fetchone():
        raise WearCycleRepositoryError("duplicate business key")
    _tombstone_allows_change(conn, key, change_time)
    average = _validated_average(operation.avg_wear_min)
    cycle_id = _ensure_manual_parent(conn, key[0], key[1], key[2], timestamp)
    conn.execute(
        """
        INSERT INTO wire_wear_cycle_records (
            cycle_id, line_group, line_class, cycle_date, tension_length,
            track, from_m, to_m, avg_wear_min, wear_percentage,
            measurement_sd, physical_intervals, source_lineage, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, '[]', ?, ?)
        """,
        (
            cycle_id,
            *key,
            canonical.track,
            float(canonical.from_m),
            float(canonical.to_m),
            average,
            calculate_wear_percentage(average),
            _json(_interval_payload(canonical.intervals)),
            timestamp,
            timestamp,
        ),
    )


def _edit_record(
    conn: sqlite3.Connection,
    operation: EditOperation,
    metadata: Sequence[MetadataInterval],
    change_time: datetime,
    timestamp: str,
) -> None:
    key, canonical = _canonical_for_key(operation.key, metadata)
    _tombstone_allows_change(conn, key, change_time)
    average = _validated_average(operation.avg_wear_min)
    cursor = conn.execute(
        """
        UPDATE wire_wear_cycle_records SET
            track = ?, from_m = ?, to_m = ?, avg_wear_min = ?,
            wear_percentage = ?, measurement_sd = NULL, physical_intervals = ?, updated_at = ?
        WHERE line_group = ? AND line_class = ? AND cycle_date = ? AND tension_length = ?
          AND updated_at = ?
        """,
        (
            canonical.track,
            float(canonical.from_m),
            float(canonical.to_m),
            average,
            calculate_wear_percentage(average),
            _json(_interval_payload(canonical.intervals)),
            timestamp,
            *key,
            operation.expected_updated_at,
        ),
    )
    if cursor.rowcount != 1:
        raise StaleRecordError("record was changed or does not exist")
    _ensure_manual_parent(conn, key[0], key[1], key[2], timestamp)


def _upsert_tombstone(
    conn: sqlite3.Connection, key: tuple[str, str, str, str], timestamp: str
) -> None:
    conn.execute(
        """
        INSERT INTO wire_wear_deletion_tombstones (
            line_group, line_class, cycle_date, tension_length, deleted_at
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(line_group, line_class, cycle_date, tension_length) DO UPDATE SET
            deleted_at = excluded.deleted_at,
            source_package_id = NULL
        """,
        (*key, timestamp),
    )


def _delete_orphan_parent(
    conn: sqlite3.Connection, line_group: str, line_class: str, cycle_date: str
) -> None:
    conn.execute(
        """
        DELETE FROM wire_wear_cycles
        WHERE line_group = ? AND line_class = ? AND cycle_date = ?
          AND NOT EXISTS (
              SELECT 1 FROM wire_wear_cycle_records
              WHERE line_group = ? AND line_class = ? AND cycle_date = ?
          )
        """,
        (line_group, line_class, cycle_date, line_group, line_class, cycle_date),
    )


def _delete_cell(
    conn: sqlite3.Connection, operation: DeleteCellOperation, timestamp: str
) -> int:
    key = _key_parts(operation.key)
    cursor = conn.execute(
        """
        DELETE FROM wire_wear_cycle_records
        WHERE line_group = ? AND line_class = ? AND cycle_date = ? AND tension_length = ?
          AND updated_at = ?
        """,
        (*key, operation.expected_updated_at),
    )
    if cursor.rowcount != 1:
        raise StaleRecordError("record was changed or does not exist")
    _upsert_tombstone(conn, key, timestamp)
    _delete_orphan_parent(conn, key[0], key[1], key[2])
    return 1


def _delete_row(
    conn: sqlite3.Connection, operation: DeleteRowOperation, timestamp: str
) -> int:
    line_group, line_class = normalize_line_identity(
        operation.line_group, operation.line_class
    )
    cycle_date = normalize_cycle_date(operation.cycle_date).isoformat()
    keys = [
        (line_group, line_class, cycle_date, row["tension_length"])
        for row in conn.execute(
            """
            SELECT tension_length FROM wire_wear_cycle_records
            WHERE line_group = ? AND line_class = ? AND cycle_date = ?
            """,
            (line_group, line_class, cycle_date),
        ).fetchall()
    ]
    conn.execute(
        "DELETE FROM wire_wear_cycle_records WHERE line_group = ? AND line_class = ? AND cycle_date = ?",
        (line_group, line_class, cycle_date),
    )
    for key in keys:
        _upsert_tombstone(conn, key, timestamp)
    _delete_orphan_parent(conn, line_group, line_class, cycle_date)
    return len(keys)


def apply_change_set(
    conn: sqlite3.Connection,
    change_set: ChangeSet,
    metadata: Sequence[MetadataInterval],
    now: datetime | None = None,
    expected_data_version: int | None = None,
) -> ChangeSetResult:
    """Apply staged manual changes atomically with optimistic concurrency."""
    change_time, timestamp = _timestamp(now)
    added = edited = deleted = 0
    with _immediate_transaction(conn):
        if (
            expected_data_version is not None
            and current_data_version(conn) != expected_data_version
        ):
            raise StaleDataVersionError(
                "wire wear data changed since the candidate preview"
            )
        for index, operation in enumerate(change_set.operations):
            try:
                if isinstance(operation, AddOperation):
                    _add_record(conn, operation, metadata, change_time, timestamp)
                    added += 1
                elif isinstance(operation, EditOperation):
                    _edit_record(conn, operation, metadata, change_time, timestamp)
                    edited += 1
                elif isinstance(operation, DeleteCellOperation):
                    deleted += _delete_cell(conn, operation, timestamp)
                elif isinstance(operation, DeleteRowOperation):
                    deleted += _delete_row(conn, operation, timestamp)
                else:
                    raise WearCycleRepositoryError(
                        f"unsupported change operation: {type(operation).__name__}"
                    )
            except Exception as exc:
                raise ChangeOperationError(index, operation, exc) from exc
        data_version = bump_data_version(conn)
    return ChangeSetResult(added, edited, deleted, data_version)


def _decode_record(row: sqlite3.Row) -> dict[str, object]:
    item = dict(row)
    raw_lineage = item.get("source_lineage")
    item["source_lineage"] = json.loads(raw_lineage) if raw_lineage else []
    raw_intervals = item.get("physical_intervals")
    intervals = json.loads(raw_intervals) if raw_intervals else []
    if not intervals:
        intervals = [{
            "track": item.get("track"),
            "from_m": item.get("from_m"),
            "to_m": item.get("to_m"),
        }]
    item["physical_intervals"] = intervals
    item["interval_count"] = len(intervals)
    return item


def list_committed_records(
    conn: sqlite3.Connection,
    *,
    line_group: str | None = None,
    line_class: str | None = None,
    tension_length_query: str = "",
    selected_tension_length: str | None = None,
    date_from: date | str | None = None,
    date_to: date | str | None = None,
) -> list[dict[str, object]]:
    """List committed cycle records in stable workbench order."""
    where: list[str] = []
    params: list[object] = []
    if line_group is not None:
        line, normalized_class = normalize_line_identity(line_group, line_class)
        where.extend(("records.line_group = ?", "records.line_class = ?"))
        params.extend((line, normalized_class))
    elif line_class is not None:
        raise WearCycleRepositoryError("line_class requires line_group")
    selected = str(selected_tension_length or "").strip()
    if selected:
        where.append("records.tension_length = ?")
        params.append(selected)
    query = str(tension_length_query or "").strip()
    if query and not selected:
        escaped_query = (
            query.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        where.append("LOWER(records.tension_length) LIKE ? ESCAPE '\\'")
        params.append(f"%{escaped_query}%")
    if date_from is not None:
        where.append("records.cycle_date >= ?")
        params.append(normalize_cycle_date(date_from).isoformat())
    if date_to is not None:
        where.append("records.cycle_date <= ?")
        params.append(normalize_cycle_date(date_to).isoformat())
    sql = """
        SELECT records.*, cycles.source_type, cycles.completeness_state
        FROM wire_wear_cycle_records AS records
        JOIN wire_wear_cycles AS cycles ON cycles.cycle_id = records.cycle_id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += (
        " ORDER BY records.cycle_date, records.from_m, records.to_m, "
        "records.tension_length"
    )
    return [_decode_record(row) for row in conn.execute(sql, params).fetchall()]


query_committed_records = list_committed_records


def build_workbench(
    conn: sqlite3.Connection,
    line_group: str,
    tension_length_query: str = "",
    date_from: date | str | None = None,
    date_to: date | str | None = None,
    line_class: str | None = None,
    selected_tension_length: str | None = None,
    summary_only: bool = False,
) -> dict[str, object]:
    """Build the filtered historical matrix and aligned latest summary."""
    line, normalized_class = normalize_line_identity(line_group, line_class)
    history = list_committed_records(
        conn,
        line_group=line,
        line_class=normalized_class,
        tension_length_query=tension_length_query,
        selected_tension_length=selected_tension_length,
    )
    values_by_tl: dict[str, list[float]] = {}
    history_by_tl: dict[str, list[dict[str, object]]] = {}
    for record in history:
        tension_length = str(record["tension_length"])
        values_by_tl.setdefault(tension_length, []).append(
            float(record["avg_wear_min"])
        )
        history_by_tl.setdefault(tension_length, []).append(record)
    historical_sd = {
        tension_length: stdev(values) if len(values) > 1 else None
        for tension_length, values in values_by_tl.items()
    }
    records = history if date_from is None and date_to is None else list_committed_records(
        conn,
        line_group=line,
        line_class=normalized_class,
        tension_length_query=tension_length_query,
        selected_tension_length=selected_tension_length,
        date_from=date_from,
        date_to=date_to,
    )
    for record in records:
        record["historical_sd"] = historical_sd[str(record["tension_length"])]

    columns_by_tl: dict[str, dict[str, object]] = {}
    for record in sorted(
        records,
        key=lambda item: (
            float(item["from_m"]),
            float(item["to_m"]),
            natural_key(str(item["tension_length"])),
        ),
    ):
        tension_length = str(record["tension_length"])
        columns_by_tl.setdefault(
            tension_length,
            {
                "tension_length": tension_length,
                "track": record["track"],
                "from_m": record["from_m"],
                "to_m": record["to_m"],
                "interval_count": record["interval_count"],
                "physical_intervals": record["physical_intervals"],
            },
        )
    columns = list(columns_by_tl.values())

    matrix_rows = []
    if not summary_only:
        records_by_date: dict[str, dict[str, dict[str, object]]] = {}
        for record in records:
            records_by_date.setdefault(str(record["cycle_date"]), {})[
                str(record["tension_length"])
            ] = record
        matrix_rows = [
            {
                "cycle_date": cycle_date,
                "values": {
                    str(column["tension_length"]): (
                        records_by_date[cycle_date]
                        .get(str(column["tension_length"]), {})
                        .get("avg_wear_min")
                    )
                    for column in columns
                },
            }
            for cycle_date in sorted(records_by_date)
        ]

    latest_by_tl: dict[str, dict[str, object]] = {}
    for record in records:
        tension_length = str(record["tension_length"])
        current = latest_by_tl.get(tension_length)
        if current is None or str(record["cycle_date"]) > str(current["cycle_date"]):
            latest_by_tl[tension_length] = record
    latest_summary = []
    for column in columns:
        tension_length = str(column["tension_length"])
        latest = latest_by_tl[tension_length]
        trend = fit_tl_trend(_history_points(history_by_tl[tension_length]))
        latest_summary.append(
            {
                "line_group": line,
                "line_class": normalized_class,
                "tension_length": tension_length,
                "latest_cycle_date": latest["cycle_date"],
                "latest_avg_wear_min": latest["avg_wear_min"],
                "latest_wear_percentage": latest["wear_percentage"],
                "historical_sd": historical_sd[tension_length],
                "wear_rate_percent_per_year": trend.wear_percent_per_year,
                "wear_rate_mm_per_year": trend.mm_per_year,
                "observation_count": trend.observation_count,
                "r_squared": trend.r_squared,
                "trend_status": trend.status,
            }
        )
    return {
        "line_group": line,
        "line_class": normalized_class,
        "columns": columns,
        "matrix_rows": matrix_rows,
        "latest_summary": latest_summary,
        "records": [] if summary_only else records,
        "summary_only": summary_only,
        "data_version": current_data_version(conn),
    }
