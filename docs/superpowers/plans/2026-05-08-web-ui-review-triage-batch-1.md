# Web UI Review Triage Batch 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first approved batch of low-risk web UI review fixes for `Q1` column sizing, `Q2` chip removal affordance, and `Q3` tab-scoped reset placement/behavior without touching unrelated workspace changes.

**Architecture:** Keep all changes inside the existing frontend view/component boundaries. Reuse current MUI and DataGrid patterns, adjust only the specific UI surfaces already identified in triage, and verify behavior with focused Vitest coverage plus small manual UI checks.

**Tech Stack:** React 18, TypeScript, MUI 5, MUI X DataGrid, Zustand, Vitest, Testing Library

---

## Scope Note

- The source triage document covers **32 review comments** in total.
- Those 32 comments are grouped into:
  - `Bug List`
  - `Quick Wins`
  - `Enhancement Plan`
- This implementation plan does **not** attempt to design or implement all 32 comments in one pass.
- This plan is intentionally limited to the approved first batch:
  - `Q1` column auto-fit / compact width tuning
  - `Q2` chip removal affordance in `Stagger Calculation`
  - `Q3` tab-adjacent `Reset All` placement and scope
- Items **not** covered by this plan must remain visible for future planning rather than being implicitly dropped.

## Deferred Items For Future Planning

- `Bug List`
  - `B1` web mode file upload compatibility
  - `B2` summary frozen-column overlap / layering issue
  - `B3` History Compare toolbar / layout density issue
- `Quick Wins`
  - `Q4` information-card spacing / hierarchy cleanup
  - `Q5` Case A / Case B labeling clarity
  - `Q6` Stagger Calculation KPI / stats presentation cleanup
- `Enhancement Plan`
  - `E1` Database Record information architecture refresh
  - `E2` Metadata Editor interaction and edit-flow cleanup
  - `E3` upload area redesign
  - `E4` results-first layout refinement
  - `E5` sticky / frozen chart-table coordination improvements
  - `E6` Trend Analyzer recommendation / explanation presentation
  - `E7` Trace tab readability improvements
  - `E8` Raw Data chart annotation improvements
  - `E9` About page cleanup
  - `E10` algorithm explanation asset / dialog polish

Future planning should either:

- create a separate plan per logical batch, or
- create a dedicated follow-up roadmap document that maps the remaining comments into priority, risk, affected files, and verification strategy.

## File Map

- Modify: `frontend/src/components/HistoryCompare/ComparisonDataGrid.tsx`
  - Narrow oversized short columns and preserve stable minimum widths for Q1.
- Modify: `frontend/src/components/DatabaseRecord/RepeatedRecordTable.tsx`
  - Align repeated-record short column widths with the same Q1 intent.
- Modify: `frontend/src/views/CalculationView.tsx`
  - Add visible/removable chips for uploaded files, wire a tab-scoped reset action, and keep action-state semantics clear for Q2/Q3.
- Modify: `frontend/src/components/Calculation/CycleTabBar.tsx`
  - Host or expose the tab-adjacent reset affordance for Q3 without changing unrelated tab behavior.
- Modify: `frontend/src/views/TrendAnalyzerView.tsx`
  - Move or add reset-all behavior next to the tab context for Q3.
- Test: `frontend/src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx`
  - Add focused assertions for short-column sizing metadata.
- Test: `frontend/src/components/DatabaseRecord/__tests__/RepeatedRecordTable.test.tsx`
  - Add focused assertions for short-column sizing metadata or auto-fit trigger behavior.
- Test: `frontend/src/views/__tests__/CalculationView.test.tsx`
  - Add coverage for removable uploaded-file chips and tab-scoped reset behavior.
- Test: `frontend/src/views/__tests__/TrendAnalyzerView.test.tsx`
  - Add coverage for reset placement/behavior in the multi-tab UI.

## Preconditions

- GitNexus impact already checked for:
  - `ComparisonDataGrid` -> `LOW`
  - `CalculationView` -> `LOW`
  - `DatabaseRecordView` -> `LOW`
  - `TrendAnalyzerView` -> `LOW`
- `CycleTabBar` was confirmed in source at `frontend/src/components/Calculation/CycleTabBar.tsx`; GitNexus did not resolve the symbol by name, so keep edits file-local and avoid abstraction drift.
- Do not modify backend, Electron, docs outside this plan file, or unrelated frontend modules.

### Task 1: Lock Down Q1 Column Width Expectations

**Files:**
- Modify: `frontend/src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx`
- Modify: `frontend/src/components/DatabaseRecord/__tests__/RepeatedRecordTable.test.tsx`

