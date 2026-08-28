# Wear Calculator TL-Cycle Aggregation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Analysis, Save Records, Wire Wear Records, Dashboard, Projection, Excel export, and JSON sync use one canonical `Line + Business Cycle Date + Tension Length` record model.

**Architecture:** Parse an upload into a deterministic complete-cycle preview, resolve every TL against line-specific canonical metadata, and persist only normalized cycle aggregates plus coverage, conflict audit, and tombstones. Keep raw measurements transient and split the backend into focused metadata, aggregation, repository, analytics, and I/O modules; the React UI consumes those contracts and stages record edits until one atomic save.

**Tech Stack:** FastAPI, SQLite, Pydantic, pandas/openpyxl, pytest, React 18, Zustand, TypeScript, MUI, MUI DataGrid, Plotly, Vitest, Testing Library, Playwright.

---

## Scope and Approved Decisions

This plan implements `docs/superpowers/specs/2026-07-08-wear-calculator-tl-cycle-aggregation-design.md` and supersedes the earlier simplified implementation plan. Database Record UI/UX improvements are explicitly excluded and will receive a separate spec and plan after this branch.

The immutable business decisions are:

- Record identity is `line_group + cycle_date + normalized tension_length`.
- One complete upload cycle produces at most one row per TL; UP and DN metadata produce `Siding`.
- Cycle Date defaults to the latest acquisition date and remains editable before save.
- EAL expects `U1`, `U2`, `U3`, `D1`, `D2`, `D3`, `LOW S1`, `RAC UP`, `RAC DN`, `LMC UP`, `LMC DN`; TML expects `U1`–`U5` and `D1`–`D5`.
- A segment is present when at least one valid measurement resolves to it. Metadata-based TL coverage is advisory.
- Metadata intervals merge when overlapping, touching, or separated by at most `0.01 m`. Larger gaps create separate physical intervals for the same TL; the record retains one business identity with bounding From/To plus interval count/details.
- Raw measurements resolve by Line + Track + Chainage to exactly one physical interval. Gap measurements and ambiguous matches block with source/TL/chainage diagnostics; compound raw TL labels are never guessed or stored.
- Duplicate measurement identities with different values preview the lower `wear_min`, remain blocked until explicitly accepted, and retain full audit.
- `measurement_sd` is nullable and distinct from derived `historical_sd`.
- Wear % remains precise in backend/export/sync and is rounded to the nearest integer only in visible UI text.
- Wire Wear Records edits are staged; Save Changes is atomic; deletions create tombstones.
- Dashboard uses three compact Top-5 tables. Projection uses one shared mm threshold and separate EAL/TML charts.
- Excel is report-only. JSON schema `wear-cycle-v1` is the only round-trip sync format.
- SQLite is not backed up and legacy raw/test wire-wear data is not migrated.

## Subagent Execution Protocol

The controller must use a fresh implementer for each task, followed by a fresh spec-compliance reviewer and then a fresh code-quality reviewer. Implementation tasks run sequentially; do not dispatch multiple implementers in parallel because all agents share the worktree.

For every task from Task 3 onward:

1. Give the implementer the full task text and relevant approved decisions; do not ask the implementer to read the plan.
2. Before editing each production function, method, class, or React component, use codebase-memory-mcp `search_graph`, then `trace_path(direction="inbound", mode="calls", risk_labels=true)` on its exact qualified name.
3. Report direct callers, affected flows, and risk. If any planned edit is HIGH or CRITICAL, stop before editing and report the blast radius to the user.
4. Follow RED → verify expected failure → GREEN → focused regression tests → refactor while green. Production code must not precede the failing test.
5. Run codebase-memory-mcp `detect_changes` before staging. Also inspect `git diff --check`, `git diff --name-only`, and `git status --short`.
6. Stage only files listed in that task. Never stage, restore, or delete unrelated screenshots, `.superpowers/brainstorm/**/server-info`, or the user's `AGENTS.md` edit.
7. Commit the task, then run spec review. The same implementer fixes every spec gap and the spec reviewer rechecks it.
8. Run code-quality review only after spec approval. The same implementer fixes every quality issue and the quality reviewer rechecks it.
9. Report changed behavior, tests, commit hash, and the next task.

Use only codebase-memory-mcp for graph discovery and impact analysis. If its active-worktree index is stale, run `index_repository` for `C:\Smart Maintanence\TOV640_Analyzer\.worktrees\wear-tl-cycle-aggregation` and retry. Use `rg` only for strings, configuration, non-code files, or when graph coverage remains insufficient. Do not use GitNexus.

## File Structure

### Backend domain and persistence

- Modify `backend/app/core/schema.sql`: final normalized cycle, segment, record, conflict, and tombstone tables; schema version `1.5`.
- Modify `backend/app/core/database.py`: destructive 1.5 migration for obsolete test-only cycle data, without backup.
- Create `backend/app/core/calculation/wear_cycle_types.py`: immutable domain dataclasses, enums, business-key normalization, expected segments.
- Create `backend/app/core/calculation/wear_cycle_metadata.py`: source segment detection, metadata interval expansion, canonical TL resolution, coverage catalog.
- Create `backend/app/core/calculation/wear_cycle_aggregation.py`: measurement identity, duplicate/conflict handling, cycle preview, deterministic digest.
- Create `backend/app/core/calculation/wear_cycle_repository.py`: cycle save, workbench query, atomic staged change set, optimistic concurrency, tombstones.
- Create `backend/app/core/calculation/wear_cycle_analytics.py`: historical SD, all-history OLS, dashboard rankings, 30-year projection.
- Create `backend/app/core/calculation/wear_cycle_io.py`: four-sheet Excel report and `wear-cycle-v1` export/preview/apply.
- Modify `backend/app/core/calculation/wear_records.py`: retain legacy facade only where existing callers still need it; route all user-facing aggregate behavior to new modules and remove SD-overwrite behavior.
- Modify `backend/app/api/endpoints/calculation.py`: complete-cycle upload preview contract.
- Modify `backend/app/api/endpoints/wear_records.py`: cycle save, changes, workbench, analytics, report, and two-phase sync endpoints.

### Backend tests

- Modify `backend/tests/test_wear_records.py`: schema and repository coverage.
- Create `backend/tests/test_wear_cycle_metadata.py`: segment and canonical metadata rules.
- Create `backend/tests/test_wear_cycle_aggregation.py`: deduplication, conflict, coverage, Cycle Date, aggregate rules.
- Create `backend/tests/test_wear_cycle_analytics.py`: SD, regression, dashboard, projection.
- Create `backend/tests/test_wear_cycle_io.py`: workbook and JSON sync rules.
- Modify `backend/tests/test_calculation_api.py`: upload preview API.
- Modify `backend/tests/test_wear_records_api.py`: save/change/workbench/analytics/I/O API.
- Modify `backend/tests/test_wire_wear_sync.py`: reject legacy schema and prevent resurrection.

### Frontend contracts and state

- Modify `frontend/src/types/api.ts`: complete-cycle preview, aggregate record, staged change, analytics, report, and sync types.
- Modify `frontend/src/api/client.ts`: exact backend endpoint wrappers.
- Modify `frontend/src/store/useWearStore.ts`: editable Cycle Date, file removal, conflict acceptance, preview/save status.
- Modify `frontend/src/store/useWearRecordsStore.ts`: committed snapshot plus staged Add/Edit/Delete Cell/Delete Row changes and navigation guard state.

### Frontend presentation

- Modify `frontend/src/components/Calculation/WearResultTable.tsx`: approved columns, natural TL sort, canonical From sort.
- Modify `frontend/src/components/Calculation/wearAnalysisPresentation.ts`: chart filtering/sorting/axis helpers using the same row array.
- Create `frontend/src/components/Calculation/WearCycleStatusPanel.tsx`: expected-segment and conflict review controls.
- Create `frontend/src/components/Calculation/WearAnalysisCharts.tsx`: Wear % and Avg Wear Min charts.
- Modify `frontend/src/components/Calculation/WearRecordsPanel.tsx`: staged workbench only.
- Modify `frontend/src/components/Calculation/WearHistoryPivotTable.tsx`: matrix interactions, adjacent trash icons, horizontal scrolling, pending styles.
- Modify `frontend/src/components/Calculation/WearLatestSummaryTable.tsx`: canonical summary order and trend fields.
- Modify `frontend/src/components/Calculation/WireWearRecordDialog.tsx`: metadata-owned fields and Add/Edit form.
- Modify `frontend/src/components/Calculation/WearDashboardPanel.tsx`: three ranked tables.
- Modify `frontend/src/components/Calculation/WearProjectionPanel.tsx`: shared threshold, two charts, expandable combined year table.
- Modify `frontend/src/views/WearCalculatorView.tsx`: four top-level tabs and unsaved-change guard.
- Update adjacent tests under `frontend/src/**/__tests__/` and `frontend/tests/calculation.spec.ts`.

---

## Completed Foundation

### Task 1: Initial Aggregated Table — Completed

- [x] Added the first `wire_wear_cycle_records` table and migration.
- [x] Verified focused backend tests.
- [x] Commit: `cb4bab0 feat: add wire wear cycle records table`

The Task 3 migration intentionally replaces this interim schema because final requirements add a parent cycle, nullable measurement SD, segments, conflict audit, and tombstones.

### Task 2: Initial Aggregate Service — Completed

- [x] Added initial save/query helpers for `Line + Cycle Date + TL`.
- [x] Verified focused backend tests.
- [x] Commit: `88fe5ec feat: add wire wear cycle record service`

Task 6 replaces user-facing behavior from this interim service. No compatibility guarantee is required for its test-only stored rows.

---

### Task 3: Final Normalized Cycle Schema

**Files:**
- Modify: `backend/app/core/schema.sql`
- Modify: `backend/app/core/database.py`
- Test: `backend/tests/test_wear_records.py`

- [ ] **Step 1: Run impact analysis**

Use `search_graph` and inbound `trace_path` for `DatabaseManager._init_database`, `DatabaseManager._apply_wire_wear_cycle_records_migration`, and `DatabaseManager._table_exists`. Report startup/test callers and risk before editing.

