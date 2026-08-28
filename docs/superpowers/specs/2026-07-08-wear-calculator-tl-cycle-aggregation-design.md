# Wear Calculator Complete-Cycle Workbench Design

Date: 2026-07-08
Project: TOV640 Analyzer
Module: Wear Calculator
Status: Approved design, pending written-spec review

## Purpose

This design turns the Wear Calculator into a complete-cycle analysis and records workbench. It addresses six connected problems:

1. analysis and exports currently expose the wrong columns and unstable chart behavior;
2. a business cycle is split across files, sessions, dates, tracks, and metadata rows;
3. historical record editing is disconnected from the visible matrix;
4. the dashboard does not show actionable Tension Length rankings;
5. projection does not show when specific Tension Lengths will cross a configurable thickness threshold; and
6. records must be moved safely between offline SQLite workstations.

The core user-facing identity is:

```text
WearCycleRecord = Line + Business Cycle Date + Tension Length
```

Analysis, persistence, Excel export, Dashboard, Projection, and JSON sync all use this identity. The UI never splits one Tension Length by track, source file, acquisition session, metadata row, class, or section within the same business cycle.

## Product Boundaries

- The application remains an offline desktop application with a React frontend, FastAPI backend, and SQLite storage.
- There is no authentication, hosted multi-user service, or PostgreSQL migration.
- Existing raw/test wear data does not need to be migrated.
- No automatic SQLite backup is created before sync.
- Raw wire-wear rows are not exposed as a primary user-facing workbench.
- Excel is a human-readable report format. JSON is the only round-trip sync format.

## User Experience Structure

The Wear Calculator has four main tabs:

```text
Analysis | Wire Wear Records | Dashboard | Projection
```

The visual language remains consistent with the existing application: compact operational controls, restrained blue accents, dense tables, and clear pending/error states. It does not introduce a second nested records application or generic KPI-card dashboard.

## Domain Model and Terminology

### Business Cycle Date

`Cycle Date` is the user-controlled business date shared by every saved row in one uploaded batch.

- It defaults to the latest acquisition date found in the accepted upload files.
- The user may override it before analysis or save.
- Acquisition dates remain source lineage and do not split the saved cycle.
- Saving is blocked if Cycle Date is missing or invalid.

### Measurement SD and Historical SD

The two statistics have different meanings and must never share one field:

- `measurement_sd`: sample standard deviation of accepted raw wear-min measurements used to calculate one Analysis TL row. It is nullable when fewer than two raw values are available.
- `historical_sd`: sample standard deviation of that TL's saved `avg_wear_min` values across business cycles. It is nullable when fewer than two historical cycles are available.

Manual Add/Edit does not ask for Measurement SD. A manually created record stores `measurement_sd = null`; Historical SD is derived for summaries only.

### Canonical Metadata

Metadata is line-specific. The same visible TL label in EAL and TML is not interchangeable.

For a selected `Line + Tension Length`, the backend:

1. collects all matching metadata intervals;
2. sorts intervals by `from_m`;
3. merges overlapping or contiguous intervals while preserving separate physical intervals across real gaps;
4. derives bounding-summary `from_m`, `to_m`, Track, interval count, and ordered interval details; and
5. rejects a measurement when its Line + Track + Chainage resolves to zero or multiple physical intervals.

One `Line + Tension Length` remains one business identity and one saved record even when its metadata has multiple disjoint physical intervals. Bounding `from_m` and `to_m` are explicitly a summary and must never imply continuity: APIs, persisted records, Excel, JSON sync, and metadata-bearing UI expose `interval_count` and the ordered physical interval details. Raw compound TL labels are resolved by Line + Track + Chainage; the compound text is never stored as a TL and is blocking when the chainage cannot select exactly one physical interval.

Track is derived as:

- only UP intervals: `UP`;
- only DN intervals: `DN`;
- both UP and DN intervals: `Siding`.

Track, From, and To are backend-owned values. The user never types or edits them.

## Complete-Cycle Upload and Analysis

### Upload Workflow

The user selects one Line, sets or accepts a Cycle Date, and uploads all files for that business cycle in one batch.

