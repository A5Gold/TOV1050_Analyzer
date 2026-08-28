# Wear Table Ordering, Export, and Database Filter Design

**Date:** 2026-08-10
**Status:** Approved
**Scope:** Wear Calculator historical and latest-summary tables; Database Record filter and section surfaces

## Context

TOV640 Analyzer is a high-density Windows maintenance analysis workbench. Wear Calculator currently presents tension-length columns in the order received from the workbench response. That order is not consistently canonical, so Historical Avg Wear Min and Latest Summary can show sequences such as `H02, H04, H01, H03` or `4, 3, 6, 5`. The two tables also diverge in selected-column indication and horizontal navigation.

Database Record now allows the data table to use more of the display window, but expanding Filters exposes a competing fixed-height and overflow boundary. Part of the filter surface can be covered by the table. The Section control band also uses the canvas background instead of the white surface used by the surrounding EAL/TML controls.

This work is a targeted correction. It preserves existing calculations, API payloads, persistence, filtering semantics, pending-change behavior, MUI component vocabulary, and user workflows.

## Goals

- Give Historical Avg Wear Min and Latest Summary one deterministic tension-length order.
- Show the top-bar tension-length selection consistently in both tables.
- Prevent sticky table headers from visually overlapping the first data row.
- Replace Latest Summary column pagination with native horizontal scrolling over all columns.
- Export the complete Historical Avg Wear Min matrix for the active Line/Class to Excel.
- Ensure expanded Database Record filters remain fully visible above the data table.
- Give the EAL/TML Section band the same white surface as the surrounding controls.

## Non-goals

- Changing tension-length metadata, measurements, calculations, database schemas, or API response shapes.
- Replacing the current MUI tables or Database Record DataGrid.
- Exporting only visible columns, selected columns, or the current horizontal viewport.
- Adding user-configurable sort modes or column reordering.
- Redesigning unrelated Wear Calculator or Database Record workflows.
- Changing global visual tokens or introducing another component library.

## Design Decisions

### 1. Canonical tension-length order

The Wear workbench frontend boundary will establish one canonical column order before data reaches either table or the Excel exporter.

The comparator will mirror the existing backend metadata order:

1. `H`-prefixed values, ordered by their numeric suffix.
2. Pure numeric values, ordered numerically.
3. `X`, `T`, `D`, `M`, and `L` prefixes in that order, with numeric suffixes ordered numerically.
4. Other values in a deterministic, case-insensitive natural order.
5. Equivalent normalized keys retain their original relative order.

Examples:

- `H01, H02, H03, H04, H05, H06`
- `3, 4, 5, 6, 7, 8, 10`
- `H02` sorts before `4`, and numeric values sort before `X01`.

A small pure helper will own this logic. `WearRecordsPanel` will derive sorted workbench columns once and pass the same array to Historical Avg Wear Min, Latest Summary, and the Excel export builder. Row values and summary values remain keyed by the original tension-length string, so sorting changes presentation only.

The API mapper and backend calculation flow will not be changed for this correction. This avoids duplicating sorting inside each table while keeping the UI robust if a workbench response arrives in an unexpected order.

### 2. Shared selected-column presentation

The top-bar `selectedTensionLength` remains the single selection source.

- Historical Avg Wear Min keeps its existing selected header and cell treatment.
- Latest Summary receives `selectedTensionLength` and applies the same semantic selected state to its matching header and metric cells.
- Selected cells expose `aria-selected` and a stable data attribute for tests.
- Selection is communicated by a light primary background plus a stronger header underline, not by color alone; the selected tension-length text remains visible.
- When selection changes, each table scrolls horizontally enough to reveal the selected column without changing column order.

The two tables keep independent scroll containers. Selecting a tension length reveals it in both containers, but manual scrolling in one table does not force the other table to follow continuously.

### 3. Sticky-header layering

Both tables will use an explicit opaque-layer contract:

- Normal body cells form the base layer.
- Sticky first-column body cells sit above horizontally scrolling body cells.
- Sticky header cells sit above body cells and use an opaque `background.paper` surface.
- The corner cell, `Cycle Date` or `Metric`, sits above both sticky axes.
- Header cells retain a bottom divider so the boundary remains visible during vertical scrolling.

No header cell may inherit a translucent background that allows values from the first row to show through. The existing compact widths and vertical scroll limits remain unless a small adjustment is required to make the header boundary reliable.

### 4. Latest Summary horizontal navigation

Latest Summary will render every sorted tension-length column in one table.

- Remove column `TablePagination`, page state, page effects, and visible-column slicing.
- Keep Metric fixed at 176px and each tension-length column fixed at 96px.
- Set table width or minimum width from `176 + columns.length * 96`.
- Keep Metric sticky on the left and the table header sticky on vertical scroll.
- Use the native horizontal scrollbar of the `TableContainer`.
- Preserve value formatting, ellipsis, titles, empty values, and metric order.

