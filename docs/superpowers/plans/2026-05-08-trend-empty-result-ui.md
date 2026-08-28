# Trend Empty Result UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Trend Analyzer clearly show that analysis completed successfully with 0 results when the repeated-report filter returns no matching L2 Wire Wear alarms.

**Architecture:** Add a lightweight `hasAnalyzed` state flag per trend tab, then branch the Trend Analyzer result area into idle, empty-success, and results states. Keep the existing API contract and result table unchanged.

**Tech Stack:** React, TypeScript, Zustand, MUI, Vitest, Testing Library

---

### Task 1: Add failing tests for empty-result UI state

**Files:**
- Modify: `frontend/src/views/__tests__/TrendAnalyzerView.test.tsx`
- Modify: `frontend/src/store/__tests__/useTrendStore.test.ts`
- Test: `frontend/src/views/__tests__/TrendAnalyzerView.test.tsx`
- Test: `frontend/src/store/__tests__/useTrendStore.test.ts`

- [ ] **Step 1: Read the existing Trend Analyzer tests and store tests**

Run:

```bash
Get-Content -Raw frontend/src/views/__tests__/TrendAnalyzerView.test.tsx
Get-Content -Raw frontend/src/store/__tests__/useTrendStore.test.ts
```

Expected: existing view/store test structure is visible so the new tests follow local patterns.

- [ ] **Step 2: Write the failing store test for empty-result success**

Add a test equivalent to:

```ts
it('marks the tab as analyzed when trend analysis returns an empty result set', async () => {
  vi.mocked(uploadTrendFiles).mockResolvedValue({ trend_results: [] });

  const { addFile, analyze } = useTrendStore.getState();
  addFile(new File(['x'], 'report.xlsx'));

  await analyze();

  const state = useTrendStore.getState();
  const activeTab = state.tabs.find((tab) => tab.id === state.activeTabId)!;
  expect(activeTab.hasAnalyzed).toBe(true);
  expect(activeTab.trendResults).toEqual([]);
  expect(activeTab.selectedResult).toBeNull();
});
```

- [ ] **Step 3: Write the failing store test for resetting empty-result state on input changes**

Add a test equivalent to:

```ts
it('clears the analyzed state when uploaded files change after an empty-result success', async () => {
  vi.mocked(uploadTrendFiles).mockResolvedValue({ trend_results: [] });

  const state = useTrendStore.getState();
  state.addFile(new File(['x'], 'report-a.xlsx'));
  await state.analyze();

  useTrendStore.getState().addFile(new File(['y'], 'report-b.xlsx'));

  const next = useTrendStore.getState();
  const activeTab = next.tabs.find((tab) => tab.id === next.activeTabId)!;
  expect(activeTab.hasAnalyzed).toBe(false);
  expect(activeTab.trendResults).toEqual([]);
  expect(activeTab.selectedResult).toBeNull();
  expect(activeTab.error).toBeNull();
});
```

- [ ] **Step 4: Write the failing view test for empty-result messaging**

Add a test equivalent to:

```tsx
it('shows a dedicated empty-result success message after analysis completes with zero results', () => {
  renderWithStore({
    tabs: [
      {
        id: 'tab-1',
        label: 'Tab 1',
        uploadedFiles: [new File(['x'], 'report.xlsx')],
        repeatedFile: new File(['y'], 'repeated.xlsx'),
        isLoading: false,
        error: null,
        trendResults: [],
        selectedResult: null,
        hasAnalyzed: true,
      },
    ],
    activeTabId: 'tab-1',
  });

  expect(screen.getByText(/No matching L2 Wire Wear alarms found/i)).toBeInTheDocument();
  expect(screen.getByText(/The analysis completed successfully with 0 result/i)).toBeInTheDocument();
});
```

- [ ] **Step 5: Run the targeted tests to verify they fail for the expected reason**

Run:

```bash
cd frontend
npm test -- --run src/store/__tests__/useTrendStore.test.ts src/views/__tests__/TrendAnalyzerView.test.tsx
```

Expected: FAIL because `hasAnalyzed` does not exist yet and the empty-result message is not rendered.

---

### Task 2: Implement the minimal Trend Analyzer state changes

**Files:**
- Modify: `frontend/src/store/useTrendStore.ts`
- Test: `frontend/src/store/__tests__/useTrendStore.test.ts`

- [ ] **Step 1: Add `hasAnalyzed` to the tab model and default tab factory**