The backend detects each file's segment from line-specific metadata and source contents. There are no manual segment checkboxes.

The expected segment sets are:

- EAL: `U1`, `U2`, `U3`, `D1`, `D2`, `D3`, `LOW S1`, `RAC UP`, `RAC DN`, `LMC UP`, `LMC DN`.
- TML: `U1`, `U2`, `U3`, `U4`, `U5`, `D1`, `D2`, `D3`, `D4`, `D5`.

The Analysis page shows an `Expected Segments` panel with, for each segment:

- detected or missing state;
- contributing source files;
- acquisition date range;
- measurement coverage percentage; and
- diagnostic gaps.

Coverage percentage and gaps are advisory. A segment counts as present when at least one valid measurement resolves to it. Save is allowed only when every expected segment for the selected line is present.

Unknown segments, unresolved rows, invalid files, or a completely empty expected segment block Save and identify the affected file or segment.

### Deduplication and Conflict Review

When a source provides a stable measurement/session ID, it is the preferred raw identity. Otherwise the compound identity is normalized Line, detected segment, Track, acquisition date, task number, station start/end, and chainage. Source filename is intentionally excluded so duplicated files collide. Within one batch:

- an exact duplicate identity with the same wear value is counted once;
- the same identity with different wear values is a conflict;
- observations from different acquisition sessions remain separate accepted observations.

Conflicts are grouped in a review panel showing every source file and value. The proposed decision is the lower wear-min value because it is the conservative remaining-thickness measurement. The user must explicitly accept the grouped decisions before Save becomes available.

Accepted conflict decisions are stored with the cycle for later audit and included in Excel and JSON outputs.

### Aggregation

After validation, deduplication, and accepted conflict resolution, the backend aggregates all accepted raw measurements by:

```text
Line + Business Cycle Date + Tension Length
```

Each Analysis row contains:

```text
Cycle Date
Line
Track
Tension Length
From (m)
To (m)
Avg Wear Min
Wear %
Measurement SD
```

Rules:

- Track, From, and To come from canonical metadata.
- `avg_wear_min` is calculated from all accepted raw measurements mapped to the TL.
- `wear_percentage` is always recalculated by the backend.
- `measurement_sd` uses the accepted raw measurements and may be null.
- Wear % is stored and returned at backend precision. UI tables round it to the nearest integer for display; tooltips, API payloads, JSON sync, and Excel retain the precise value.
- The default table order is numeric `from_m` ascending.
- Tension Length sorting is natural, for example `1, 2, 10, 101`.

### Analysis Charts

Wear % and Avg Wear Min charts use the exact Analysis row set, not a separately aggregated dataset.

- The X-axis is categorical by Tension Length and consumes the available chart width.
- The Y-axis range is calculated from plotted values with a small readable padding.
- Track filters are exactly `UP`, `DN`, and `Siding`.
- Chart sorting supports From ascending/descending and metric ascending/descending.
- Chart sorting does not mutate DataGrid ordering.
- Empty filters show a clear empty state rather than a blank chart region.

### Save Records

Save stores the complete validated batch as one business cycle transaction. It is blocked until:

- every expected segment is present;
- all rows resolve to canonical metadata;
- all conflicts are explicitly accepted; and
- Cycle Date is valid.

Any write failure rolls back the whole cycle. Duplicate checks use `Line + Cycle Date + Tension Length`.

## Wire Wear Records Workbench

This tab contains two coordinated tables and no separate raw-record card.

### Historical Avg Wear Min Matrix

- Rows are Business Cycle Dates.
- Columns are Tension Lengths in canonical From order.
- Cells show saved `avg_wear_min`.
- Line, TL search, and date-range controls filter the matrix.
- Horizontal scrollbar drag, mouse wheel/shift-wheel, and trackpad scrolling are supported.

Pointer or keyboard focus reveals contextual actions:

- cell: Edit or Delete Cell;
- date row: Delete Row for that Line + Cycle Date.

The compact interaction is:

