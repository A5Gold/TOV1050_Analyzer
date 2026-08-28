# Wire Wear Records Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Wear Calculator Wire Wear Records workbench with aggregated Table 1, aggregated Table 2, Tension Length drill-down, raw-record CRUD, Excel export, and a next-phase plan for offline sync / packaging / hosted server work.

**Architecture:** Keep raw wire wear rows in the existing SQLite `wire_wear_records` table and add a calculated workbench response over those rows. Backend aggregation owns the engineering math; frontend components render the returned matrices and operate Add/Edit/Delete on raw record IDs shown in the detail panel.

**Tech Stack:** FastAPI, SQLite, pandas/openpyxl, pytest, React 18, Zustand, MUI, MUI DataGrid, Plotly, Vitest, Testing Library, TypeScript.

---

## Scope Check

This plan implements Phase 1 from `docs/superpowers/specs/2026-07-07-wire-wear-records-workbench-design.md`. Phase 2 packaging/offline-sync/hosted-server work is represented by a separate next-phase plan document created in Task 8; no Phase 2 sync engine or server mode is implemented in this plan.

Before editing production symbols, run impact analysis with codebase-memory MCP. Use `mcp__codebase_memory_mcp.trace_path` with `risk_labels=true` on the target symbol before modifying functions/classes.

## File Structure

- Modify `backend/app/core/calculation/wear_records.py`
  - Add aggregated TL workbench calculations.
  - Add raw record update/delete helpers.
  - Add Excel workbook builder.
- Modify `backend/app/api/endpoints/wear_records.py`
  - Add workbench, export, manual add, update, and delete endpoints.
- Modify `backend/tests/test_wear_records.py`
  - Add core aggregation, projection-label, CRUD, and workbook tests.
- Modify `backend/tests/test_wear_records_api.py`
  - Add API coverage for workbench, CRUD, and export endpoints.
- Modify `frontend/src/types/api.ts`
  - Add workbench, update, and export types.
- Modify `frontend/src/api/client.ts`
  - Add API client methods for workbench, CRUD, and Excel export.
- Modify `frontend/src/store/useWearRecordsStore.ts`
  - Add workbench state and actions.
- Create `frontend/src/components/Calculation/WearHistoryPivotTable.tsx`
  - Render Table 1.
- Create `frontend/src/components/Calculation/WearLatestSummaryTable.tsx`
  - Render Table 2.
- Create `frontend/src/components/Calculation/WearTensionLengthDetailPanel.tsx`
  - Render raw rows for selected TL and row actions.
- Create `frontend/src/components/Calculation/WireWearRecordDialog.tsx`
  - Add/Edit raw records.
- Modify `frontend/src/components/Calculation/WearRecordsPanel.tsx`
  - Replace current raw table panel with workbench shell.
- Modify `frontend/src/views/WearCalculatorView.tsx`
  - Change Analysis selector from `Line Class` to `Line` and remove `LMC` as a user option.
- Modify `frontend/src/views/__tests__/WearCalculatorView.test.tsx`
  - Verify Analysis line selector only has `EAL` and `TML`.
- Add/modify frontend component tests under `frontend/src/components/Calculation/__tests__/`.
- Create `docs/superpowers/plans/2026-07-07-wire-wear-offline-sync-packaging-server-next-phase.md`
  - Next-phase plan for Issue 2.

---

### Task 1: Backend Workbench Aggregation

**Files:**
- Modify: `backend/tests/test_wear_records.py`
- Modify: `backend/app/core/calculation/wear_records.py`

- [ ] **Step 1: Run impact analysis before editing `wear_records.py`**

Run with MCP before code edits:

```json
{
  "project": "C-Smart-Maintanence-TOV640_Analyzer",
  "function_name": "build_projection_summary",
  "direction": "both",
  "mode": "calls",
  "depth": 2,
  "risk_labels": true
}
```

Report direct callers and risk. If impact is HIGH or CRITICAL, stop and tell the user before editing.

- [ ] **Step 2: Write failing aggregation tests**

Append these tests to `backend/tests/test_wear_records.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_wear_records.py::test_workbench_history_averages_raw_rows_by_line_date_and_tension_length tests/test_wear_records.py::test_workbench_latest_summary_uses_aggregated_time_series -q
```

Expected: FAIL with `ImportError` or `AttributeError` for `build_workbench_summary`.

- [ ] **Step 4: Implement aggregated workbench helpers**

In `backend/app/core/calculation/wear_records.py`, add these helpers after `query_wire_wear_records` and before `build_dashboard_summary`:

```python
def _average(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _format_float(value: float, decimals: int = 3) -> float:
    return round(float(value), decimals)


def _projection_year_label(latest_year: int, latest_wear: float, rate: float, threshold: float, point_count: int) -> str:
    if point_count < 2 or rate <= 0:
        return "Insufficient Data"
    if latest_wear >= threshold:
        return str(latest_year)
    projected_year = latest_year + math.ceil((threshold - latest_wear) / rate)
    if projected_year > 2100:
        return "Beyond 2100"
    return str(projected_year)


def _aggregated_tension_length_series(records: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
    detail_records: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        tension_length = str(record["tension_length"])
        grouped.setdefault((record["cycle_date"], tension_length), []).append(record)
        detail_records.setdefault(tension_length, []).append(record)

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


def _rate_for_aggregated_points(points: List[Dict[str, Any]], field_name: str) -> float:
    if len(points) < 2:
        return 0.0
    base_date = points[0]["cycle_date"]
    return _linear_slope([
        (_years_between(base_date, item["cycle_date"]), float(item[field_name]))
        for item in points
    ])


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
        mm_rate = max(0.0, -_rate_for_aggregated_points(points, "avg_wear_min"))
        metric_values["Latest Wear %"][tension_length] = f"{latest['wear_percentage']:.2f} %"
        metric_values["Wear % Rate per year"][tension_length] = f"{percent_rate:.2f} % /year"
        metric_values["Wear mm Rate per year"][tension_length] = f"{mm_rate:.3f} mm /year"
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
```

