# History Compare Toolbar Density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce toolbar density and scanning pressure in `HistoryCompareView` without redesigning upload workflow, data contracts, or the repeated-data grid itself.

**Architecture:** Keep the work inside the existing `HistoryCompareView` result toolbar and filter-panel boundaries. Reorganize visible controls into clearer primary and secondary action groups, preserve all existing behaviors, and add focused tests that verify layout-affecting UI states by role and label rather than snapshots.

**Tech Stack:** React 18, TypeScript, MUI 5, Vitest, Testing Library, Vite

---

## Scope Guard

- Stay inside:
  - `frontend/src/views/HistoryCompareView.tsx`
  - `frontend/src/components/HistoryCompare/ComparisonFilterPanel.tsx`
  - new focused tests under `frontend/src/views/__tests__` and `frontend/src/components/HistoryCompare/__tests__`
- Do not change:
  - backend compare API
  - upload parsing logic
  - `ComparisonDataGrid` column model
  - chart logic
  - save-to-DB / check-1-year business rules
- Treat this as a toolbar-density cleanup only, not a full IA or workflow redesign.

## File Map

- Modify: `frontend/src/views/HistoryCompareView.tsx`
  - reorganize result-toolbar controls into clearer primary/secondary groups
  - keep all existing actions and callbacks
- Modify: `frontend/src/components/HistoryCompare/ComparisonFilterPanel.tsx`
  - tighten filter summary row wording and spacing if needed
  - preserve existing filter semantics
- Create: `frontend/src/views/__tests__/HistoryCompareView.test.tsx`
  - cover toolbar density states and grouped action visibility
- Create or Modify: `frontend/src/components/HistoryCompare/__tests__/ComparisonFilterPanel.test.tsx`
  - cover compact filter summary behavior and clear action state

### Task 1: Add Focused Regression Tests for the Current Toolbar Contract

**Files:**
- Create: `frontend/src/views/__tests__/HistoryCompareView.test.tsx`
- Create: `frontend/src/components/HistoryCompare/__tests__/ComparisonFilterPanel.test.tsx`

- [ ] **Step 1: Write the failing `HistoryCompareView` toolbar tests**

```tsx
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import HistoryCompareView from '../HistoryCompareView';
import { useAnalysisStore } from '../../store/useAnalysisStore';

vi.mock('../../components/HistoryCompare/ComparisonDataGrid', () => ({
  __esModule: true,
  default: () => <div data-testid="comparison-grid" />,
}));

test('shows primary tabs and condensed action groups after comparison results exist', () => {
  useAnalysisStore.setState({
    compareSessions: [{
      id: 'cmp-1',
      label: 'Comparison 1',
      latestFile: null,
      closestPreviousFile: null,
      olderPreviousFiles: [],
      repeatedData: [{ id: 'EX-1', 'exception type': 'Low Height' } as any],
      latestFileName: 'EAL_UP_20260101.xlsx',
      loading: false,
      error: null,
      tabIndex: 0,
    }],
    activeCompareTabId: 'cmp-1',
  });

  render(<HistoryCompareView />);

  expect(screen.getByRole('tab', { name: /Repeated Table/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Comparison Chart/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Batch Edit/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Save Edit/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the new `HistoryCompareView` test to verify it fails**

Run: `npm test -- --run src/views/__tests__/HistoryCompareView.test.tsx`

Expected: FAIL because the new grouped-toolbar assertions are not implemented yet.

- [ ] **Step 3: Write the failing `ComparisonFilterPanel` compact-summary tests**

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ComparisonFilterPanel from '../ComparisonFilterPanel';

test('shows active filter count and enables clear only when filters are active', async () => {
  const user = userEvent.setup();
  render(<ComparisonFilterPanel data={[]} onFilteredDataChange={() => {}} />);

  expect(screen.queryByText(/active/i)).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Clear/i })).toBeDisabled();

  await user.click(screen.getByText(/Filters/i));
  await user.type(screen.getByLabelText(/Chainage From/i), '100');
  await user.type(screen.getByLabelText(/Chainage To/i), '200');

  expect(screen.getByText(/1 active/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Clear/i })).toBeEnabled();
});
```

