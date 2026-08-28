"""Persistence and analytics for Wear Calculator wire wear records."""
from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

import pandas as pd


class WireWearValidationError(ValueError):
    """Raised when wire wear record input cannot be normalized."""


@dataclass(frozen=True)
class WireWearRecordInput:
    tension_length: str
    from_m: float
    to_m: float
    avg_wear_min: float
    sd: float
    wear_percentage: float


@dataclass(frozen=True)
class WireWearSaveRequest:
    line_group: str
    line_class: str
    track: str
    section: str
    cycle_date: str
    source_file_names: List[str]
    records: List[WireWearRecordInput]
    saved_by: Optional[str] = None


@dataclass(frozen=True)
class WireWearSaveResult:
    saved_count: int
    updated_count: int
    duplicate_count: int
    duplicates: List[Dict[str, Any]] = field(default_factory=list)


def normalize_line_group(line_group: str, line_class: str) -> tuple[str, str]:
    normalized_group = (line_group or "").strip().upper()
    normalized_class = (line_class or normalized_group).strip().upper()
    if normalized_class == "LMC":
        return "EAL", "LMC"
    if normalized_class == "TML" or normalized_group == "TML":
        return "TML", "TML"
    return "EAL", "EAL"


def _parse_cycle_date(value: str) -> str:
    text = str(value or "").strip().replace("/", "-")
    try:
        if len(text) == 8 and text.isdigit():
            return date.fromisoformat(f"{text[:4]}-{text[4:6]}-{text[6:8]}").isoformat()
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError as exc:
        raise WireWearValidationError(f"Invalid cycle date: {value}") from exc


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    result = dict(row)
    raw_sources = result.get("source_file_names")
    result["source_file_names"] = json.loads(raw_sources) if raw_sources else []
    return result


def _duplicate_key(
    line_group: str,
    line_class: str,
    track: str,
    section: str,
    cycle_date: str,
    tension_length: str,
) -> tuple[str, str, str, str, str, str]:
    return (line_group, line_class, track, section, cycle_date, tension_length)


def _find_duplicates(conn: sqlite3.Connection, request: WireWearSaveRequest) -> List[Dict[str, Any]]:
    line_group, line_class = normalize_line_group(request.line_group, request.line_class)
    cycle_date = _parse_cycle_date(request.cycle_date)
    duplicates: List[Dict[str, Any]] = []
    for record in request.records:
        row = conn.execute(
            """
            SELECT * FROM wire_wear_records
            WHERE line_group = ?
              AND line_class = ?
              AND track = ?
              AND section = ?
              AND cycle_date = ?
              AND tension_length = ?
            """,
            (line_group, line_class, request.track, request.section, cycle_date, record.tension_length),
        ).fetchone()
        if row:
            duplicates.append(_row_to_dict(row))
    return duplicates