- [ ] **Step 2: Write the failing schema test**

Add a test that initializes a database, reads `PRAGMA table_info`, `PRAGMA foreign_key_list`, and `PRAGMA index_list`, and asserts this contract:

```python
def test_complete_cycle_schema_is_normalized(tmp_path):
    db = DatabaseManager(str(tmp_path / "wear-cycle.db"))
    try:
        with db.get_connection() as conn:
            cycle_columns = _column_names(conn, "wire_wear_cycles")
            record_columns = _column_names(conn, "wire_wear_cycle_records")
            tables = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
    finally:
        db.close()
        DatabaseManager.reset_instance()

    assert {"line_group", "cycle_date", "completeness_state", "source_type"} <= cycle_columns
    assert {"cycle_id", "measurement_sd", "source_lineage"} <= record_columns
    assert "sd" not in record_columns
    assert {
        "wire_wear_cycle_segments",
        "wire_wear_conflict_decisions",
        "wire_wear_deletion_tombstones",
    } <= tables
```

- [ ] **Step 3: Verify RED**

Run:

```powershell
cd backend
python -m pytest tests/test_wear_records.py::test_complete_cycle_schema_is_normalized -q
```

Expected: FAIL because `wire_wear_cycles` and the audit/tombstone tables do not exist and `sd` is still present.

- [ ] **Step 4: Implement schema 1.5**

Replace the interim cycle table block in `schema.sql` with concrete tables using these keys and constraints:

```sql
CREATE TABLE IF NOT EXISTS wire_wear_cycles (
    cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_group TEXT NOT NULL CHECK(line_group IN ('EAL', 'TML')),
    cycle_date TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK(source_type IN ('analysis', 'manual', 'sync')),
    acquisition_date_from TEXT,
    acquisition_date_to TEXT,
    completeness_state TEXT NOT NULL CHECK(completeness_state IN ('complete', 'incomplete')),
    source_lineage TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(line_group, cycle_date)
);

CREATE TABLE IF NOT EXISTS wire_wear_cycle_segments (
    segment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id INTEGER NOT NULL,
    segment_name TEXT NOT NULL,
    is_present INTEGER NOT NULL CHECK(is_present IN (0, 1)),
    coverage_percentage REAL NOT NULL,
    diagnostic_gaps TEXT NOT NULL DEFAULT '[]',
    source_file_names TEXT NOT NULL DEFAULT '[]',
    acquisition_date_from TEXT,
    acquisition_date_to TEXT,
    UNIQUE(cycle_id, segment_name),
    FOREIGN KEY(cycle_id) REFERENCES wire_wear_cycles(cycle_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS wire_wear_cycle_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id INTEGER NOT NULL,
    line_group TEXT NOT NULL CHECK(line_group IN ('EAL', 'TML')),
    cycle_date TEXT NOT NULL,
    tension_length TEXT NOT NULL,
    track TEXT NOT NULL CHECK(track IN ('UP', 'DN', 'Siding')),
    from_m REAL NOT NULL,
    to_m REAL NOT NULL,
    avg_wear_min REAL NOT NULL,
    wear_percentage REAL NOT NULL,
    measurement_sd REAL,
    source_lineage TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(line_group, cycle_date, tension_length),
    FOREIGN KEY(cycle_id) REFERENCES wire_wear_cycles(cycle_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS wire_wear_conflict_decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id INTEGER NOT NULL,
    measurement_identity TEXT NOT NULL,
    source_values TEXT NOT NULL,
    selected_wear_min REAL NOT NULL,
    accepted_at TEXT NOT NULL,
    UNIQUE(cycle_id, measurement_identity),
    FOREIGN KEY(cycle_id) REFERENCES wire_wear_cycles(cycle_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS wire_wear_deletion_tombstones (
    tombstone_id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_group TEXT NOT NULL CHECK(line_group IN ('EAL', 'TML')),
    cycle_date TEXT NOT NULL,
    tension_length TEXT NOT NULL,
    deleted_at TEXT NOT NULL,
    source_package_id TEXT,
    UNIQUE(line_group, cycle_date, tension_length)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_wire_wear_cycle_identity
ON wire_wear_cycle_records(line_group, cycle_date, tension_length);
CREATE INDEX IF NOT EXISTS idx_wire_wear_cycle_tl_history
ON wire_wear_cycle_records(line_group, tension_length, cycle_date);
CREATE UNIQUE INDEX IF NOT EXISTS ux_wire_wear_parent_cycle
ON wire_wear_cycles(line_group, cycle_date);

INSERT OR IGNORE INTO system_metadata (key, value, description)
VALUES ('wire_wear_data_version', '0', 'Optimistic version for committed wear cycle data');
```

Implement migration `1.5` in `database.py`. Because stored values are test-only, it must drop the interim `wire_wear_cycle_records` table and its trigger/indexes, create the five final tables, initialize `wire_wear_data_version=0`, set `schema_version` and `last_migration` to `1.5`, and never call a backup helper.

- [ ] **Step 5: Verify GREEN and migration idempotency**

Run:

```powershell
python -m pytest tests/test_wear_records.py::test_complete_cycle_schema_is_normalized tests/test_database.py -q
```

Expected: PASS; creating the same `DatabaseManager` twice preserves schema and raises no migration error.

- [ ] **Step 6: Detect scope and commit**

Run `detect_changes(since="HEAD", scope="wear complete-cycle schema", depth=2)`, `git diff --check`, and `git status --short`. Stage only the three Task 3 files and commit:

```powershell
git add backend/app/core/schema.sql backend/app/core/database.py backend/tests/test_wear_records.py
git commit -m "feat: normalize wear complete-cycle schema"
```

---

### Task 4: Domain Types, Segment Detection, and Canonical Metadata

**Files:**
- Create: `backend/app/core/calculation/wear_cycle_types.py`
- Create: `backend/app/core/calculation/wear_cycle_metadata.py`
- Create: `backend/tests/test_wear_cycle_metadata.py`

- [ ] **Step 1: Run impact analysis**

Scan `MetadataManager.get_tension_length_lookup`, `MetadataManager._get_sheet_name_for_calc`, and `ChartDataRecord`. The new modules may call these symbols but must not modify them unless their reported risk is below HIGH.

- [ ] **Step 2: Write failing segment and metadata tests**

Cover filename aliases, ambiguous files, interval merge tolerance, gap rejection, and Siding:

```python
@pytest.mark.parametrize(
    ("line_group", "filename", "expected"),
    [
        ("EAL", "20260301_EAL_U2_FOT-TAP_Exception_Report.xlsx", "U2"),
        ("EAL", "20260409_EAL_D1A_HUH-ADM_Exception_Report.xlsx", "D1"),
        ("EAL", "20260301_EAL_UP_RAC_Exception_Report.xlsx", "RAC UP"),
        ("EAL", "20260306_EAL_DN_RAC_Exception_Report.xlsx", "RAC DN"),
        ("EAL", "20260302_EAL_S1_LOW_Exception_Report.xlsx", "LOW S1"),
        ("EAL", "20260419_EAL_DN_LMC_Exception_Report.xlsx", "LMC DN"),
        ("TML", "20260222_TML_D5_TUM-KSR_Exception_Report.xlsx", "D5"),
    ],
)
def test_detect_segment_uses_known_source_identity(line_group, filename, expected):
    assert detect_segment(line_group, filename, {}) == expected

def test_canonical_metadata_merges_overlap_and_cross_track_for_tl28():
    result = resolve_canonical_tl(
        "EAL",
        "28",
        [
            MetadataInterval("28", "DN", 111361.0, 111633.0, "RAC DN"),
            MetadataInterval("28", "DN", 111409.0, 112486.5, "RAC DN"),
            MetadataInterval("28", "UP", 112486.5, 112700.0, "U2"),
        ],
    )
    assert result == CanonicalTensionLength("EAL", "28", "Siding", 111361.0, 112700.0)

def test_canonical_metadata_rejects_true_gap():
    with pytest.raises(MetadataResolutionError, match="gap 0.02 m"):
        resolve_canonical_tl(
            "EAL",
            "28",
            [
                MetadataInterval("28", "DN", 111361.0, 111633.0, "D1"),
                MetadataInterval("28", "DN", 111633.02, 112486.5, "D2"),
            ],
        )
```

- [ ] **Step 3: Verify RED**

Run `python -m pytest tests/test_wear_cycle_metadata.py -q` from `backend`.

Expected: collection FAIL because the two new modules do not exist.

- [ ] **Step 4: Implement exact domain contracts**

Define these core values in `wear_cycle_types.py`:

```python
EXPECTED_SEGMENTS = {
    "EAL": ("U1", "U2", "U3", "D1", "D2", "D3", "LOW S1", "RAC UP", "RAC DN", "LMC UP", "LMC DN"),
    "TML": ("U1", "U2", "U3", "U4", "U5", "D1", "D2", "D3", "D4", "D5"),
}

@dataclass(frozen=True)
class BusinessKey:
    line_group: Literal["EAL", "TML"]
    cycle_date: str
    tension_length: str

@dataclass(frozen=True)
class CanonicalTensionLength:
    line_group: str
    tension_length: str
    track: Literal["UP", "DN", "Siding"]
    from_m: float
    to_m: float

@dataclass(frozen=True)
class MetadataInterval:
    tension_length: str
    track: Literal["UP", "DN"]
    from_m: float
    to_m: float
    sheet_name: str

@dataclass(frozen=True)
class RawWearMeasurement:
    acquisition_date: str
    line_group: str
    track: str
    task_no: str
    station_start: str
    station_end: str
    chainage: Decimal
    wear_min: float
    tension_length: str
    stable_measurement_id: str | None = None

@dataclass(frozen=True)
class ParsedWearSource:
    filename: str
    segment_name: str
    from_m: float
    to_m: float
    measurements: tuple[RawWearMeasurement, ...]

@dataclass(frozen=True)
class SegmentCoverage:
    segment_name: str
    is_present: bool
    coverage_percentage: float
    diagnostic_gaps: tuple[str, ...]
    source_file_names: tuple[str, ...]
    acquisition_dates: tuple[str, ...]

@dataclass(frozen=True)
class ConflictPreview:
    conflict_id: str
    measurement_identity: str
    source_values: tuple[tuple[str, float], ...]
    selected_wear_min: float
    is_accepted: bool

@dataclass(frozen=True)
class AggregatedWearRecord:
    key: BusinessKey
    track: Literal["UP", "DN", "Siding"]
    from_m: float
    to_m: float
    avg_wear_min: float
    wear_percentage: float
    measurement_sd: float | None
    has_data_conflict: bool
    conflict_ids: tuple[str, ...]
    source_lineage: tuple[str, ...]

@dataclass(frozen=True)
class CyclePreview:
    line_group: str
    cycle_date: str
    records: tuple[AggregatedWearRecord, ...]
    segments: tuple[SegmentCoverage, ...]
    conflicts: tuple[ConflictPreview, ...]
    unresolved: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    can_save: bool
    generated_at: str
```

