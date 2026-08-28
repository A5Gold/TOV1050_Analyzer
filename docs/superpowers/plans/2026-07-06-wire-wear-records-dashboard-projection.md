# Wire Wear Records Dashboard Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Wear Calculator internal wire wear records database, historical chart views, line-split dashboard rankings, and 20 percent wear projection from saved cycle records.

**Architecture:** Keep all user-facing record review, dashboard, and projection UI inside `WearCalculatorView`, not the existing Database module. Persist calculated cycle-level tension length wear results in SQLite through calculation-owned APIs under `/api/calculation/wear-records`. Build backend rate and projection calculations from saved records so imported cycles remain available after upload state is cleared.

**Tech Stack:** FastAPI, SQLite, Python dataclasses, React 18, Zustand, MUI, MUI DataGrid, Plotly, Vitest, pytest.

---

## Approved Product Decisions

- The Wear Calculator module has four feature workspaces: `Analysis`, `Wire Wear Records`, `Dashboard`, and `Projection`.
- The existing current-cycle graph of every tension length wire wear percentage remains visible immediately after Analysis. The existing `WearOverviewChart` in `frontend/src/components/Calculation/WearResultTable.tsx` already covers this surface and should be reused/refined.
- `Wire Wear Records` is the visible record database for users. Do not put this UI in the Database module.
- Historical chart modes:
  - `By Cycle`: select one cycle date and compare all tension lengths in that cycle.
  - `By Tension Length`: select one tension length and show all cycle records over time.
- Dashboard is split by `line_group`: `EAL` and `TML`.
- `LMC` is not a separate `line_group`. Store it as `line_class = LMC` under `line_group = EAL`.
- Use this storage rule everywhere:
  - `line_group: EAL | TML`
  - `line_class: EAL | LMC | TML`
- Dashboard cards:
  - Top 5 Max wire wear rate, displayed as `%/year` and `mm/year`.
  - Top 5 Min wire wear rate, displayed as `%/year` and `mm/year`.
  - Top 5 current wire wear, ranked by latest `wear_percentage` with rate columns beside it. This resolves the ambiguous user phrase "Top 5 wire wear rate" without duplicating the Max rate card.
- Projection targets 20 percent wear over the next 30 years, bucketed by projected year and split by `line_group`.

## Codebase-Memory Findings

Use the existing codebase-memory graph project `C-Smart-Maintanence-TOV640_Analyzer`. The index is ready with 3629 nodes and 7550 edges.

Important graph nodes:

- `frontend/src/views/WearCalculatorView.tsx`
  - `WearCalculatorView`, lines 19-202.
  - Current top tabs are calculation-run tabs, not feature workspaces.
- `frontend/src/store/useWearStore.ts`
  - `analyze`, lines 107-135.
  - Calls `uploadWearFiles(tab.uploadedFiles, tab.line)` and stores `res.date` plus `res.wear_results`.
- `frontend/src/api/client.ts`
  - `uploadWearFiles`, lines 46-61.
  - Posts multipart data to `/calculation/wear`.
- `backend/app/api/endpoints/calculation.py`
  - `upload_wear`, lines 78-141.
  - Parses uploaded reports, dedupes latest chainage data, loads tension length lookup, calls `calculate_average_wear`, and returns `date` plus `wear_results`.
- `backend/app/core/calculation/wear_calculator.py`
  - `WearResult`, lines 20-30.
  - `calculate_average_wear`, lines 48-157.
  - Result fields: `tension_length`, `from_m`, `to_m`, `line`, `track`, `avg_wear_min`, `sd`, `wear_percentage`, `dates`, `record_points`.
- `frontend/src/components/Calculation/WearResultTable.tsx`
  - `WearOverviewChart`, lines 98-133.
  - Already plots current cycle tension length `wear_percentage` as a bar chart.
- `backend/app/core/database.py`
  - `DatabaseManager.get_connection`, lines 273-288.
  - Existing endpoints use `get_database()` and `with db.get_connection() as conn:`.
- `backend/app/core/schema.sql`
  - Existing schema initializes through `DatabaseManager._init_database`.
  - Add the wire wear records table here and add a targeted legacy migration in `DatabaseManager`.

## File Structure

Create:

- `backend/app/core/calculation/wear_records.py`
  - Dataclasses, line group normalization, save/query functions, rate calculation, dashboard summary, and projection calculation.
- `backend/app/api/endpoints/wear_records.py`
  - FastAPI request/response models and `/calculation/wear-records` endpoints.
- `backend/tests/test_wear_records.py`
  - Unit tests for save/query/rate/projection functions.
- `backend/tests/test_wear_records_api.py`
  - API tests for save conflict, overwrite, list, dashboard, and projection.
- `frontend/src/components/Calculation/WearRecordsPanel.tsx`
  - User-visible DataGrid plus chart mode controls.
- `frontend/src/components/Calculation/WearDashboardPanel.tsx`
  - EAL and TML dashboard cards.
- `frontend/src/components/Calculation/WearProjectionPanel.tsx`
  - Projection summary table and 30-year bucket chart.
- `frontend/src/components/Calculation/wearRecordCharts.tsx`
  - Shared Plotly chart components for records, dashboard, and projection.
- `frontend/src/store/useWearRecordsStore.ts`
  - Fetch/save/overwrite/list/dashboard/projection state.
- `frontend/src/store/__tests__/useWearRecordsStore.test.ts`
- `frontend/src/components/Calculation/__tests__/WearRecordsPanel.test.tsx`
- `frontend/src/components/Calculation/__tests__/WearDashboardPanel.test.tsx`
- `frontend/src/components/Calculation/__tests__/WearProjectionPanel.test.tsx`

Modify:

- `backend/app/core/schema.sql`
  - Add `wire_wear_records` table, indexes, and metadata triggers.
- `backend/app/core/database.py`
  - Add `_apply_wire_wear_records_migration`.
  - Call it from `_init_database` before `conn.executescript(schema_sql)`.
- `backend/app/main.py`
  - Include `wear_records.router`.
- `frontend/src/types/api.ts`
  - Add wire wear record, save, dashboard, and projection types.
- `frontend/src/api/client.ts`
  - Add calculation-owned wire wear records API helpers.
- `frontend/src/store/useWearStore.ts`
  - Add `lineClass` to the analysis tab state and send the matching `section` to `/calculation/wear`.
- `frontend/src/views/WearCalculatorView.tsx`
  - Add feature workspace tabs and render Analysis, Wire Wear Records, Dashboard, and Projection within the same module.
- `frontend/src/components/Calculation/WearResultTable.tsx`
  - Add optional save action props while keeping the current-cycle chart.
- Existing tests:
  - Update `frontend/src/views/__tests__/WearCalculatorView.test.tsx`.
  - Update `frontend/src/store/__tests__/useWearStore.test.ts`.
  - Update API client tests if present.

---

### Task 1: Database Schema and Migration

**Files:**
- Modify: `backend/app/core/schema.sql`
- Modify: `backend/app/core/database.py`
- Test: `backend/tests/test_wear_records.py`

- [ ] **Step 1: Write the failing schema test**

Add this to `backend/tests/test_wear_records.py`:

```python
import sqlite3

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
        "created_at",
        "updated_at",
    }.issubset(columns)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest backend/tests/test_wear_records.py::test_wire_wear_records_table_exists -q
```

Expected: fail because `wire_wear_records` does not exist.

- [ ] **Step 3: Add the schema**

Append this section to `backend/app/core/schema.sql` before the final trigger/index section if one exists, otherwise after `saved_repeated_exceptions` indexes:

```sql
-- -----------------------------------------------------------------------------
-- Table: wire_wear_records
-- Purpose: Wear Calculator internal database for cycle-level tension length wear
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wire_wear_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_group TEXT NOT NULL CHECK(line_group IN ('EAL', 'TML')),
    line_class TEXT NOT NULL CHECK(line_class IN ('EAL', 'LMC', 'TML')),
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
    saved_by TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(line_group, line_class, track, section, cycle_date, tension_length)
);

CREATE INDEX IF NOT EXISTS idx_wire_wear_line_group
    ON wire_wear_records(line_group);
CREATE INDEX IF NOT EXISTS idx_wire_wear_line_class
    ON wire_wear_records(line_class);
CREATE INDEX IF NOT EXISTS idx_wire_wear_cycle_date
    ON wire_wear_records(cycle_date);
CREATE INDEX IF NOT EXISTS idx_wire_wear_tension_length
    ON wire_wear_records(tension_length);
CREATE INDEX IF NOT EXISTS idx_wire_wear_group_tl_date
    ON wire_wear_records(line_group, tension_length, cycle_date);

CREATE TRIGGER IF NOT EXISTS trg_wire_wear_updated_at
AFTER UPDATE ON wire_wear_records
BEGIN
    UPDATE wire_wear_records
    SET updated_at = CURRENT_TIMESTAMP
    WHERE record_id = NEW.record_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_increment_db_version_wire_wear
AFTER INSERT ON wire_wear_records
BEGIN
    UPDATE system_metadata
    SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT),
        updated_at = CURRENT_TIMESTAMP
    WHERE key = 'db_version';
END;
```

- [ ] **Step 4: Add legacy migration**

In `backend/app/core/database.py`, add this method inside `DatabaseManager` after `_apply_repeated_records_migration`:

```python
    def _apply_wire_wear_records_migration(self, conn: sqlite3.Connection) -> None:
        """Migration 1.3: Ensure Wear Calculator wire wear records table exists."""
        if self._table_exists(conn, "wire_wear_records"):
            return

        conn.execute("""
            CREATE TABLE IF NOT EXISTS wire_wear_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_group TEXT NOT NULL CHECK(line_group IN ('EAL', 'TML')),
                line_class TEXT NOT NULL CHECK(line_class IN ('EAL', 'LMC', 'TML')),
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
                saved_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(line_group, line_class, track, section, cycle_date, tension_length)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wire_wear_line_group ON wire_wear_records(line_group)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wire_wear_line_class ON wire_wear_records(line_class)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wire_wear_cycle_date ON wire_wear_records(cycle_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wire_wear_tension_length ON wire_wear_records(tension_length)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wire_wear_group_tl_date "
            "ON wire_wear_records(line_group, tension_length, cycle_date)"
        )
        if self._table_exists(conn, "system_metadata"):
            set_system_metadata(conn, "schema_version", "1.3")
            set_system_metadata(conn, "last_migration", "1.3")
```

Then update `_init_database`:

```python
            self._apply_repeated_records_migration(conn)
            self._apply_wire_wear_records_migration(conn)
            conn.executescript(schema_sql)
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
python -m pytest backend/tests/test_wear_records.py::test_wire_wear_records_table_exists -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/schema.sql backend/app/core/database.py backend/tests/test_wear_records.py
git commit -m "feat: add wire wear records schema"
```

### Task 2: Backend Save and Query Service

**Files:**
- Create: `backend/app/core/calculation/wear_records.py`
- Test: `backend/tests/test_wear_records.py`

- [ ] **Step 1: Write failing save/query tests**

Append:

```python
from app.core.calculation.wear_records import (
    WireWearRecordInput,
    WireWearSaveRequest,
    query_wire_wear_records,
    save_wire_wear_records,
)


def test_save_wire_wear_records_maps_lmc_to_eal_group(tmp_path):
    db = DatabaseManager(str(tmp_path / "wear_records_save.db"))
    try:
        request = WireWearSaveRequest(
            line_group="EAL",
            line_class="LMC",
            track="UP",
            section="LMC",
            cycle_date="2026-02-01",
            source_file_names=["cycle.xlsx"],
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
    assert records[0]["line_group"] == "EAL"
    assert records[0]["line_class"] == "LMC"


def test_save_wire_wear_records_detects_duplicate_without_overwrite(tmp_path):
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest backend/tests/test_wear_records.py -q
```

Expected: import failure for `app.core.calculation.wear_records`.

- [ ] **Step 3: Implement service dataclasses and save/query**

Create `backend/app/core/calculation/wear_records.py`:

```python
"""Persistence and analytics for Wear Calculator wire wear records."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List, Optional


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


@dataclass(frozen=True)
class WireWearSaveResult:
    saved_count: int
    updated_count: int
    duplicate_count: int
    duplicates: List[Dict[str, Any]]


def normalize_line_group(line_group: str, line_class: str) -> tuple[str, str]:
    normalized_class = (line_class or line_group or "").strip().upper()
    if normalized_class == "LMC":
        return "EAL", "LMC"
    if normalized_class == "TML":
        return "TML", "TML"
    return "EAL", "EAL"


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    result = dict(row)
    raw_sources = result.get("source_file_names")
    result["source_file_names"] = json.loads(raw_sources) if raw_sources else []
    return result


def _parse_cycle_date(value: str) -> str:
    text = str(value or "").strip().replace("/", "-")
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return date.fromisoformat(text[:10]).isoformat()


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
        return WireWearSaveResult(0, 0, len(duplicates), duplicates)

    saved_count = 0
    updated_count = 0
    source_file_names = json.dumps(request.source_file_names)
    for record in request.records:
        before = conn.total_changes
        conn.execute(
            """
            INSERT INTO wire_wear_records (
                line_group, line_class, track, section, cycle_date,
                tension_length, from_m, to_m, avg_wear_min, sd,
                wear_percentage, source_file_names
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(line_group, line_class, track, section, cycle_date, tension_length)
            DO UPDATE SET
                from_m = excluded.from_m,
                to_m = excluded.to_m,
                avg_wear_min = excluded.avg_wear_min,
                sd = excluded.sd,
                wear_percentage = excluded.wear_percentage,
                source_file_names = excluded.source_file_names,
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
            ),
        )
        changed = conn.total_changes - before
        if overwrite and duplicates and changed:
            updated_count += 1
        elif changed:
            saved_count += 1

    return WireWearSaveResult(saved_count, updated_count, len(duplicates), duplicates)


def query_wire_wear_records(
    conn: sqlite3.Connection,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    filters = filters or {}
    where: List[str] = []
    params: List[Any] = []
    for field in ("line_group", "line_class", "track", "section", "tension_length"):
        value = filters.get(field)
        if value:
            where.append(f"{field} = ?")
            params.append(str(value))
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
```

- [ ] **Step 4: Run service tests**

```bash
python -m pytest backend/tests/test_wear_records.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/calculation/wear_records.py backend/tests/test_wear_records.py
git commit -m "feat: persist wire wear records"
```

### Task 3: Backend Rate, Dashboard, and Projection Calculations

**Files:**
- Modify: `backend/app/core/calculation/wear_records.py`
- Test: `backend/tests/test_wear_records.py`

- [ ] **Step 1: Write failing analytics tests**

Append:

```python
from app.core.calculation.wear_records import (
    build_dashboard_summary,
    build_projection_summary,
)


def _seed_rate_records(conn):
    request = WireWearSaveRequest(
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
    )
    save_wire_wear_records(conn, request, overwrite=False)
    request_2025 = WireWearSaveRequest(
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
    )
    save_wire_wear_records(conn, request_2025, overwrite=False)


def test_dashboard_summary_splits_lmc_under_eal(tmp_path):
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
    assert summary["TML"]["top_max_rate"] == []


def test_projection_summary_buckets_next_30_years(tmp_path):
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest backend/tests/test_wear_records.py -q
```

Expected: missing function import failure.

- [ ] **Step 3: Implement analytics functions**

Append to `backend/app/core/calculation/wear_records.py`:

```python
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


def _rate_rows(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
    for record in records:
        key = (record["line_group"], record["tension_length"])
        grouped.setdefault(key, []).append(record)

    rows: List[Dict[str, Any]] = []
    for (line_group, tension_length), values in grouped.items():
        values = sorted(values, key=lambda item: item["cycle_date"])
        base_date = values[0]["cycle_date"]
        percent_points = [
            (_years_between(base_date, item["cycle_date"]), float(item["wear_percentage"]))
            for item in values
        ]
        height_points = [
            (_years_between(base_date, item["cycle_date"]), float(item["avg_wear_min"]))
            for item in values
        ]
        percent_slope = _linear_slope(percent_points)
        remaining_height_slope = _linear_slope(height_points)
        latest = values[-1]
        rows.append({
            "line_group": line_group,
            "line_class": latest["line_class"],
            "track": latest["track"],
            "section": latest["section"],
            "tension_length": tension_length,
            "latest_cycle_date": latest["cycle_date"],
            "latest_wear_percentage": latest["wear_percentage"],
            "latest_avg_wear_min": latest["avg_wear_min"],
            "wear_percent_per_year": round(percent_slope, 4),
            "wear_mm_per_year": round(max(0.0, -remaining_height_slope), 4),
            "record_count": len(values),
        })
    return rows


def build_dashboard_summary(conn: sqlite3.Connection) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    rates = _rate_rows(query_wire_wear_records(conn))
    summary: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for line_group in ("EAL", "TML"):
        group_rows = [row for row in rates if row["line_group"] == line_group]
        summary[line_group] = {
            "top_max_rate": sorted(group_rows, key=lambda row: row["wear_percent_per_year"], reverse=True)[:5],
            "top_min_rate": sorted(group_rows, key=lambda row: row["wear_percent_per_year"])[:5],
            "top_current_wear": sorted(group_rows, key=lambda row: row["latest_wear_percentage"], reverse=True)[:5],
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
        buckets = [{"year": offset, "count": 0} for offset in range(0, years + 1)]
        projected_records: List[Dict[str, Any]] = []
        for row in group_rows:
            rate = float(row["wear_percent_per_year"])
            latest = float(row["latest_wear_percentage"])
            if latest >= threshold_percentage:
                years_to_threshold = 0.0
            elif rate <= 0:
                years_to_threshold = None
            else:
                years_to_threshold = (threshold_percentage - latest) / rate
            projected = {**row, "years_to_threshold": years_to_threshold}
            if years_to_threshold is not None and years_to_threshold <= years:
                bucket_index = max(0, min(years, int(round(years_to_threshold))))
                buckets[bucket_index]["count"] += 1
            projected_records.append(projected)
        output["line_groups"][line_group] = {
            "year_buckets": buckets,
            "records": projected_records,
        }
    return output
```

- [ ] **Step 4: Run analytics tests**

```bash
python -m pytest backend/tests/test_wear_records.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/calculation/wear_records.py backend/tests/test_wear_records.py
git commit -m "feat: calculate wire wear dashboard rates"
```

### Task 4: Backend API Endpoints

**Files:**
- Create: `backend/app/api/endpoints/wear_records.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_wear_records_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_wear_records_api.py`:

```python
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import DatabaseManager


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "api_wear_records.db"
    os.environ["TOV640_TEST_DB_PATH"] = str(db_path)
    DatabaseManager.reset_instance()
    manager = DatabaseManager(str(db_path))
    manager.close()
    yield TestClient(app)
    DatabaseManager.reset_instance()
    os.environ.pop("TOV640_TEST_DB_PATH", None)


def _payload():
    return {
        "line_group": "EAL",
        "line_class": "LMC",
        "track": "UP",
        "section": "LMC",
        "cycle_date": "2026-02-01",
        "source_file_names": ["cycle.xlsx"],
        "records": [
            {
                "tension_length": "H46",
                "from_m": 100.0,
                "to_m": 200.0,
                "avg_wear_min": 12.4,
                "sd": 0.2,
                "wear_percentage": 6.5,
            }
        ],
    }


def test_save_wire_wear_records_api(client):
    response = client.post("/api/calculation/wear-records", json=_payload())

    assert response.status_code == 200
    assert response.json()["saved_count"] == 1


def test_save_wire_wear_records_conflict_then_overwrite(client):
    assert client.post("/api/calculation/wear-records", json=_payload()).status_code == 200

    conflict = client.post("/api/calculation/wear-records", json=_payload())
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["duplicate_count"] == 1

    overwrite = client.post("/api/calculation/wear-records?overwrite=true", json=_payload())
    assert overwrite.status_code == 200
    assert overwrite.json()["updated_count"] == 1


def test_list_dashboard_projection_api(client):
    client.post("/api/calculation/wear-records", json=_payload())

    records = client.get("/api/calculation/wear-records?line_group=EAL")
    dashboard = client.get("/api/calculation/wear-records/dashboard")
    projection = client.get("/api/calculation/wear-records/projection")

    assert records.status_code == 200
    assert records.json()["records"][0]["line_class"] == "LMC"
    assert dashboard.status_code == 200
    assert "EAL" in dashboard.json()["line_groups"]
    assert projection.status_code == 200
    assert projection.json()["threshold_percentage"] == 20.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest backend/tests/test_wear_records_api.py -q
```

Expected: 404 for new routes.

- [ ] **Step 3: Implement endpoint router**

Create `backend/app/api/endpoints/wear_records.py`:

```python
"""Wear Calculator wire wear record endpoints."""
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.calculation.wear_records import (
    WireWearRecordInput,
    WireWearSaveRequest,
    build_dashboard_summary,
    build_projection_summary,
    query_wire_wear_records,
    save_wire_wear_records,
)
from app.core.database import get_database

router = APIRouter(prefix="/calculation/wear-records")


class WireWearRecordInputModel(BaseModel):
    tension_length: str
    from_m: float
    to_m: float
    avg_wear_min: float
    sd: float = 0
    wear_percentage: float


class WireWearSaveRequestModel(BaseModel):
    line_group: str = Field(pattern="^(EAL|TML)$")
    line_class: str = Field(pattern="^(EAL|LMC|TML)$")
    track: str
    section: str
    cycle_date: str
    source_file_names: List[str] = []
    records: List[WireWearRecordInputModel]


class WireWearSaveResponse(BaseModel):
    saved_count: int
    updated_count: int
    duplicate_count: int
    duplicates: List[dict]


class WireWearRecordsResponse(BaseModel):
    records: List[dict]


def _to_core_request(payload: WireWearSaveRequestModel) -> WireWearSaveRequest:
    return WireWearSaveRequest(
        line_group=payload.line_group,
        line_class=payload.line_class,
        track=payload.track,
        section=payload.section,
        cycle_date=payload.cycle_date,
        source_file_names=payload.source_file_names,
        records=[
            WireWearRecordInput(
                tension_length=record.tension_length,
                from_m=record.from_m,
                to_m=record.to_m,
                avg_wear_min=record.avg_wear_min,
                sd=record.sd,
                wear_percentage=record.wear_percentage,
            )
            for record in payload.records
        ],
    )


@router.post("", response_model=WireWearSaveResponse)
async def save_records(payload: WireWearSaveRequestModel, overwrite: bool = Query(default=False)):
    db = get_database()
    with db.get_connection() as conn:
        result = save_wire_wear_records(conn, _to_core_request(payload), overwrite=overwrite)
    if result.duplicate_count and not overwrite:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Wire wear records already exist for this line/class/track/section/date/TL.",
                "duplicate_count": result.duplicate_count,
                "duplicates": result.duplicates,
            },
        )
    return WireWearSaveResponse(**result.__dict__)


@router.get("", response_model=WireWearRecordsResponse)
async def list_records(
    line_group: Optional[str] = None,
    line_class: Optional[str] = None,
    track: Optional[str] = None,
    section: Optional[str] = None,
    tension_length: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    filters = {
        "line_group": line_group,
        "line_class": line_class,
        "track": track,
        "section": section,
        "tension_length": tension_length,
        "date_from": date_from,
        "date_to": date_to,
    }
    db = get_database()
    with db.get_connection() as conn:
        records = query_wire_wear_records(conn, filters)
    return WireWearRecordsResponse(records=records)


@router.get("/dashboard")
async def dashboard() -> Dict[str, dict]:
    db = get_database()
    with db.get_connection() as conn:
        return {"line_groups": build_dashboard_summary(conn)}


@router.get("/projection")
async def projection(
    threshold_percentage: float = Query(default=20.0),
    years: int = Query(default=30, ge=1, le=100),
):
    db = get_database()
    with db.get_connection() as conn:
        return build_projection_summary(conn, threshold_percentage=threshold_percentage, years=years)
```