This matches the Historical table interaction and supports direct comparison without page boundaries hiding adjacent tension lengths.

### 5. Historical Avg Wear Min Excel export

An `Export Excel` action will appear in the Historical Avg Wear Min title row. It will use the existing MUI download icon and the already-installed `xlsx` dependency.

The export content is the complete current matrix:

- Scope: the currently selected Line/Class in the Wear Records workbench.
- Rows: every historical cycle row in the current matrix, not only the current vertical page.
- Columns: `Cycle Date` followed by every canonical sorted tension length.
- Values: the same effective values currently represented by the workbench, including staged add/edit values visible in the table. Pending deletions must follow the table's effective data semantics rather than silently exporting a stale pre-edit snapshot.
- Horizontal scope: independent of current scroll position, virtualization window, selected tension length, or visible cells.
- Row order: the same descending cycle-date order used by the table.
- Empty cells: exported as empty workbook cells.
- Numeric wear values: exported as numeric cells, not formatted strings.

The filename will identify the active Line/Class and report purpose, for example `EAL_Historical_Avg_Wear_Min.xlsx` or `LMC_Historical_Avg_Wear_Min.xlsx`. Invalid filename characters will be sanitized. The button is disabled when there are no columns or no historical rows.

The export is a client-side view export and does not replace the existing committed cycle-report or data-package exports.

### 6. Database Record filter layout contract

The filter surface, section controls, and DataGrid will participate in one predictable vertical flow.

- Keep `LineTabPanel` as the only owner of the filter expanded state.
- The expanded `Collapse` must be allowed to contribute its complete measured height.
- The filter Paper and its controls must not be clipped by a parent `overflow: hidden` boundary.
- The data region begins after the expanded filter surface and keeps a definite usable height for DataGrid virtualization.
- Normal page scrolling remains available when the combined controls and grid exceed the viewport.
- The grid keeps its own internal vertical and horizontal scrolling.
- Filter controls may wrap according to existing MUI Grid breakpoints; buttons and date controls must remain completely visible.

The preferred implementation is a targeted height/overflow correction in `DatabaseRecordView` and `LineTabPanel`. Shared `pageLayout` constants will only change if impact analysis shows the change is safe for every consumer.

Collapsing Filters must recover the compact table-first layout. Expanding Filters may move the table downward, but it must never overlay or cover any filter control.

### 7. Database Record Section surface

The Section control band below the EAL/TML tabs will use `background.paper` rather than `background.default`.

- The band, toggle buttons, labels, count chips, horizontal overflow, and selection behavior remain unchanged.
- Selected section state continues to use the established primary MUI treatment.
- The white surface applies consistently for both EAL and TML.
- Light and dark themes use the semantic theme token rather than a hard-coded white value.

## Data and State Flow

```text
Workbench API response
        |
        v
canonical tension-length sorter
        |
        +--> Historical table
        +--> Latest Summary table
        +--> Historical Excel column order

selectedTensionLength store state
        |
        +--> Historical selected column + reveal
        +--> Latest Summary selected column + reveal
```

Database Record line, section, and filter values retain their current local/store ownership. This design changes only layout containment and surface styling, not API filter construction or fetch timing.

## Expected Implementation Surface

Primary Wear files:

- `frontend/src/components/Calculation/WearRecordsPanel.tsx`
- `frontend/src/components/Calculation/WearHistoryPivotTable.tsx`
- `frontend/src/components/Calculation/WearLatestSummaryTable.tsx`
- A focused tension-length ordering/export helper under `frontend/src/components/Calculation/` or `frontend/src/utils/`

Primary Database Record files:

- `frontend/src/views/DatabaseRecordView.tsx`
- `frontend/src/components/DatabaseRecord/LineTabPanel.tsx`
- `frontend/src/components/DatabaseRecord/FilterPanel.tsx`, only if local spacing or wrapping is required
- `frontend/src/utils/pageLayout.ts`, only if shared impact is verified first

Expected tests:

- `frontend/src/components/Calculation/__tests__/WearWorkbenchTables.test.tsx`
- `frontend/src/components/Calculation/__tests__/WearRecordsPanel.test.tsx`
- A focused helper/export test if separating these responsibilities improves clarity
- `frontend/src/components/DatabaseRecord/__tests__/LineTabPanel.test.tsx`
- `frontend/src/views/__tests__/DatabaseRecordView.test.tsx`

## Testing Strategy

### Automated tests