Normalize line to uppercase, Cycle Date to ISO `YYYY-MM-DD`, and TL by trimmed case-preserving text with numeric forms normalized (`"28.0"` → `"28"`).

In `wear_cycle_metadata.py`, implement:

```python
def detect_segment(line_group: str, filename: str, source_fields: Mapping[str, str]) -> str:
    haystacks = [normalize_source_label(filename), *map(normalize_source_label, source_fields.values())]
    matches = {
        segment
        for segment, patterns in segment_patterns(normalize_line_group(line_group)).items()
        if any(pattern.search(value) for pattern in patterns for value in haystacks)
    }
    if len(matches) != 1:
        raise SegmentDetectionError(filename=filename, matches=tuple(sorted(matches)))
    return matches.pop()

def load_line_metadata(manager: MetadataManager, line_group: str) -> list[MetadataInterval]:
    intervals: list[MetadataInterval] = []
    for track, section, sheet_name in metadata_sources(normalize_line_group(line_group)):
        lookup = manager.get_tension_length_lookup(line_group, track, section)
        for row in lookup.to_dict("records"):
            for tension_length in split_tension_lengths(row["tension_length"]):
                intervals.append(MetadataInterval(
                    tension_length=normalize_tension_length(tension_length),
                    track=track,
                    from_m=float(row["from_m"]),
                    to_m=float(row["to_m"]),
                    sheet_name=sheet_name,
                ))
    return sorted(intervals, key=lambda item: (natural_key(item.tension_length), item.from_m, item.to_m))

def resolve_canonical_tl(
    line_group: str,
    tension_length: str,
    intervals: Sequence[MetadataInterval],
    gap_tolerance_m: float = 0.01,
) -> CanonicalTensionLength:
    normalized_tl = normalize_tension_length(tension_length)
    matches = sorted(
        (item for item in intervals if item.tension_length == normalized_tl),
        key=lambda item: (item.from_m, item.to_m),
    )
    if not matches:
        raise MetadataResolutionError(f"unknown TL {normalized_tl}")
    merged_from, merged_to = matches[0].from_m, matches[0].to_m
    tracks = {matches[0].track}
    for item in matches[1:]:
        gap = item.from_m - merged_to
        if gap > gap_tolerance_m:
            raise MetadataResolutionError(f"TL {normalized_tl} gap {gap:.2f} m")
        merged_to = max(merged_to, item.to_m)
        tracks.add(item.track)
    track = "Siding" if tracks == {"UP", "DN"} else next(iter(tracks))
    return CanonicalTensionLength(line_group, normalized_tl, track, merged_from, merged_to)
```

Segment detection checks filename first, then normalized `task_no`, `station_start`, and `station_end`. It accepts `U1A/D1A` as `U1/D1`; recognizes both `UP_RAC` and `RAC_UP`; maps `S1_LOW`, `LOW_S1`, and `UP_LOW` to `LOW S1`; and rejects zero or multiple matches. It never assigns ordinal segments by file ordering or chainage. `ParsedWearSource.from_m/to_m` are the minimum and maximum chainage of all structurally valid parsed measurements before TL-resolution filtering, preserving the uploaded file's complete range for coverage.

Coverage uses each detected source file's complete `from_m..to_m` range without clipping displayed canonical TL ranges. For a present segment, denominator is the set of canonical TLs whose compatible-track metadata intervals intersect the union of its source ranges; numerator is the subset with at least one accepted measurement in that segment. Return `round(100 * numerator / denominator, 2)`. A missing segment returns `0.0` and a missing-segment diagnostic. A present segment with an empty denominator returns `0.0` and a blocking metadata diagnostic. This makes coverage metadata-based while allowing overlapping source ranges such as `[99999, 111999]` and `[111000, 139999]`.

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
python -m pytest tests/test_wear_cycle_metadata.py tests/test_metadata_tension_length.py tests/test_metadata_manager.py -q
```

Expected: PASS, including overlap/touch merge and `0.02 m` rejection.

- [ ] **Step 6: Detect scope and commit**

Run codebase-memory `detect_changes`, `git diff --check`, then stage only Task 4 files:

```powershell
git add backend/app/core/calculation/wear_cycle_types.py backend/app/core/calculation/wear_cycle_metadata.py backend/tests/test_wear_cycle_metadata.py
git commit -m "feat: resolve canonical wear cycle metadata"
```

---

### Task 5: Complete-Cycle Aggregation Pipeline

**Files:**
- Create: `backend/app/core/calculation/wear_cycle_aggregation.py`
- Modify: `backend/app/core/calculation/wear_calculator.py`
- Create: `backend/tests/test_wear_cycle_aggregation.py`
- Modify: `backend/tests/test_wear_calculator.py`

- [ ] **Step 1: Run impact analysis**

Scan `calculate_average_wear`, `calculate_wear_percentage`, `ChartDataRecord`, and `WearResult`. If `calculate_average_wear` reports HIGH/CRITICAL, stop; otherwise record all API/test callers before replacing its user-facing aggregation path.

- [ ] **Step 2: Write failing aggregation tests**

Use two files whose full ranges overlap and whose TL28 metadata interval is shared. Assert source file range never clips canonical metadata:

```python
def test_preview_merges_tl_across_overlapping_files_and_uses_canonical_range():
    preview = build_cycle_preview(
        line_group="EAL",
        requested_cycle_date="2026-05-28",
        sources=[
            source("EAL_U2", 99999.0, 111999.0, measurement("28", 111361.0, 11.8)),
            source("EAL_D1", 111000.0, 139999.0, measurement("28", 112486.5, 11.4)),
        ],
        metadata=[
            MetadataInterval("28", "UP", 111361.0, 111633.0, "U2"),
            MetadataInterval("28", "DN", 111409.0, 112486.5, "D1"),
        ],
        accepted_conflict_ids=set(),
    )
    assert len(preview.records) == 1
    assert preview.records[0].track == "Siding"
    assert (preview.records[0].from_m, preview.records[0].to_m) == (111361.0, 112486.5)
    assert preview.records[0].avg_wear_min == pytest.approx(11.6)

def test_conflicting_identity_previews_lower_value_and_blocks_save():
    preview = build_cycle_preview(
        line_group="EAL",
        requested_cycle_date=None,
        sources=[
            source("a/EAL_U2.xlsx", measurement("28", 111500.0, 12.1, task_no="9")),
            source("b/EAL_U2.xlsx", measurement("28", 111500.0, 11.7, task_no="9")),
        ],
        metadata=metadata_for_tl28(),
        accepted_conflict_ids=set(),
    )
    assert preview.records[0].avg_wear_min == 11.7
    assert preview.conflicts[0].values == (11.7, 12.1)
    assert preview.can_save is False
    assert "conflict_not_accepted" in preview.blocking_reasons
```

Also test exact duplicates count once, different acquisition sessions remain distinct, latest acquisition date default, user Cycle Date override, all expected-segment presence, advisory coverage, nullable single-value SD, unresolved metadata, and natural canonical From order.

- [ ] **Step 3: Verify RED**

Run `python -m pytest tests/test_wear_cycle_aggregation.py -q`.

Expected: collection FAIL because `build_cycle_preview` does not exist.

- [ ] **Step 4: Implement deterministic preview**

Define the fallback measurement identity exactly as normalized:

```python
identity = (
    line_group,
    segment_name,
    track,
    acquisition_date,
    task_no,
    station_start,
    station_end,
    decimal_chainage,
)
```

Use a stable source measurement/session ID when present. Filename is lineage, never identity. For equal identities: one equal value is accepted once; unequal values form one conflict with sorted `(source_file, wear_min)` pairs. The selected preview value is `min(values)`. A conflict is resolved only if its deterministic SHA-256 ID is present in `accepted_conflict_ids`.

Implement these public functions:

```python
def build_cycle_preview(
    *,
    line_group: str,
    requested_cycle_date: str | None,
    sources: Sequence[ParsedWearSource],
    metadata: Sequence[MetadataInterval],
    accepted_conflict_ids: set[str],
) -> CyclePreview:
    normalized_line = normalize_line_group(line_group)
    parsed_sources = tuple(
        resolve_source(normalized_line, source, metadata) for source in sources
    )
    observations, raw_conflicts = deduplicate_measurements(parsed_sources)
    conflicts = tuple(
        replace(conflict, is_accepted=conflict.conflict_id in accepted_conflict_ids)
        for conflict in raw_conflicts
    )
    records, unresolved = aggregate_tension_lengths(
        normalized_line,
        requested_cycle_date,
        observations,
        metadata,
    )
    segments = build_segment_coverage(normalized_line, parsed_sources, observations, metadata)
    cycle_date = resolve_cycle_date(requested_cycle_date, parsed_sources)
    blocking_reasons = collect_blocking_reasons(
        cycle_date=cycle_date,
        segments=segments,
        conflicts=conflicts,
        accepted_conflict_ids=accepted_conflict_ids,
        unresolved=unresolved,
    )
    return CyclePreview(
        line_group=normalized_line,
        cycle_date=cycle_date,
        records=tuple(sorted(records, key=lambda row: (row.from_m, natural_key(row.tension_length)))),
        segments=segments,
        conflicts=conflicts,
        unresolved=unresolved,
        blocking_reasons=blocking_reasons,
        can_save=not blocking_reasons,
        generated_at=utc_now_iso(),
    )

