# History Compare Empty State Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish a low-risk consistency pass for `History Compare` so empty-result states, summary messaging, and filter/result transitions read as one coherent workflow without changing backend logic or grid structure.

**Architecture:** Keep the work local to `HistoryCompareView`, `ComparisonDataGrid`, and focused tests. Treat this batch as a UX consistency and state-contract cleanup on top of the recently-fixed filter behavior: preserve existing compare logic, business actions, and column model, while clarifying what the user sees when there are no matches, no filtered rows, or no compare run yet.

**Tech Stack:** React 18, TypeScript, MUI 5, Vitest, Testing Library, Vite

---

## Scope Guard

- Stay inside:
  - `frontend/src/views/HistoryCompareView.tsx`
  - `frontend/src/components/HistoryCompare/ComparisonDataGrid.tsx`
  - `frontend/src/views/__tests__/HistoryCompareView.test.tsx`
  - `frontend/src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx`
- Do not change:
  - backend compare API
  - upload parsing logic
  - `ComparisonFilterPanel` filter semantics
  - `SaveToDBDialog`, `Check1YearDialog`, `BatchEditDialog`
  - repeated-data business rules
  - sticky/frozen grid behavior

## File Map

- Modify: `frontend/src/views/HistoryCompareView.tsx`
  - make filter-result state transitions explicit and stable
  - keep toolbar logic intact
- Modify: `frontend/src/components/HistoryCompare/ComparisonDataGrid.tsx`
  - clarify empty-state copy and differentiate zero-match scenarios
- Modify: `frontend/src/views/__tests__/HistoryCompareView.test.tsx`
  - cover unfiltered vs filtered-empty transitions
- Modify: `frontend/src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx`
  - cover empty-state messaging variants

### Task 1: Lock the Empty-Result State Contract with Failing Tests

**Files:**
- Modify: `frontend/src/views/__tests__/HistoryCompareView.test.tsx`
- Modify: `frontend/src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx`

- [ ] **Step 1: Add a failing `HistoryCompareView` test for filtered-empty persistence**