- Comparator tests cover shuffled `H` values, pure numeric values such as `4, 3, 6, 5, 8, 7, 10`, known prefix groups, unknown labels, and stable equal keys.
- Both Wear tables receive and render the identical sorted column sequence.
- Latest Summary renders all columns, contains no column pagination, and exposes horizontal overflow.
- Selecting a tension length marks the matching header and cells in both tables and triggers reveal behavior.
- Sticky header and sticky first-column cells use opaque backgrounds and the expected layer order.
- Excel export writes `Cycle Date` plus every sorted tension-length column, every history row, numeric values, empty cells, and the approved filename.
- Excel export remains complete when the selected tension length is near the end of a wide column set.
- Database Record Filters start collapsed, expand through one control, and remain in layout before the table.
- Section bands use the semantic paper background for EAL and TML.
- Existing line/section filtering, Clear All, record counts, batch editing, and DataGrid rendering remain functional.

### Browser verification

At minimum verify a 1440x900 desktop viewport and a narrower supported Electron window:

- Compare both Wear tables against `docs/screenshot/Historical Avg Wear Min & Latest Summary Table.png`.
- Confirm canonical column order is identical in both tables.
- Select an early, middle, and late tension length and confirm both tables reveal and highlight it.
- Scroll vertically in both tables and confirm the header does not overlap the first row.
- Scroll Latest Summary horizontally from first to last tension length without pagination.
- Export the workbook, parse it back, and verify complete row/column counts and representative values.
- Compare Database Record against `docs/screenshot/Database Record - Filter Tab does not show all button.png`.
- Expand Filters and confirm every button and input remains visible above the grid.
- Collapse Filters and confirm the data table regains the compact viewport.
- Switch EAL/TML and Section tabs and confirm the white surface and existing behavior.
- Check light and dark theme contrast, keyboard focus, and native scrollbars.

### Commands

Before the first `npm`, `npx`, or `npm exec` command in each PowerShell process, set `NODE_USE_SYSTEM_CA=1`.

- Run focused Vitest files for the sorter, Wear tables, Wear Records panel, LineTabPanel, and DatabaseRecordView.
- Run the complete frontend test suite and record any unrelated pre-existing failures separately.
- Run `npm --prefix frontend run build`.
- Start the supported root development command and perform Playwright browser verification.

## Impact and Risk

Codebase-memory identifies `WearRecordsPanel`, the two Wear tables, `LineTabPanel`, and `DatabaseRecordView` as main-screen components with direct user workflow impact. The main risks are inconsistent ordering, exporting stale or partial data, sticky-layer regressions, and breaking DataGrid virtualization through an indefinite height.

Risk controls:

- Use one pure comparator and one sorted column array.
- Keep row and summary lookup keyed by the original tension-length identifier.
- Test Excel output by reading the generated workbook rather than only asserting a download click.
- Preserve selected state in the existing store and pass it down explicitly.
- Keep the DataGrid inside a definite-height region while allowing the surrounding page to scroll.
- Run codebase-memory impact analysis before editing every affected symbol and verify changed scope before commit.
- Preserve unrelated dirty backend, Projection, API type, document, and screenshot changes.

## Development Sequencing and Delegation

1. Add the canonical tension-length ordering helper and tests.
2. Apply the sorted columns at the Wear workbench boundary.
3. Update Latest Summary selection, sticky layering, and horizontal scrolling.
4. Add full-matrix Historical Excel export and tests.
5. Correct shared sticky presentation in Historical Avg Wear Min.
6. Correct Database Record filter containment and Section surface.
7. Run focused tests, full frontend tests, build, and browser verification.
8. Re-index codebase-memory and verify final affected scope before commit.

Database Record layout and focused tests are a bounded, independent component cluster and should be delegated to a subagent during implementation. The primary agent retains ownership of the Wear ordering/export work, integration review, shared layout decisions, final diff inspection, and complete verification.

## Documentation Impact

`PRODUCT.md` and `DESIGN.md` were reviewed. This correction does not change product purpose, target users, positioning, workflow principles, accessibility expectations, global tokens, typography, or reusable visual-system conventions. No update is required unless implementation introduces a reusable layout or export convention beyond this scoped fix.

## Acceptance Criteria

- Historical Avg Wear Min and Latest Summary show the same canonical tension-length order.
- Mixed labels sort deterministically, including correctly ordered `H` values and numeric values.
- Selecting a tension length in the top bar highlights and reveals it in both tables.
- Sticky headers remain readable and do not overlap or show values from the first body row.
- Latest Summary has no tension-length pagination and supports native horizontal scrolling through all columns.
- Historical Avg Wear Min exports every history row and every sorted tension-length column for the active Line/Class, independent of the current viewport.
- Exported wear values are numeric, empty cells remain empty, and the filename identifies the active Line/Class.
- Expanded Database Record filters show every control without being covered by the table.
- The Database Record grid remains scrollable and keeps a definite usable height.
- EAL/TML Section bands use the semantic white paper surface.
- Existing calculation, filter, edit, save, import, export, pending-change, and navigation behavior remains functional.
- Focused tests, production build, and browser verification pass; unrelated full-suite failures are documented rather than hidden.