- [ ] **Step 1: Add a focused metadata test for History Compare short columns**

```tsx
import * as ComparisonModule from '../ComparisonDataGrid';

test('uses compact widths for short identifier columns', () => {
  const columns = (ComparisonModule as any).__TEST_ONLY__?.baseColumns ?? [];

  const idColumn = columns.find((column: { field: string }) => column.field === 'id');
  const levelColumn = columns.find((column: { field: string }) => column.field === 'level');

  expect(idColumn).toMatchObject({
    field: 'id',
    minWidth: expect.any(Number),
  });
  expect(idColumn.width).toBeLessThanOrEqual(180);
  expect(levelColumn.width).toBeLessThanOrEqual(80);
});
```

- [ ] **Step 2: Add a focused metadata test for Repeated Record short columns**

```tsx
import * as RepeatedModule from '../RepeatedRecordTable';

test('keeps track and small numeric columns compact after auto-fit tuning', () => {
  const columns = (RepeatedModule as any).__TEST_ONLY__?.baseColumns ?? [];

  const trackColumn = columns.find((column: { field: string }) => column.field === 'track');
  const meterColumn = columns.find((column: { field: string }) => column.field === 'm');

  expect(trackColumn.width).toBeLessThanOrEqual(80);
  expect(meterColumn.width).toBeLessThanOrEqual(90);
});
```

- [ ] **Step 3: Run the focused tests and verify they fail before implementation**

Run:

```bash
cd frontend
npm test -- --run src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx src/components/DatabaseRecord/__tests__/RepeatedRecordTable.test.tsx
```

Expected: FAIL because `__TEST_ONLY__` column metadata is not yet exported or the current widths do not satisfy the assertions.

### Task 2: Implement Q1 Compact Column Sizing

**Files:**
- Modify: `frontend/src/components/HistoryCompare/ComparisonDataGrid.tsx`
- Modify: `frontend/src/components/DatabaseRecord/RepeatedRecordTable.tsx`
- Test: `frontend/src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx`
- Test: `frontend/src/components/DatabaseRecord/__tests__/RepeatedRecordTable.test.tsx`

- [ ] **Step 1: Extract stable column metadata for History Compare and expose a test hook**

```tsx
const historyBaseColumns: GridColDef[] = [
  { field: 'id', headerName: 'ID', width: 160, minWidth: 120 },
  { field: 'FromM', headerName: 'FromM', width: 96, type: 'number' },
  { field: 'ToM', headerName: 'ToM', width: 96, type: 'number' },
  { field: 'length', headerName: 'Length', width: 76, type: 'number' },
  { field: 'level', headerName: 'Level', width: 68 },
  { field: 'Track Type', headerName: 'Track Type', width: 92 },
];

export const __TEST_ONLY__ = {
  baseColumns: historyBaseColumns,
};
```

- [ ] **Step 2: Rebuild the full History Compare column list from the compact base definitions**

```tsx
const columns = useMemo<GridColDef[]>(() => [
  selectionColumn,
  chartActionColumn,
  ...historyBaseColumns,
  ...previousColumns,
  ...workflowColumns,
], [maxPreviousCount, allSelected, someSelected, selectedRowIds, onRowUpdate, onViewChart]);
```

- [ ] **Step 3: Tune Repeated Record short columns and expose a test hook**

```tsx
const repeatedBaseColumns: GridColDef[] = [
  { field: 'track', headerName: 'Track', width: 72, minWidth: 64 },
  { field: 'section', headerName: 'Section', width: 96, minWidth: 88 },
  { field: 'm', headerName: 'M', width: 84, minWidth: 72, type: 'number' },
  { field: 'km', headerName: 'KM', width: 84, minWidth: 72, type: 'number' },
];

export const __TEST_ONLY__ = {
  baseColumns: repeatedBaseColumns,
};
```

- [ ] **Step 4: Run the focused column tests and verify they pass**

Run:

```bash
cd frontend
npm test -- --run src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx src/components/DatabaseRecord/__tests__/RepeatedRecordTable.test.tsx
```

Expected: PASS for the new compact-width assertions.

- [ ] **Step 5: Manual verification for Q1**

Run:

```bash
cd frontend
npm run dev
```

Check:

- `History Compare` short columns (`ID`, `Level`, `Track Type`, small numeric columns) no longer dominate horizontal space.
- `Database Record` short columns stay readable and do not cause header/body misalignment.
- Existing horizontal scrolling still works and no sticky/frozen behavior is changed.