- double-clicking a value cell opens Edit;
- double-clicking an empty historical cell opens Add with Line, Cycle Date, TL, Track, From, and To prefilled;
- hovering or focusing a value cell reveals a small Trash icon beside the value;
- the date-row Trash icon sits immediately beside the Cycle Date; and
- cell or row deletion uses one confirmation dialog and never requires typing the date.

Touch devices expose the same commands through an explicit overflow action button.

### Latest Summary

The summary is aligned to the same TL order and includes:

```text
Line
Tension Length
Latest Cycle Date
Latest Avg Wear Min
Latest Wear %
Wear Rate (% / year)
Wear Rate (mm / year)
Historical SD
R-squared
Trend Status
```

### Manual Add/Edit

The editable inputs are:

```text
Line
Cycle Date
Tension Length
Avg Wear Min
```

Line and TL are searchable controlled selectors. After selection, the form previews backend-resolved Track, From, To, and calculated Wear %. Measurement SD is not shown as an editable field and remains null for manual records.

Manual records participate in Trend, Dashboard, and Projection immediately after commit. A manual-only cycle is marked incomplete and does not become the latest complete uploaded cycle. Adding a manual record to an existing complete cycle does not downgrade that cycle.

### Staged Change Set

Add, Edit, Delete Cell, and Delete Row are staged locally before persistence.

- Added and edited cells use an orange pending style.
- Deleted cells/rows remain visible in a struck or muted pending state until commit.
- A change summary lists each pending operation.
- `Save Changes` applies the whole set in one SQLite transaction.
- A failed save rolls back everything and retains the pending change set for correction.
- Switching tabs, changing context, closing the workbench, or refreshing with pending changes triggers a Save/Discard/Cancel guard.

Delete Row creates a deletion for every committed business key in that Line + Cycle Date. Delete Cell creates one deletion. Both create sync tombstones when committed.

## Trend Model

Trend calculations use all committed history for each `Line + Tension Length`; they do not use only the latest two cycles.

The backend runs ordinary least-squares regression against continuous elapsed years derived from Cycle Date.

- Remaining-thickness model: `avg_wear_min` versus elapsed years.
- `mm/year` is the positive loss rate, equal to the negative fitted thickness slope.
- `%/year` is derived consistently from the fitted wear progression and backend wear formula.
- `R-squared` and observation count are returned as quality information, not blocking thresholds.
- Two distinct dates are sufficient for an eligible trend. They are not placed in a separate provisional chart series or visual category.
- Fewer than two distinct dates produce status `insufficient_data` and no rate or projection.
- Zero or negative loss rate produces status `non_positive_rate` and no future threshold crossing.

All consumers use this one backend trend service.

## Dashboard

Dashboard contains three compact ranked tables, not generic charts or KPI cards:

1. Top 5 Max Wear Rate
2. Top 5 Min Positive Wear Rate
3. Top 5 Current Wear

Rows show Line and TL so labels remain unambiguous across EAL and TML.

- Max and Min tables show `%/year`, `mm/year`, R-squared, and trend status.
- Min excludes zero, negative, and insufficient rates.
- Current Wear ranks the latest committed record by highest Wear % and shows its Avg Wear Min.
- A line filter supports All, EAL, and TML.
- Manual committed records participate like uploaded records.

## Projection

Projection shows EAL and TML simultaneously in two compact 30-year charts with one shared thickness threshold input in millimetres. The presets are `10.2`, `9.1`, `8.9`, `7.44`, and `7.24 mm`, with `10.2 mm` selected initially. Custom positive millimetre values are allowed within the backend wire-geometry range. Changing the threshold recalculates both lines without modifying stored data.

The backend converts the thickness threshold to its precise equivalent Wear %. The UI displays that percentage rounded to the nearest integer; API, JSON, and Excel retain the precise value.

For each eligible TL, the backend solves the all-history fitted thickness line for the date it first reaches the threshold.

- The horizon is the next 30 complete calendar years.
- The chart bucket is the projected crossing calendar year.
- TLs already at or below the threshold are reported separately as `already_at_threshold`.
- Insufficient or non-positive trends are reported separately and do not enter chart buckets.
- Every eligible two-or-more-date trend contributes to the same chart series without a separate provisional distinction.

