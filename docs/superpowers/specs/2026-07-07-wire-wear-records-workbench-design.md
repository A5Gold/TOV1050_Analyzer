# Wire Wear Records Workbench Design

Date: 2026-07-07
Project: TOV640 Analyzer
Module: Wear Calculator

## Purpose

This design upgrades the Wear Calculator `Wire Wear Records` tab from a read-only chart/table into a database workbench for wire wear records. The first implementation phase focuses on Issue 1: user database control, requested Table 1 and Table 2 formats, graph drill-down by Tension Length, and Excel export.

Issue 2 is included as the next-phase development plan. The first phase will document and reserve clean export/import boundaries, but it will not implement multi-PC synchronization or hosted-server mode yet.

## Current State

The application already has:

- SQLite persistence for `wire_wear_records`.
- Backend APIs for save, list, dashboard, and projection under `/api/calculation/wear-records`.
- Frontend records, dashboard, and projection panels.
- Packaged Electron production mode that sets `DB_PATH` to `<packaged app root>/data/analysis.db`.
- Current Windows packaging target set to `dir`, not a single-file executable.

Current gaps:

- `Wire Wear Records` has no user-facing Add, Edit, Delete, or Export Excel controls.
- Current records view shows raw records, not the requested pivot-style historical table.
- Projection output supports a single threshold at a time and does not produce the requested 20 percent and 33 percent summary table.
- `Analysis` input lets the user select `LMC`; the requested behavior is line selection only for `EAL` and `TML`, while class/section is inferred by the database/calculation flow.

## Approved Decisions

1. First phase scope is the full Wire Wear Records workbench.
2. Offline sync, packaging choice, and hosted-server guideline are included in the next-phase plan, not implemented in this phase.
3. Main tables are centered on `Tension Length`.
4. Main tables merge records by `Line + Date + Tension Length`.
5. When multiple `Class / Track / Section` rows exist under the same `Line + Date + Tension Length`, Table 1 uses the average `avg_wear_min`.
6. Table 2 also uses the aggregated Tension Length time series:
   - `Latest Wear %`: average `wear_percentage` for the latest date and TL.
   - `Wear % Rate per year`: linear slope of aggregated wear percentage over time.
   - `Wear mm Rate per year`: height-loss slope from aggregated `avg_wear_min` over time.
   - `20% Wear Projection year` and `33% Wear Projection year`: calculated from aggregated latest wear and rate.
7. Raw `Class / Track / Section` rows remain available in a detail drawer or detail panel after selecting a Tension Length.
8. Add, Edit, and Delete operate on raw database records, not directly on merged summary cells.

## User Experience

### Analysis Tab

The `Analysis` tab line selector changes from `Line Class` to `Line`.

Allowed user choices:

- `EAL`
- `TML`

The user will not manually select `LMC` in this tab. The backend and save flow can still store `line_class` and `section` values such as `Mainline`, `RAC`, `LOW S1`, or `LMC` based on parsed/calculated data.

### Wire Wear Records Tab

The tab becomes a workbench with:

- Toolbar:
  - Line selector: `EAL` or `TML`
  - Date range filter
  - View mode selector, if useful: History, Summary, Raw Records
  - Add
  - Edit
  - Delete
  - Export Excel
  - Refresh
- Table 1: Historical average wire wear minimum by cycle date and Tension Length.
- Table 2: Latest wear, wear rate, mm rate, 20 percent projection, and 33 percent projection by Tension Length.
- Graph area:
  - Click a Tension Length header/button to show its trend graph.
  - Existing graph modes can remain available: by cycle and by Tension Length.
- Detail drawer or detail panel:
  - Shows raw rows for the selected Tension Length.
  - Includes `Class`, `Track`, `Section`, `Cycle Date`, `From (m)`, `To (m)`, `Avg Wear Min`, `Wear %`, `SD`, and source metadata.
  - Edit and Delete are available at the raw row level.

## Table 1 Format

Table 1 returns a matrix:

- Row key: `cycle_date`
- Column key: `tension_length`
- Cell value: aggregated `avg_wear_min`

Aggregation:

```text
group by line_group, cycle_date, tension_length
cell avg_wear_min = average(raw avg_wear_min values)
```

Formatting:

- Dates should display consistently as `YYYY-MM-DD` in the app.
- Excel export may use the same ISO date format unless a later requirement asks for `DD/MM/YYYY`.
- Empty cells represent no records for that cycle date and Tension Length.
- Numeric cells should preserve enough precision for engineering review. Recommended display is 3 decimal places in UI and full numeric value in Excel.

## Table 2 Format

Table 2 returns a row-per-metric matrix:

Metrics:

- `Latest Wear %`
- `Wear % Rate per year`
- `Wear mm Rate per year`
- `20% Wear Projection year`
- `33% Wear Projection year`

Columns:

- Tension Length values for the selected line.

Aggregation and rate calculation:

1. Aggregate raw rows by `line_group + cycle_date + tension_length`.
2. For each aggregated point:
   - `avg_wear_min` = average raw `avg_wear_min`.
   - `wear_percentage` = average raw `wear_percentage`.
3. For each Tension Length, sort aggregated points by date.
4. Latest values come from the latest aggregated date.
5. Rates use linear regression slope over years from the first aggregated date.

Projection display rules:

- If there are fewer than 2 aggregated data points, show `Insufficient Data`.
- If the wear percentage rate is less than or equal to 0, show `Insufficient Data`.
- If projected year is greater than 2100, show `Beyond 2100`.
- Otherwise show the projected calendar year.
- If latest wear is already at or above the threshold, show the latest cycle year.

## Backend Design

### Core calculations

Add core functions in the wire wear records calculation layer:

- Build aggregated time series by line and Tension Length.
- Build Table 1 history matrix.
- Build Table 2 projection matrix for 20 percent and 33 percent thresholds.
- Update one raw wire wear record.
- Delete one raw wire wear record.
- Insert a manually created raw wire wear record.
- Export records workbook content as Excel.

The current `_rate_rows` logic can be reused or refactored, but Table 2 must calculate rates from the aggregated Tension Length time series rather than raw `Class / Track / Section` identities.

### API endpoints

Extend `/api/calculation/wear-records` with:

- `POST /api/calculation/wear-records/manual`
  - Add one or more manually entered records.
- `PATCH /api/calculation/wear-records/{record_id}`
  - Edit raw record fields.
- `DELETE /api/calculation/wear-records/{record_id}`
  - Delete one raw record.
- `GET /api/calculation/wear-records/workbench`
  - Returns Table 1, Table 2, available Tension Lengths, and raw detail rows for the selected line/filter.
- `GET /api/calculation/wear-records/export`
  - Returns an Excel workbook.

The existing save endpoint should remain compatible with analysis-result save behavior.

### Excel export

Export should produce a workbook with at least three sheets:

1. `History Avg Wear Min`
   - Table 1 pivot matrix.
2. `Latest Summary`
   - Table 2 matrix.
3. `Raw Records`
   - Raw database rows with full identity and timestamps.

Optional later sheets:

- `Selected TL Detail`
- `Projection Inputs`

## Frontend Design

### Types and API client

Add TypeScript types for:

- Workbench response.
- Table 1 rows and columns.
- Table 2 metric rows.
- Raw detail rows.
- Manual add and update payloads.

Add API client functions for:

- Fetch workbench.
- Add raw record.
- Update raw record.
- Delete raw record.
- Export Excel.

### Store

Extend `useWearRecordsStore` or split a focused workbench store if the existing store becomes too broad.

State should include:

- Selected line.
- Date range.
- Selected Tension Length.
- Workbench data.
- Raw detail rows.
- Loading/saving/exporting state.
- Error state.

### Components

Recommended component split:

- `WearRecordsPanel`
  - Workbench shell and toolbar.
- `WearHistoryPivotTable`
  - Table 1.
- `WearLatestSummaryTable`
  - Table 2.