def save_wire_wear_records(
    conn: sqlite3.Connection,
    request: WireWearSaveRequest,
    overwrite: bool = False,
) -> WireWearSaveResult:
    line_group, line_class = normalize_line_group(request.line_group, request.line_class)
    cycle_date = _parse_cycle_date(request.cycle_date)
    duplicates = _find_duplicates(conn, request)
    if duplicates and not overwrite:
        return WireWearSaveResult(
            saved_count=0,
            updated_count=0,
            duplicate_count=len(duplicates),
            duplicates=duplicates,
        )

    duplicate_keys = {
        _duplicate_key(
            row["line_group"],
            row["line_class"],
            row["track"],
            row["section"],
            row["cycle_date"],
            row["tension_length"],
        )
        for row in duplicates
    }
    source_file_names = json.dumps(request.source_file_names)
    saved_count = 0
    updated_count = 0

    for record in request.records:
        key = _duplicate_key(
            line_group,
            line_class,
            request.track,
            request.section,
            cycle_date,
            record.tension_length,
        )
        conn.execute(
            """
            INSERT INTO wire_wear_records (
                line_group, line_class, track, section, cycle_date,
                tension_length, from_m, to_m, avg_wear_min, sd,
                wear_percentage, source_file_names, saved_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(line_group, line_class, track, section, cycle_date, tension_length)
            DO UPDATE SET
                from_m = excluded.from_m,
                to_m = excluded.to_m,
                avg_wear_min = excluded.avg_wear_min,
                sd = excluded.sd,
                wear_percentage = excluded.wear_percentage,
                source_file_names = excluded.source_file_names,
                saved_by = excluded.saved_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                line_group,
                line_class,
                request.track,
                request.section,
                cycle_date,
                record.tension_length,
                record.from_m,
                record.to_m,
                record.avg_wear_min,
                record.sd,
                record.wear_percentage,
                source_file_names,
                request.saved_by,
            ),
        )
        if key in duplicate_keys:
            updated_count += 1
        else:
            saved_count += 1

    return WireWearSaveResult(
        saved_count=saved_count,
        updated_count=updated_count,
        duplicate_count=len(duplicates),
        duplicates=duplicates,
    )


_UPDATEABLE_RECORD_FIELDS = {
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
}


def _normalize_update_value(field_name: str, value: Any) -> Any:
    if field_name == "cycle_date":
        return _parse_cycle_date(str(value))
    if field_name in {"line_group", "line_class"}:
        return str(value).strip().upper()
    if field_name == "source_file_names":
        return json.dumps(value or [])
    if field_name in {"from_m", "to_m", "avg_wear_min", "sd", "wear_percentage"}:
        return float(value)
    return str(value)


def update_wire_wear_record(conn: sqlite3.Connection, record_id: int, updates: Dict[str, Any]) -> bool:
    filtered = {
        key: _normalize_update_value(key, value)
        for key, value in updates.items()
        if key in _UPDATEABLE_RECORD_FIELDS and value is not None
    }
    if not filtered:
        return False
    if "line_group" in filtered or "line_class" in filtered:
        current = conn.execute(
            "SELECT line_group, line_class FROM wire_wear_records WHERE record_id = ?",
            (record_id,),
        ).fetchone()
        if current is None:
            return False
        line_group, line_class = normalize_line_group(
            filtered.get("line_group", current["line_group"]),
            filtered.get("line_class", current["line_class"]),
        )
        filtered["line_group"] = line_group
        filtered["line_class"] = line_class
    assignments = ", ".join(f"{field_name} = ?" for field_name in filtered)
    cursor = conn.execute(
        f"UPDATE wire_wear_records SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE record_id = ?",
        [*filtered.values(), record_id],
    )
    return cursor.rowcount == 1


def delete_wire_wear_record(conn: sqlite3.Connection, record_id: int) -> bool:
    cursor = conn.execute("DELETE FROM wire_wear_records WHERE record_id = ?", (record_id,))
    return cursor.rowcount == 1


def query_wire_wear_records(
    conn: sqlite3.Connection,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    filters = filters or {}
    where: List[str] = []
    params: List[Any] = []

    for field_name in ("line_group", "line_class", "track", "section", "tension_length"):
        value = filters.get(field_name)
        if value:
            where.append(f"{field_name} = ?")
            params.append(str(value).strip().upper() if field_name in {"line_group", "line_class"} else str(value))

    if filters.get("date_from"):
        where.append("cycle_date >= ?")
        params.append(_parse_cycle_date(str(filters["date_from"])))
    if filters.get("date_to"):
        where.append("cycle_date <= ?")
        params.append(_parse_cycle_date(str(filters["date_to"])))

    sql = "SELECT * FROM wire_wear_records"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY line_group, line_class, cycle_date, from_m, tension_length"
    return [_row_to_dict(row) for row in conn.execute(sql, params).fetchall()]


def _years_between(start_iso: str, end_iso: str) -> float:
    start = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso)
    return max((end - start).days / 365.25, 0.0)


def _linear_slope(points: List[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return 0.0
    return sum((x - x_mean) * (y - y_mean) for x, y in points) / denominator


def _average(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _format_float(value: float, decimals: int = 3) -> float:
    return round(float(value), decimals)


def _projection_year_label(
    latest_year: int,
    latest_wear: float,
    rate: Optional[float],
    threshold: float,
    point_count: int,
) -> str:
    if point_count < 2 or rate is None or not math.isfinite(rate) or rate <= 0:
        return "Insufficient Data"
    if latest_wear >= threshold:
        return str(latest_year)
    projected_year = latest_year + math.ceil((threshold - latest_wear) / rate)
    if projected_year > 2100:
        return "Beyond 2100"
    return str(projected_year)


def _aggregated_tension_length_series(records: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
    for record in records:
        tension_length = str(record["tension_length"])
        grouped.setdefault((record["cycle_date"], tension_length), []).append(record)

    by_tl: Dict[str, List[Dict[str, Any]]] = {}
    for (cycle_date, tension_length), values in grouped.items():
        by_tl.setdefault(tension_length, []).append({
            "cycle_date": cycle_date,
            "tension_length": tension_length,
            "avg_wear_min": _average([float(item["avg_wear_min"]) for item in values]),
            "wear_percentage": _average([float(item["wear_percentage"]) for item in values]),
            "raw_count": len(values),
        })

    for values in by_tl.values():
        values.sort(key=lambda item: item["cycle_date"])
    return by_tl


def _rate_for_aggregated_points(
    points: List[Dict[str, Any]], field_name: str
) -> Optional[float]:
    if len(points) < 2:
        return None
    base_date = points[0]["cycle_date"]
    slope = _linear_slope([
        (_years_between(base_date, item["cycle_date"]), float(item[field_name]))
        for item in points
    ])
    return slope if math.isfinite(slope) else None


def build_workbench_summary(
    conn: sqlite3.Connection,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    filters = filters or {}
    line_group = str(filters.get("line_group") or "EAL").strip().upper()
    records = query_wire_wear_records(conn, {**filters, "line_group": line_group})
    tension_lengths = sorted({str(record["tension_length"]) for record in records})
    series_by_tl = _aggregated_tension_length_series(records)

    dates = sorted({record["cycle_date"] for record in records})
    history_rows: List[Dict[str, Any]] = []
    for cycle_date in dates:
        values: Dict[str, Optional[float]] = {}
        for tension_length in tension_lengths:
            point = next(
                (item for item in series_by_tl.get(tension_length, []) if item["cycle_date"] == cycle_date),
                None,
            )
            values[tension_length] = _format_float(point["avg_wear_min"]) if point else None
        history_rows.append({"cycle_date": cycle_date, "values": values})

    latest_metrics = [
        ("Latest Wear %", {}),
        ("Wear % Rate per year", {}),
        ("Wear mm Rate per year", {}),
        ("20% Wear Projection year", {}),
        ("33% Wear Projection year", {}),
    ]
    metric_values = {name: values for name, values in latest_metrics}

    for tension_length in tension_lengths:
        points = series_by_tl.get(tension_length, [])
        if not points:
            continue
        latest = points[-1]
        latest_year = date.fromisoformat(latest["cycle_date"]).year
        percent_rate = _rate_for_aggregated_points(points, "wear_percentage")
        thickness_slope = _rate_for_aggregated_points(points, "avg_wear_min")
        mm_rate = (
            -thickness_slope
            if thickness_slope is not None and -thickness_slope > 0
            else None
        )
        if mm_rate is None:
            percent_rate = None
        metric_values["Latest Wear %"][tension_length] = f"{latest['wear_percentage']:.2f} %"
        metric_values["Wear % Rate per year"][tension_length] = (
            f"{percent_rate:.2f} % /year" if percent_rate is not None else "N/A"
        )
        metric_values["Wear mm Rate per year"][tension_length] = (
            f"{mm_rate:.3f} mm /year" if mm_rate is not None else "N/A"
        )
        metric_values["20% Wear Projection year"][tension_length] = _projection_year_label(
            latest_year, float(latest["wear_percentage"]), percent_rate, 20.0, len(points)
        )
        metric_values["33% Wear Projection year"][tension_length] = _projection_year_label(
            latest_year, float(latest["wear_percentage"]), percent_rate, 33.0, len(points)
        )

    return {
        "line_group": line_group,
        "tension_lengths": tension_lengths,
        "history_rows": history_rows,
        "latest_summary_rows": [
            {"metric": metric, "values": metric_values[metric]}
            for metric in (
                "Latest Wear %",
                "Wear % Rate per year",
                "Wear mm Rate per year",
                "20% Wear Projection year",
                "33% Wear Projection year",
            )
        ],
        "detail_records": {
            tension_length: [
                record for record in records
                if str(record["tension_length"]) == tension_length
            ]
            for tension_length in tension_lengths
        },
        "raw_records": records,
    }


def build_workbench_excel(conn: sqlite3.Connection, filters: Optional[Dict[str, Any]] = None) -> bytes:
    summary = build_workbench_summary(conn, filters)
    buffer = BytesIO()

    history_rows = []
    for row in summary["history_rows"]:
        history_rows.append({"Date": row["cycle_date"], **row["values"]})

    latest_rows = []
    for row in summary["latest_summary_rows"]:
        latest_rows.append({"Metric": row["metric"], **row["values"]})

    raw_rows = summary["raw_records"]

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(history_rows).to_excel(writer, sheet_name="History Avg Wear Min", index=False)
        pd.DataFrame(latest_rows).to_excel(writer, sheet_name="Latest Summary", index=False)
        pd.DataFrame(raw_rows).to_excel(writer, sheet_name="Raw Records", index=False)

    return buffer.getvalue()


_WIRE_WEAR_SYNC_COLUMNS = [
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
]


def _metadata_hashes(metadata_dir: Optional[Path]) -> List[Dict[str, str]]:
    if not metadata_dir or not metadata_dir.exists():
        return []

    hashes: List[Dict[str, str]] = []
    for path in sorted(metadata_dir.glob("*.xlsx")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes.append({
            "file_name": path.name,
            "path": str(path),
            "sha256": digest,
        })
    return hashes


def _system_data_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT value FROM system_metadata WHERE key = 'db_version'").fetchone()
    if not row:
        return 1
    try:
        return int(row["value"])
    except (TypeError, ValueError):
        return 1


def _table_rows(conn: sqlite3.Connection, table_name: str) -> List[Dict[str, Any]]:
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    if not table_exists:
        return []
    return [dict(row) for row in conn.execute(f"SELECT * FROM {table_name}").fetchall()]


def build_wire_wear_sync_package(
    conn: sqlite3.Connection,
    source_label: str,
    include_repeated: bool = False,
    metadata_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    records = query_wire_wear_records(conn)
    return {
        "package_type": "tov640-wire-wear-sync",
        "schema_version": 1,
        "data_version": _system_data_version(conn),
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "source_label": source_label,
        "wire_wear_records": records,
        "repeated_records": _table_rows(conn, "saved_repeated_exceptions") if include_repeated else [],
        "metadata_hashes": _metadata_hashes(metadata_dir),
    }


def _parse_timestamp(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.min
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime.min


def _wire_wear_key(record: Dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    return (
        str(record.get("line_group", "")).strip().upper(),
        str(record.get("line_class", "")).strip().upper(),
        str(record.get("track", "")),
        str(record.get("section", "")),
        _parse_cycle_date(str(record.get("cycle_date", ""))),
        str(record.get("tension_length", "")),
    )


def _normalize_sync_record(record: Dict[str, Any]) -> Dict[str, Any]:
    line_group, line_class = normalize_line_group(
        str(record.get("line_group", "")),
        str(record.get("line_class", "")),
    )
    source_file_names = record.get("source_file_names") or []
    if isinstance(source_file_names, str):
        try:
            source_file_names = json.loads(source_file_names)
        except json.JSONDecodeError:
            source_file_names = [source_file_names]
    return {
        "line_group": line_group,
        "line_class": line_class,
        "track": str(record.get("track", "")),
        "section": str(record.get("section", "")),
        "cycle_date": _parse_cycle_date(str(record.get("cycle_date", ""))),
        "tension_length": str(record.get("tension_length", "")),
        "from_m": float(record.get("from_m", 0)),
        "to_m": float(record.get("to_m", 0)),
        "avg_wear_min": float(record.get("avg_wear_min", 0)),
        "sd": float(record.get("sd", 0)),
        "wear_percentage": float(record.get("wear_percentage", 0)),
        "source_file_names": json.dumps(source_file_names),
        "saved_by": record.get("saved_by"),
        "created_at": str(record.get("created_at") or datetime.now().isoformat(timespec="seconds")),
        "updated_at": str(record.get("updated_at") or datetime.now().isoformat(timespec="seconds")),
    }


def _create_sqlite_backup(conn: sqlite3.Connection, db_path: Optional[Path]) -> Optional[str]:
    if db_path is None:
        return None
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    backup_dir = db_path.parent / "sync-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{db_path.stem}-sync-backup-{datetime.now():%Y%m%d%H%M%S}-{uuid4().hex[:8]}.db"
    with sqlite3.connect(str(backup_path)) as backup_conn:
        conn.backup(backup_conn)
    return str(backup_path)


def import_wire_wear_sync_package(
    conn: sqlite3.Connection,
    package: Dict[str, Any],
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    if package.get("package_type") != "tov640-wire-wear-sync":
        raise WireWearValidationError("Invalid wire wear sync package.")

    backup_path = _create_sqlite_backup(conn, db_path)
    inserted_count = 0
    updated_count = 0
    skipped_rows: List[Dict[str, Any]] = []

    for raw_record in package.get("wire_wear_records", []):
        record = _normalize_sync_record(raw_record)
        key = _wire_wear_key(record)
        existing = conn.execute(
            """
            SELECT * FROM wire_wear_records
            WHERE line_group = ?
              AND line_class = ?
              AND track = ?
              AND section = ?
              AND cycle_date = ?
              AND tension_length = ?
            """,
            key,
        ).fetchone()

        if existing is not None:
            if _parse_timestamp(existing["updated_at"]) >= _parse_timestamp(record["updated_at"]):
                skipped_rows.append({
                    "tension_length": record["tension_length"],
                    "cycle_date": record["cycle_date"],
                    "reason": "local_newer_or_same",
                    "local_updated_at": existing["updated_at"],
                    "import_updated_at": record["updated_at"],
                })
                continue
            assignments = ", ".join(f"{column} = ?" for column in _WIRE_WEAR_SYNC_COLUMNS)
            conn.execute(
                f"UPDATE wire_wear_records SET {assignments} WHERE record_id = ?",
                [record[column] for column in _WIRE_WEAR_SYNC_COLUMNS] + [existing["record_id"]],
            )
            updated_count += 1
            continue

        conn.execute(
            f"""
            INSERT INTO wire_wear_records ({", ".join(_WIRE_WEAR_SYNC_COLUMNS)})
            VALUES ({", ".join("?" for _ in _WIRE_WEAR_SYNC_COLUMNS)})
            """,
            [record[column] for column in _WIRE_WEAR_SYNC_COLUMNS],
        )
        inserted_count += 1

    conn.commit()
    return {
        "backup_path": backup_path,
        "inserted_count": inserted_count,
        "updated_count": updated_count,
        "skipped_count": len(skipped_rows),
        "skipped_rows": skipped_rows,
        "metadata_hashes": package.get("metadata_hashes", []),
        "source_label": package.get("source_label", ""),
        "exported_at": package.get("exported_at", ""),
    }


def _rate_rows(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[tuple[str, str, str, str, str], List[Dict[str, Any]]] = {}
    for record in records:
        key = (
            record["line_group"],
            record["line_class"],
            record["track"],
            record["section"],
            record["tension_length"],
        )
        grouped.setdefault(key, []).append(record)

    rows: List[Dict[str, Any]] = []
    for (line_group, line_class, track, section, tension_length), values in grouped.items():
        values = sorted(values, key=lambda item: item["cycle_date"])
        by_date: Dict[str, List[Dict[str, Any]]] = {}
        for item in values:
            by_date.setdefault(str(item["cycle_date"]), []).append(item)
        aggregated = [
            {
                "cycle_date": cycle_date,
                "wear_percentage": _average([
                    float(item["wear_percentage"]) for item in date_values
                ]),
                "avg_wear_min": _average([
                    float(item["avg_wear_min"]) for item in date_values
                ]),
            }
            for cycle_date, date_values in sorted(by_date.items())
        ]
        base_date = aggregated[0]["cycle_date"]
        percent_points = [
            (_years_between(base_date, item["cycle_date"]), float(item["wear_percentage"]))
            for item in aggregated
        ]
        remaining_height_points = [
            (_years_between(base_date, item["cycle_date"]), float(item["avg_wear_min"]))
            for item in aggregated
        ]
        percent_slope = _linear_slope(percent_points) if len(aggregated) >= 2 else None
        remaining_height_slope = (
            _linear_slope(remaining_height_points) if len(aggregated) >= 2 else None
        )
        mm_rate = (
            -remaining_height_slope
            if remaining_height_slope is not None
            and math.isfinite(remaining_height_slope)
            and -remaining_height_slope > 0
            else None
        )
        trend_status = "eligible"
        if len(aggregated) < 2:
            trend_status = "insufficient_data"
        elif mm_rate is None:
            trend_status = "non_positive_rate"
        if percent_slope is None or not math.isfinite(percent_slope) or trend_status != "eligible":
            percent_slope = None
        latest = values[-1]
        rows.append({
            "line_group": line_group,
            "line_class": line_class,
            "track": track,
            "section": section,
            "tension_length": tension_length,
            "latest_cycle_date": latest["cycle_date"],
            "latest_wear_percentage": latest["wear_percentage"],
            "latest_avg_wear_min": latest["avg_wear_min"],
            "wear_percent_per_year": round(percent_slope, 4) if percent_slope is not None else None,
            "wear_mm_per_year": round(mm_rate, 4) if mm_rate is not None else None,
            "wear_rate_percent_per_year": round(percent_slope, 4) if percent_slope is not None else None,
            "wear_rate_mm_per_year": round(mm_rate, 4) if mm_rate is not None else None,
            "record_count": len(aggregated),
            "observation_count": len(aggregated),
            "trend_status": trend_status,
        })
    return rows


def build_dashboard_summary(conn: sqlite3.Connection) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    rates = _rate_rows(query_wire_wear_records(conn))
    summary: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for line_group in ("EAL", "TML"):
        group_rows = [row for row in rates if row["line_group"] == line_group]
        eligible_rows = [row for row in group_rows if row["trend_status"] == "eligible"]
        summary[line_group] = {
            "top_max_rate": sorted(
                eligible_rows,
                key=lambda row: row["wear_percent_per_year"],
                reverse=True,
            )[:5],
            "top_min_rate": sorted(eligible_rows, key=lambda row: row["wear_percent_per_year"])[:5],
            "top_current_wear": sorted(
                group_rows,
                key=lambda row: row["latest_wear_percentage"],
                reverse=True,
            )[:5],
        }
    return summary


def build_projection_summary(
    conn: sqlite3.Connection,
    threshold_percentage: float = 20.0,
    years: int = 30,
) -> Dict[str, Any]:
    rates = _rate_rows(query_wire_wear_records(conn))
    output: Dict[str, Any] = {
        "threshold_percentage": threshold_percentage,
        "years": years,
        "line_groups": {},
    }

    for line_group in ("EAL", "TML"):
        group_rows = [row for row in rates if row["line_group"] == line_group]
        anchor_year = min(
            (date.fromisoformat(row["latest_cycle_date"]).year for row in group_rows),
            default=date.today().year,
        )
        buckets = [{"year": anchor_year + offset, "count": 0} for offset in range(years + 1)]
        projected_records: List[Dict[str, Any]] = []

        for row in group_rows:
            rate_value = row["wear_percent_per_year"]
            rate = float(rate_value) if rate_value is not None else None
            latest = float(row["latest_wear_percentage"])
            latest_year = date.fromisoformat(row["latest_cycle_date"]).year
            if latest >= threshold_percentage:
                years_to_threshold: Optional[float] = 0.0
            elif rate is None or rate <= 0:
                years_to_threshold = None
            else:
                years_to_threshold = (threshold_percentage - latest) / rate

            projected_year = None
            if years_to_threshold is not None and math.isfinite(years_to_threshold):
                projected_year = latest_year + max(0, math.ceil(years_to_threshold))

            projected = {
                **row,
                "years_to_threshold": years_to_threshold,
                "projected_year": projected_year,
            }
            if projected_year is not None and anchor_year <= projected_year <= anchor_year + years:
                buckets[projected_year - anchor_year]["count"] += 1
            projected_records.append(projected)

        output["line_groups"][line_group] = {
            "year_buckets": buckets,
            "records": projected_records,
        }
    return output