Below the charts, one combined year table contains:

```text
Projected Year | Count | Tension Lengths
```

Each year expands to Line, TL, latest thickness, latest Cycle Date, mm/year, projected crossing date, R-squared, and trend status. Chart counts and expanded rows come from the same backend bucket payload.

## Persistence Design

The new persistence layer is normalized around the business cycle:

### `wire_wear_cycles`

- `id`
- `line_group`
- `cycle_date`
- `source_type` (`analysis`, `manual`, or `sync`)
- acquisition date range
- completeness state
- source lineage
- `created_at`
- `updated_at`

Unique key: `line_group + cycle_date`.

### `wire_wear_cycle_segments`

- parent cycle ID
- segment identity
- present state
- coverage percentage
- diagnostic gaps
- source file names

### `wire_wear_cycle_records`

- parent cycle ID
- line group and cycle date for explicit business-key queries
- normalized Tension Length
- canonical Track, From, and To
- Avg Wear Min
- Wear %
- nullable Measurement SD
- source lineage
- `created_at`
- `updated_at`

Unique key: `line_group + cycle_date + tension_length`.

### `wire_wear_conflict_decisions`

- parent cycle ID
- raw measurement identity
- source values and source files
- selected lower value
- accepted timestamp

### `wire_wear_deletion_tombstones`

- line group
- cycle date
- normalized Tension Length
- `deleted_at`
- source workstation/package identity when available

No legacy raw/test records are migrated. The existing Task 1/Task 2 schema and service work must be revised to this final model before frontend implementation continues.

## API Design

The exact module placement should follow existing FastAPI routing conventions. The behavioral endpoints are:

```text
POST /calculation/wear
POST /calculation/wear-records/changes
GET  /calculation/wear-records/workbench
GET  /calculation/wear-records/dashboard
GET  /calculation/wear-records/projection?threshold_mm=10.2
GET  /calculation/wear-records/export.xlsx
GET  /calculation/wear-records/sync.json
POST /calculation/wear-records/sync/preview
POST /calculation/wear-records/sync/apply
```

- Analysis returns aggregated rows, segment coverage, unresolved diagnostics, and grouped conflict decisions.
- Changes applies staged Add/Edit/Delete operations atomically with optimistic timestamps.
- Workbench returns matrix, latest summary, and trend metadata.
- Dashboard and Projection are read-only views over committed records.
- Export and sync responses are backend-generated so formulas and business keys are consistent.

## Excel Output

Excel is a report artifact and cannot be imported.

The workbook contains:

1. `Wear Records`
2. `Cycle Coverage`
3. `Conflict Audit`
4. `Workbook Info`

`Wear Records` uses the Analysis column order and defaults to canonical From ascending. `Workbook Info` includes schema name, export time, application version, and metadata fingerprint.

## JSON Sync

JSON is the only sync import format. The package schema is named `wear-cycle-v1` and contains:

- package/export identity and timestamps;
- metadata fingerprint;
- committed aggregated records;
- cycle and segment coverage;
- accepted conflict audit;
- deletion tombstones; and
- record-level `updated_at` values.

Import matches records and tombstones by:

```text
Line + Cycle Date + Tension Length
```

Conflict precedence:

- the later of record `updated_at` and tombstone `deleted_at` wins;
- a tombstone wins an exact timestamp tie to prevent deleted records from being resurrected;
- a newer committed record may intentionally recreate a deleted business key.

Import is two-phase:

1. Preview parses and validates the package, resolves all records against local canonical metadata, recalculates Wear %, and reports Create, Update, Delete, Unchanged, Conflict, and Error rows.
2. Apply requires the preview's `expected_data_version` and commits all accepted actions in one transaction.

Unknown TLs, duplicate package keys, invalid dates or values, incompatible schema, unresolved metadata, or a stale data version block Apply. A metadata fingerprint difference is advisory if every imported record resolves identically against local metadata; otherwise it blocks Apply.

## Error Handling