- [ ] **Step 5: Run aggregation tests to verify they pass**

Run:

```powershell
cd backend
python -m pytest tests/test_wear_records.py::test_workbench_history_averages_raw_rows_by_line_date_and_tension_length tests/test_wear_records.py::test_workbench_latest_summary_uses_aggregated_time_series -q
```

Expected: `2 passed`.

- [ ] **Step 6: Commit Task 1**

Run:

```powershell
git add backend/tests/test_wear_records.py backend/app/core/calculation/wear_records.py
git commit -m "feat: add wire wear workbench aggregation"
```

---

### Task 2: Backend Raw Record CRUD Core

**Files:**
- Modify: `backend/tests/test_wear_records.py`
- Modify: `backend/app/core/calculation/wear_records.py`

- [ ] **Step 1: Run impact analysis before editing CRUD helpers**

Run `trace_path` for `query_wire_wear_records` with `direction=both`, `depth=2`, and `risk_labels=true`. Report callers and risk before editing.

- [ ] **Step 2: Write failing CRUD core tests**

Append to `backend/tests/test_wear_records.py`:

```python
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
```

- [ ] **Step 3: Run CRUD tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_wear_records.py::test_update_wire_wear_record_updates_only_allowed_fields tests/test_wear_records.py::test_delete_wire_wear_record_removes_one_row -q
```

Expected: FAIL because `update_wire_wear_record` and `delete_wire_wear_record` are not defined.

- [ ] **Step 4: Implement CRUD helpers**

Add to `backend/app/core/calculation/wear_records.py` after `save_wire_wear_records`:

```python
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
```

- [ ] **Step 5: Run CRUD tests to verify they pass**

Run:

```powershell
cd backend
python -m pytest tests/test_wear_records.py::test_update_wire_wear_record_updates_only_allowed_fields tests/test_wear_records.py::test_delete_wire_wear_record_removes_one_row -q
```

Expected: `2 passed`.

- [ ] **Step 6: Commit Task 2**

Run:

```powershell
git add backend/tests/test_wear_records.py backend/app/core/calculation/wear_records.py
git commit -m "feat: add wire wear raw record crud helpers"
```

---

### Task 3: Backend API and Excel Export

**Files:**
- Modify: `backend/tests/test_wear_records_api.py`
- Modify: `backend/app/api/endpoints/wear_records.py`
- Modify: `backend/app/core/calculation/wear_records.py`

- [ ] **Step 1: Run impact analysis before editing endpoint functions**

Run `trace_path` for `save_records`, `list_records`, and `projection` with `direction=both`, `depth=2`, and `risk_labels=true`. Report affected route callers.

- [ ] **Step 2: Write failing API tests**

Append to `backend/tests/test_wear_records_api.py`:

```python
def test_workbench_api_returns_history_summary_and_details(client):
    payload = _payload()
    payload["records"][0]["tension_length"] = "X1"
    payload["records"][0]["avg_wear_min"] = 12.0
    payload["records"][0]["wear_percentage"] = 10.0
    assert client.post("/api/calculation/wear-records", json=payload).status_code == 200

    second = _payload()
    second["line_class"] = "EAL"
    second["section"] = "Mainline"
    second["track"] = "DN"
    second["records"][0]["tension_length"] = "X1"
    second["records"][0]["avg_wear_min"] = 10.0
    second["records"][0]["wear_percentage"] = 14.0
    assert client.post("/api/calculation/wear-records", json=second).status_code == 200

    response = client.get("/api/calculation/wear-records/workbench?line_group=EAL")

    assert response.status_code == 200
    body = response.json()
    assert body["history_rows"][0]["values"]["X1"] == 11.0
    assert len(body["detail_records"]["X1"]) == 2


def test_update_and_delete_wire_wear_record_api(client):
    assert client.post("/api/calculation/wear-records", json=_payload()).status_code == 200
    record_id = client.get("/api/calculation/wear-records?line_group=EAL").json()["records"][0]["record_id"]

    update = client.patch(
        f"/api/calculation/wear-records/{record_id}",
        json={"avg_wear_min": 11.1, "wear_percentage": 9.9},
    )
    records_after_update = client.get("/api/calculation/wear-records?line_group=EAL").json()["records"]
    delete = client.delete(f"/api/calculation/wear-records/{record_id}")
    records_after_delete = client.get("/api/calculation/wear-records?line_group=EAL").json()["records"]

    assert update.status_code == 200
    assert records_after_update[0]["avg_wear_min"] == 11.1
    assert records_after_update[0]["wear_percentage"] == 9.9
    assert delete.status_code == 200
    assert records_after_delete == []


def test_export_wire_wear_records_returns_excel(client):
    assert client.post("/api/calculation/wear-records", json=_payload()).status_code == 200

    response = client.get("/api/calculation/wear-records/export?line_group=EAL")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.content[:2] == b"PK"


def test_manual_add_wire_wear_record_api(client):
    payload = _payload()
    payload["records"][0]["tension_length"] = "X88"

    response = client.post("/api/calculation/wear-records/manual", json=payload)
    records = client.get("/api/calculation/wear-records?line_group=EAL").json()["records"]

    assert response.status_code == 200
    assert response.json()["saved_count"] == 1
    assert records[0]["tension_length"] == "X88"
```

- [ ] **Step 3: Run API tests to verify they fail**

Run:

```powershell
cd backend
python -m pytest tests/test_wear_records_api.py::test_workbench_api_returns_history_summary_and_details tests/test_wear_records_api.py::test_update_and_delete_wire_wear_record_api tests/test_wear_records_api.py::test_export_wire_wear_records_returns_excel tests/test_wear_records_api.py::test_manual_add_wire_wear_record_api -q
```

Expected: FAIL with 404 for new endpoints.

- [ ] **Step 4: Add Excel workbook builder**

Add imports to `backend/app/core/calculation/wear_records.py`:

```python
from io import BytesIO
import pandas as pd
```

Add function after `build_workbench_summary`:

```python
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
```

- [ ] **Step 5: Add endpoint models and routes**

Modify `backend/app/api/endpoints/wear_records.py` imports:

```python
from fastapi.responses import Response
```

Extend calculation imports:

```python
    build_workbench_excel,
    build_workbench_summary,
    delete_wire_wear_record,
    update_wire_wear_record,