- `WearTensionLengthDetailPanel`
  - Raw rows, row actions, and graph controls.
- `WireWearRecordDialog`
  - Add/edit form.

The current chart components can be reused where possible.

## Validation Rules

Manual add/edit should validate:

- `line_group` is `EAL` or `TML`.
- `cycle_date` is a valid date.
- `tension_length` is not empty.
- `from_m` and `to_m` are numeric and `to_m >= from_m`.
- `avg_wear_min`, `sd`, and `wear_percentage` are numeric.
- `wear_percentage` should not be negative.

Duplicate handling should reuse the existing database uniqueness rule:

```text
line_group, line_class, track, section, cycle_date, tension_length
```

If a manual add conflicts with an existing row, the UI should ask whether to update the existing row or cancel.

## Testing Strategy

Backend tests:

- Table 1 averages multiple raw rows for the same `Line + Date + Tension Length`.
- Table 2 uses the aggregated time series for rates and projections.
- Projection display rules cover insufficient data, non-positive rate, beyond 2100, already over threshold, 20 percent, and 33 percent.
- Add, edit, and delete endpoints affect only the intended raw record.
- Export endpoint returns an `.xlsx` workbook with expected sheets and headers.

Frontend tests:

- `Analysis` tab shows only `EAL` and `TML` line choices.
- Workbench loads and displays Table 1 and Table 2.
- Clicking a Tension Length selects it and shows raw detail rows.
- Add/edit/delete actions call the correct API client functions.
- Export button calls the export API and triggers a save/download flow.

Manual verification:

- Run backend tests for wear records.
- Run frontend unit tests for Wear Calculator components/store.
- Run frontend build.
- Start the app and visually verify workbench layout and no overlapping text.

## Next Phase Plan: Packaging, Offline Sync, Hosted Server

The next phase should produce a separate implementation plan for Issue 2.

### Packaging recommendation to analyze

The current app is best aligned with a directory package because:

- Electron already packages the app with `win.target = dir`.
- The backend is a PyInstaller directory under `resources/backend`.
- Production DB path is currently set by Electron to `<packaged app root>/data/analysis.db`.
- A folder package keeps the editable SQLite database and config files visible and backup-friendly.

Single executable packaging is less suitable for editable metadata and SQLite unless the app explicitly externalizes data to `%APPDATA%` or another writable folder. A single exe cannot safely write edited metadata or database content into its embedded application payload.

### Offline sync concept

Offline multi-PC sync should use explicit export/import packages instead of copying raw SQLite files between active users.

Recommended direction:

- Export a sync package containing records, metadata, export timestamp, source machine/user, and row-level `updated_at`.
- Import compares row-level timestamps and preserves newer local edits.
- Conflicts are reported in an import summary.
- SQLite backups are generated before import.

The existing repeated-record import logic already has row-level timestamp comparison patterns that can inform this design.

### Hosted server concept

For an online hosted database, consider:

- A central FastAPI backend hosted on a VPS.
- A managed or self-hosted PostgreSQL database.
- Authentication and role-based access before exposing write APIs.
- HTTPS termination, firewall rules, and backups.
- Migration path from local SQLite to server-side database.

If Cloudzy VPS is used again, the guideline should cover OS hardening, reverse proxy, TLS certificates, backups, and restricted database access. SharePoint may still be useful for file exchange and backups, but it is not a database concurrency layer.

## Risks

- Aggregating by Tension Length can hide severe Class/Track/Section rows. The detail panel mitigates this by keeping raw rows visible.
- Very wide Tension Length tables may need horizontal scrolling or column virtualization.
- Editing raw records changes aggregated historical and projection values immediately; the UI should refresh after mutations.
- Excel export must preserve raw detail data so users can audit aggregate values.

## Out of Scope for Phase 1

- Real-time multi-user database sync.
- Hosted server deployment.
- User authentication.
- SharePoint integration.
- Changing the production package target from `dir` to single exe.
- Replacing SQLite with PostgreSQL.