- [ ] **Step 4: Run the new `ComparisonFilterPanel` test to verify it fails**

Run: `npm test -- --run src/components/HistoryCompare/__tests__/ComparisonFilterPanel.test.tsx`

Expected: FAIL until the compact-summary expectations match the updated component output.

- [ ] **Step 5: Commit the failing-test baseline**

```bash
git add frontend/src/views/__tests__/HistoryCompareView.test.tsx frontend/src/components/HistoryCompare/__tests__/ComparisonFilterPanel.test.tsx
git commit -m "test: add history compare toolbar density coverage"
```

### Task 2: Reduce Result Toolbar Density in `HistoryCompareView`

**Files:**
- Modify: `frontend/src/views/HistoryCompareView.tsx`
- Test: `frontend/src/views/__tests__/HistoryCompareView.test.tsx`

- [ ] **Step 1: Add an impact note before editing the component**

Run:

```bash
npx gitnexus impact --target HistoryCompareView --direction upstream
```

Expected: record the reported blast radius in the task log before changing the component.

- [ ] **Step 2: Implement a clearer primary/secondary toolbar grouping**

Use a compact grouped structure like this inside the existing result-toolbar block:

```tsx
<Box
  sx={{
    borderBottom: 1,
    borderColor: 'divider',
    bgcolor: 'background.paper',
    px: 2,
    py: 1,
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 1.5,
  }}
>
  <Tabs value={resultTabIndex} onChange={(_, v) => setResultTabIndex(v)} sx={{ minHeight: 44 }}>
    <Tab icon={<TableChartIcon fontSize="small" />} iconPosition="start" label="Repeated Table" />
    <Tab icon={<ShowChartIcon fontSize="small" />} iconPosition="start" label="Comparison Chart" />
  </Tabs>

  <Box sx={{ flexGrow: 1, minWidth: 24 }} />

  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ alignItems: 'center' }}>
    <Typography variant="body2" color="success.main" fontWeight={700}>
      {activeSession.repeatedData.length} Matches
    </Typography>
    {pendingChanges.size > 0 && (
      <Chip label={`${pendingChanges.size} pending`} size="small" color="warning" variant="outlined" />
    )}
  </Stack>

  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ alignItems: 'center' }}>
    <Button variant="outlined" size="small" startIcon={<EditIcon />} disabled={selectedRowIds.size === 0}>
      Batch Edit ({selectedRowIds.size})
    </Button>
    <Button variant="contained" size="small" color="warning" startIcon={<SaveIcon />} disabled={pendingChanges.size === 0}>
      Save Edit
    </Button>
    <Button variant="outlined" size="small" startIcon={<UndoIcon />} disabled={pendingChanges.size === 0}>
      Discard
    </Button>
  </Stack>

  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ alignItems: 'center' }}>
    <Button variant="outlined" size="small" color="info" startIcon={<HistoryIcon />}>
      Check 1 Year Record
    </Button>
    <Button variant="outlined" size="small" color="success" startIcon={<DownloadIcon />}>
      Export
    </Button>
    <Button variant="contained" size="small" color="secondary" startIcon={<SaveIcon />}>
      Save to DB
    </Button>
  </Stack>
</Box>
```

- [ ] **Step 3: Keep the current behaviors and handlers wired exactly as before**

Preserve the existing event handlers on the grouped buttons:

```tsx
onClick={() => setBatchEditDialogOpen(true)}
onClick={handleSaveEdit}
onClick={handleDiscardChanges}
onClick={handleOpenCheck1YearDialog}
onClick={handleDownload}
onClick={handleOpenSaveDialog}
```

Do not rename handlers or change disabled-state logic.

- [ ] **Step 4: Run the `HistoryCompareView` focused test to verify it passes**