def preview_digest(preview: CyclePreview) -> str:
    payload = asdict(preview)
    payload.pop("generated_at", None)
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
```

Aggregate accepted values by normalized TL across all sources and dates. Use canonical Track/From/To, arithmetic mean, sample SD with `statistics.stdev` for two or more values, otherwise `None`, and backend `calculate_wear_percentage`. `can_save` requires valid Cycle Date, every expected segment present, no unknown source segment, no unresolved TL, and every conflict accepted. Coverage percentage never changes `can_save` when the segment has at least one valid measurement.

Keep `calculate_average_wear` as a compatibility adapter that delegates to shared mean/SD/wear helpers; do not let it derive displayed From/To from uploaded ranges.

- [ ] **Step 5: Verify GREEN and parser performance**

Run:

```powershell
python -m pytest tests/test_wear_cycle_aggregation.py tests/test_wear_calculator.py tests/test_calculation.py -q
```

Expected: PASS. The existing large-input test remains below its current performance threshold and no duplicate file doubles the sample count.

- [ ] **Step 6: Detect scope and commit**

Run `detect_changes`, `git diff --check`, and stage only Task 5 files:

```powershell
git add backend/app/core/calculation/wear_cycle_aggregation.py backend/app/core/calculation/wear_calculator.py backend/tests/test_wear_cycle_aggregation.py backend/tests/test_wear_calculator.py
git commit -m "feat: aggregate complete wire wear cycles"
```

---

### Task 6: Cycle Repository and Atomic Staged Changes

**Files:**
- Create: `backend/app/core/calculation/wear_cycle_repository.py`
- Modify: `backend/app/core/calculation/wear_records.py`
- Modify: `backend/tests/test_wear_records.py`

- [ ] **Step 1: Run impact analysis**

Scan `save_wire_wear_cycle_records`, `query_wire_wear_cycle_records`, `recalculate_cycle_sd_for_tension_length`, `update_wire_wear_record`, and `delete_wire_wear_record`. Report legacy and aggregate callers. The implementation must remove all user-facing calls that overwrite stored SD history.

- [ ] **Step 2: Write failing repository tests**

Add tests for one-transaction cycle save, rollback, manual metadata resolution, optimistic concurrency, cell/row tombstones, and no SD overwrite:

```python
def test_apply_change_set_rolls_back_all_changes_on_stale_record(conn, seeded_cycle):
    before = list_cycle_records(conn, line_group="EAL")
    request = ChangeSet(
        operations=(
            AddOperation(BusinessKey("EAL", "2026-06-01", "28"), avg_wear_min=11.4),
            EditOperation(
                BusinessKey("EAL", "2026-05-28", "25"),
                avg_wear_min=11.2,
                expected_updated_at="2000-01-01T00:00:00Z",
            ),
        )
    )
    with pytest.raises(StaleRecordError):
        apply_change_set(conn, request, metadata_catalog())
    assert list_cycle_records(conn, line_group="EAL") == before

def test_delete_row_creates_one_tombstone_per_business_key(conn, seeded_cycle):
    result = apply_change_set(
        conn,
        ChangeSet((DeleteRowOperation("EAL", "2026-05-28"),)),
        metadata_catalog(),
    )
    assert result.deleted == 8
    assert conn.execute(
        "SELECT COUNT(*) FROM wire_wear_deletion_tombstones WHERE line_group='EAL' AND cycle_date='2026-05-28'"
    ).fetchone()[0] == 8
```

- [ ] **Step 3: Verify RED**

Run the new named tests with `python -m pytest tests/test_wear_records.py -k "change_set or tombstone or complete_cycle" -q`.

Expected: FAIL because repository types and atomic operations are absent.

- [ ] **Step 4: Implement repository transaction boundaries**

Define the operation union before the repository functions:

```python
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
    cycle_date: str

ChangeOperation = AddOperation | EditOperation | DeleteCellOperation | DeleteRowOperation

@dataclass(frozen=True)
class ChangeSet:
    operations: tuple[ChangeOperation, ...]

@dataclass(frozen=True)
class ChangeSetResult:
    added: int
    edited: int
    deleted: int
    data_version: int