Modify `backend/app/main.py`:

```python
from app.api.endpoints import analysis, metadata, sessions, database_records, calculation, wear_records

app.include_router(wear_records.router, prefix="/api", tags=["calculation"])
```

- [ ] **Step 4: Run API tests**

```bash
python -m pytest backend/tests/test_wear_records_api.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/endpoints/wear_records.py backend/app/main.py backend/tests/test_wear_records_api.py
git commit -m "feat: expose wire wear records api"
```

### Task 5: Frontend API Types and Records Store

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/store/useWearRecordsStore.ts`
- Test: `frontend/src/store/__tests__/useWearRecordsStore.test.ts`

- [ ] **Step 1: Write failing store tests**

Create `frontend/src/store/__tests__/useWearRecordsStore.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { MockedFunction } from 'vitest';

vi.mock('../../api/client', () => ({
  saveWireWearRecords: vi.fn(),
  fetchWireWearRecords: vi.fn(),
  fetchWireWearDashboard: vi.fn(),
  fetchWireWearProjection: vi.fn(),
}));

import {
  fetchWireWearDashboard,
  fetchWireWearProjection,
  fetchWireWearRecords,
  saveWireWearRecords,
} from '../../api/client';
import { useWearRecordsStore } from '../useWearRecordsStore';

const mockedSave = saveWireWearRecords as MockedFunction<typeof saveWireWearRecords>;
const mockedFetchRecords = fetchWireWearRecords as MockedFunction<typeof fetchWireWearRecords>;
const mockedFetchDashboard = fetchWireWearDashboard as MockedFunction<typeof fetchWireWearDashboard>;
const mockedFetchProjection = fetchWireWearProjection as MockedFunction<typeof fetchWireWearProjection>;