- Domain validation failures return `422` with file, segment, TL, cell, or business-key context.
- Duplicate identity, stale `updated_at`, and stale sync data-version conflicts return `409`.
- Save Cycle, Save Changes, and Sync Apply are atomic and roll back on any error.
- The frontend retains staged changes after a failed commit and focuses the first actionable error.
- Unsupported legacy sync packages are rejected with a clear schema-version message.
- Dashboard and Projection never read uncommitted Analysis or pending workbench state.

## Testing Strategy

Implementation follows test-driven development at backend-service, API, frontend-component, and end-to-end levels.

### Backend Tests

- Multiple files, sessions, dates, tracks, and metadata rows aggregate to one TL-cycle record.
- Exact raw duplicates are counted once.
- Conflicting raw values use the lower proposal and block Save before acceptance.
- EAL/TML expected-segment detection and completeness rules.
- Coverage percentage remains diagnostic and does not replace segment presence.
- Cycle Date default and user override.
- Canonical metadata interval merge and gap rejection.
- Track derives as UP, DN, or Siding.
- Measurement SD and Historical SD remain separate and nullable under their own rules.
- Wear % is recalculated on analysis, manual changes, and sync import.
- Staged Add/Edit/Delete is atomic and honors optimistic concurrency.
- Cell and row deletes create tombstones.
- Sync record/tombstone precedence prevents resurrection.
- All-history regression, two-point eligibility, non-positive rate, observation count, and R-squared.
- Dashboard ranking and Min-positive exclusion.
- Shared mm threshold produces correct EAL/TML 30-year buckets.
- Chart buckets and expanded projection table use identical record sets.
- Excel workbook sheets and JSON schema contents.
- Large-file parsing and deduplication do not regress streaming behavior.

### Frontend Tests

- Four main tabs render with the approved compact layouts.
- Analysis columns, default From sort, natural TL sort, charts, and exact track filters.
- Expected-segment and conflict panels control Save availability.
- Cycle Date default and override apply to all Analysis rows.
- Historical matrix and Latest Summary remain aligned and horizontally scrollable.
- Pointer, keyboard, and touch actions expose cell/row commands.
- Pending Add/Edit/Delete styles, summary, atomic Save, and navigation guard.
- Manual form exposes only Line, Cycle Date, TL, and Avg Wear Min as inputs.
- Dashboard renders three ranked Top 5 tables with concrete Line/TL values.
- Projection renders simultaneous EAL/TML charts and one expandable combined table.
- Sync preview displays Create/Update/Delete/Unchanged/Conflict/Error states.

### Manual Verification

- Upload a complete EAL cycle split across files/sessions and confirm one row per TL.
- Confirm missing expected segments and unaccepted conflicts block Save.
- Save a cycle and verify matrix, latest summary, Dashboard, and Projection refresh.
- Stage mixed add/edit/delete operations, cancel navigation, then commit atomically.
- Export Excel and inspect all four sheets.
- Export JSON on one workstation, preview/apply on another, delete a record, sync both directions, and verify no resurrection.
- Change the shared threshold and verify both line charts and year details update consistently.

## Risks and Mitigations

- Segment detection may be ambiguous for malformed files. Block Save and show source-level diagnostics instead of guessing.
- Metadata gaps can make a TL unresolved. Keep metadata backend-owned and fail with the exact intervals involved.
- Full-history regression can imply unrealistic long-range results. Show R-squared/status and exclude non-positive rates rather than hiding uncertainty.
- Large complete-cycle batches may stress memory. Preserve the existing streaming parser and deduplicate incrementally.
- Offline clock differences can affect timestamp conflict resolution. Include package/export identity, show conflicts in preview, and let tombstones win timestamp ties.

## Out of Scope

- Manual expected-segment checkboxes.
- Editing Track, From, To, Wear %, Measurement SD, or Historical SD.
- Importing Excel as a sync source.
- Generic Dashboard trend/distribution charts.
- A general raw-record grid alongside the historical matrix.
- Automatic database backup or legacy raw-data migration.
- Authentication, role permissions, cloud sync, or concurrent multi-user editing.