```

Expose:

```python
def save_analysis_cycle(conn: sqlite3.Connection, preview: CyclePreview) -> SavedCycle:
    if not preview.can_save:
        raise IncompleteCycleError(preview.blocking_reasons)
    conn.execute("BEGIN IMMEDIATE")
    try:
        cycle_id = insert_cycle_parent(conn, preview)
        insert_cycle_segments(conn, cycle_id, preview.segments)
        insert_cycle_records(conn, cycle_id, preview.records)
        insert_conflict_decisions(conn, cycle_id, preview.conflicts)
        bump_data_version(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_saved_cycle(conn, cycle_id)

def apply_change_set(
    conn: sqlite3.Connection,
    change_set: ChangeSet,
    metadata: Sequence[MetadataInterval],
    now: datetime | None = None,
) -> ChangeSetResult:
    timestamp = now or datetime.now(timezone.utc)
    counters = ChangeCounters()
    conn.execute("BEGIN IMMEDIATE")
    try:
        for operation_index, operation in enumerate(change_set.operations):
            try:
                counters = apply_operation(conn, operation, metadata, timestamp, counters)
            except Exception as exc:
                raise ChangeOperationError(operation_index, str(exc)) from exc
        data_version = bump_data_version(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return ChangeSetResult(
        added=counters.added,
        edited=counters.edited,
        deleted=counters.deleted,
        data_version=data_version,
    )

def build_workbench(
    conn: sqlite3.Connection,
    *,
    line_group: str,
    tension_length_query: str = "",
    date_from: str | None = None,
    date_to: str | None = None,
) -> WorkbenchSnapshot:
    records = query_committed_records(
        conn,
        line_group=line_group,
        tension_length_query=tension_length_query,
        date_from=date_from,
        date_to=date_to,
    )
    columns = canonical_tl_columns(records)
    return WorkbenchSnapshot(
        line_group=line_group,
        columns=columns,
        matrix_rows=build_matrix_rows(records, columns),
        latest_summary=build_latest_summary(records, columns),
        data_version=current_data_version(conn),
    )
```

Rules:

- Save rejects `can_save=False` and duplicate business keys with `409`-mapped domain errors.
- Saved conflict decisions copy every source filename/value and selected lower value from the preview and stamp `accepted_at` with the cycle transaction timestamp.
- Manual Add/Edit accepts only Line, Cycle Date, TL, Avg Wear Min; resolves Track/From/To from canonical metadata; recalculates precise Wear %; stores `measurement_sd=NULL`.
- A new manual-only parent cycle is `incomplete`; editing/adding to an existing complete cycle preserves `complete`. Queries for latest complete uploaded cycle filter `completeness_state='complete'`, while historical/trend/dashboard/projection include every committed manual and uploaded record.
- Edit requires matching `expected_updated_at`. Delete Cell and each expanded Delete Row key create/upsert a tombstone with the transaction timestamp.
- Add/Edit newer than an existing tombstone removes that tombstone; equality is not newer.
- After Delete Cell/Delete Row, remove a parent cycle only when it has no remaining records; tombstones remain independent and are never cascade-deleted.
- Historical SD is computed in workbench output from all committed `avg_wear_min` values for the same Line+TL and is never written into `measurement_sd`.
- `current_data_version` and `bump_data_version` read/update only `system_metadata.wire_wear_data_version`; one successful cycle/change transaction increments it exactly once.
- One failed operation rolls back records, parent cycles, and tombstones and returns the failing operation index.

Reduce `wear_records.py` to compatibility wrappers for still-tested legacy `wire_wear_records`; new API code imports the repository directly. Deprecate `recalculate_cycle_sd_for_tension_length` and ensure no aggregate save/update calls it.

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
python -m pytest tests/test_wear_records.py tests/test_wire_wear_sync.py -q
```

Expected: PASS; rollback test leaves byte-for-byte equivalent query rows and manual SD remains null.

- [ ] **Step 6: Detect scope and commit**

Run `detect_changes`, `git diff --check`, stage only Task 6 files, and commit:

```powershell
git add backend/app/core/calculation/wear_cycle_repository.py backend/app/core/calculation/wear_records.py backend/tests/test_wear_records.py
git commit -m "feat: apply atomic wear cycle changes"
```

---

### Task 7: Complete-Cycle Upload and Records API

**Files:**
- Modify: `backend/app/api/endpoints/calculation.py`
- Modify: `backend/app/api/endpoints/wear_records.py`
- Modify: `backend/tests/test_calculation_api.py`
- Modify: `backend/tests/test_wear_records_api.py`

- [ ] **Step 1: Run impact analysis**

Scan `upload_wear`, `save_records`, `workbench`, `add_manual_records`, `update_record`, and `delete_record`. Trace inbound routes and frontend callers; stop if any edit is HIGH/CRITICAL.

- [ ] **Step 2: Write failing API tests**

Use multipart upload and assert the final response shape:

```python
def test_upload_wear_returns_complete_cycle_preview(client, wear_files, metadata_config):
    response = client.post(
        "/api/calculation/wear",
        files=wear_files,
        data={"line_group": "EAL", "cycle_date": "2026-05-28", "accepted_conflict_ids": "[]"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cycle_date"] == "2026-05-28"
    assert set(body) >= {
        "records", "segments", "conflicts", "blocking_reasons", "can_save",
        "preview_digest", "expected_data_version",
    }
    assert all(row["line_group"] == "EAL" for row in body["records"])

def test_changes_endpoint_returns_409_for_stale_timestamp(client, seeded_cycle):
    response = client.post(
        "/api/calculation/wear-records/changes",
        json={"operations": [{
            "kind": "edit",
            "key": {"line_group": "EAL", "cycle_date": "2026-05-28", "tension_length": "28"},
            "avg_wear_min": 11.4,
            "expected_updated_at": "2000-01-01T00:00:00Z",
        }]},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["operation_index"] == 0
```

Also test invalid Cycle Date and unresolved segment as `422`, unaccepted conflict save as `422`, duplicate cycle as `409`, successful cycle save, metadata preview for manual Add/Edit, and Delete Row expansion.

- [ ] **Step 3: Verify RED**

Run:

```powershell
python -m pytest tests/test_calculation_api.py -k complete_cycle -q
python -m pytest tests/test_wear_records_api.py -k "cycle or changes or workbench" -q
```

Expected: FAIL because existing upload and CRUD contracts use track/section and immediate row mutation.

- [ ] **Step 4: Implement request/response models and routes**

`POST /api/calculation/wear` accepts `files`, required `line_group`, optional `cycle_date`, and JSON-string `accepted_conflict_ids`. It parses every file independently, preserves filename/source fields, detects segments, builds one preview, and returns the current `expected_data_version`. Parse/metadata errors return `422` diagnostics rather than silently discarding rows.

Replace user-facing records routes with:

```text
POST /api/calculation/wear-records/cycles
POST /api/calculation/wear-records/changes
GET  /api/calculation/wear-records/workbench
GET  /api/calculation/wear-records/metadata-preview
```

Cycle save is multipart and accepts the same retained source files, Line, Cycle Date, accepted conflict IDs, expected `preview_digest`, and expected wear data version. The backend reparses the files, rebuilds the canonical preview, compares its digest, and then calls `save_analysis_cycle`; it never trusts client-supplied aggregate rows, coverage, or conflict audit. Changes uses a discriminated `kind` field (`add`, `edit`, `delete_cell`, `delete_row`). Workbench returns matrix rows, canonical TL columns, latest summary, catalog, and `wire_wear_data_version`.

Map domain errors consistently: invalid input/unresolved metadata `422`; duplicate/stale timestamp/digest mismatch `409`; unexpected database failure `500` after rollback.

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
python -m pytest tests/test_calculation_api.py tests/test_wear_records_api.py tests/test_calculation_routes.py -q
```

Expected: PASS; legacy combined/trend/stagger upload routes remain unchanged.

- [ ] **Step 6: Detect scope and commit**

Run `detect_changes`, `git diff --check`, stage only Task 7 files, and commit:

```powershell
git add backend/app/api/endpoints/calculation.py backend/app/api/endpoints/wear_records.py backend/tests/test_calculation_api.py backend/tests/test_wear_records_api.py
git commit -m "feat: expose complete wear cycle APIs"
```

---

### Task 8: Historical Analytics, Dashboard, and Projection

**Files:**
- Create: `backend/app/core/calculation/wear_cycle_analytics.py`
- Create: `backend/tests/test_wear_cycle_analytics.py`
- Modify: `backend/app/core/calculation/wear_cycle_repository.py`
- Modify: `backend/app/api/endpoints/wear_records.py`
- Modify: `backend/tests/test_wear_records_api.py`

- [ ] **Step 1: Run impact analysis**

Scan existing `_rate_rows`, `build_dashboard_summary`, `build_projection_summary`, repository `build_workbench`, and API `dashboard`/`projection`. Record their record-query dependencies before replacement.

- [ ] **Step 2: Write failing analytics tests**

Test elapsed-year OLS across all history, two-date eligibility, non-positive rate, ranking, and synchronized projection buckets:

```python
def test_fit_trend_uses_all_dates_and_returns_quality_fields():
    trend = fit_tl_trend([
        point("2024-01-01", 12.8),
        point("2025-01-01", 12.2),
        point("2026-07-01", 11.0),
    ])
    assert trend.status == "eligible"
    assert trend.observation_count == 3
    assert trend.mm_per_year > 0
    assert 0 <= trend.r_squared <= 1

def test_projection_uses_same_rows_for_chart_and_expansion(seeded_history):
    projection = build_projection(seeded_history, threshold_mm=10.2, as_of=date(2026, 7, 10))
    for line in ("EAL", "TML"):
        assert sum(bucket.count for bucket in projection.lines[line].buckets) == sum(
            len(bucket.records) for bucket in projection.lines[line].buckets
        )
    assert projection.threshold_wear_percentage == pytest.approx(
        calculate_wear_percentage(10.2)
    )
```

Dashboard tests assert Max descending, Min ascending but strictly positive, Current Wear highest precise Wear %, five-row cap, and Line/TL labels. Projection tests assert already-at-threshold, insufficient, non-positive, next 30 complete calendar years, crossing date, and shared threshold for both lines.

- [ ] **Step 3: Verify RED**

Run `python -m pytest tests/test_wear_cycle_analytics.py -q`.

Expected: collection FAIL because the analytics module does not exist.

- [ ] **Step 4: Implement one analytics service**

Implement:

```python
def fit_tl_trend(points: Sequence[HistoryPoint]) -> TrendResult:
    dates = sorted({point.cycle_date for point in points})
    if len(dates) < 2:
        return TrendResult(status="insufficient_data", observation_count=len(dates))
    x = np.array([(value - dates[0]).days / 365.2425 for value in dates], dtype=float)
    y = np.array([mean_for_date(points, value) for value in dates], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 if ss_tot == 0.0 else 1.0 - (ss_res / ss_tot)
    mm_per_year = -float(slope)
    status = "eligible" if mm_per_year > 0 else "non_positive_rate"
    return TrendResult(
        status=status,
        observation_count=len(dates),
        thickness_slope=float(slope),
        thickness_intercept=float(intercept),
        mm_per_year=mm_per_year if mm_per_year > 0 else None,
        percent_per_year=wear_rate_percentage(intercept, slope) if mm_per_year > 0 else None,
        r_squared=r_squared,
        first_cycle_date=dates[0],
        latest_cycle_date=dates[-1],
    )

def build_dashboard(records: Sequence[CommittedRecord], line_group: str | None) -> DashboardResult:
    selected = filter_line(records, line_group)
    rows = [dashboard_row(group) for group in group_history_by_tl(selected).values()]
    eligible = [row for row in rows if row.mm_per_year is not None and row.mm_per_year > 0]
    return DashboardResult(
        max_wear_rate=tuple(sorted(eligible, key=lambda row: row.mm_per_year, reverse=True)[:5]),
        min_positive_wear_rate=tuple(sorted(eligible, key=lambda row: row.mm_per_year)[:5]),
        current_wear=tuple(sorted(rows, key=lambda row: row.latest_wear_percentage, reverse=True)[:5]),
    )

def build_projection(
    records: Sequence[CommittedRecord],
    threshold_mm: float,
    as_of: date,
    horizon_years: int = 30,
) -> ProjectionResult:
    validate_threshold_mm(threshold_mm)
    evaluated = tuple(
        project_tl(group, threshold_mm, as_of, horizon_years)
        for group in group_history_by_line_and_tl(records).values()
    )
    return ProjectionResult(
        threshold_mm=threshold_mm,
        threshold_wear_percentage=calculate_wear_percentage(threshold_mm),
        lines={
            line: build_line_projection(line, evaluated, as_of, horizon_years)
            for line in ("EAL", "TML")
        },
    )
```

`mm_per_year = -slope`; `percent_per_year` uses the same fitted thickness progression and backend wear formula; R² is `1 - ss_res/ss_tot`, with `1.0` for exact constant response only when slope is zero. Non-positive loss returns `non_positive_rate` and no crossing. Projection solves `(threshold_mm - intercept) / slope`, converts elapsed years to a date, then buckets by calendar year only when it lies in the next 30 complete years after `as_of.year`.

Update GET `/dashboard?line_group=ALL|EAL|TML` and GET `/projection?threshold_mm=10.2`. Validate threshold as positive and inside the backend geometry range. Responses return precise values; no provisional/established category exists.

Extend repository `build_workbench` latest-summary rows with the same `fit_tl_trend` result: Wear Rate (%/year), Wear Rate (mm/year), observation count, R-squared, and trend status. Keep Historical SD derived independently from committed thickness values.

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
python -m pytest tests/test_wear_cycle_analytics.py tests/test_wear_records_api.py -k "dashboard or projection or trend or workbench" -q
```

Expected: PASS and chart counts equal expanded record counts.

- [ ] **Step 6: Detect scope and commit**

Run `detect_changes`, `git diff --check`, stage only Task 8 files, and commit:

```powershell
git add backend/app/core/calculation/wear_cycle_analytics.py backend/tests/test_wear_cycle_analytics.py backend/app/core/calculation/wear_cycle_repository.py backend/app/api/endpoints/wear_records.py backend/tests/test_wear_records_api.py
git commit -m "feat: add wear cycle analytics"
```

---

### Task 9: Excel Report and Two-Phase JSON Sync

**Files:**
- Create: `backend/app/core/calculation/wear_cycle_io.py`
- Create: `backend/tests/test_wear_cycle_io.py`
- Modify: `backend/app/api/endpoints/wear_records.py`
- Modify: `backend/tests/test_wear_records_api.py`
- Modify: `backend/tests/test_wire_wear_sync.py`

- [ ] **Step 1: Run impact analysis**

Scan `build_workbench_excel`, `build_wire_wear_sync_package`, `import_wire_wear_sync_package`, `export_records`, `export_sync_package`, and `import_sync_package`. Report all backup-helper callers; the new sync flow must not call `_create_sqlite_backup`.

- [ ] **Step 2: Write failing workbook and sync tests**

```python
def test_excel_report_contains_four_approved_sheets(conn, seeded_cycles):
    workbook = load_workbook(BytesIO(build_excel_report(conn, line_group="EAL")), data_only=True)
    assert workbook.sheetnames == ["Wear Records", "Cycle Coverage", "Conflict Audit", "Workbook Info"]
    assert [cell.value for cell in workbook["Wear Records"][1]] == [
        "Cycle Date", "Line", "Track", "Tension Length", "From (m)", "To (m)",
        "Avg Wear Min", "Wear %", "Measurement SD",
    ]

def test_tombstone_wins_equal_timestamp_and_prevents_resurrection(conn, seeded_cycles):
    package = package_with_record_and_tombstone(
        key=("EAL", "2026-05-28", "28"),
        timestamp="2026-07-10T12:00:00Z",
    )
    preview = preview_sync_import(conn, package, metadata_catalog())
    assert preview.actions[0].action == "delete"
    apply_sync_import(
        conn,
        source_package=preview.source_package,
        preview_digest=preview.preview_digest,
        expected_data_version=preview.expected_data_version,
        metadata=metadata_catalog(),
    )
    assert find_record(conn, "EAL", "2026-05-28", "28") is None
```

Also test record-newer-than-tombstone recreation, duplicate package keys, stale data version, unknown TL, metadata fingerprint advisory/blocking behavior, precise Wear % recalculation, atomic rollback, and no `.bak` file.

- [ ] **Step 3: Verify RED**

Run:

```powershell
python -m pytest tests/test_wear_cycle_io.py tests/test_wire_wear_sync.py -q
```

Expected: FAIL because the current workbook/sync use legacy rows, one-phase import, and backup creation.

- [ ] **Step 4: Implement Excel and `wear-cycle-v1`**

Excel `Wear Records` uses canonical From ascending within cycle and precise numeric cells. `Cycle Coverage` has one row per expected segment. `Conflict Audit` includes measurement identity, every source file/value pair, selected lower value, and accepted time. `Workbook Info` includes schema `wear-cycle-report-v1`, export timestamp, application version, and metadata fingerprint. No Excel import endpoint exists.

Emit this JSON shape:

```json
{
  "schema": "wear-cycle-v1",
  "package_id": "uuid",
  "exported_at": "2026-07-10T12:00:00Z",
  "source_workstation": "TOV640-01",
  "metadata_fingerprint": {"EAL": "sha256", "TML": "sha256"},
  "cycles": [],
  "records": [],
  "segments": [],
  "conflict_decisions": [],
  "tombstones": []
}
```

Implement `build_sync_package`, `preview_sync_import`, and `apply_sync_import`. Preview validates the full package and returns the canonical source package, per-key Create/Update/Delete/Unchanged/Conflict/Error actions, `expected_data_version`, and a deterministic `preview_digest`. Apply receives the source package, digest, and expected version, reruns validation against current metadata/data, rejects a changed digest or stale version with `409`, and commits all actions atomically. No server-side preview cache is required. Later timestamp wins; equal timestamp tombstone wins. Local metadata always supplies Track/From/To and recalculated Wear %.

Expose:

```text
GET  /api/calculation/wear-records/export.xlsx?line_group=EAL&cycle_date=2026-05-28
GET  /api/calculation/wear-records/sync.json
POST /api/calculation/wear-records/sync/preview
POST /api/calculation/wear-records/sync/apply
```

Excel query filters are optional; when both are supplied the report represents the saved Analysis cycle exactly. Legacy package schemas return `422` with supported schema `wear-cycle-v1`. Apply returns `409` for stale data version. Remove backup creation from all new sync paths.

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
python -m pytest tests/test_wear_cycle_io.py tests/test_wire_wear_sync.py tests/test_wear_records_api.py -k "export or sync or workbook" -q
```

Expected: PASS; no backup path is returned or created.

- [ ] **Step 6: Detect scope and commit**

Run `detect_changes`, `git diff --check`, stage only Task 9 files, and commit:

```powershell
git add backend/app/core/calculation/wear_cycle_io.py backend/tests/test_wear_cycle_io.py backend/app/api/endpoints/wear_records.py backend/tests/test_wear_records_api.py backend/tests/test_wire_wear_sync.py
git commit -m "feat: add wear cycle report and sync"
```

---

### Task 10: Frontend Contracts, API Client, and Staged Stores

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/store/useWearStore.ts`
- Modify: `frontend/src/store/useWearRecordsStore.ts`
- Modify: `frontend/src/api/__tests__/calculationApi.test.ts`
- Modify: `frontend/src/store/__tests__/useWearStore.test.ts`
- Modify: `frontend/src/store/__tests__/useWearRecordsStore.test.ts`
- Modify: `frontend/src/store/__tests__/useWearRecordsStore.workbench.test.ts`

- [ ] **Step 1: Run impact analysis**

Scan `uploadWearFiles`, all `*WireWear*` client functions, `useWearStore`, and `useWearRecordsStore`. Trace view/component consumers before changing signatures.

- [ ] **Step 2: Write failing store tests**

```typescript
it('stages delete row without calling the API until saveChanges', async () => {
  const api = vi.mocked(client.applyWireWearChanges)
  useWearRecordsStore.getState().hydrate(workbenchFixture)
  useWearRecordsStore.getState().stageDeleteRow('EAL', '2026-05-28')

  expect(api).not.toHaveBeenCalled()
  expect(useWearRecordsStore.getState().pendingChanges).toEqual([
    { kind: 'delete_row', lineGroup: 'EAL', cycleDate: '2026-05-28' },
  ])

  await useWearRecordsStore.getState().saveChanges()
  expect(api).toHaveBeenCalledTimes(1)
})

it('re-analyzes with accepted conflicts and editable cycle date', async () => {
  const store = useWearStore.getState()
  store.setCycleDate('2026-05-28')
  store.acceptConflict('conflict-28')
  await store.analyze()
  expect(client.uploadWearFiles).toHaveBeenCalledWith(
    expect.any(Array),
    expect.objectContaining({ cycleDate: '2026-05-28', acceptedConflictIds: ['conflict-28'] }),
  )
})
```

Test Discard restores committed snapshot, failed Save retains pending changes/errors, file removal clears invalid conflict decisions, and `hasPendingChanges` drives the guard.
Test change coalescing: Add→Edit becomes one Add with the final value, Add→Delete removes the pending operation, Edit→Delete becomes Delete Cell, and Delete Row supersedes every pending cell operation for that Line+Cycle Date.

- [ ] **Step 3: Verify RED**

Run from `frontend`:

```powershell
npm test -- --run src/store/__tests__/useWearStore.test.ts src/store/__tests__/useWearRecordsStore.test.ts src/store/__tests__/useWearRecordsStore.workbench.test.ts
```

Expected: FAIL because current store immediately mutates backend rows and upload lacks Cycle Date/conflict inputs.

- [ ] **Step 4: Implement exact TypeScript contracts**

Define camelCase UI types with explicit API mappers; do not leak mixed snake_case into components:

```typescript
export type WearLine = 'EAL' | 'TML'
export type WearTrack = 'UP' | 'DN' | 'Siding'
export interface WearBusinessKey {
  lineGroup: WearLine
  cycleDate: string
  tensionLength: string
}
export interface WearCycleRecord {
  key: WearBusinessKey
  track: WearTrack
  fromM: number
  toM: number
  avgWearMin: number
  wearPercentage: number
  measurementSd: number | null
  hasDataConflict: boolean
  conflictIds: string[]
  updatedAt: string | null
}

export type WearRecordChange =
  | { kind: 'add'; key: WearBusinessKey; avgWearMin: number }
  | { kind: 'edit'; key: WearBusinessKey; avgWearMin: number; expectedUpdatedAt: string }
  | { kind: 'delete_cell'; key: WearBusinessKey; expectedUpdatedAt: string }
  | { kind: 'delete_row'; lineGroup: WearLine; cycleDate: string }
```

Client methods must match Task 7–9 routes: preview upload, multipart save cycle with retained files and preview digest, apply changes, metadata preview, workbench, dashboard, projection, Excel blob, sync JSON blob, sync preview, sync apply.

`useWearStore` owns files, line, editable Cycle Date, preview, accepted conflict IDs, analyzing/saving/error. Removing a file removes any accepted conflict whose audit no longer exists after re-analysis. `useWearRecordsStore` owns `committedSnapshot`, coalesced `pendingChanges`, derived optimistic matrix, change summary, commit errors, and guard decision. Apply the tested Add/Edit/Delete coalescing rules whenever a pending operation is staged. No Add/Edit/Delete method performs HTTP before `saveChanges`.

- [ ] **Step 5: Verify GREEN and type build**

Run:

```powershell
npm test -- --run src/api/__tests__/calculationApi.test.ts src/store/__tests__/useWearStore.test.ts src/store/__tests__/useWearRecordsStore.test.ts src/store/__tests__/useWearRecordsStore.workbench.test.ts
npm run build
```

Expected: PASS and TypeScript reports no contract mismatch.

- [ ] **Step 6: Detect scope and commit**

Run `detect_changes`, `git diff --check`, stage only Task 10 files, and commit:

```powershell
git add frontend/src/types/api.ts frontend/src/api/client.ts frontend/src/store/useWearStore.ts frontend/src/store/useWearRecordsStore.ts frontend/src/api/__tests__/calculationApi.test.ts frontend/src/store/__tests__/useWearStore.test.ts frontend/src/store/__tests__/useWearRecordsStore.test.ts frontend/src/store/__tests__/useWearRecordsStore.workbench.test.ts
git commit -m "feat: stage wear cycle frontend changes"
```

---

### Task 11: Analysis Complete-Cycle UI

**Files:**
- Modify: `frontend/src/components/Calculation/WearResultTable.tsx`
- Modify: `frontend/src/components/Calculation/wearAnalysisPresentation.ts`
- Create: `frontend/src/components/Calculation/WearCycleStatusPanel.tsx`
- Create: `frontend/src/components/Calculation/WearAnalysisCharts.tsx`
- Modify: `frontend/src/views/WearCalculatorView.tsx`
- Modify: `frontend/src/components/Calculation/__tests__/WearResultTable.test.tsx`
- Modify: `frontend/src/components/Calculation/__tests__/wearAnalysisPresentation.test.ts`
- Create: `frontend/src/components/Calculation/__tests__/WearCycleStatusPanel.test.tsx`
- Modify: `frontend/src/views/__tests__/WearCalculatorView.test.tsx`

- [ ] **Step 1: Run impact analysis**

Scan `WearResultTable`, presentation helpers, `WearCalculatorView`, and `handleSaveWearRecords`. Trace store and child-component callers. Delete split-by-track/section payload construction only after risk is below HIGH.

- [ ] **Step 2: Write failing component tests**

Test approved columns/default order, same-row chart data, exact filters, conflict controls, and Cycle Date:

```typescript
it('renders the approved aggregate columns and rounds wear percent only in the cell', () => {
  render(<WearResultTable rows={[recordFixture({ wearPercentage: 18.49 })]} />)
  expect(screen.getAllByRole('columnheader').map(node => node.textContent)).toEqual([
    'Cycle Date', 'Line', 'Track', 'Tension Length', 'From (m)', 'To (m)',
    'Avg Wear Min', 'Wear %', 'Measurement SD',
  ])
  expect(screen.getByText('18%')).toBeInTheDocument()
  expect(screen.getByTitle('18.49%')).toBeInTheDocument()
})

it('blocks save until each conflict is accepted', async () => {
  render(<WearCycleStatusPanel preview={blockedConflictPreview} />)
  expect(screen.getByRole('button', { name: /save records/i })).toBeDisabled()
  await userEvent.click(screen.getByRole('button', { name: /accept lower value/i }))
  expect(useWearStore.getState().acceptedConflictIds).toContain('conflict-28')
})
```

Also test From ascending default, natural TL ascending (`1,2,10,101`), a visible Data Conflict badge on affected TL rows before and after acceptance, chart filters exactly UP/DN/Siding, chart metric/from sorting independent of grid, y-axis padding around actual values, categorical x-axis occupying full width, file removal, and expected-segment coverage display.

- [ ] **Step 3: Verify RED**

Run the four Task 11 Vitest files.

Expected: FAIL because current table omits Cycle Date/Line, charts use separate data shaping, and conflict/coverage UI is absent.

- [ ] **Step 4: Implement Analysis UI**

`WearCalculatorView` Analysis controls contain Line, multi-file upload, and prefilled/editable Cycle Date. After upload, render `WearCycleStatusPanel`, the aggregate DataGrid, and two `WearAnalysisCharts` plots from the exact same `preview.records` reference. File chips include Remove; conflict rows show source files/values, proposed lower value, and explicit Accept Lower Value. Any row with `hasDataConflict` keeps a Data Conflict badge after acceptance so the conservative substitution remains visible until save and auditable afterward.

Presentation helpers must be pure:

```typescript
export interface AnalysisChartSort {
  field: 'fromM' | 'avgWearMin' | 'wearPercentage'
  direction: 'asc' | 'desc'
}

export const visibleAnalysisRows = (
  rows: WearCycleRecord[],
  tracks: WearTrack[],
  sort: AnalysisChartSort,
): WearCycleRecord[] => {
  const direction = sort.direction === 'asc' ? 1 : -1
  const filtered = rows.filter(row => tracks.includes(row.track))
  const value = (row: WearCycleRecord): number => {
    if (sort.field === 'avgWearMin') return row.avgWearMin
    if (sort.field === 'wearPercentage') return row.wearPercentage
    return row.fromM
  }
  return [...filtered].sort((left, right) => direction * (value(left) - value(right)))
}

export const chartAxisRange = (values: number[]): [number, number] => {
  const min = Math.min(...values)
  const max = Math.max(...values)
  const pad = Math.max((max - min) * 0.08, Math.abs(max) * 0.01, 0.05)
  return [min - pad, max + pad]
}
```

Use Plotly categorical X values and no numeric range. Empty filter state shows explanatory text. Table Track/From/To values come from backend only. Save Records reuses the retained files, Cycle Date, accepted conflict IDs, expected data version, and preview digest; it performs no frontend regrouping. After save, enable Excel download for that committed Line+Cycle Date.

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
npm test -- --run src/components/Calculation/__tests__/WearResultTable.test.tsx src/components/Calculation/__tests__/wearAnalysisPresentation.test.ts src/components/Calculation/__tests__/WearCycleStatusPanel.test.tsx src/views/__tests__/WearCalculatorView.test.tsx
npm run build
```

Expected: PASS; chart row count equals filtered table-source row count.

- [ ] **Step 6: Detect scope and commit**

Run `detect_changes`, `git diff --check`, stage only Task 11 files, and commit:

```powershell
git add frontend/src/components/Calculation/WearResultTable.tsx frontend/src/components/Calculation/wearAnalysisPresentation.ts frontend/src/components/Calculation/WearCycleStatusPanel.tsx frontend/src/components/Calculation/WearAnalysisCharts.tsx frontend/src/views/WearCalculatorView.tsx frontend/src/components/Calculation/__tests__/WearResultTable.test.tsx frontend/src/components/Calculation/__tests__/wearAnalysisPresentation.test.ts frontend/src/components/Calculation/__tests__/WearCycleStatusPanel.test.tsx frontend/src/views/__tests__/WearCalculatorView.test.tsx
git commit -m "feat: build complete-cycle analysis UI"
```

---

### Task 12: Historical Matrix and Staged Record Editing UI

**Files:**
- Modify: `frontend/src/components/Calculation/WearRecordsPanel.tsx`
- Modify: `frontend/src/components/Calculation/WearHistoryPivotTable.tsx`
- Modify: `frontend/src/components/Calculation/WearLatestSummaryTable.tsx`
- Modify: `frontend/src/components/Calculation/WireWearRecordDialog.tsx`
- Modify: `frontend/src/components/Calculation/__tests__/WearRecordsPanel.test.tsx`
- Modify: `frontend/src/components/Calculation/__tests__/WearWorkbenchTables.test.tsx`
- Modify: `frontend/src/components/Calculation/__tests__/wearRecordCharts.test.tsx`

- [ ] **Step 1: Run impact analysis**

Scan the four production components and their callbacks. Trace `useWearRecordsStore` consumers before replacing immediate CRUD.

- [ ] **Step 2: Write failing interaction tests**

```typescript
it('double-clicks an empty cell into a prefilled Add dialog', async () => {
  render(<WearRecordsPanel />)
  await userEvent.dblClick(screen.getByTestId('history-cell-2026-05-28-28-empty'))
  expect(screen.getByRole('dialog', { name: /add wire wear record/i })).toHaveFormValues({
    lineGroup: 'EAL', cycleDate: '2026-05-28', tensionLength: '28',
  })
  expect(screen.getByDisplayValue('Siding')).toBeDisabled()
})

it('keeps a deleted cell visible with pending orange strikethrough until save', async () => {
  render(<WearRecordsPanel />)
  await userEvent.hover(screen.getByText('11.45'))
  await userEvent.click(screen.getByRole('button', { name: /delete 28 on 2026-05-28/i }))
  await userEvent.click(screen.getByRole('button', { name: /^confirm$/i }))
  expect(screen.getByText('11.45')).toHaveStyle({ textDecoration: 'line-through' })
  expect(screen.getByText('11.45').closest('td')).toHaveAttribute('data-pending', 'delete')
})
```

Test value-cell double-click Edit, hover/focus Trash, date-adjacent row Trash, single confirmation without typed date, touch overflow, Save Changes, Discard, failed-save retention, Shift-wheel/trackpad/horizontal scrollbar, and historical/latest table TL alignment.

- [ ] **Step 3: Verify RED**

Run the three Task 12 Vitest files.

Expected: FAIL because current panel still performs immediate CRUD and lacks staged matrix interactions.

- [ ] **Step 4: Implement staged workbench**

`WearRecordsPanel` contains filters, a compact Add Record action, Historical Avg Wear Min matrix, Latest Summary, pending change summary, Save Changes, and Discard. Add Record opens the same metadata-backed dialog for a new Line+Cycle Date+TL. The panel contains no Dashboard/Projection cards and no raw-record card.

Dialog editable fields are exactly Line, Cycle Date, searchable TL, and Avg Wear Min. Track/From/To and precise Wear % come from metadata preview and are disabled/read-only. Measurement SD is absent. Visible Wear % uses `Math.round`; tooltip preserves precise value.

Matrix interactions:

- Non-empty cell: double-click Edit; hover/focus exposes compact Trash beside value.
- Empty historical cell: double-click Add prefilled with its row date and TL column.
- Date cell: Cycle Date and Trash use inline flex with `gap: 4px`, eliminating empty space.
- Delete confirmation names the key and has Cancel/Confirm only.
- Pending add/edit uses orange background; pending delete uses orange muted background plus strikethrough; rows remain in layout.
- Horizontal scroll container always exposes a draggable scrollbar and translates Shift-wheel to horizontal movement without blocking normal vertical wheel.

Before tab/context/navigation/refresh with pending changes, show Save/Discard/Cancel. Save calls one atomic API request; on failure focus the first error and retain every pending operation.

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
npm test -- --run src/components/Calculation/__tests__/WearRecordsPanel.test.tsx src/components/Calculation/__tests__/WearWorkbenchTables.test.tsx src/components/Calculation/__tests__/wearRecordCharts.test.tsx
npm run build
```

Expected: PASS, including keyboard-accessible Trash controls and retained pending deletions.

- [ ] **Step 6: Detect scope and commit**

Run `detect_changes`, `git diff --check`, stage only Task 12 files, and commit:

```powershell
git add frontend/src/components/Calculation/WearRecordsPanel.tsx frontend/src/components/Calculation/WearHistoryPivotTable.tsx frontend/src/components/Calculation/WearLatestSummaryTable.tsx frontend/src/components/Calculation/WireWearRecordDialog.tsx frontend/src/components/Calculation/__tests__/WearRecordsPanel.test.tsx frontend/src/components/Calculation/__tests__/WearWorkbenchTables.test.tsx frontend/src/components/Calculation/__tests__/wearRecordCharts.test.tsx
git commit -m "feat: stage wire wear record edits"
```

---

### Task 13: Dashboard, Dual-Line Projection, and Four Tabs

**Files:**
- Modify: `frontend/src/components/Calculation/WearDashboardPanel.tsx`
- Modify: `frontend/src/components/Calculation/WearProjectionPanel.tsx`
- Modify: `frontend/src/views/WearCalculatorView.tsx`
- Modify: `frontend/src/components/Calculation/__tests__/WearDashboardPanel.test.tsx`
- Modify: `frontend/src/components/Calculation/__tests__/WearProjectionPanel.test.tsx`
- Modify: `frontend/src/views/__tests__/WearCalculatorView.test.tsx`

- [ ] **Step 1: Run impact analysis**

Scan `WearDashboardPanel`, `WearProjectionPanel`, and `WearCalculatorView`; trace API/store/component callers and report risk.

- [ ] **Step 2: Write failing rendering tests**

```typescript
it('renders max, min-positive, and current wear as ordered tables', () => {
  render(<WearDashboardPanel />)
  expect(screen.getByRole('table', { name: /top 5 max wear rate/i })).toBeInTheDocument()
  expect(screen.getByRole('table', { name: /top 5 min positive wear rate/i })).toBeInTheDocument()
  expect(screen.getByRole('table', { name: /top 5 current wear/i })).toBeInTheDocument()
  expect(screen.getAllByText('28').length).toBeGreaterThan(0)
  expect(screen.getByText(/5.5%\/yr/)).toBeInTheDocument()
  expect(screen.getByText(/0.42 mm\/yr/)).toBeInTheDocument()
})

it('shows one shared threshold and separate EAL and TML charts', async () => {
  render(<WearProjectionPanel />)
  expect(screen.getByLabelText(/threshold mm/i)).toHaveValue(10.2)
  expect(screen.getByText(/equivalent wear: \d+%/i)).toBeInTheDocument()
  expect(screen.getByRole('img', { name: /eal 30-year projection/i })).toBeInTheDocument()
  expect(screen.getByRole('img', { name: /tml 30-year projection/i })).toBeInTheDocument()
})
```

Test preset buttons `10.2, 9.1, 8.9, 7.44, 7.24`, custom positive input, nearest-integer display only, expandable combined year rows, status lists, line Dashboard filter, table order, and exact four tab labels.

- [ ] **Step 3: Verify RED**

Run the three Task 13 Vitest files.

Expected: FAIL because current panels show counts/cards or one-line projection and the tab structure is not final.

- [ ] **Step 4: Implement final layouts**

Dashboard renders three compact semantic tables with rank, Line, TL, rate/current values, R², and status. Max orders highest positive rate first; Min orders smallest strictly positive first; Current orders highest precise Wear % first. Filter options are All/EAL/TML.

Projection has one controlled `thresholdMm`, preset chips, precise backend conversion but visible rounded percentage, and side-by-side/stacked responsive EAL/TML charts from the same response. Below, render one combined `Projected Year | Count | Tension Lengths` table; expanded rows show Line, TL, latest thickness/date, mm/year, crossing date, R², and status. Separate sections list already-at-threshold, insufficient-data, and non-positive-rate TLs.

`WearCalculatorView` tabs are exactly `Analysis`, `Wire Wear Records`, `Dashboard`, `Projection`. Dashboard and Projection load only committed backend data, never Analysis preview or staged workbench changes.

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
npm test -- --run src/components/Calculation/__tests__/WearDashboardPanel.test.tsx src/components/Calculation/__tests__/WearProjectionPanel.test.tsx src/views/__tests__/WearCalculatorView.test.tsx
npm run build
```

Expected: PASS; no established/provisional legend or category appears.

- [ ] **Step 6: Detect scope and commit**

Run `detect_changes`, `git diff --check`, stage only Task 13 files, and commit:

```powershell
git add frontend/src/components/Calculation/WearDashboardPanel.tsx frontend/src/components/Calculation/WearProjectionPanel.tsx frontend/src/views/WearCalculatorView.tsx frontend/src/components/Calculation/__tests__/WearDashboardPanel.test.tsx frontend/src/components/Calculation/__tests__/WearProjectionPanel.test.tsx frontend/src/views/__tests__/WearCalculatorView.test.tsx
git commit -m "feat: finish wear dashboard and projection"
```

---

### Task 14: End-to-End Verification and Final Review

**Files:**
- Modify only when a new failing regression test proves a defect in a Task 3–13 file.
- Test: `frontend/tests/calculation.spec.ts`

- [ ] **Step 1: Run impact analysis before any verification fix**

No production edit is allowed until the failing verification identifies an exact symbol and `search_graph` plus inbound `trace_path` reports risk below HIGH. Add the regression test first, verify RED, then apply the smallest fix.

- [ ] **Step 2: Add or update the Playwright complete-cycle smoke**

The test must exercise:

```typescript
test('wear calculator complete-cycle workflow', async ({ page }) => {
  await page.goto('/')
  await page.getByText('Wear Calculator', { exact: true }).click()
  await expect(page.getByRole('tab')).toHaveText([
    'Analysis', 'Wire Wear Records', 'Dashboard', 'Projection',
  ])
  await uploadApprovedEalCycle(page)
  await expect(page.getByRole('cell', { name: 'Siding' })).toBeVisible()
  await acceptAllConflicts(page)
  await page.getByRole('button', { name: 'Save Records' }).click()
  await expect(page.getByText(/cycle saved/i)).toBeVisible()
  await page.getByRole('tab', { name: 'Wire Wear Records' }).click()
  await expect(page.getByTestId('history-cell-2026-05-28-28')).toBeVisible()
})
```

- [ ] **Step 3: Run focused then full backend verification**

```powershell
cd backend
python -m pytest tests/test_wear_cycle_metadata.py tests/test_wear_cycle_aggregation.py tests/test_wear_records.py tests/test_wear_cycle_analytics.py tests/test_wear_cycle_io.py tests/test_calculation_api.py tests/test_wear_records_api.py tests/test_wire_wear_sync.py -q
python -m pytest -q
```

Expected: all tests PASS with no unhandled warnings introduced by this feature.

- [ ] **Step 4: Run focused then full frontend verification**

```powershell
cd ../frontend
npm test -- --run src/api/__tests__/calculationApi.test.ts src/store/__tests__/useWearStore.test.ts src/store/__tests__/useWearRecordsStore.test.ts src/components/Calculation/__tests__/WearResultTable.test.tsx src/components/Calculation/__tests__/WearRecordsPanel.test.tsx src/components/Calculation/__tests__/WearDashboardPanel.test.tsx src/components/Calculation/__tests__/WearProjectionPanel.test.tsx src/views/__tests__/WearCalculatorView.test.tsx
npm test -- --run
npm run lint
npm run build
npm run test:e2e -- calculation.spec.ts
```

Expected: all tests, lint, build, and Playwright PASS.

- [ ] **Step 5: Perform manual product verification**

Verify with EAL and TML sample files:

- Cycle Date defaults to latest acquisition date and accepts an override.
- Expected segments identify actual filenames; coverage remains advisory.
- Duplicate conflict shows both files/values, lower proposal, explicit acceptance, and Save blocking.
- One TL appears once; shared UP/DN TL is Siding; metadata From/To are fixed.
- Analysis charts and table contain identical filtered TL rows and use all width.
- Saved cycle creates one matrix cell per business key.
- Empty-cell Add, value Edit/Delete, row Trash, staged orange/strikethrough, Save/Discard/Cancel all work.
- Dashboard tables list ordered TL values.
- `10.2 mm` defaults in Projection; EAL/TML charts and expanded year table agree.
- Excel has four sheets and precise Wear %.
- JSON preview/apply reports actions, propagates tombstones, and creates no SQLite backup.

- [ ] **Step 6: Run final change detection and scope audit**

Run:

```powershell
git diff --check
git status --short
git log --oneline --decorate -15
```

Call:

```json
{
  "tool": "detect_changes",
  "project": "C-Smart-Maintanence-TOV640_Analyzer-.worktrees-wear-tl-cycle-aggregation",
  "since": "39d74eb",
  "scope": "wear calculator complete-cycle aggregation",
  "depth": 3
}
```

Expected: changed production scope is limited to Wear Calculator calculation, persistence, API, and frontend surfaces. `AGENTS.md`, unrelated screenshots, and `.superpowers/brainstorm/**/server-info` remain unstaged and unmodified by agents.

- [ ] **Step 7: Commit only proven verification fixes**

If Step 3–5 required a fix, stage exactly its regression test and production file, rerun the affected focused and full suites, call `detect_changes`, then commit:

```powershell
git commit -m "fix: verify wear complete-cycle workflow"
```

If no fix was required, create no Task 14 commit.

- [ ] **Step 8: Run final independent review**

Dispatch one final high-capability reviewer with the approved spec, commits from Task 3 onward, full test output, and final `detect_changes`. Resolve every spec or quality issue through a fresh failing test and re-review. After approval, use `finishing-a-development-branch` to offer merge/PR/keep-worktree choices; do not merge or push without user instruction.

## Self-Review Checklist

### Spec coverage

- Complete-cycle identity, Cycle Date, expected segments, canonical metadata, deduplication/conflict review, coverage, fixed range, Siding, sample SD, and Save blocking: Tasks 4–7.
- Normalized cycles, records, segments, conflict audit, tombstones, no legacy migration/backup: Tasks 3, 6, and 9.
- Historical matrix, metadata-owned manual fields, staged Add/Edit/Delete Cell/Delete Row, atomic save, orange/strikethrough, and navigation guard: Tasks 6, 7, 10, and 12.
- All-history OLS, Historical SD separation, Dashboard rankings, two-line configurable projection: Tasks 8 and 13.
- Analysis columns/sorts/charts/filters and same-row-set guarantee: Task 11.
- Excel four-sheet report and `wear-cycle-v1` two-phase sync precedence: Task 9.
- Four tabs and separation of committed versus pending/preview state: Tasks 10–13.
- Full automated/manual verification and final codebase-memory change detection: Task 14.

### Type and signature consistency

- Python uses `line_group`, `cycle_date`, `tension_length`, `measurement_sd`, and `historical_sd`; `sd` is not reused.
- TypeScript components use camelCase through explicit API mappers.
- Track values are exactly `UP`, `DN`, `Siding`.
- Change kinds are exactly `add`, `edit`, `delete_cell`, `delete_row`.
- Sync schema is exactly `wear-cycle-v1`; Excel schema is report-only.
- Dashboard and Projection read committed repository records only.

### Plan quality

- Every production task begins with symbol impact analysis.
- Every behavior change has an explicit failing test and expected RED condition before implementation.
- Every task has focused GREEN verification, change detection, precise staging scope, and commit command.
- Every implementation step names its validation and error outcomes explicitly.