### Task 3: Lock Down Q2 Chip Removal Behavior

**Files:**
- Modify: `frontend/src/views/__tests__/CalculationView.test.tsx`

- [ ] **Step 1: Add a failing test for removable uploaded-file chips**

```tsx
test('renders uploaded files as removable chips in stagger calculation', () => {
  useCalculationStore.setState((state) => ({
    ...state,
    cycles: state.cycles.map((cycle) => ({
      ...cycle,
      uploadedFiles: [new File(['excel'], 'cycle-a.xlsx')],
    })),
  }));

  render(<CalculationView />);

  expect(screen.getByText('cycle-a.xlsx')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /delete cycle-a.xlsx/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the focused CalculationView test and verify it fails**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/CalculationView.test.tsx
```

Expected: FAIL because the uploaded-file chip currently has no delete affordance.

### Task 4: Implement Q2 Chip Removal Affordance

**Files:**
- Modify: `frontend/src/views/CalculationView.tsx`
- Test: `frontend/src/views/__tests__/CalculationView.test.tsx`

- [ ] **Step 1: Confirm the store already exposes the removal API before changing UI**

```tsx
const {
  setUploadedFile,
  setRepeatedFile,
  // add this only if already available in store
  removeUploadedFile,
} = useCalculationStore();
```

If `removeUploadedFile` does not exist, stop and add a plan note in code comments before implementation rather than inventing cross-store behavior here.

- [ ] **Step 2: Render uploaded files with visible delete affordance**

```tsx
{activeCycle.uploadedFiles.map((file) => (
  <Chip
    key={file.name}
    label={file.name}
    size="small"
    color="primary"
    variant="outlined"
    onDelete={() => removeUploadedFile(file.name)}
    deleteIcon={<CloseIcon aria-label={`Delete ${file.name}`} />}
  />
))}
```

- [ ] **Step 3: Keep the repeated-file chip visually consistent**

```tsx
<Chip
  label={`n_Repeated: ${activeCycle.repeatedFile.name}`}
  size="small"
  color="secondary"
  variant="outlined"
  onDelete={() => setRepeatedFile(null)}
  deleteIcon={<CloseIcon aria-label={`Delete ${activeCycle.repeatedFile.name}`} />}
/>
```