```

Add model:

```python
class WireWearUpdateRequestModel(BaseModel):
    line_group: Optional[Literal["EAL", "TML"]] = None
    line_class: Optional[Literal["EAL", "LMC", "TML"]] = None
    track: Optional[str] = None
    section: Optional[str] = None
    cycle_date: Optional[str] = None
    tension_length: Optional[str] = None
    from_m: Optional[float] = None
    to_m: Optional[float] = None
    avg_wear_min: Optional[float] = None
    sd: Optional[float] = None
    wear_percentage: Optional[float] = None
    source_file_names: Optional[List[str]] = None
    saved_by: Optional[str] = None
```

Add routes after `list_records` and before dashboard:

```python
@router.post("/manual", response_model=WireWearSaveResponse)
async def add_manual_records(payload: WireWearSaveRequestModel):
    db = get_database()
    try:
        with db.get_connection() as conn:
            result = save_wire_wear_records(conn, _to_core_request(payload), overwrite=False)
    except WireWearValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result.duplicate_count:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Wire wear records already exist for this line/class/track/section/date/tension length.",
                "duplicate_count": result.duplicate_count,
                "duplicates": result.duplicates,
            },
        )
    return WireWearSaveResponse(**result.__dict__)


@router.get("/workbench")
async def workbench(
    line_group: Literal["EAL", "TML"] = "EAL",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    filters = {"line_group": line_group, "date_from": date_from, "date_to": date_to}
    db = get_database()
    try:
        with db.get_connection() as conn:
            return build_workbench_summary(conn, filters)
    except WireWearValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{record_id}")
async def update_record(record_id: int, payload: WireWearUpdateRequestModel):
    updates = {key: value for key, value in payload.model_dump().items() if value is not None}
    db = get_database()
    try:
        with db.get_connection() as conn:
            success = update_wire_wear_record(conn, record_id, updates)
    except WireWearValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not success:
        raise HTTPException(status_code=404, detail=f"Wire wear record not found: {record_id}")
    return {"status": "success", "message": f"Wire wear record updated: {record_id}"}


@router.delete("/{record_id}")
async def delete_record(record_id: int):
    db = get_database()
    with db.get_connection() as conn:
        success = delete_wire_wear_record(conn, record_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Wire wear record not found: {record_id}")
    return {"status": "success", "message": f"Wire wear record deleted: {record_id}"}


@router.get("/export")
async def export_records(line_group: Literal["EAL", "TML"] = "EAL"):
    db = get_database()
    with db.get_connection() as conn:
        content = build_workbench_excel(conn, {"line_group": line_group})
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="wire-wear-records-{line_group}.xlsx"'},
    )
```

- [ ] **Step 6: Run API tests to verify they pass**

Run:

```powershell
cd backend
python -m pytest tests/test_wear_records_api.py -q
```

Expected: all tests in `test_wear_records_api.py` pass.

- [ ] **Step 7: Commit Task 3**

Run:

```powershell
git add backend/tests/test_wear_records_api.py backend/app/api/endpoints/wear_records.py backend/app/core/calculation/wear_records.py
git commit -m "feat: expose wire wear workbench api"
```

---

### Task 4: Frontend API Types and Store

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/store/useWearRecordsStore.ts`
- Create: `frontend/src/store/__tests__/useWearRecordsStore.workbench.test.ts`

- [ ] **Step 1: Run impact analysis before editing store/API functions**

Run graph or file impact checks for `fetchWireWearRecords`, `useWearRecordsStore`, and `WireWearSavedRecord`. Report direct importers.

- [ ] **Step 2: Write failing store test**

Create `frontend/src/store/__tests__/useWearRecordsStore.workbench.test.ts`:

```typescript
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { useWearRecordsStore } from '../useWearRecordsStore';
import * as client from '../../api/client';

vi.mock('../../api/client', async () => {
  const actual = await vi.importActual<typeof import('../../api/client')>('../../api/client');
  return {
    ...actual,
    fetchWireWearWorkbench: vi.fn(),
    addManualWireWearRecords: vi.fn(),
    updateWireWearRecord: vi.fn(),
    deleteWireWearRecord: vi.fn(),
    exportWireWearRecords: vi.fn(),
  };
});

describe('useWearRecordsStore workbench actions', () => {
  beforeEach(() => {
    useWearRecordsStore.getState().reset();
    vi.clearAllMocks();
  });

  it('loads workbench data for a selected line', async () => {
    vi.mocked(client.fetchWireWearWorkbench).mockResolvedValue({
      line_group: 'EAL',
      tension_lengths: ['X1'],
      history_rows: [{ cycle_date: '2026-02-01', values: { X1: 11 } }],
      latest_summary_rows: [{ metric: 'Latest Wear %', values: { X1: '12.00 %' } }],
      detail_records: { X1: [] },
      raw_records: [],
    });

    await useWearRecordsStore.getState().loadWorkbench({ line_group: 'EAL' });

    expect(client.fetchWireWearWorkbench).toHaveBeenCalledWith({ line_group: 'EAL' });
    expect(useWearRecordsStore.getState().workbench?.tension_lengths).toEqual(['X1']);
  });

  it('adds a manual record and reloads the selected line workbench', async () => {
    vi.mocked(client.addManualWireWearRecords).mockResolvedValue({
      saved_count: 1,
      updated_count: 0,
      duplicate_count: 0,
      duplicates: [],
    });
    vi.mocked(client.fetchWireWearWorkbench).mockResolvedValue({
      line_group: 'EAL',
      tension_lengths: ['X1'],
      history_rows: [],
      latest_summary_rows: [],
      detail_records: { X1: [] },
      raw_records: [],
    });

    await useWearRecordsStore.getState().addManualRecord({
      line_group: 'EAL',
      line_class: 'EAL',
      track: 'UP',
      section: 'Mainline',
      cycle_date: '2026-02-01',
      source_file_names: [],
      records: [{ tension_length: 'X1', from_m: 0, to_m: 10, avg_wear_min: 11, sd: 0, wear_percentage: 12 }],
    });

    expect(client.addManualWireWearRecords).toHaveBeenCalled();
    expect(client.fetchWireWearWorkbench).toHaveBeenCalledWith({ line_group: 'EAL' });
  });
});
```

- [ ] **Step 3: Run store test to verify it fails**

Run:

```powershell
cd frontend
npm test -- --run src/store/__tests__/useWearRecordsStore.workbench.test.ts
```

Expected: FAIL because workbench functions and state are not defined.

- [ ] **Step 4: Add TypeScript types**

Append to the wire wear section of `frontend/src/types/api.ts`:

```typescript
export interface WireWearHistoryRow {
  cycle_date: string
  values: Record<string, number | null>
}

export interface WireWearLatestSummaryRow {
  metric: string
  values: Record<string, string>
}

export interface WireWearWorkbenchResponse {
  line_group: WireWearLineGroup
  tension_lengths: string[]
  history_rows: WireWearHistoryRow[]
  latest_summary_rows: WireWearLatestSummaryRow[]
  detail_records: Record<string, WireWearSavedRecord[]>
  raw_records: WireWearSavedRecord[]
}

export type WireWearUpdateRequest = Partial<
  Pick<
    WireWearSavedRecord,
    | 'line_group'
    | 'line_class'
    | 'track'
    | 'section'
    | 'cycle_date'
    | 'tension_length'
    | 'from_m'
    | 'to_m'
    | 'avg_wear_min'
    | 'sd'
    | 'wear_percentage'
    | 'source_file_names'
    | 'saved_by'
  >
>
```

- [ ] **Step 5: Add API client functions**

Modify `frontend/src/api/client.ts` imports to include `WireWearUpdateRequest`, `WireWearWorkbenchResponse`, and `WireWearSaveResponse`.

Add functions after `fetchWireWearRecords`:

```typescript
export const fetchWireWearWorkbench = async (
  params: Record<string, string | undefined> = {},
): Promise<WireWearWorkbenchResponse> => {
  const response = await apiClient.get<WireWearWorkbenchResponse>('/calculation/wear-records/workbench', { params });
  return response.data;
};

export const addManualWireWearRecords = async (
  payload: WireWearSaveRequest,
): Promise<WireWearSaveResponse> => {
  const response = await apiClient.post<WireWearSaveResponse>('/calculation/wear-records/manual', payload);
  return response.data;
};

export const updateWireWearRecord = async (
  recordId: number,
  payload: WireWearUpdateRequest,
): Promise<ApiSuccessResponse> => {
  const response = await apiClient.patch<ApiSuccessResponse>(`/calculation/wear-records/${recordId}`, payload);
  return response.data;
};

export const deleteWireWearRecord = async (recordId: number): Promise<ApiSuccessResponse> => {
  const response = await apiClient.delete<ApiSuccessResponse>(`/calculation/wear-records/${recordId}`);
  return response.data;
};

export const exportWireWearRecords = async (
  params: Record<string, string | undefined> = {},
): Promise<Blob> => {
  const response = await apiClient.get('/calculation/wear-records/export', {
    params,
    responseType: 'blob',
  });
  return response.data;
};
```

- [ ] **Step 6: Extend store**

In `frontend/src/store/useWearRecordsStore.ts`, add imports and state:

```typescript
  addManualWireWearRecords,
  deleteWireWearRecord,
  exportWireWearRecords,
  fetchWireWearWorkbench,
  updateWireWearRecord,
```

Add types to imported type list:

```typescript
  WireWearUpdateRequest,
  WireWearWorkbenchResponse,
```

Add interface members:

```typescript
  workbench: WireWearWorkbenchResponse | null
  selectedLineGroup: WireWearLineGroup
  selectedTensionLength: string | null
  isExporting: boolean
  loadWorkbench: (params?: Record<string, string | undefined>) => Promise<void>
  setSelectedLineGroup: (lineGroup: WireWearLineGroup) => void
  setSelectedTensionLength: (tensionLength: string | null) => void
  addManualRecord: (payload: WireWearSaveRequest) => Promise<void>
  updateRecord: (recordId: number, payload: WireWearUpdateRequest) => Promise<void>
  deleteRecord: (recordId: number) => Promise<void>
  exportRecords: (params?: Record<string, string | undefined>) => Promise<Blob | null>
```

Add initial state:

```typescript
  workbench: null,
  selectedLineGroup: 'EAL' as WireWearLineGroup,
  selectedTensionLength: null,
  isExporting: false,
```

Add actions:

```typescript
  loadWorkbench: async (params = {}) => {
    set({ isLoading: true, error: null });
    try {
      const workbench = await fetchWireWearWorkbench(params);
      set({
        workbench,
        records: workbench.raw_records,
        selectedLineGroup: workbench.line_group,
        selectedTensionLength: workbench.tension_lengths[0] ?? null,
        isLoading: false,
      });
    } catch (err: any) {
      set({ error: err.message || 'Failed to load wire wear workbench', isLoading: false });
    }
  },

  setSelectedLineGroup: (lineGroup) => set({ selectedLineGroup: lineGroup }),
  setSelectedTensionLength: (tensionLength) => set({ selectedTensionLength: tensionLength }),

  addManualRecord: async (payload) => {
    set({ isSaving: true, error: null, duplicateConflict: null });
    try {
      await addManualWireWearRecords(payload);
      set({ isSaving: false });
      await get().loadWorkbench({ line_group: payload.line_group });
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
      set({ error: detail?.message || detail || err.message || 'Failed to add wire wear record', isSaving: false });
    }
  },

  updateRecord: async (recordId, payload) => {
    set({ isSaving: true, error: null });
    try {
      await updateWireWearRecord(recordId, payload);
      set({ isSaving: false });
      await get().loadWorkbench({ line_group: get().selectedLineGroup });
    } catch (err: any) {
      set({ error: err.message || 'Failed to update wire wear record', isSaving: false });
    }
  },

  deleteRecord: async (recordId) => {
    set({ isSaving: true, error: null });
    try {
      await deleteWireWearRecord(recordId);
      set({ isSaving: false });
      await get().loadWorkbench({ line_group: get().selectedLineGroup });
    } catch (err: any) {
      set({ error: err.message || 'Failed to delete wire wear record', isSaving: false });
    }
  },

  exportRecords: async (params = {}) => {
    set({ isExporting: true, error: null });
    try {
      const blob = await exportWireWearRecords(params);
      set({ isExporting: false });
      return blob;
    } catch (err: any) {
      set({ error: err.message || 'Failed to export wire wear records', isExporting: false });
      return null;
    }
  },
```

- [ ] **Step 7: Run store test to verify it passes**

Run:

```powershell
cd frontend
npm test -- --run src/store/__tests__/useWearRecordsStore.workbench.test.ts
```

Expected: test passes.

- [ ] **Step 8: Commit Task 4**

Run:

```powershell
git add frontend/src/types/api.ts frontend/src/api/client.ts frontend/src/store/useWearRecordsStore.ts frontend/src/store/__tests__/useWearRecordsStore.workbench.test.ts
git commit -m "feat: add wire wear workbench frontend state"
```

---

### Task 5: Frontend Workbench Components

**Files:**
- Create: `frontend/src/components/Calculation/WearHistoryPivotTable.tsx`
- Create: `frontend/src/components/Calculation/WearLatestSummaryTable.tsx`
- Create: `frontend/src/components/Calculation/WearTensionLengthDetailPanel.tsx`
- Create: `frontend/src/components/Calculation/WireWearRecordDialog.tsx`
- Create: tests under `frontend/src/components/Calculation/__tests__/`

- [ ] **Step 1: Write failing component tests**

Create `frontend/src/components/Calculation/__tests__/WearWorkbenchTables.test.tsx`:

```typescript
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';

import WearHistoryPivotTable from '../WearHistoryPivotTable';
import WearLatestSummaryTable from '../WearLatestSummaryTable';
import WearTensionLengthDetailPanel from '../WearTensionLengthDetailPanel';
import WireWearRecordDialog from '../WireWearRecordDialog';

const detailRecord = {
  record_id: 1,
  line_group: 'EAL',
  line_class: 'LMC',
  track: 'UP',
  section: 'LMC',
  cycle_date: '2026-02-01',
  tension_length: 'X1',
  from_m: 100,
  to_m: 200,
  avg_wear_min: 11,
  sd: 0.1,
  wear_percentage: 12,
  source_file_names: ['cycle.xlsx'],
  created_at: '',
  updated_at: '',
} as const;

describe('wire wear workbench tables', () => {
  it('renders history pivot cells and lets the user select a tension length', () => {
    const onSelect = vi.fn();
    render(
      <WearHistoryPivotTable
        tensionLengths={['X1']}
        rows={[{ cycle_date: '2026-02-01', values: { X1: 11 } }]}
        selectedTensionLength={null}
        onSelectTensionLength={onSelect}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'X1' }));

    expect(screen.getByText('2026-02-01')).toBeInTheDocument();
    expect(screen.getByText('11.000')).toBeInTheDocument();
    expect(onSelect).toHaveBeenCalledWith('X1');
  });

  it('renders latest summary metrics', () => {
    render(
      <WearLatestSummaryTable
        tensionLengths={['X1']}
        rows={[{ metric: 'Latest Wear %', values: { X1: '12.00 %' } }]}
        selectedTensionLength="X1"
        onSelectTensionLength={vi.fn()}
      />,
    );

    expect(screen.getByText('Latest Wear %')).toBeInTheDocument();
    expect(screen.getByText('12.00 %')).toBeInTheDocument();
  });

  it('renders detail records and row actions', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    render(
      <WearTensionLengthDetailPanel
        tensionLength="X1"
        records={[detailRecord]}
        onEdit={onEdit}
        onDelete={onDelete}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /Edit/i }));
    fireEvent.click(screen.getByRole('button', { name: /Delete/i }));

    expect(screen.getByText(/X1 details/i)).toBeInTheDocument();
    expect(screen.getByText('LMC')).toBeInTheDocument();
    expect(onEdit).toHaveBeenCalledWith(detailRecord);
    expect(onDelete).toHaveBeenCalledWith(detailRecord);
  });

  it('saves values from the add edit dialog', () => {
    const onSave = vi.fn();
    render(
      <WireWearRecordDialog
        open
        lineGroup="EAL"
        initialRecord={detailRecord}
        onClose={vi.fn()}
        onSave={onSave}
      />,
    );

    fireEvent.change(screen.getByLabelText(/Avg Wear Min/i), { target: { value: '10.5' } });
    fireEvent.click(screen.getByRole('button', { name: /Save/i }));

    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ avg_wear_min: 10.5 }));
  });
});
```

- [ ] **Step 2: Run component tests to verify they fail**

Run:

```powershell
cd frontend
npm test -- --run src/components/Calculation/__tests__/WearWorkbenchTables.test.tsx
```

Expected: FAIL because components do not exist.

- [ ] **Step 3: Create `WearHistoryPivotTable.tsx`**

```typescript
import { Box, Button, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import type { WireWearHistoryRow } from '../../types/api';

interface Props {
  tensionLengths: string[]
  rows: WireWearHistoryRow[]
  selectedTensionLength: string | null
  onSelectTensionLength: (tensionLength: string) => void
}

export default function WearHistoryPivotTable({
  tensionLengths,
  rows,
  selectedTensionLength,
  onSelectTensionLength,
}: Props) {
  return (
    <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 420 }}>
      <Table stickyHeader size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ minWidth: 120, fontWeight: 700 }}>Date</TableCell>
            {tensionLengths.map(tensionLength => (
              <TableCell key={tensionLength} align="right" sx={{ minWidth: 96, fontWeight: 700 }}>
                <Button
                  size="small"
                  variant={selectedTensionLength === tensionLength ? 'contained' : 'text'}
                  onClick={() => onSelectTensionLength(tensionLength)}
                >
                  {tensionLength}
                </Button>
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map(row => (
            <TableRow key={row.cycle_date}>
              <TableCell>{row.cycle_date}</TableCell>
              {tensionLengths.map(tensionLength => {
                const value = row.values[tensionLength];
                return (
                  <TableCell key={tensionLength} align="right">
                    {typeof value === 'number' ? value.toFixed(3) : ''}
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {rows.length === 0 && <Box sx={{ p: 2, color: 'text.secondary' }}>No history records</Box>}
    </TableContainer>
  );
}
```

- [ ] **Step 4: Create `WearLatestSummaryTable.tsx`**

```typescript
import { Button, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import type { WireWearLatestSummaryRow } from '../../types/api';

interface Props {
  tensionLengths: string[]
  rows: WireWearLatestSummaryRow[]
  selectedTensionLength: string | null
  onSelectTensionLength: (tensionLength: string) => void
}

export default function WearLatestSummaryTable({
  tensionLengths,
  rows,
  selectedTensionLength,
  onSelectTensionLength,
}: Props) {
  return (
    <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 360 }}>
      <Table stickyHeader size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ minWidth: 190, fontWeight: 700 }}>Metric</TableCell>
            {tensionLengths.map(tensionLength => (
              <TableCell key={tensionLength} align="right" sx={{ minWidth: 120, fontWeight: 700 }}>
                <Button
                  size="small"
                  variant={selectedTensionLength === tensionLength ? 'contained' : 'text'}
                  onClick={() => onSelectTensionLength(tensionLength)}
                >
                  {tensionLength}
                </Button>
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map(row => (
            <TableRow key={row.metric}>
              <TableCell>{row.metric}</TableCell>
              {tensionLengths.map(tensionLength => (
                <TableCell key={tensionLength} align="right">{row.values[tensionLength] ?? ''}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
```

- [ ] **Step 5: Create `WearTensionLengthDetailPanel.tsx`**

```typescript
import { Button, Paper, Stack, Typography } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import type { WireWearSavedRecord } from '../../types/api';

interface Props {
  tensionLength: string | null
  records: WireWearSavedRecord[]
  onEdit: (record: WireWearSavedRecord) => void
  onDelete: (record: WireWearSavedRecord) => void
}

export default function WearTensionLengthDetailPanel({ tensionLength, records, onEdit, onDelete }: Props) {
  const columns: GridColDef[] = [
    { field: 'cycle_date', headerName: 'Cycle Date', width: 120 },
    { field: 'line_class', headerName: 'Class', width: 90 },
    { field: 'track', headerName: 'Track', width: 90 },
    { field: 'section', headerName: 'Section', width: 110 },
    { field: 'from_m', headerName: 'From (m)', width: 100 },
    { field: 'to_m', headerName: 'To (m)', width: 100 },
    { field: 'avg_wear_min', headerName: 'Avg Wear Min', width: 130 },
    { field: 'wear_percentage', headerName: 'Wear %', width: 100 },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 180,
      sortable: false,
      renderCell: params => (
        <Stack direction="row" spacing={1}>
          <Button size="small" startIcon={<EditIcon />} onClick={() => onEdit(params.row)}>Edit</Button>
          <Button size="small" color="error" startIcon={<DeleteIcon />} onClick={() => onDelete(params.row)}>Delete</Button>
        </Stack>
      ),
    },
  ];

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
        {tensionLength ? `${tensionLength} details` : 'Tension Length details'}
      </Typography>
      <DataGrid
        rows={records.map(record => ({ ...record, id: record.record_id }))}
        columns={columns}
        autoHeight
        disableRowSelectionOnClick
        hideFooter={records.length <= 25}
        pageSizeOptions={[25, 50]}
      />
    </Paper>
  );
}
```

- [ ] **Step 6: Create `WireWearRecordDialog.tsx`**

```typescript
import React from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
} from '@mui/material';
import type {
  WireWearLineClass,
  WireWearLineGroup,
  WireWearSavedRecord,
  WireWearUpdateRequest,
} from '../../types/api';

interface Props {
  open: boolean
  lineGroup: WireWearLineGroup
  initialRecord?: Partial<WireWearSavedRecord> | null
  onClose: () => void
  onSave: (payload: WireWearUpdateRequest) => void
}

const defaultForm = {
  line_class: 'EAL' as WireWearLineClass,
  track: 'UP',
  section: 'Mainline',
  cycle_date: '',
  tension_length: '',
  from_m: 0,
  to_m: 0,
  avg_wear_min: 0,
  sd: 0,
  wear_percentage: 0,
};

export default function WireWearRecordDialog({ open, lineGroup, initialRecord, onClose, onSave }: Props) {
  const [form, setForm] = React.useState({ ...defaultForm, line_group: lineGroup });

  React.useEffect(() => {
    setForm({
      ...defaultForm,
      line_group: lineGroup,
      ...initialRecord,
    });
  }, [initialRecord, lineGroup, open]);

  const setField = (field: keyof typeof form, value: string | number) => {
    setForm(current => ({ ...current, [field]: value }));
  };

  const handleSave = () => {
    onSave({
      line_group: lineGroup,
      line_class: form.line_class,
      track: String(form.track),
      section: String(form.section),
      cycle_date: String(form.cycle_date),
      tension_length: String(form.tension_length),
      from_m: Number(form.from_m),
      to_m: Number(form.to_m),
      avg_wear_min: Number(form.avg_wear_min),
      sd: Number(form.sd),
      wear_percentage: Number(form.wear_percentage),
    });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{initialRecord?.record_id ? 'Edit Wire Wear Record' : 'Add Wire Wear Record'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField select label="Class" value={form.line_class} onChange={event => setField('line_class', event.target.value)}>
            <MenuItem value="EAL">EAL</MenuItem>
            <MenuItem value="LMC">LMC</MenuItem>
            <MenuItem value="TML">TML</MenuItem>
          </TextField>
          <TextField label="Track" value={form.track} onChange={event => setField('track', event.target.value)} />
          <TextField label="Section" value={form.section} onChange={event => setField('section', event.target.value)} />
          <TextField label="Cycle Date" type="date" value={form.cycle_date} onChange={event => setField('cycle_date', event.target.value)} InputLabelProps={{ shrink: true }} />
          <TextField label="Tension Length" value={form.tension_length} onChange={event => setField('tension_length', event.target.value)} />
          <TextField label="From (m)" type="number" value={form.from_m} onChange={event => setField('from_m', event.target.value)} />
          <TextField label="To (m)" type="number" value={form.to_m} onChange={event => setField('to_m', event.target.value)} />
          <TextField label="Avg Wear Min" type="number" value={form.avg_wear_min} onChange={event => setField('avg_wear_min', event.target.value)} />
          <TextField label="SD" type="number" value={form.sd} onChange={event => setField('sd', event.target.value)} />
          <TextField label="Wear %" type="number" value={form.wear_percentage} onChange={event => setField('wear_percentage', event.target.value)} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSave}>Save</Button>
      </DialogActions>
    </Dialog>
  );
}
```

- [ ] **Step 7: Run component tests to verify they pass**

Run:

```powershell
cd frontend
npm test -- --run src/components/Calculation/__tests__/WearWorkbenchTables.test.tsx
```

Expected: tests pass.

- [ ] **Step 8: Commit Task 5**

Run:

```powershell
git add frontend/src/components/Calculation/WearHistoryPivotTable.tsx frontend/src/components/Calculation/WearLatestSummaryTable.tsx frontend/src/components/Calculation/WearTensionLengthDetailPanel.tsx frontend/src/components/Calculation/WireWearRecordDialog.tsx frontend/src/components/Calculation/__tests__/WearWorkbenchTables.test.tsx
git commit -m "feat: add wire wear workbench tables"
```

---

### Task 6: Replace WearRecordsPanel With Workbench Shell

**Files:**
- Modify: `frontend/src/components/Calculation/WearRecordsPanel.tsx`
- Modify: `frontend/src/components/Calculation/__tests__/WearRecordsPanel.test.tsx`

- [ ] **Step 1: Write failing panel tests**

Replace the core assertions in `WearRecordsPanel.test.tsx` with workbench-oriented assertions:

```typescript
it('renders workbench toolbar and aggregated tables', () => {
  useWearRecordsStore.setState({
    workbench: {
      line_group: 'EAL',
      tension_lengths: ['X1'],
      history_rows: [{ cycle_date: '2026-02-01', values: { X1: 11 } }],
      latest_summary_rows: [{ metric: 'Latest Wear %', values: { X1: '12.00 %' } }],
      detail_records: { X1: [] },
      raw_records: [],
    },
    selectedLineGroup: 'EAL',
    selectedTensionLength: 'X1',
    loadWorkbench: vi.fn(),
    setSelectedLineGroup: vi.fn(),
    setSelectedTensionLength: vi.fn(),
    addManualRecord: vi.fn(),
    updateRecord: vi.fn(),
    deleteRecord: vi.fn(),
    exportRecords: vi.fn(),
  } as any);

  render(<WearRecordsPanel />);

  expect(screen.getByRole('button', { name: /Export Excel/i })).toBeInTheDocument();
  expect(screen.getByText(/Historical Avg Wear Min/i)).toBeInTheDocument();
  expect(screen.getByText(/Latest Summary/i)).toBeInTheDocument();
  expect(screen.getByText('11.000')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run panel test to verify it fails**

Run:

```powershell
cd frontend
npm test -- --run src/components/Calculation/__tests__/WearRecordsPanel.test.tsx
```

Expected: FAIL because current panel still renders old By Cycle / By Tension Length layout.

- [ ] **Step 3: Implement workbench panel**

Rewrite `WearRecordsPanel.tsx` to:

- Load workbench with selected `line_group`.
- Render toolbar.
- Render `WearHistoryPivotTable`.
- Render `WearLatestSummaryTable`.
- Render `TensionLengthTrendChart` for selected TL details.
- Render `WearTensionLengthDetailPanel`.
- Trigger `addManualRecord(payload)` for Add.
- Trigger `updateRecord(record_id, payload)` for Edit.
- Trigger `deleteRecord(record_id)` for Delete after confirmation.
- Trigger `exportRecords({ line_group })` and save the blob through browser download.

Use this shell structure:

```typescript
const selectedRecords = selectedTensionLength
  ? workbench?.detail_records[selectedTensionLength] ?? []
  : [];

const handleExport = async () => {
  const blob = await exportRecords({ line_group: selectedLineGroup });
  if (!blob) return;
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `wire-wear-records-${selectedLineGroup}.xlsx`;
  link.click();
  URL.revokeObjectURL(url);
};
```

- [ ] **Step 4: Run panel tests**

Run:

```powershell
cd frontend
npm test -- --run src/components/Calculation/__tests__/WearRecordsPanel.test.tsx
```

Expected: tests pass.

- [ ] **Step 5: Commit Task 6**

Run:

```powershell
git add frontend/src/components/Calculation/WearRecordsPanel.tsx frontend/src/components/Calculation/__tests__/WearRecordsPanel.test.tsx
git commit -m "feat: replace wire wear records panel with workbench"
```

---

### Task 7: Analysis Tab Line Selector

**Files:**
- Modify: `frontend/src/views/__tests__/WearCalculatorView.test.tsx`
- Modify: `frontend/src/views/WearCalculatorView.tsx`

- [ ] **Step 1: Run impact analysis before editing `WearCalculatorView`**

Run `trace_path` for `WearCalculatorView` and `setLineClass` with `direction=both`, `depth=2`, and `risk_labels=true`. Report direct callers and tests.

- [ ] **Step 2: Write failing Analysis selector test**

Append to `frontend/src/views/__tests__/WearCalculatorView.test.tsx`:

```typescript
it('shows only EAL and TML in the Analysis line selector', () => {
  render(<WearCalculatorView />);

  fireEvent.mouseDown(screen.getByLabelText(/Line/i));

  expect(screen.getByRole('option', { name: 'EAL' })).toBeInTheDocument();
  expect(screen.getByRole('option', { name: 'TML' })).toBeInTheDocument();
  expect(screen.queryByRole('option', { name: 'LMC' })).not.toBeInTheDocument();
});
```

- [ ] **Step 3: Run view test to verify it fails**

Run:

```powershell
cd frontend
npm test -- --run src/views/__tests__/WearCalculatorView.test.tsx
```

Expected: FAIL because label is `Line Class` or `LMC` is present.

- [ ] **Step 4: Update selector in `WearCalculatorView.tsx`**

Change:

```tsx
<InputLabel id="wear-line-class-label">Line Class</InputLabel>
```

to:

```tsx
<InputLabel id="wear-line-class-label">Line</InputLabel>
```

Remove the `LMC` menu item:

```tsx
<MenuItem value="EAL">EAL</MenuItem>
<MenuItem value="TML">TML</MenuItem>
```

Keep `handleSaveWearRecords` mapping as:

```typescript
const lineGroup: WireWearLineGroup = lineClass === 'TML' ? 'TML' : 'EAL';
```

This preserves existing saved-data compatibility if legacy tabs still contain `lineClass: 'LMC'`.

- [ ] **Step 5: Run view test to verify it passes**

Run:

```powershell
cd frontend
npm test -- --run src/views/__tests__/WearCalculatorView.test.tsx
```

Expected: tests pass.

- [ ] **Step 6: Commit Task 7**

Run:

```powershell
git add frontend/src/views/WearCalculatorView.tsx frontend/src/views/__tests__/WearCalculatorView.test.tsx
git commit -m "feat: simplify wear analysis line selector"
```

---

### Task 8: Next-Phase Plan for Packaging, Offline Sync, and Hosted Server

**Files:**
- Create: `docs/superpowers/plans/2026-07-07-wire-wear-offline-sync-packaging-server-next-phase.md`

- [ ] **Step 1: Create next-phase plan document**

Create the file with this content:

```markdown
# Wire Wear Offline Sync Packaging Server Next Phase Plan

## Goal

Define the next phase after the Wire Wear Records Workbench: package strategy, offline export/import sync, and optional hosted-server deployment.

## Phase 2A: Packaging Decision

- Keep `dir` folder packaging as the recommended default for portable offline use.
- Document that production Electron currently sets `DB_PATH` to `<packaged app root>/data/analysis.db`.
- Document that single exe packaging must externalize writable data to `%APPDATA%` or another writable folder because embedded executable resources are not a database storage location.
- Add an in-app About or diagnostics view showing the active database path.

## Phase 2B: Offline Sync Package

- Add export sync package action that writes:
  - SQLite data version.
  - Export timestamp.
  - Source machine/user label.
  - Wire wear records.
  - Repeated records if selected.
  - Metadata file hashes.
- Add import sync package action that:
  - Creates a SQLite backup before import.
  - Compares row-level `updated_at`.
  - Updates local rows only when import rows are newer.
  - Reports conflicts and skipped rows.

## Phase 2C: Hosted Server Option

- Evaluate central FastAPI deployment on VPS.
- Prefer PostgreSQL for multi-user writes.
- Add authentication before exposing write APIs.
- Use HTTPS, firewall restrictions, backups, and database migration scripts.
- Treat SharePoint as file exchange/backup storage, not as the live concurrency database.
```

- [ ] **Step 2: Commit next-phase plan**

Run:

```powershell
git add docs/superpowers/plans/2026-07-07-wire-wear-offline-sync-packaging-server-next-phase.md
git commit -m "docs: plan wire wear offline sync phase"
```

---

### Task 9: Full Verification

**Files:**
- No planned edits.

- [ ] **Step 1: Run backend wear tests**

Run:

```powershell
cd backend
python -m pytest tests/test_wear_records.py tests/test_wear_records_api.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend targeted tests**

Run:

```powershell
cd frontend
npm test -- --run src/store/__tests__/useWearRecordsStore.workbench.test.ts src/components/Calculation/__tests__/WearWorkbenchTables.test.tsx src/components/Calculation/__tests__/WearRecordsPanel.test.tsx src/views/__tests__/WearCalculatorView.test.tsx
```

Expected: all tests pass.

- [ ] **Step 3: Run frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected: TypeScript and Vite build pass.

- [ ] **Step 4: Run full repository status and change detection**

Run:

```powershell
git status --short
```

Run MCP:

```json
{
  "project": "C-Smart-Maintanence-TOV640_Analyzer",
  "scope": "wire wear records workbench",
  "depth": 2
}
```

Expected: only intended workbench files and next-phase plan are changed after the final task commit sequence. `detect_changes` should show no unrelated execution-flow impacts.

- [ ] **Step 5: Manual UI verification**

Start the app:

```powershell
npm run dev
```

Verify:

- `Analysis` selector shows `Line` with `EAL` and `TML`.
- `Wire Wear Records` tab loads Table 1 and Table 2.
- Clicking a TL selects it and updates the detail panel and graph.
- Edit and Delete buttons act on raw rows.
- Export Excel downloads a workbook with `History Avg Wear Min`, `Latest Summary`, and `Raw Records` sheets.

- [ ] **Step 6: Finish verification**

If verification required code changes, write a short follow-up plan for the specific failing file and repeat the same failing-test, implementation, passing-test cycle before committing that fix. If no fixes were needed, do not create an empty commit.