describe('useWearRecordsStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useWearRecordsStore.getState().reset();
  });

  it('stores duplicate conflict for overwrite confirmation', async () => {
    mockedSave.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { detail: { duplicate_count: 1, duplicates: [{ tension_length: 'H46' }] } },
      },
    });

    await useWearRecordsStore.getState().saveAnalysisResults({
      line_group: 'EAL',
      line_class: 'LMC',
      track: 'UP',
      section: 'LMC',
      cycle_date: '2026-02-01',
      source_file_names: ['cycle.xlsx'],
      records: [],
    });

    expect(useWearRecordsStore.getState().duplicateConflict?.duplicate_count).toBe(1);
  });

  it('loads records dashboard and projection', async () => {
    mockedFetchRecords.mockResolvedValueOnce({ records: [] });
    mockedFetchDashboard.mockResolvedValueOnce({ line_groups: { EAL: {}, TML: {} } as any });
    mockedFetchProjection.mockResolvedValueOnce({
      threshold_percentage: 20,
      years: 30,
      line_groups: { EAL: { year_buckets: [], records: [] }, TML: { year_buckets: [], records: [] } },
    });

    await useWearRecordsStore.getState().loadAll();

    expect(mockedFetchRecords).toHaveBeenCalled();
    expect(mockedFetchDashboard).toHaveBeenCalled();
    expect(mockedFetchProjection).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend
npm test -- src/store/__tests__/useWearRecordsStore.test.ts --run
```

Expected: missing module errors.

- [ ] **Step 3: Add API types**

Append to the calculation types section of `frontend/src/types/api.ts`:

```ts
export type WireWearLineGroup = 'EAL' | 'TML'
export type WireWearLineClass = 'EAL' | 'LMC' | 'TML'

export interface WireWearRecordInput {
  tension_length: string
  from_m: number
  to_m: number
  avg_wear_min: number
  sd: number
  wear_percentage: number
}

export interface WireWearSaveRequest {
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  track: string
  section: string
  cycle_date: string
  source_file_names: string[]
  records: WireWearRecordInput[]
}

export interface WireWearSavedRecord extends WireWearRecordInput {
  record_id: number
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  track: string
  section: string
  cycle_date: string
  source_file_names: string[]
  created_at: string
  updated_at: string
}

export interface WireWearSaveResponse {
  saved_count: number
  updated_count: number
  duplicate_count: number
  duplicates: WireWearSavedRecord[]
}

export interface WireWearRecordsResponse {
  records: WireWearSavedRecord[]
}

export interface WireWearRateRow {
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  track: string
  section: string
  tension_length: string
  latest_cycle_date: string
  latest_wear_percentage: number
  latest_avg_wear_min: number
  wear_percent_per_year: number
  wear_mm_per_year: number
  record_count: number
}

export interface WireWearDashboardResponse {
  line_groups: Record<WireWearLineGroup, {
    top_max_rate: WireWearRateRow[]
    top_min_rate: WireWearRateRow[]
    top_current_wear: WireWearRateRow[]
  }>
}

export interface WireWearProjectionResponse {
  threshold_percentage: number
  years: number
  line_groups: Record<WireWearLineGroup, {
    year_buckets: Array<{ year: number; count: number }>
    records: Array<WireWearRateRow & { years_to_threshold: number | null }>
  }>
}
```

- [ ] **Step 4: Add API client helpers**

Modify imports in `frontend/src/api/client.ts` to include the new types. Add:

```ts
export const saveWireWearRecords = async (
  payload: WireWearSaveRequest,
  overwrite = false,
): Promise<WireWearSaveResponse> => {
  const response = await apiClient.post<WireWearSaveResponse>(
    '/calculation/wear-records',
    payload,
    { params: { overwrite } },
  );
  return response.data;
};

export const fetchWireWearRecords = async (
  params: Record<string, string | undefined> = {},
): Promise<WireWearRecordsResponse> => {
  const response = await apiClient.get<WireWearRecordsResponse>('/calculation/wear-records', { params });
  return response.data;
};

export const fetchWireWearDashboard = async (): Promise<WireWearDashboardResponse> => {
  const response = await apiClient.get<WireWearDashboardResponse>('/calculation/wear-records/dashboard');
  return response.data;
};

export const fetchWireWearProjection = async (
  thresholdPercentage = 20,
  years = 30,
): Promise<WireWearProjectionResponse> => {
  const response = await apiClient.get<WireWearProjectionResponse>('/calculation/wear-records/projection', {
    params: { threshold_percentage: thresholdPercentage, years },
  });
  return response.data;
};
```

- [ ] **Step 5: Add records store**

Create `frontend/src/store/useWearRecordsStore.ts`:

```ts
import { create } from 'zustand';
import {
  fetchWireWearDashboard,
  fetchWireWearProjection,
  fetchWireWearRecords,
  saveWireWearRecords,
} from '../api/client';
import type {
  WireWearDashboardResponse,
  WireWearProjectionResponse,
  WireWearRecordsResponse,
  WireWearSaveRequest,
} from '../types/api';

interface DuplicateConflict {
  duplicate_count: number
  duplicates: unknown[]
}

interface WearRecordsState {
  records: WireWearRecordsResponse['records']
  dashboard: WireWearDashboardResponse | null
  projection: WireWearProjectionResponse | null
  isLoading: boolean
  isSaving: boolean
  error: string | null
  duplicateConflict: DuplicateConflict | null
  saveAnalysisResults: (payload: WireWearSaveRequest, overwrite?: boolean) => Promise<void>
  loadRecords: (params?: Record<string, string | undefined>) => Promise<void>
  loadDashboard: () => Promise<void>
  loadProjection: () => Promise<void>
  loadAll: () => Promise<void>
  reset: () => void
}

const initialState = {
  records: [],
  dashboard: null,
  projection: null,
  isLoading: false,
  isSaving: false,
  error: null,
  duplicateConflict: null,
};

export const useWearRecordsStore = create<WearRecordsState>((set, get) => ({
  ...initialState,

  saveAnalysisResults: async (payload, overwrite = false) => {
    set({ isSaving: true, error: null, duplicateConflict: null });
    try {
      await saveWireWearRecords(payload, overwrite);
      set({ isSaving: false });
      await get().loadAll();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 409 && detail) {
        set({
          duplicateConflict: {
            duplicate_count: detail.duplicate_count,
            duplicates: detail.duplicates,
          },
          isSaving: false,
        });
        return;
      }
      set({ error: detail?.message || detail || err.message || 'Failed to save wire wear records', isSaving: false });
    }
  },

  loadRecords: async (params = {}) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetchWireWearRecords(params);
      set({ records: response.records, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to load wire wear records', isLoading: false });
    }
  },

  loadDashboard: async () => {
    const dashboard = await fetchWireWearDashboard();
    set({ dashboard });
  },

  loadProjection: async () => {
    const projection = await fetchWireWearProjection();
    set({ projection });
  },

  loadAll: async () => {
    set({ isLoading: true, error: null });
    try {
      const [records, dashboard, projection] = await Promise.all([
        fetchWireWearRecords(),
        fetchWireWearDashboard(),
        fetchWireWearProjection(),
      ]);
      set({ records: records.records, dashboard, projection, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to load wire wear data', isLoading: false });
    }
  },

  reset: () => set(initialState),
}));
```

- [ ] **Step 6: Run frontend store tests**

```bash
cd frontend
npm test -- src/store/__tests__/useWearRecordsStore.test.ts --run
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/api/client.ts frontend/src/store/useWearRecordsStore.ts frontend/src/store/__tests__/useWearRecordsStore.test.ts
git commit -m "feat: add wire wear records frontend api"
```

### Task 6: Analysis Save Flow and Line Class

**Files:**
- Modify: `frontend/src/store/useWearStore.ts`
- Modify: `frontend/src/views/WearCalculatorView.tsx`
- Modify: `frontend/src/components/Calculation/WearResultTable.tsx`
- Test: `frontend/src/store/__tests__/useWearStore.test.ts`
- Test: `frontend/src/views/__tests__/WearCalculatorView.test.tsx`

- [ ] **Step 1: Write failing tests for line class reset and save action**

Update `frontend/src/store/__tests__/useWearStore.test.ts`:

```ts
it('maps LMC line class to EAL line with LMC section during analysis', async () => {
  mockedUploadWearFiles.mockResolvedValueOnce({ date: '2026-01-16', wear_results: [] });

  useWearStore.getState().setLine('EAL');
  useWearStore.getState().setLineClass('LMC');
  useWearStore.getState().addFile(new File(['exception'], 'exception-report.xlsx'));
  await useWearStore.getState().analyze();

  expect(mockedUploadWearFiles).toHaveBeenCalledWith(
    expect.any(Array),
    'EAL',
    undefined,
    'LMC',
  );
});
```

Update `frontend/src/views/__tests__/WearCalculatorView.test.tsx` to assert module tabs:

```ts
it('shows Wear Calculator feature tabs inside the module', () => {
  render(<WearCalculatorView />);

  expect(screen.getByRole('tab', { name: /Analysis/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Wire Wear Records/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Dashboard/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Projection/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend
npm test -- src/store/__tests__/useWearStore.test.ts src/views/__tests__/WearCalculatorView.test.tsx --run
```

Expected: missing `setLineClass` and missing feature tabs.

- [ ] **Step 3: Extend wear store**

Modify `frontend/src/store/useWearStore.ts`:

```ts
export interface WearTab {
  id: string;
  label: string;
  line: 'EAL' | 'TML';
  lineClass: 'EAL' | 'LMC' | 'TML';
  uploadedFiles: File[];
  isLoading: boolean;
  error: string | null;
  date: string;
  wearResults: WearResult[];
  hasAnalyzed: boolean;
}
```

Set default:

```ts
lineClass: 'EAL',
```

Add state action:

```ts
setLineClass: (lineClass: 'EAL' | 'LMC' | 'TML') => void;
```

Add implementation:

```ts
  setLineClass: (lineClass) => {
    const { tabs, activeTabId } = get();
    const line = lineClass === 'TML' ? 'TML' : 'EAL';
    set({ tabs: updateActive(tabs, activeTabId, {
      line,
      lineClass,
      date: '',
      wearResults: [],
      hasAnalyzed: false,
      error: null,
    }) });
  },
```

Update `setLine` to reset class:

```ts
      line,
      lineClass: line === 'TML' ? 'TML' : 'EAL',
```

Update `analyze`:

```ts
      const section = tab.lineClass === 'LMC' ? 'LMC' : 'Mainline';
      const res = await uploadWearFiles(tab.uploadedFiles, tab.line, undefined, section);
```

- [ ] **Step 4: Add feature tabs and class selector**

In `frontend/src/views/WearCalculatorView.tsx`, add local state:

```ts
const [featureTab, setFeatureTab] = useState<'analysis' | 'records' | 'dashboard' | 'projection'>('analysis');
```

Render feature tabs above the existing analysis run tab bar:

```tsx
<Tabs
  value={featureTab}
  onChange={(_, value) => setFeatureTab(value)}
  sx={{ borderBottom: 1, borderColor: 'divider', mb: 1 }}
>
  <Tab value="analysis" label="Analysis" />
  <Tab value="records" label="Wire Wear Records" />
  <Tab value="dashboard" label="Dashboard" />
  <Tab value="projection" label="Projection" />
</Tabs>
```

Only render the existing calculation-run tab bar and upload panel when `featureTab === 'analysis'`.

Add class selector beside the line selector in Analysis:

```tsx
<FormControl size="small" sx={{ minWidth: 140 }}>
  <InputLabel id="wear-class-label">Class</InputLabel>
  <Select
    labelId="wear-class-label"
    value={activeTab.lineClass}
    label="Class"
    onChange={(e) => setLineClass(e.target.value as 'EAL' | 'LMC' | 'TML')}
  >
    {activeTab.line === 'EAL' && <MenuItem value="EAL">EAL</MenuItem>}
    {activeTab.line === 'EAL' && <MenuItem value="LMC">LMC</MenuItem>}
    {activeTab.line === 'TML' && <MenuItem value="TML">TML</MenuItem>}
  </Select>
</FormControl>
```

- [ ] **Step 5: Add optional save action to result table**

Modify `WearResultTableProps`:

```ts
  onSaveRecords?: () => void;
  isSavingRecords?: boolean;
```

Add a button next to Export Excel:

```tsx
{onSaveRecords && (
  <Button
    size="small"
    variant="contained"
    onClick={onSaveRecords}
    disabled={isSavingRecords}
  >
    {isSavingRecords ? 'Saving...' : 'Save to Wire Wear Records'}
  </Button>
)}
```

- [ ] **Step 6: Wire save payload in `WearCalculatorView`**

Import `useWearRecordsStore` and build payload from active analysis results:

```ts
const { saveAnalysisResults, isSaving } = useWearRecordsStore();

const handleSaveWearRecords = () => {
  if (!activeTab.wearResults.length) return;
  const lineGroup = activeTab.lineClass === 'TML' ? 'TML' : 'EAL';
  const section = activeTab.lineClass === 'LMC' ? 'LMC' : 'Mainline';
  saveAnalysisResults({
    line_group: lineGroup,
    line_class: activeTab.lineClass,
    track: activeTab.wearResults[0]?.track || '',
    section,
    cycle_date: activeTab.date,
    source_file_names: activeTab.uploadedFiles.map(file => file.name),
    records: activeTab.wearResults.map(result => ({
      tension_length: result.tension_length,
      from_m: result.from_m,
      to_m: result.to_m,
      avg_wear_min: result.avg_wear_min,
      sd: result.sd,
      wear_percentage: result.wear_percentage,
    })),
  });
};
```

Pass it to `WearResultTable`:

```tsx
<WearResultTable
  results={activeTab.wearResults}
  date={activeTab.date}
  line={activeTab.wearResults[0]?.line ?? ''}
  track={activeTab.wearResults[0]?.track ?? ''}
  onSaveRecords={handleSaveWearRecords}
  isSavingRecords={isSaving}
/>
```

- [ ] **Step 7: Run frontend tests**

```bash
cd frontend
npm test -- src/store/__tests__/useWearStore.test.ts src/views/__tests__/WearCalculatorView.test.tsx --run
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/store/useWearStore.ts frontend/src/views/WearCalculatorView.tsx frontend/src/components/Calculation/WearResultTable.tsx frontend/src/store/__tests__/useWearStore.test.ts frontend/src/views/__tests__/WearCalculatorView.test.tsx
git commit -m "feat: save analysis wear records"
```

### Task 7: Wire Wear Records Panel

**Files:**
- Create: `frontend/src/components/Calculation/WearRecordsPanel.tsx`
- Create: `frontend/src/components/Calculation/wearRecordCharts.tsx`
- Modify: `frontend/src/views/WearCalculatorView.tsx`
- Test: `frontend/src/components/Calculation/__tests__/WearRecordsPanel.test.tsx`

- [ ] **Step 1: Write failing panel test**

Create `frontend/src/components/Calculation/__tests__/WearRecordsPanel.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import WearRecordsPanel from '../WearRecordsPanel';
import { useWearRecordsStore } from '../../../store/useWearRecordsStore';

describe('WearRecordsPanel', () => {
  beforeEach(() => {
    useWearRecordsStore.setState({
      records: [
        {
          record_id: 1,
          line_group: 'EAL',
          line_class: 'LMC',
          track: 'UP',
          section: 'LMC',
          cycle_date: '2026-02-01',
          tension_length: 'H46',
          from_m: 100,
          to_m: 200,
          avg_wear_min: 12.4,
          sd: 0.2,
          wear_percentage: 6.5,
          source_file_names: ['cycle.xlsx'],
          created_at: '',
          updated_at: '',
        },
      ],
      isLoading: false,
      error: null,
    } as any);
  });

  it('renders record table and chart mode controls', () => {
    render(<WearRecordsPanel />);

    expect(screen.getByRole('button', { name: /By Cycle/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /By Tension Length/i })).toBeInTheDocument();
    expect(screen.getByText('H46')).toBeInTheDocument();
    expect(screen.getByText('LMC')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend
npm test -- src/components/Calculation/__tests__/WearRecordsPanel.test.tsx --run
```

Expected: missing component.

- [ ] **Step 3: Create shared chart components**

Create `frontend/src/components/Calculation/wearRecordCharts.tsx`:

```tsx
import { Box } from '@mui/material';
import Plot from 'react-plotly.js';
import type { WireWearSavedRecord } from '../../types/api';

export function CycleWearBarChart({ records }: { records: WireWearSavedRecord[] }) {
  const sorted = [...records].sort((a, b) => a.from_m - b.from_m);
  return (
    <Box sx={{ width: '100%', height: 300 }}>
      <Plot
        data={[{
          x: sorted.map(record => record.tension_length),
          y: sorted.map(record => record.wear_percentage),
          type: 'bar',
          marker: { color: sorted.map(record => record.wear_percentage >= 10 ? '#d32f2f' : '#1976d2') },
        }]}
        layout={{
          autosize: true,
          margin: { t: 20, r: 20, b: 80, l: 50 },
          xaxis: { title: { text: 'Tension Length' }, type: 'category', tickangle: -45 },
          yaxis: { title: { text: 'Wear %' }, rangemode: 'tozero' },
        }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
        config={{ responsive: true, displaylogo: false }}
      />
    </Box>
  );
}

export function TensionLengthTrendChart({ records }: { records: WireWearSavedRecord[] }) {
  const sorted = [...records].sort((a, b) => a.cycle_date.localeCompare(b.cycle_date));
  return (
    <Box sx={{ width: '100%', height: 300 }}>
      <Plot
        data={[{
          x: sorted.map(record => record.cycle_date),
          y: sorted.map(record => record.wear_percentage),
          type: 'scatter',
          mode: 'lines+markers',
          line: { color: '#1976d2' },
        }]}
        layout={{
          autosize: true,
          margin: { t: 20, r: 20, b: 60, l: 50 },
          xaxis: { title: { text: 'Cycle Date' } },
          yaxis: { title: { text: 'Wear %' }, rangemode: 'tozero' },
        }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
        config={{ responsive: true, displaylogo: false }}
      />
    </Box>
  );
}
```

- [ ] **Step 4: Create records panel**

Create `frontend/src/components/Calculation/WearRecordsPanel.tsx`:

```tsx
import React, { useMemo, useState } from 'react';
import { Box, Button, ButtonGroup, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';

import { useWearRecordsStore } from '../../store/useWearRecordsStore';
import { CycleWearBarChart, TensionLengthTrendChart } from './wearRecordCharts';

const columns: GridColDef[] = [
  { field: 'cycle_date', headerName: 'Cycle Date', width: 120 },
  { field: 'line_group', headerName: 'Line', width: 90 },
  { field: 'line_class', headerName: 'Class', width: 90 },
  { field: 'track', headerName: 'Track', width: 90 },
  { field: 'tension_length', headerName: 'Tension Length', minWidth: 150, flex: 1 },
  { field: 'from_m', headerName: 'From (m)', width: 110 },
  { field: 'to_m', headerName: 'To (m)', width: 110 },
  { field: 'avg_wear_min', headerName: 'Avg Wear Min', width: 130 },
  { field: 'wear_percentage', headerName: 'Wear %', width: 100 },
];

const WearRecordsPanel: React.FC = () => {
  const { records, isLoading, loadRecords } = useWearRecordsStore();
  const [mode, setMode] = useState<'cycle' | 'tl'>('cycle');
  const [lineGroup, setLineGroup] = useState('EAL');
  const [selectedCycle, setSelectedCycle] = useState('');
  const [selectedTl, setSelectedTl] = useState('');

  React.useEffect(() => {
    loadRecords({ line_group: lineGroup });
  }, [lineGroup, loadRecords]);

  const cycleOptions = useMemo(() => Array.from(new Set(records.map(record => record.cycle_date))).sort(), [records]);
  const tlOptions = useMemo(() => Array.from(new Set(records.map(record => record.tension_length))).sort(), [records]);
  const activeCycle = selectedCycle || cycleOptions[0] || '';
  const activeTl = selectedTl || tlOptions[0] || '';
  const chartRecords = mode === 'cycle'
    ? records.filter(record => record.cycle_date === activeCycle)
    : records.filter(record => record.tension_length === activeTl);

  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 2 }}>
        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
          <TextField select size="small" label="Line" value={lineGroup} onChange={(event) => setLineGroup(event.target.value)}>
            <MenuItem value="EAL">EAL</MenuItem>
            <MenuItem value="TML">TML</MenuItem>
          </TextField>
          <ButtonGroup size="small">
            <Button variant={mode === 'cycle' ? 'contained' : 'outlined'} onClick={() => setMode('cycle')}>By Cycle</Button>
            <Button variant={mode === 'tl' ? 'contained' : 'outlined'} onClick={() => setMode('tl')}>By Tension Length</Button>
          </ButtonGroup>
          {mode === 'cycle' ? (
            <TextField select size="small" label="Cycle" value={activeCycle} onChange={(event) => setSelectedCycle(event.target.value)} sx={{ minWidth: 160 }}>
              {cycleOptions.map(option => <MenuItem key={option} value={option}>{option}</MenuItem>)}
            </TextField>
          ) : (
            <TextField select size="small" label="Tension Length" value={activeTl} onChange={(event) => setSelectedTl(event.target.value)} sx={{ minWidth: 180 }}>
              {tlOptions.map(option => <MenuItem key={option} value={option}>{option}</MenuItem>)}
            </TextField>
          )}
        </Stack>
        <Box sx={{ mt: 2 }}>
          {mode === 'cycle' ? <CycleWearBarChart records={chartRecords} /> : <TensionLengthTrendChart records={chartRecords} />}
        </Box>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>Wire Wear Records</Typography>
        <DataGrid
          rows={records.map(record => ({ ...record, id: record.record_id }))}
          columns={columns}
          loading={isLoading}
          autoHeight
          disableRowSelectionOnClick
          pageSizeOptions={[25, 50, 100]}
          initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
        />
      </Paper>
    </Stack>
  );
};

export default WearRecordsPanel;
```

- [ ] **Step 5: Render panel from WearCalculatorView**

Import and render:

```tsx
import WearRecordsPanel from '../components/Calculation/WearRecordsPanel';

{featureTab === 'records' && <WearRecordsPanel />}
```

- [ ] **Step 6: Run component test**

```bash
cd frontend
npm test -- src/components/Calculation/__tests__/WearRecordsPanel.test.tsx --run
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Calculation/WearRecordsPanel.tsx frontend/src/components/Calculation/wearRecordCharts.tsx frontend/src/views/WearCalculatorView.tsx frontend/src/components/Calculation/__tests__/WearRecordsPanel.test.tsx
git commit -m "feat: show wire wear records in calculator"
```

### Task 8: Dashboard and Projection Panels

**Files:**
- Create: `frontend/src/components/Calculation/WearDashboardPanel.tsx`
- Create: `frontend/src/components/Calculation/WearProjectionPanel.tsx`
- Modify: `frontend/src/components/Calculation/wearRecordCharts.tsx`
- Modify: `frontend/src/views/WearCalculatorView.tsx`
- Test: `frontend/src/components/Calculation/__tests__/WearDashboardPanel.test.tsx`
- Test: `frontend/src/components/Calculation/__tests__/WearProjectionPanel.test.tsx`

- [ ] **Step 1: Write failing tests**

Create dashboard test:

```tsx
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import WearDashboardPanel from '../WearDashboardPanel';
import { useWearRecordsStore } from '../../../store/useWearRecordsStore';

describe('WearDashboardPanel', () => {
  it('renders EAL and TML dashboard groups', () => {
    useWearRecordsStore.setState({
      dashboard: {
        line_groups: {
          EAL: { top_max_rate: [], top_min_rate: [], top_current_wear: [] },
          TML: { top_max_rate: [], top_min_rate: [], top_current_wear: [] },
        },
      },
    } as any);

    render(<WearDashboardPanel />);

    expect(screen.getByText(/EAL/i)).toBeInTheDocument();
    expect(screen.getByText(/TML/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Top 5 Max/i).length).toBeGreaterThan(0);
  });
});
```

Create projection test:

```tsx
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import WearProjectionPanel from '../WearProjectionPanel';
import { useWearRecordsStore } from '../../../store/useWearRecordsStore';

describe('WearProjectionPanel', () => {
  it('renders 20 percent projection content', () => {
    useWearRecordsStore.setState({
      projection: {
        threshold_percentage: 20,
        years: 30,
        line_groups: {
          EAL: { year_buckets: [{ year: 1, count: 2 }], records: [] },
          TML: { year_buckets: [], records: [] },
        },
      },
    } as any);

    render(<WearProjectionPanel />);

    expect(screen.getByText(/20%/i)).toBeInTheDocument();
    expect(screen.getByText(/Next 30 Years/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend
npm test -- src/components/Calculation/__tests__/WearDashboardPanel.test.tsx src/components/Calculation/__tests__/WearProjectionPanel.test.tsx --run
```

Expected: missing components.

- [ ] **Step 3: Add dashboard panel**

Create `frontend/src/components/Calculation/WearDashboardPanel.tsx`:

```tsx
import React from 'react';
import { Box, Paper, Stack, Typography } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';

import { useWearRecordsStore } from '../../store/useWearRecordsStore';
import type { WireWearLineGroup, WireWearRateRow } from '../../types/api';

const columns: GridColDef[] = [
  { field: 'tension_length', headerName: 'TL', minWidth: 110, flex: 1 },
  { field: 'line_class', headerName: 'Class', width: 90 },
  { field: 'latest_cycle_date', headerName: 'Latest Cycle', width: 130 },
  { field: 'latest_wear_percentage', headerName: 'Latest Wear %', width: 130 },
  { field: 'wear_percent_per_year', headerName: '%/year', width: 110 },
  { field: 'wear_mm_per_year', headerName: 'mm/year', width: 110 },
];

function RankingTable({ title, rows }: { title: string; rows: WireWearRateRow[] }) {
  return (
    <Paper variant="outlined" sx={{ p: 1.5 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>{title}</Typography>
      <DataGrid
        rows={rows.map((row, index) => ({ ...row, id: `${row.tension_length}-${index}` }))}
        columns={columns}
        autoHeight
        hideFooter
        disableRowSelectionOnClick
      />
    </Paper>
  );
}

function LineGroupDashboard({ lineGroup }: { lineGroup: WireWearLineGroup }) {
  const dashboard = useWearRecordsStore(state => state.dashboard);
  const group = dashboard?.line_groups[lineGroup];
  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>{lineGroup}</Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr 1fr' }, gap: 2 }}>
        <RankingTable title="Top 5 Max wire wear rate" rows={group?.top_max_rate ?? []} />
        <RankingTable title="Top 5 Min wire wear rate" rows={group?.top_min_rate ?? []} />
        <RankingTable title="Top 5 current wire wear" rows={group?.top_current_wear ?? []} />
      </Box>
    </Paper>
  );
}

const WearDashboardPanel: React.FC = () => {
  const { loadDashboard } = useWearRecordsStore();
  React.useEffect(() => { loadDashboard(); }, [loadDashboard]);

  return (
    <Stack spacing={2}>
      <LineGroupDashboard lineGroup="EAL" />
      <LineGroupDashboard lineGroup="TML" />
    </Stack>
  );
};

export default WearDashboardPanel;
```

- [ ] **Step 4: Add projection chart and panel**

Append to `wearRecordCharts.tsx`:

```tsx
export function ProjectionBucketChart({
  buckets,
  title,
}: {
  buckets: Array<{ year: number; count: number }>
  title: string
}) {
  return (
    <Box sx={{ width: '100%', height: 300 }}>
      <Plot
        data={[{
          x: buckets.map(bucket => bucket.year),
          y: buckets.map(bucket => bucket.count),
          type: 'bar',
          marker: { color: '#1976d2' },
        }]}
        layout={{
          title: { text: title },
          autosize: true,
          margin: { t: 50, r: 20, b: 50, l: 50 },
          xaxis: { title: { text: 'Years from latest cycle' } },
          yaxis: { title: { text: 'TL count reaching threshold' }, rangemode: 'tozero' },
        }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
        config={{ responsive: true, displaylogo: false }}
      />
    </Box>
  );
}
```

Create `frontend/src/components/Calculation/WearProjectionPanel.tsx`:

```tsx
import React from 'react';
import { Paper, Stack, Typography } from '@mui/material';

import { useWearRecordsStore } from '../../store/useWearRecordsStore';
import { ProjectionBucketChart } from './wearRecordCharts';

const WearProjectionPanel: React.FC = () => {
  const { projection, loadProjection } = useWearRecordsStore();
  React.useEffect(() => { loadProjection(); }, [loadProjection]);

  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 700 }}>
          20% Wear Projection: Next 30 Years
        </Typography>
      </Paper>
      <Paper sx={{ p: 2 }}>
        <ProjectionBucketChart
          title="EAL projected TL count"
          buckets={projection?.line_groups.EAL.year_buckets ?? []}
        />
      </Paper>
      <Paper sx={{ p: 2 }}>
        <ProjectionBucketChart
          title="TML projected TL count"
          buckets={projection?.line_groups.TML.year_buckets ?? []}
        />
      </Paper>
    </Stack>
  );
};

export default WearProjectionPanel;
```

- [ ] **Step 5: Render panels from WearCalculatorView**

Import:

```tsx
import WearDashboardPanel from '../components/Calculation/WearDashboardPanel';
import WearProjectionPanel from '../components/Calculation/WearProjectionPanel';
```

Render:

```tsx
{featureTab === 'dashboard' && <WearDashboardPanel />}
{featureTab === 'projection' && <WearProjectionPanel />}
```

- [ ] **Step 6: Run panel tests**

```bash
cd frontend
npm test -- src/components/Calculation/__tests__/WearDashboardPanel.test.tsx src/components/Calculation/__tests__/WearProjectionPanel.test.tsx --run
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Calculation/WearDashboardPanel.tsx frontend/src/components/Calculation/WearProjectionPanel.tsx frontend/src/components/Calculation/wearRecordCharts.tsx frontend/src/views/WearCalculatorView.tsx frontend/src/components/Calculation/__tests__/WearDashboardPanel.test.tsx frontend/src/components/Calculation/__tests__/WearProjectionPanel.test.tsx
git commit -m "feat: add wire wear dashboard projection"
```

### Task 9: Duplicate Confirmation UX

**Files:**
- Modify: `frontend/src/views/WearCalculatorView.tsx`
- Modify: `frontend/src/store/useWearRecordsStore.ts`
- Test: `frontend/src/views/__tests__/WearCalculatorView.test.tsx`

- [ ] **Step 1: Write failing duplicate dialog test**

Add:

```tsx
it('shows overwrite confirmation when save returns duplicates', () => {
  useWearRecordsStore.setState({
    duplicateConflict: {
      duplicate_count: 1,
      duplicates: [{ tension_length: 'H46', cycle_date: '2026-02-01' }],
    },
  } as any);

  render(<WearCalculatorView />);

  expect(screen.getByText(/already exist/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Overwrite/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend
npm test -- src/views/__tests__/WearCalculatorView.test.tsx --run
```

Expected: no dialog.

- [ ] **Step 3: Add duplicate conflict controls**

Add to `useWearRecordsStore`:

```ts
clearDuplicateConflict: () => void
```

Implementation:

```ts
clearDuplicateConflict: () => set({ duplicateConflict: null }),
```

In `WearCalculatorView`, render MUI `Dialog` when `duplicateConflict` exists. The Overwrite button calls `handleSaveWearRecords(true)`.

```tsx
<Dialog open={Boolean(duplicateConflict)} onClose={clearDuplicateConflict}>
  <DialogTitle>Wire wear records already exist</DialogTitle>
  <DialogContent>
    <Typography variant="body2">
      {duplicateConflict?.duplicate_count ?? 0} record(s) already exist for this cycle. Overwrite them to update the saved database.
    </Typography>
  </DialogContent>
  <DialogActions>
    <Button onClick={clearDuplicateConflict}>Cancel</Button>
    <Button variant="contained" color="warning" onClick={() => handleSaveWearRecords(true)}>Overwrite</Button>
  </DialogActions>
</Dialog>
```

- [ ] **Step 4: Run test**

```bash
cd frontend
npm test -- src/views/__tests__/WearCalculatorView.test.tsx --run
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/WearCalculatorView.tsx frontend/src/store/useWearRecordsStore.ts frontend/src/views/__tests__/WearCalculatorView.test.tsx
git commit -m "feat: confirm wire wear record overwrite"
```

### Task 10: End-to-End Verification and Polish

**Files:**
- Modify only files needed by failing tests or visual issues.

- [ ] **Step 1: Run backend focused tests**

```bash
python -m pytest backend/tests/test_wear_records.py backend/tests/test_wear_records_api.py backend/tests/test_wear_calculator.py backend/tests/test_calculation_api.py -q
```

Expected: pass.

- [ ] **Step 2: Run frontend focused tests**

```bash
cd frontend
npm test -- src/store/__tests__/useWearStore.test.ts src/store/__tests__/useWearRecordsStore.test.ts src/views/__tests__/WearCalculatorView.test.tsx src/components/Calculation/__tests__/WearRecordsPanel.test.tsx src/components/Calculation/__tests__/WearDashboardPanel.test.tsx src/components/Calculation/__tests__/WearProjectionPanel.test.tsx --run
```

Expected: pass.

- [ ] **Step 3: Run frontend build**

```bash
cd frontend
npm run build
```

Expected: TypeScript and Vite build pass.

- [ ] **Step 4: Manual smoke test**

Start backend and frontend using the project's normal development commands. In the UI:

1. Open Wear Calculator.
2. Confirm feature tabs show `Analysis`, `Wire Wear Records`, `Dashboard`, `Projection`.
3. Upload an Exception Report and run Analysis.
4. Confirm the current-cycle tension length wear percentage chart is visible.
5. Save to Wire Wear Records.
6. Switch to Wire Wear Records and confirm the record is visible.
7. Switch chart mode between By Cycle and By Tension Length.
8. Switch to Dashboard and confirm EAL/TML split cards render.
9. Switch to Projection and confirm the 20 percent next 30 years chart renders.
10. Repeat save of the same cycle and confirm overwrite dialog appears.

- [ ] **Step 5: Commit fixes**

If verification creates fixes, stage the concrete modified paths shown by `git status --short`. For example, if only the dashboard panel and projection test changed:

```bash
git add frontend/src/components/Calculation/WearDashboardPanel.tsx frontend/src/components/Calculation/__tests__/WearProjectionPanel.test.tsx
git commit -m "fix: polish wire wear records workflow"
```

If no verification fixes were needed, skip this commit step.

## Self-Review

Spec coverage:

- Wear record database is visible inside Wear Calculator through `Wire Wear Records`.
- Analysis keeps current-cycle every tension length wear percentage graph by reusing `WearOverviewChart`.
- Database chart modes are covered by `WearRecordsPanel`.
- Dashboard top-five rankings are covered by backend summary plus `WearDashboardPanel`.
- Dashboard is split by EAL/TML, with LMC stored under EAL group as `line_class`.
- Projection to 20 percent wear over the next 30 years is covered by backend projection and frontend projection chart.

Placeholder scan:

- No unresolved placeholder text is intentionally left in the implementation steps.
- Ambiguous "Top 5 wire wear rate" is resolved as "Top 5 current wire wear" with rate columns shown beside the current wear value.

Type consistency:

- Backend save model uses snake_case to match existing API style.
- Frontend TypeScript interfaces mirror backend JSON exactly.
- `line_group` and `line_class` names are consistent across schema, backend service, API, store, and UI.
