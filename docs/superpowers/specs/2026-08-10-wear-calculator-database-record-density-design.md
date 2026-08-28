# Wear Calculator and Database Record Density Design

**Date:** 2026-08-10
**Status:** Approved
**Scope:** Wear Calculator historical records, latest summary, remaining life, and Database Record viewport usage

## Context

TOV640 Analyzer is a high-density Windows maintenance analysis workbench. The affected screens currently spend too much horizontal or vertical space on duplicated actions, oversized table geometry, combined chart content, and persistent control regions. These defects reduce the number of maintenance records that can be inspected without scrolling and make the primary data surfaces harder to scan.

The changes in this design preserve existing MUI and Plotly conventions, API contracts, filtering behavior, pending-change semantics, and record editing workflows. The work is a targeted evolution of the current interface, not a redesign.

## Goals

- Remove the duplicate row-delete affordance from Historical Avg Wear Min.
- Make Latest Summary display a useful number of tension-length columns in the initial viewport.
- Separate EAL and TML remaining-life curves and apply the requested line colors.
- Add explicit Estimated life severity presentation with deterministic boundary rules.
- Let the Database Record table use the available desktop viewport instead of being compressed by persistent controls.
- Preserve existing data, validation, filtering, editing, import, export, and pending-change behavior.

## Non-goals

- Replacing MUI tables with MUI DataGrid.
- Changing wire-wear calculations, remaining-life formulas, API payloads, or database schemas.
- Changing the meaning or ordering of tension lengths, metrics, lines, sections, or filters.
- Redesigning unrelated Wear Calculator or Database Record workflows.
- Introducing a new design system or changing global visual tokens.

## Design Decisions

### 1. Historical Avg Wear Min row deletion

Each Cycle Date row will expose one row-level delete action: the existing trash-bin icon button.

- Remove `MoreVertIcon`, its per-row action button, the `Menu`, and the `Delete Row` menu item.
- Keep the existing `onDeleteRow(cycleDate)` callback and accessible label on the trash-bin button.
- Keep the cycle date, pending marker, and delete button on one line. The cell may truncate or reserve compact action space, but it must not wrap because of duplicate actions.
- Cell-level delete buttons remain unchanged because they delete individual tension-length values rather than the entire cycle row.

### 2. Latest Summary table density

The table will continue to use a fixed Metric column followed by horizontally arranged tension-length columns, but width calculations will describe only the rendered column window.

- Keep Metric as the sticky semantic anchor at a fixed width of 176px, sufficient for `Wear Rate (mm / year)` without excessive whitespace.
- Give each tension-length column a fixed width of 96px with compact horizontal padding.
- Replace the current 25-column page with a 12-column rendering window.
- Calculate table width from the visible columns, not every tension length in the complete dataset.
- Preserve canonical tension-length order, horizontal scrolling, current value formatting, sticky header behavior, and pagination controls.
- Pagination text must describe tension lengths rather than rows.

The implementation will use the fixed 12-column window and must not add ResizeObserver-driven column calculations.

### 3. Remaining Life presentation

#### Curve separation

`RemainingLifeCurve` will render two independent chart regions:

- EAL chart color: light blue `#64b5f6`.
- TML chart color: brown `#8d6e63`.
- Each chart receives only rows belonging to its line group.
- Each chart preserves its own title, axes, legend, responsive resizing, and Plotly interaction.
- If a line has no eligible selected curve, its chart region shows a concise line-specific empty state instead of a blank plot.

The existing default-row and manually selected-row behavior remains unchanged. A tension length is still deduplicated by `lineGroup:tensionLength`.

#### Estimated life severity

The Estimated life cell will derive a presentation category using this priority order:

1. `non_positive_rate`: grey.
2. Remaining life less than or equal to 10 years: red.
3. Remaining life greater than 10 and less than or equal to 30 years: yellow.
4. Remaining life greater than 30 years: green.
5. Other semantic states such as insufficient data or already at threshold retain explicit text and use an appropriate neutral or existing error treatment.

The boundary comparison should use the numeric remaining-life value, preferably `remainingDays / 365.25`, rather than parsing the formatted display string. Color is supplementary: the existing Estimated life text remains visible, and contrast must work in both light and dark themes.

### 4. Database Record viewport use

The Database Record screen will use normal page scrolling for its control regions and a definite-height DataGrid for virtualized records.

#### Scrolling contract

- The page header, action toolbar, EAL/TML tabs, and Section controls remain in normal document flow and scroll out of view.
- Filters are collapsed by default and can be expanded manually.
- Only DataGrid's own column and group headers remain sticky within the grid.
- The page root must not use a desktop `overflow: hidden` rule that prevents normal document scrolling.

#### Collapse contract

The current outer `Collapse` plus inner `Accordion` creates two independent expansion controls. Replace it with one source of truth.

- The LineTabPanel filter toggle is the only owner of whether the filter content is shown.
- FilterPanel renders one compact filter surface without `Accordion`, `AccordionSummary`, or its own expansion state.
- Switching EAL/TML must preserve existing independent filter data behavior.
- Clear All continues to reset the active line's filters and refetch with the established API filter rules.

#### Density and grid height

- Reduce excess padding in the page header, line tabs, and section controls without reducing readable target sizes or changing labels.
- Keep the DataGrid inside a definite-height region using the existing `fillDataRegionSx` height contract, or an equivalent local `calc(100dvh - 220px)` height with a 520px minimum, so virtualization and scrollbars remain reliable.
- Remove competing fixed-height formulas that allocate viewport space twice.
- The table region must display multiple data rows at the reference desktop viewport when filters are collapsed.
- Expanded filters may reduce visible rows temporarily, but the page must remain scrollable and the grid must retain a usable minimum height.

