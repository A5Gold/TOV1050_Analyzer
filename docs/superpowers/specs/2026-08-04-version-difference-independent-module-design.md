# Version Difference Independent Module Design

Date: 2026-08-04
Status: Approved design, pending implementation plan
Supersedes: `2026-08-04-history-compare-version-difference-design.md` for UI placement and API ownership

## Context

Version Difference currently sits inside History Compare and requests alignment as an optional extension of `/analyze/compare`. This couples raw `ChartData` alignment to repeated-exception analysis, makes the History Compare view larger, and performs work that Version Difference does not need.

The existing graph also places the Plotly legend over the raw chart. With eight traces for two cycles, the legend obscures data. Users cannot centrally hide series, change transparency, or control trace order. The feature currently compares only Latest with Previous 1.

The approved direction is an independent operational module that accepts up to three Exception Report workbooks and compares both earlier cycles against Latest.

## Goals

1. Add `Version Difference` as an independent navigation module and view.
2. Accept two or three Excel reports in explicit roles: Latest, Previous 1, and optional Previous 2.
3. Align Previous 1 and Previous 2 independently against Latest.
4. Show a raw overlay and the differences `Latest - Previous 1` and `Latest - Previous 2`.
5. Keep legends outside Plotly's drawing area.
6. Let users hide series, adjust opacity, and change trace layer order for each chart independently.
7. Reduce loading work by reading only `ChartData` through a dedicated API.
8. Preserve History Compare repeated-table, comparison-chart, edit, export, and database workflows.
9. Preserve Version Difference inputs, request progress, errors, and results when the user visits another module.
10. Support up to six independent Version Difference comparison tabs whose requests may run concurrently.

## Non-Goals

- Comparing Previous 1 directly with Previous 2.
- Supporting more than three reports.
- Changing the existing chainage alignment formula, 0.25 m sampling rule, or quality thresholds.
- Adding Version Difference data to History Compare exports.
- Persisting chart control preferences between application launches.
- Persisting comparison tabs or results after the application process exits.
- Redesigning unrelated navigation or History Compare functions.

## Product Workflow

1. The user opens `Version Difference` from the application sidebar.
2. The user assigns reports to Latest, Previous 1, and optionally Previous 2. Slot order is authoritative; the application does not reorder files by filename date.
3. Compare becomes available after Latest and Previous 1 contain valid Excel files.
4. The application uploads the files to the dedicated endpoint and shows a stable loading skeleton.
5. On success, the user selects Height, Stagger, or Wear and examines:
   - Raw overlay for Latest, shifted Previous 1, and shifted Previous 2 when supplied.
   - `Latest - Previous 1`.
   - `Latest - Previous 2` when Previous 2 was supplied.
6. Each plot has its own toolbar. The Series command opens that plot's controls without covering its drawing area.
7. Changing an input clears the stale result and requires a new comparison.
8. The user may add comparison tabs and start work in another tab while earlier comparisons continue.
9. Leaving Version Difference does not stop active comparisons. Returning restores each tab's files, loading or error state, and completed result.

## Frontend Architecture

### Navigation and View

- Add a new `version-difference` view type and sidebar item.
- Add a standalone `VersionDifferenceView` responsible for rendering file slots, invoking store actions, presenting request state and errors, metric selection, and the chart workspace.
- Remove the Version Difference result tab and alignment request from `HistoryCompareView`.
- Keep reusable plot rendering and series-control logic under a dedicated `components/VersionDifference` directory rather than History Compare.

This boundary keeps the already large History Compare view from owning unrelated raw-cycle analysis.

### Comparison Tabs and Request Lifecycle

