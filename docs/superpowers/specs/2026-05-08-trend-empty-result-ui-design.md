# Trend Analyzer Empty Result UI Design

Date: 2026-05-08
Scope: Trend Analyzer empty-result feedback when `n_Repeated Exception Report` is uploaded and the backend returns `0` matching results.

## Problem

The backend bug for the `repeated_records=[]` case is fixed, but the frontend still treats an empty result set as if analysis has not happened yet.

Current behavior in Trend Analyzer:
- Before analysis: the page shows the default idle prompt.
- After analysis with results: the page shows the result table and chart.
- After analysis with `0` results: the page falls back to the same idle prompt.

This is misleading because the user cannot tell whether:
- analysis has not started, or
- analysis completed successfully but the repeated-filter produced no matching L2 Wire Wear alarms.

The practical effect is that users may click `Analyze` repeatedly because the UI does not acknowledge completion.

## Goal

Make the Trend Analyzer UI explicitly acknowledge successful completion when the result set is empty, especially for the repeated-report filter case.

## Non-Goals

- No backend behavior changes.
- No changes to trend result table columns or chart logic.
- No change to analysis rules or wording outside the empty-result experience.

## Recommended Approach

Introduce an explicit post-analysis empty state in Trend Analyzer, separate from the pre-analysis idle state.

This keeps the UI semantics clear:
- `idle`: no analysis has been run yet
- `success-with-results`: analysis completed and returned rows
- `success-empty`: analysis completed successfully and returned `0` rows

## UX Design

### Idle State

Shown when the user has not run analysis for the current tab state.

Content:
- Keep the existing helper message:
  - `Upload Exception Report files from multiple inspection dates and click Analyze`

### Success With Results

Shown when `trendResults.length > 0`.

Content:
- Keep the existing chart and result table behavior unchanged.

### Success Empty

Shown when the analysis request succeeds and returns an empty `trend_results` array.

Content:
- Replace the idle prompt with a dedicated empty-result panel.
- Use the approved wording:
  - `No matching L2 Wire Wear alarms found in the uploaded n_Repeated Exception Report after filter.`
  - `The analysis completed successfully with 0 result.`

Presentation:
- Render the message in a distinct informational/success UI block so it is visually different from the idle prompt.
- Keep the Analyze button available so the user can rerun after changing files.

## State Model

Add a lightweight analysis-status signal to each trend tab.

Recommended tab fields:
- `hasAnalyzed: boolean`

Derived rendering rules:
- `!hasAnalyzed`: show idle state
- `hasAnalyzed && trendResults.length === 0`: show success-empty state
- `trendResults.length > 0`: show success-with-results state

This is sufficient without introducing a more complex enum because the current flow only needs to distinguish:
- never run
- completed with no rows
- completed with rows

## State Transitions

### On Analyze Start

- Keep `isLoading=true`
- Clear `error`

Do not reset the uploaded files.

### On Analyze Success

- Set `hasAnalyzed=true`
- Store `trendResults`
- If results exist, keep current selected-row behavior
- If results are empty, clear `selectedResult`

### On Analyze Failure

- Keep `hasAnalyzed=false`
- Show existing error alert

Failure should not be presented as an empty-result success state.

### On Input Changes

When the user changes the analysis inputs, reset the analysis-completion state for the active tab:
- add/remove Exception Report file
- set/remove repeated file
- reset tab

Recommended reset behavior:
- `hasAnalyzed=false`
- `trendResults=[]`
- `selectedResult=null`
- `error=null`

This prevents stale success-empty messaging from remaining visible after the user changes input files.

## Implementation Notes

Primary files expected to change:
- `frontend/src/store/useTrendStore.ts`
- `frontend/src/views/TrendAnalyzerView.tsx`
- relevant frontend tests for Trend Analyzer view/store

Suggested UI structure in `TrendAnalyzerView`:
- keep the current top upload panel
- branch the result area into:
  - results panel
  - empty-result panel
  - idle panel

## Testing

Add or update frontend tests to cover:

1. Idle state before analysis
- shows the default upload/analyze helper text

2. Success empty state
- after successful analysis with `trend_results=[]`, shows:
  - `No matching L2 Wire Wear alarms found in the uploaded n_Repeated Exception Report after filter.`
  - `The analysis completed successfully with 0 result.`

3. Success with results
- existing result table still renders when rows are returned

4. Reset on file changes
- after empty-result success, changing uploaded files or repeated file returns the tab to idle state

5. Failure path
- API failure still shows the error alert and does not show the empty-result success message

## Risk

Low.

This change is frontend-only and does not alter calculation logic or API contracts. The main risk is stale UI state, which is addressed by resetting analysis-completion state whenever input files change.