## Existing Worktree Integration

The working tree already contains uncommitted changes in Remaining Life, Wear Projection, chart utilities, the wear-record store, API types, tests, screenshots, and backend analytics. Implementation must preserve and integrate these changes.

In particular:

- Keep the shared wear threshold state and null-safe Remaining Life behavior already present.
- Keep existing non-positive-rate formatting and extend it with visual severity rules.
- Do not revert unrelated backend analytics or tests.
- Review changes at hunk level before editing files that already differ from `HEAD`.

## Expected Implementation Surface

Primary files:

- `frontend/src/components/Calculation/WearHistoryPivotTable.tsx`
- `frontend/src/components/Calculation/WearLatestSummaryTable.tsx`
- `frontend/src/components/Calculation/RemainingLifePanel.tsx`
- `frontend/src/components/Calculation/RemainingLifeCurve.tsx`
- `frontend/src/views/DatabaseRecordView.tsx`
- `frontend/src/components/DatabaseRecord/LineTabPanel.tsx`
- `frontend/src/components/DatabaseRecord/FilterPanel.tsx`
- `frontend/src/components/DatabaseRecord/RepeatedRecordTable.tsx`
- `frontend/src/utils/pageLayout.ts`, only if a shared layout contract can be changed without affecting unrelated views

Tests expected to change:

- `frontend/src/components/Calculation/__tests__/WearWorkbenchTables.test.tsx`
- `frontend/src/components/Calculation/__tests__/RemainingLifePanel.test.tsx`
- A focused `RemainingLifeCurve` test if Plotly trace assertions do not fit the panel test
- `frontend/src/views/__tests__/DatabaseRecordView.test.tsx`
- `frontend/src/components/DatabaseRecord/__tests__/LineTabPanel.test.tsx`
- `frontend/src/components/DatabaseRecord/__tests__/RepeatedRecordTable.test.tsx`
- `frontend/src/utils/__tests__/pageLayout.test.ts`, only if shared page layout values change

## Testing Strategy

### Automated tests

- Historical table renders one row-delete button and no row-actions menu.
- Historical cell delete remains available and distinct from row delete.
- Latest Summary preserves canonical tension-length order and renders only the configured visible window for a wide dataset.
- Latest Summary width is based on visible columns and keeps Metric and tension-length widths compact.
- Remaining Life groups Plotly traces into separate EAL and TML charts with exact requested colors.
- Remaining Life handles a line with no selected eligible curve.
- Estimated life category tests cover non-positive rate, exactly 10 years, between 10 and 30 years, exactly 30 years, and more than 30 years.
- Database Record filters start collapsed and use one expansion control.
- EAL/TML and Section filtering, counts, Clear All, batch edit, and table rendering continue to work.
- Layout tests confirm the page can scroll and the DataGrid still has a definite usable height.

### Manual verification

- Compare all five supplied screenshots against the updated application.
- Verify desktop widths representative of maximized and smaller Electron windows.
- Confirm the Database Record table displays several rows with filters collapsed.
- Confirm page scrolling moves the header, tabs, sections, and filters out of view.
- Confirm DataGrid vertical and horizontal scrollbars remain usable.
- Verify light and dark themes, keyboard focus, tooltip labels, and semantic text.

### Commands

Before the first npm command in each PowerShell process, set `NODE_USE_SYSTEM_CA=1`.

- Run focused frontend Vitest files for the changed components.
- Run the complete frontend test suite.
- Run the supported root frontend build command.
- Start the supported root development command for viewport verification.

## Impact and Risk

Codebase-memory reports direct main-screen callers for the Wear workbench tables and Database Record components, so their immediate impact paths are classified as CRITICAL. The behavioral blast radius is constrained to the two requested modules, but layout regressions could affect table virtualization, scrolling, filter state, and existing navigation tests.

Risk controls:

- Preserve callback and store interfaces.
- Avoid shared page-layout changes unless targeted styles cannot solve the problem.
- Add focused boundary and viewport-contract tests before broad visual verification.
- Re-index the repository after implementation and verify changed scope before any final commit.

## Development Sequencing and Delegation

1. Update and test the two Wear Records tables.
2. Add Remaining Life severity classification and split charts, integrating existing dirty changes.
3. Refactor the Database Record height and single-collapse contract.
4. Run focused tests, then the full frontend suite and build.
5. Perform browser or Electron viewport verification against the supplied screenshots.
6. Re-index codebase-memory and verify affected scope.

During implementation, Database Record layout and its focused tests may be delegated to a subagent because that work is bounded to a separate component cluster. The primary agent will retain ownership of shared layout decisions, integrate all changes, inspect the final diff, and run end-to-end verification.

## Documentation Impact

`PRODUCT.md` and `DESIGN.md` were reviewed. This work does not change the product purpose, target users, positioning, workflow principles, accessibility expectations, global tokens, typography, or reusable visual system. No updates are required unless implementation reveals a new reusable layout convention beyond this targeted fix.

## Acceptance Criteria

- Historical Avg Wear Min has exactly one row-delete affordance per Cycle Date row and does not wrap because of duplicated row actions.
- Latest Summary initially shows a practical multi-column tension-length view at the reference desktop viewport.
- Remaining Life shows separate EAL and TML graphs using the exact requested colors.
- Estimated life uses grey, green, yellow, and red according to the approved priority and year boundaries while retaining readable text.
- Database Record controls scroll away, filters start collapsed, and the table shows multiple rows in the available desktop viewport.
- Existing data, filter, edit, save, import, export, pending-change, and threshold workflows remain functional.
- Focused tests, full frontend tests, build, and manual viewport checks pass.