- Add a dedicated Zustand store for Version Difference rather than extending `App` or keeping every application module mounted.
- Initialize the store with one tab named `Comparison 1` and allow at most six open tabs.
- Each tab owns its Latest, Previous 1, and Previous 2 files, response, loading state, error, and stable identifier.
- Adding a tab selects it. Closing a tab selects the nearest remaining tab and is disabled when only one tab remains.
- Each tab label exposes its background loading state so the user can see which comparisons are still running while working elsewhere.
- Starting a comparison captures the source tab identifier and its file snapshot. Completion updates that tab even if another tab or application module is active.
- Multiple tabs may have requests in flight concurrently and may complete in any order without overwriting one another.
- Closing a loading tab is allowed. If its request later completes, the store discards the response because the target tab no longer exists.
- File replacement or removal clears only that tab's stale response and error. Inputs in a loading tab remain disabled until its request settles.
- Switching application modules unmounts the Version Difference view, but the store and its asynchronous actions remain active. Returning reconstructs the view from the store without restarting work.
- Chart-only interaction state, including selected metric, zoom, visibility, opacity, and trace order, may return to defaults after a view remount. The API response and visible analytical output remain available.

This design avoids retaining hidden Plotly trees and avoids coupling Version Difference business state to the application navigation shell.

### Input Area

- Three stable file slots: `Latest`, `Previous 1`, and `Previous 2 (Optional)`.
- Each slot supports file picker, drag and drop, replacement, and removal.
- Accepted files follow the application's existing Excel validation rules.
- Compare is disabled until Latest and Previous 1 are populated.
- Removing or replacing any file clears result and API error state.

### Chart Workspace

- Metric selection uses a segmented control for Height, Stagger, and Wear.
- Unavailable metrics are disabled with an accessible explanation.
- All visible plots share the same chainage zoom range. Reset Zoom restores each metric's complete available range.
- Plotly uses `scattergl`, does not connect gaps, and has `showlegend: false`.
- Cycle color remains consistent across charts. Channel number remains encoded by line dash.

The layout contains:

1. Raw overlay.
2. Latest - Previous 1.
3. Latest - Previous 2, only when Previous 2 exists.

### Per-Chart Series Toolbar

The approved UI is option C: each chart has an independent compact toolbar.

- The Series command opens a popover anchored to the chart toolbar.
- Raw overlay controls are grouped by Latest, Previous 1, and Previous 2. Each group has a master visibility toggle and opacity slider and can expand to four channel rows.
- Difference controls contain four channel rows.
- Channel rows expose visibility and move-up/move-down icon buttons.
- Reordering changes Plotly trace array order; the last trace is rendered on top.
- Controls are keyboard reachable, have visible focus, and use explicit accessible names.
- Closing the popover leaves settings active. Settings remain local to the current result and reset on a new comparison.
- On narrow layouts, the popover is constrained to the viewport and scrolls internally rather than overlapping unrelated controls.

## API Design

### Endpoint

`POST /analyze/version-difference`

Multipart fields:

- `latest`: required Excel file.
- `previous_1`: required Excel file.
- `previous_2`: optional Excel file.

The endpoint preserves the explicit roles. It does not sort filenames and does not update History Compare result/export globals.

### Processing

1. Read each workbook once and extract only its `ChartData` sheet.
2. Validate Latest and Previous 1 before alignment.
3. Call the existing pure alignment helper for Latest versus Previous 1.
4. If supplied, call it independently for Latest versus Previous 2.
5. Return the successful and unavailable comparison results together so one unavailable previous cycle or metric does not hide usable data.

No repeated-exception sheets are parsed, and `RepeatedExceptionFinder` is not invoked.

### Response Contract

```json
{
  "status": "ready",
  "latest_file": "20260611.xlsx",
  "comparisons": [
    {
      "key": "previous_1",
      "previous_file": "20260521.xlsx",
      "status": "ready",
      "reason": null,
      "step_m": 0.25,
      "max_shift_m": 50.0,
      "metrics": {
        "height": {},
        "stagger": {},
        "wear": {}
      }
    },
    {
      "key": "previous_2",
      "previous_file": "20260412.xlsx",
      "status": "ready",
      "reason": null,
      "step_m": 0.25,
      "max_shift_m": 50.0,
      "metrics": {
        "height": {},
        "stagger": {},
        "wear": {}
      }
    }
  ]
}
```