```tsx
it('keeps filtered empty results visible until filters are cleared', async () => {
  const user = userEvent.setup();

  render(<HistoryCompareView />);

  expect(screen.getByText('Grid rows: 1')).toBeInTheDocument();

  await user.click(screen.getByRole('button', { name: /Apply empty filter/i }));
  expect(await screen.findByText('Grid rows: 0')).toBeInTheDocument();

  await user.click(screen.getByRole('button', { name: /Apply full data/i }));
  expect(await screen.findByText('Grid rows: 1')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the single `HistoryCompareView` test file to verify it fails**

Run: `npm test -- --run src/views/__tests__/HistoryCompareView.test.tsx`

Expected: FAIL until the mocked filter-transition contract and view state handling are aligned.

- [ ] **Step 3: Add a failing `ComparisonDataGrid` test for zero-filtered-results messaging**

```tsx
it('shows a filtered-empty message when analysis exists but filters remove all rows', () => {
  render(
    <ComparisonDataGrid
      data={[]}
      hasAnalyzed
    />
  );

  expect(screen.getByText(/No rows match the current filters/i)).toBeInTheDocument();
  expect(screen.queryByText(/No Repeated Exceptions Found/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 4: Run the single `ComparisonDataGrid` test file to verify it fails**

Run: `npm test -- --run src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx`

Expected: FAIL because the component currently uses only one generic empty-state branch.

- [ ] **Step 5: Commit the failing-test baseline**

```bash
git add frontend/src/views/__tests__/HistoryCompareView.test.tsx frontend/src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx
git commit -m "test: add history compare empty state regression coverage"
```

### Task 2: Differentiate Unfiltered Empty vs Filtered Empty in `HistoryCompareView`

**Files:**
- Modify: `frontend/src/views/HistoryCompareView.tsx`
- Test: `frontend/src/views/__tests__/HistoryCompareView.test.tsx`

- [ ] **Step 1: Run GitNexus impact analysis before editing**

Run:

```bash
npx gitnexus impact --target HistoryCompareView --direction upstream
```

Expected: record the reported blast radius before changing the view.

- [ ] **Step 2: Track whether the current table state is filtered or unfiltered**

Introduce an explicit filtered-state flag beside `filteredComparisonData`:

```tsx
const [filteredComparisonData, setFilteredComparisonData] = useState<ComparisonRow[] | null>(null);
const [hasActiveFilteredView, setHasActiveFilteredView] = useState(false);
```

- [ ] **Step 3: Replace the raw setter with a state-aware wrapper**

Use a callback like this:

```tsx
const handleFilteredDataChange = (rows: ComparisonRow[]) => {
  setFilteredComparisonData(rows);
  setHasActiveFilteredView(true);
};
```

Then pass it to `ComparisonFilterPanel`:

```tsx
<ComparisonFilterPanel
  data={activeSession.repeatedData as ComparisonRow[]}
  onFilteredDataChange={handleFilteredDataChange}
/>
```

- [ ] **Step 4: Reset the filtered-view flag when compare results refresh**

After compare succeeds, clear the filtered state:

```tsx
updateCompareSession(activeSession.id, {
  repeatedData: flat,
  latestFileName: latest,
  loading: false,
  chartData: response.data.chart_data,
});
setFilteredComparisonData(null);
setHasActiveFilteredView(false);
```

Also clear it when the active session changes or when repeated data is cleared:

```tsx
useEffect(() => {
  setFilteredComparisonData(null);
  setHasActiveFilteredView(false);
}, [activeSession?.id, activeSession?.repeatedData.length]);
```

- [ ] **Step 5: Feed `ComparisonDataGrid` the right data source explicitly**

Use this decision instead of implicit fallback:

```tsx
const tableRows = hasActiveFilteredView
  ? (filteredComparisonData ?? [])
  : activeSession.repeatedData;
```

Then render:

```tsx
<ComparisonDataGrid
  data={tableRows}
  hasAnalyzed={!!activeSession.latestFileName}
  ...
/>;
```

- [ ] **Step 6: Run the `HistoryCompareView` focused tests to verify they pass**

Run: `npm test -- --run src/views/__tests__/HistoryCompareView.test.tsx`

Expected: PASS

- [ ] **Step 7: Commit the filtered-state fix**

```bash
git add frontend/src/views/HistoryCompareView.tsx frontend/src/views/__tests__/HistoryCompareView.test.tsx
git commit -m "fix: preserve empty history compare filter results"
```

### Task 3: Clarify `ComparisonDataGrid` Empty-State Messaging

**Files:**
- Modify: `frontend/src/components/HistoryCompare/ComparisonDataGrid.tsx`
- Test: `frontend/src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx`

- [ ] **Step 1: Add an explicit prop to distinguish filtered-empty from true no-match**

Extend the props:

```tsx
interface ComparisonDataGridProps {
  data: ExceptionRecord[];
  hasAnalyzed?: boolean;
  isFilteredView?: boolean;
  ...
}
```

- [ ] **Step 2: Replace the single empty branch with two user-facing variants**

Implement the render logic like this:

```tsx
if (hasAnalyzed === false) {
  // Ready to Compare
}

if (displayData.length === 0 && isFilteredView) {
  return (
    <Box ...>
      <Alert severity="info" icon={<InfoIcon />} sx={{ maxWidth: 600, width: '100%' }}>
        <AlertTitle>No rows match the current filters</AlertTitle>
        <Typography variant="body2">
          Try broadening the filter criteria or clear the active filters to view all repeated exceptions.
        </Typography>
      </Alert>
    </Box>
  );
}

if (displayData.length === 0) {
  return (
    <Box ...>
      <Alert severity="info" icon={<InfoIcon />} sx={{ maxWidth: 600, width: '100%' }}>
        <AlertTitle>No Repeated Exceptions Found</AlertTitle>
        <Typography variant="body2">
          No repeated exceptions were detected in the comparison.
        </Typography>
        ...
      </Alert>
    </Box>
  );
}
```

- [ ] **Step 3: Pass the new prop from `HistoryCompareView`**

```tsx
<ComparisonDataGrid
  data={tableRows}
  hasAnalyzed={!!activeSession.latestFileName}
  isFilteredView={hasActiveFilteredView}
  ...
/>;
```

- [ ] **Step 4: Run the `ComparisonDataGrid` focused tests to verify they pass**

Run: `npm test -- --run src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit the empty-state copy cleanup**

```bash
git add frontend/src/components/HistoryCompare/ComparisonDataGrid.tsx frontend/src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx frontend/src/views/HistoryCompareView.tsx
git commit -m "refactor: clarify history compare empty state messaging"
```

### Task 4: Final Verification for the Empty-State Batch

**Files:**
- Verify only

- [ ] **Step 1: Run targeted History Compare tests**

Run:

```bash
npm test -- --run src/views/__tests__/HistoryCompareView.test.tsx src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx src/components/HistoryCompare/__tests__/ComparisonFilterPanel.test.tsx src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx
```

Expected: PASS

- [ ] **Step 2: Run the frontend production build**

Run:

```bash
npm run build
```

Expected: PASS

- [ ] **Step 3: Run a manual smoke check on History Compare**

Run:

```bash
npm run dev
```

Check:
- before compare: `Ready to Compare`
- compare returns no repeated exceptions: `No Repeated Exceptions Found`
- compare has rows, then filters remove all rows: `No rows match the current filters`
- clearing filters returns the repeated rows
- toolbar summary and table state remain aligned through the transitions

- [ ] **Step 4: Run GitNexus change detection before commit**

Run:

```bash
npx gitnexus detect-changes
```

Expected: scope remains limited to `HistoryCompareView`, `ComparisonDataGrid`, and related tests.

If the CLI is unavailable, use the MCP `detect_changes` tool instead.

## Exit Criteria

- filtered-empty state no longer looks like an unfiltered no-data state
- compare-empty state and filter-empty state use distinct, readable messaging
- clearing filters reliably restores the repeated rows
- targeted History Compare tests pass
- frontend build passes

## Out of Scope Reminder

Do **not** expand this batch into:

- sticky/frozen overlap fixes
- upload workflow redesign
- repeated-data grid column redesign
- chart redesign
- database workflow behavior changes
- broader History Compare IA rewrite