Run: `npm test -- --run src/views/__tests__/HistoryCompareView.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit the toolbar-density change**

```bash
git add frontend/src/views/HistoryCompareView.tsx frontend/src/views/__tests__/HistoryCompareView.test.tsx
git commit -m "feat: reduce history compare toolbar density"
```

### Task 3: Tighten the Filter Summary Row Without Changing Filter Semantics

**Files:**
- Modify: `frontend/src/components/HistoryCompare/ComparisonFilterPanel.tsx`
- Test: `frontend/src/components/HistoryCompare/__tests__/ComparisonFilterPanel.test.tsx`

- [ ] **Step 1: Implement a denser filter summary row**

Keep the same accordion behavior, but tighten the summary-row layout:

```tsx
<AccordionSummary
  expandIcon={<ExpandMoreIcon />}
  sx={{
    minHeight: 40,
    px: 1.5,
    '& .MuiAccordionSummary-content': { my: 0.5 },
  }}
>
  <Stack direction="row" alignItems="center" spacing={1} sx={{ width: '100%', minWidth: 0 }}>
    <FilterListIcon color="action" fontSize="small" />
    <Typography variant="body2" fontWeight={600}>Filters</Typography>
    {activeCount > 0 && (
      <Chip label={`${activeCount} active`} size="small" color="primary" variant="outlined" />
    )}
    <Box sx={{ flexGrow: 1 }} />
    <Button
      size="small"
      startIcon={<ClearIcon fontSize="small" />}
      onClick={(e) => { e.stopPropagation(); handleClear(); }}
      disabled={activeCount === 0}
      sx={{ minWidth: 'auto', px: 1 }}
    >
      Clear
    </Button>
  </Stack>
</AccordionSummary>
```

- [ ] **Step 2: Preserve the existing filter logic exactly**

Do not change these behaviors in `applyFilters`:

```ts
if (filters.exception_type !== 'All') { ... }
if (filters.track_type !== 'All') { ... }
if (filters.level !== 'All') { ... }
if (filters.action !== 'All') { ... }
if (!isNaN(chainageFrom) && !isNaN(chainageTo)) {
  filtered = filtered.filter((row) => row.FromM <= chainageTo && row.ToM >= chainageFrom);
}
```

- [ ] **Step 3: Run the `ComparisonFilterPanel` focused test to verify it passes**

Run: `npm test -- --run src/components/HistoryCompare/__tests__/ComparisonFilterPanel.test.tsx`

Expected: PASS

- [ ] **Step 4: Run both focused History Compare tests together**

Run: `npm test -- --run src/views/__tests__/HistoryCompareView.test.tsx src/components/HistoryCompare/__tests__/ComparisonFilterPanel.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit the filter-panel density cleanup**

```bash
git add frontend/src/components/HistoryCompare/ComparisonFilterPanel.tsx frontend/src/components/HistoryCompare/__tests__/ComparisonFilterPanel.test.tsx
git commit -m "refactor: compact history compare filter summary"
```

### Task 4: Final Verification for the B3 Batch

**Files:**
- Verify only

- [ ] **Step 1: Run the full targeted History Compare frontend tests**

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

- [ ] **Step 3: Run a manual smoke check on the History Compare page**

Run:

```bash
npm run dev
```

Check:
- result toolbar wraps cleanly at narrower widths
- tabs remain visible and clickable
- pending chip and match count do not overlap action buttons
- Batch Edit / Save Edit / Discard stay grouped logically
- Check 1 Year / Export / Save to DB remain discoverable without looking crowded
- filter summary row remains readable when collapsed and expanded

- [ ] **Step 4: Run GitNexus change detection before commit**

Run:

```bash
npx gitnexus detect-changes
```

Expected: scope remains limited to `HistoryCompareView`, `ComparisonFilterPanel`, and related tests.

If CLI is unavailable, use the MCP `detect_changes` tool instead.

## Exit Criteria

- History Compare result toolbar no longer reads as one overloaded control strip
- all existing actions remain available with unchanged behavior
- filter summary row is denser but still clear
- focused tests for toolbar/filter density pass
- targeted History Compare tests pass
- frontend build passes

## Out of Scope Reminder

Do **not** expand this batch into:

- sticky/frozen table overlap fixes
- upload workflow redesign
- repeated-data grid column redesign
- chart redesign
- database workflow logic changes
- full History Compare IA rewrite