Each metric retains the existing alignment result fields: status, reason, shift, RMSE, normalized RMSE, overlap, valid-point count, chainage, latest channels, shifted previous channels, and difference channels.

The frontend builds the raw overlay from Latest and shifted previous traces in the comparison results. Each trace uses its comparison's chainage array, so comparisons may have different union ranges without interpolation.

## Validation and Error Handling

- Missing Latest or Previous 1: HTTP 422 with a role-specific message.
- Unsupported or unreadable workbook: HTTP 400 with the affected role and a safe explanation.
- Latest missing `ChartData`: HTTP 422 because no comparison can proceed.
- Previous file missing `ChartData`: HTTP 200 with that comparison marked unavailable; another comparison may remain usable.
- Individual metric missing or lacking trustworthy overlap: that metric remains unavailable with the alignment helper's reason.
- Unexpected server error: HTTP 500 with a stable user-facing message and full server-side logging.
- Frontend request failure: preserve the selected files, show an error alert, and allow retry.
- Partial response: render available metrics and comparison panels while placing the reason in affected panels.

The API never fabricates zero difference values for gaps or unavailable alignment.

## Performance

- The dedicated endpoint reads only `ChartData` and avoids repeated-exception comparison, result grouping, statistics, and export-cache updates.
- Each upload is read once per request.
- Alignment continues to use normalized tick maps and NumPy arrays.
- The frontend uses WebGL traces and memoizes trace construction from response data and control state.
- Plot dimensions remain stable while controls, loading state, and unavailable messages change.

## Testing Strategy

### Backend

- Two-file request returns one comparison with `previous_1`.
- Three-file request returns two comparisons in role order.
- Both previous cycles align independently to Latest.
- The endpoint does not call repeated-exception matching or modify History Compare caches.
- Latest missing `ChartData`, previous missing `ChartData`, corrupt workbook, and unsupported file are covered.
- A missing metric in one comparison does not remove available metrics or the other comparison.
- Existing alignment unit tests continue to cover direction, gaps, nulls, quality thresholds, and deterministic tie-breaking.

### Frontend

- Sidebar navigation opens the independent module.
- Compare enablement and multipart field roles are correct for two and three files.
- Replacing or clearing files invalidates stale results.
- Previous 2 panel is conditional.
- Raw overlay contains two or three cycle groups as appropriate.
- Plotly legends are disabled.
- Visibility, opacity, and trace move actions affect only the selected chart.
- Zoom synchronization and Reset Zoom cover all visible plots.
- Loading, empty, full error, partial comparison, and unavailable metric states are covered.
- An unresolved comparison survives view unmount and writes its result to the originating tab after resolution.
- Two tabs can compare concurrently and retain the correct results when responses resolve in reverse order.
- Switching tabs preserves each tab's files, loading state, errors, and result without leaking state to another tab.
- Closing a loading tab safely ignores its eventual response.
- The add action stops at six open tabs, and the final remaining tab cannot be closed.
- History Compare no longer requests alignment and its existing result workflows remain green.

### Reference Workflow

Run the complete three-file workflow with the supplied EAL U2 Exception Reports dated 2026-04-12, 2026-05-21, and 2026-06-11. Verify all available metrics, both Latest-based differences, series controls, and responsive layout in the packaged desktop viewport.

## Migration

The worktree already contains an in-progress two-file Version Difference implementation inside History Compare. Implementation will preserve its alignment algorithm and applicable tests while moving ownership to the new endpoint and standalone view. History Compare-specific state and response fields will be removed only after the independent workflow is covered.

No unrelated dirty-worktree changes are to be reverted or included in the feature commit.

## Risk and Scope Control

Codebase impact analysis marks the `HistoryCompareView` to `App` path as HIGH/CRITICAL. The implementation therefore minimizes changes to History Compare, adds the new view through the established navigation switch, and protects both modules with focused regression tests.

Before committing implementation, re-index the codebase graph and verify the changed symbol scope and callers.