Implement the shape change:

```ts
export interface TrendTab {
  id: string;
  label: string;
  uploadedFiles: File[];
  repeatedFile: File | null;
  isLoading: boolean;
  error: string | null;
  trendResults: TrendResult[];
  selectedResult: TrendResult | null;
  hasAnalyzed: boolean;
}

const makeTab = (id: string, label: string): TrendTab => ({
  id,
  label,
  uploadedFiles: [],
  repeatedFile: null,
  isLoading: false,
  error: null,
  trendResults: [],
  selectedResult: null,
  hasAnalyzed: false,
});
```

- [ ] **Step 2: Reset analysis state when inputs change**

Update `addFile`, `removeFile`, and `setRepeatedFile` to apply this patch shape:

```ts
{
  hasAnalyzed: false,
  trendResults: [],
  selectedResult: null,
  error: null,
}
```

Keep the specific file mutation for each action.

- [ ] **Step 3: Mark success-empty and success-with-results explicitly in `analyze()`**

Update the success path to:

```ts
const res = await uploadTrendFiles(tab.uploadedFiles, tab.repeatedFile);
const nextSelected = res.trend_results.length > 0 ? tab.selectedResult : null;
const { tabs: t2 } = get();
set({
  tabs: updateActive(t2, tabId, {
    trendResults: res.trend_results,
    selectedResult: nextSelected,
    hasAnalyzed: true,
    isLoading: false,
  }),
});
```

On failure, keep:

```ts
hasAnalyzed: false
```

and do not treat errors as empty-result success.

- [ ] **Step 4: Run the store tests to verify they pass**

Run:

```bash
cd frontend
npm test -- --run src/store/__tests__/useTrendStore.test.ts
```

Expected: PASS for the new store assertions.

---

### Task 3: Implement the dedicated empty-result UI

**Files:**
- Modify: `frontend/src/views/TrendAnalyzerView.tsx`
- Test: `frontend/src/views/__tests__/TrendAnalyzerView.test.tsx`

- [ ] **Step 1: Read `TrendAnalyzerView` rendering branches before editing**

Run:

```bash
Get-Content -Raw frontend/src/views/TrendAnalyzerView.tsx
```

Expected: current render logic shows only `results.length > 0` or the generic idle panel.

- [ ] **Step 2: Add the three-state render branch**

Refactor the bottom panel logic to use:

```tsx
const hasResults = activeTab.trendResults.length > 0;
const showEmptySuccess = activeTab.hasAnalyzed && !hasResults && !activeTab.isLoading && !activeTab.error;
```

Render:

```tsx
{hasResults ? (
  // existing results panel
) : showEmptySuccess ? (
  <Paper sx={{ p: 4 }}>
    <Alert severity="info">
      <Typography variant="body1">
        No matching L2 Wire Wear alarms found in the uploaded n_Repeated Exception Report after filter.
      </Typography>
      <Typography variant="body2" sx={{ mt: 0.5 }}>
        The analysis completed successfully with 0 result.
      </Typography>
    </Alert>
  </Paper>
) : (
  // existing idle prompt panel
)}
```

- [ ] **Step 3: Keep the idle state unchanged for first load**

Ensure the existing helper message:

```tsx
Upload Exception Report files from multiple inspection dates and click Analyze
```

still shows only when `hasAnalyzed` is false.

- [ ] **Step 4: Run the view test to verify it passes**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/TrendAnalyzerView.test.tsx
```

Expected: PASS, including the new empty-result message assertion.

---

### Task 4: Run focused verification for Trend Analyzer

**Files:**
- Verify only

- [ ] **Step 1: Run the focused frontend test set**

Run:

```bash
cd frontend
npm test -- --run src/store/__tests__/useTrendStore.test.ts src/views/__tests__/TrendAnalyzerView.test.tsx src/components/Calculation/__tests__/TrendResultTable.test.tsx
```

Expected: PASS with 0 failures.

- [ ] **Step 2: Run a production build check**

Run:

```bash
cd frontend
npm run build
```

Expected: build succeeds with exit code 0.

- [ ] **Step 3: Re-run the Electron app and verify the empty-result UI manually**

Run:

```bash
cd ..
npm run dev
```

Manual check:
- upload Exception Reports plus a repeated file that filters to zero results
- click `Analyze`
- confirm the dedicated empty-result message appears instead of the idle helper text