- [ ] **Step 4: Run the CalculationView tests and verify they pass**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/CalculationView.test.tsx
```

Expected: PASS with the new removable-chip assertion and no regressions in existing tests.

### Task 5: Lock Down Q3 Reset Placement and Scope

**Files:**
- Modify: `frontend/src/views/__tests__/TrendAnalyzerView.test.tsx`
- Modify: `frontend/src/views/__tests__/CalculationView.test.tsx`

- [ ] **Step 1: Add a failing test that expects reset control next to the tab context in Trend Analyzer**

```tsx
test('shows reset control alongside the tab actions in trend analyzer', () => {
  render(<TrendAnalyzerView />);

  expect(screen.getByRole('button', { name: /reset all/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Add a failing test for tab-scoped reset semantics in CalculationView**

```tsx
test('keeps reset action in the cycle tab context for stagger calculation', () => {
  render(<CalculationView />);

  const resetButton = screen.getByRole('button', { name: /reset all/i });
  const cycleTab = screen.getByRole('tab', { name: /Cycle A/i });

  expect(resetButton.closest('[data-testid=\"cycle-tab-bar\"]')).toContainElement(cycleTab);
});
```

- [ ] **Step 3: Run the focused view tests and verify they fail**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/CalculationView.test.tsx src/views/__tests__/TrendAnalyzerView.test.tsx
```

Expected: FAIL because reset is not yet exposed in the expected tab-adjacent location.

### Task 6: Implement Q3 Reset Placement with Minimum Surface Area

**Files:**
- Modify: `frontend/src/components/Calculation/CycleTabBar.tsx`
- Modify: `frontend/src/views/CalculationView.tsx`
- Modify: `frontend/src/views/TrendAnalyzerView.tsx`
- Test: `frontend/src/views/__tests__/CalculationView.test.tsx`
- Test: `frontend/src/views/__tests__/TrendAnalyzerView.test.tsx`

- [ ] **Step 1: Extend `CycleTabBar` with an optional action slot rather than hardcoding new layout rules**

```tsx
interface CycleTabBarProps {
  tabs: CycleTabItem[];
  activeId: string;
  onChange: (id: string) => void;
  onAdd: () => void;
  onClose: (id: string) => void;
  actions?: React.ReactNode;
}

const CycleTabBar: React.FC<CycleTabBarProps> = ({ tabs, activeId, onChange, onAdd, onClose, actions }) => (
  <Box data-testid="cycle-tab-bar" sx={{ display: 'flex', alignItems: 'center', borderBottom: 1, borderColor: 'divider' }}>
    <Tabs ... />
    {actions}
    <Tooltip title="Add cycle tab">
      <IconButton ... />
    </Tooltip>
  </Box>
);
```

- [ ] **Step 2: Wire the existing stagger reset handler into the tab bar action area**

```tsx
<CycleTabBar
  tabs={cycleTabs}
  activeId={activeCycleId}
  onChange={setActiveCycle}
  onAdd={createCycle}
  onClose={closeCycle}
  actions={(
    <Button
      size="small"
      variant="text"
      onClick={resetActiveCycle}
      disabled={activeCycle.isLoading}
    >
      Reset All
    </Button>
  )}
/>
```

- [ ] **Step 3: Apply the same tab-adjacent reset pattern in Trend Analyzer**

```tsx
<Box sx={{ display: 'flex', alignItems: 'center', borderBottom: 1, borderColor: 'divider' }}>
  <Tabs ... />
  <Button
    size="small"
    variant="text"
    onClick={resetActiveTab}
    disabled={activeTab.isLoading}
  >
    Reset All
  </Button>
  <Tooltip title={tabs.length >= 6 ? 'Maximum 6 tabs' : 'New analysis tab'}>
    <span>
      <IconButton ... />
    </span>
  </Tooltip>
</Box>
```

- [ ] **Step 4: Keep reset scope local to the active tab/cycle**

```tsx
const handleResetAll = () => {
  resetActiveTab();
};
```

Do not rename the action to something broader and do not clear other tabs unless the current store contract already does that.

- [ ] **Step 5: Run the focused view tests and verify they pass**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/CalculationView.test.tsx src/views/__tests__/TrendAnalyzerView.test.tsx
```

Expected: PASS for the tab-adjacent reset assertions.

### Task 7: Final Verification for Batch 1

**Files:**
- Modify: none
- Test: `frontend/src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx`
- Test: `frontend/src/components/DatabaseRecord/__tests__/RepeatedRecordTable.test.tsx`
- Test: `frontend/src/views/__tests__/CalculationView.test.tsx`
- Test: `frontend/src/views/__tests__/TrendAnalyzerView.test.tsx`

- [ ] **Step 1: Run the full targeted test suite for this batch**

Run:

```bash
cd frontend
npm test -- --run src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx src/components/DatabaseRecord/__tests__/RepeatedRecordTable.test.tsx src/views/__tests__/CalculationView.test.tsx src/views/__tests__/TrendAnalyzerView.test.tsx
```

Expected: PASS

- [ ] **Step 2: Run lint only if any new prop/interface changes trigger type fallout**

Run:

```bash
cd frontend
npm run build
```

Expected: TypeScript and Vite build complete successfully.

- [ ] **Step 3: Manual UI verification checklist**

Check:

- `History Compare` and `Database Record` short columns read naturally and do not waste horizontal space.
- `Stagger Calculation` uploaded-file chips now show delete affordance and can be removed individually.
- `Stagger Calculation` repeated-file chip still removes correctly.
- `Reset All` sits visually inside the tab/cycle action area in both `Stagger Calculation` and `Trend Analyzer`.
- `Reset All` only clears the active tab/cycle, not neighboring tabs.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/HistoryCompare/ComparisonDataGrid.tsx frontend/src/components/DatabaseRecord/RepeatedRecordTable.tsx frontend/src/views/CalculationView.tsx frontend/src/components/Calculation/CycleTabBar.tsx frontend/src/views/TrendAnalyzerView.tsx frontend/src/components/HistoryCompare/__tests__/ComparisonDataGrid.test.tsx frontend/src/components/DatabaseRecord/__tests__/RepeatedRecordTable.test.tsx frontend/src/views/__tests__/CalculationView.test.tsx frontend/src/views/__tests__/TrendAnalyzerView.test.tsx docs/superpowers/plans/2026-05-08-web-ui-review-triage-batch-1.md
git commit -m "feat: implement web ui review triage batch 1"
```

## Self-Review

- Spec coverage: This plan covers only the approved first batch `Q1 + Q2 + Q3`.
- Placeholder scan: No `TODO` or open-ended implementation placeholders remain.
- Type consistency: All proposed file paths and symbol names match the currently inspected frontend structure, except store reset/remove handlers which must be confirmed before implementation and kept local if already present.
