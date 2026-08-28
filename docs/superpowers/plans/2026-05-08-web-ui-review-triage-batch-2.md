# Web UI Review Triage Batch 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the second approved batch of low-risk web UI review improvements focused on Stagger Calculation information hierarchy, algorithm dialog clarity, History Compare dialog spacing, and About page cleanup without entering broader layout refactors or cross-module bug fixes.

**Architecture:** Keep changes local to existing frontend view and dialog boundaries. Reuse the current MUI layout system, existing cards/chips/alerts patterns, and focused Vitest coverage. Avoid store contract changes, backend changes, upload workflow redesign, and sticky/frozen-table behavior changes in this batch.

**Tech Stack:** React 18, TypeScript, MUI 5, Vitest, Testing Library

---

## Scope Note

- The source triage document covers **32 review comments** total.
- Batch 1 already implemented:
  - `Q1` column auto-fit / compact width tuning
  - `Q2` Stagger Calculation chip removal affordance
  - `Q3` tab/cycle reset placement and scoped reset behavior
- This Batch 2 plan is intentionally limited to the next approved low-risk UI cleanup items:
  - `Q4` History Compare algorithm dialog spacing / hierarchy cleanup
  - `Q5` Stagger Calculation Case A / Case B labeling clarity
  - `Q6` Stagger Calculation KPI / stats presentation cleanup
  - `E9` About page cleanup
  - `E10` Stagger algorithm explanation dialog asset / layout polish

## Deferred Items For Later Batches / Roadmap

- `Bug List`
  - `B1` web-mode upload compatibility
  - `B2` summary frozen-column overlap / layering issue
  - `B3` History Compare density / toolbar pressure
- `Enhancement Plan`
  - `E1` Database Record information architecture refresh
  - `E2` Metadata Editor interaction cleanup
  - `E3` upload area redesign across modules
  - `E4` results-first layout restructuring
  - `E5` sticky/frozen chart-table coordination improvements
  - `E6` Trend Analyzer recommendation presentation rework
  - `E7` Trace tab readability improvements
  - `E8` Raw Data chart annotation improvements

These items remain intentionally deferred because they either cross more modules, touch interaction contracts, or are likely to expand into higher-risk layout or behavior refactors.

## Impact Analysis Summary

Per `AGENTS.md`, impact analysis was run before planning edits for candidate symbols that would likely be modified in implementation:

- `CalculationView` (`frontend/src/views/CalculationView.tsx`) -> `LOW`
- `StaggerAlgorithmDialog` (`frontend/src/components/Calculation/StaggerAlgorithmDialog.tsx`) -> `LOW`
- `TrendAlgorithmDialog` (`frontend/src/components/Calculation/TrendAlgorithmDialog.tsx`) -> `LOW`
- `AboutView` (`frontend/src/views/AboutView.tsx`) -> `LOW`

`AlgorithmTutorialDialog.tsx` is also a local frontend dialog candidate with a file-local UI surface; keep changes constrained to presentation and avoid inventing new shared abstractions.

## File Map

- Modify: `frontend/src/views/CalculationView.tsx`
  - Clarify Case A / Case B messaging and restack KPI summary content for scanability.
- Modify: `frontend/src/views/__tests__/CalculationView.test.tsx`
  - Add focused assertions for the revised Case A / Case B explanatory structure and KPI labels.
- Modify: `frontend/src/components/Calculation/StaggerAlgorithmDialog.tsx`
  - Improve section hierarchy, incorporate the algorithm PNG asset when available, and keep dialog reading flow coherent.
- Modify: `frontend/src/components/HistoryCompare/AlgorithmTutorialDialog.tsx`
  - Normalize card spacing and section hierarchy for the algorithm explanation dialog.
- Modify or Create: `frontend/src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx`
  - Add dialog smoke coverage for the revised structure and image/section presence.
- Modify or Create: `frontend/src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx`
  - Add smoke coverage for the revised section headings or case cards.
- Modify: `frontend/src/views/AboutView.tsx`
  - Reduce information-wall presentation and improve module-card scanability.
- Modify or Create: `frontend/src/views/__tests__/AboutView.test.tsx`
  - Add a light rendering test for the cleaned-up About structure if none exists.

## Preconditions

- Do not modify backend, Electron, API contracts, or Zustand store shape in this batch.
- Do not redesign shared upload dropzones across other modules; this batch is Stagger-focused presentation cleanup only.
- If the PNG asset path for `E10` is missing or packaging it through Vite is non-trivial, copy/import the asset using the existing frontend asset pattern before continuing. Do not hotlink docs assets directly at runtime without confirming the bundler path works.
- Keep text changes faithful to actual system behavior, especially around `Case B` fallback and warning semantics.

### Task 1: Lock Down the Revised Stagger Information Hierarchy in Tests

**Files:**
- Modify: `frontend/src/views/__tests__/CalculationView.test.tsx`

- [ ] **Step 1: Add a failing test that expects separate Case A and Case B explanatory blocks**

```tsx
test('separates Case A and Case B usage guidance in the upload workspace', () => {
  render(<CalculationView />);

  expect(screen.getByText(/Case A/i)).toBeInTheDocument();
  expect(screen.getByText(/只使用 Exception Report/i)).toBeInTheDocument();
  expect(screen.getByText(/Case B/i)).toBeInTheDocument();
  expect(screen.getByText(/額外上傳 n_Repeated Report/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Add a failing test for KPI labels that match the cleaned-up stats presentation**

```tsx
test('renders concise summary KPI labels for the active cycle', () => {
  render(<CalculationView />);

  expect(screen.getByText(/Uploaded Files/i)).toBeInTheDocument();
  expect(screen.getByText(/Results/i)).toBeInTheDocument();
  expect(screen.getByText(/Partial Trace/i)).toBeInTheDocument();
  expect(screen.getByText(/Analysis Mode/i)).toBeInTheDocument();
});
```

- [ ] **Step 3: Run the focused test and verify it fails before implementation**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/CalculationView.test.tsx
```

Expected: FAIL because the current labels or explanatory grouping do not yet match the desired structure.

### Task 2: Implement `Q5` + `Q6` in `CalculationView`

**Files:**
- Modify: `frontend/src/views/CalculationView.tsx`
- Test: `frontend/src/views/__tests__/CalculationView.test.tsx`

- [ ] **Step 1: Replace the current mixed Case A / Case B alert copy with two clearer content groups**

```tsx
<Stack spacing={1.5}>
  <Alert severity="success" variant="outlined">
    <strong>Case A:</strong> 只使用 Exception Report 的 Summary 與 ChartData 計算。
  </Alert>
  <Alert severity={activeCycle.repeatedFile ? 'info' : 'warning'} variant="outlined">
    <strong>Case B:</strong> 額外上傳 n_Repeated Report 後，系統只會在 repeated 內有對應 stagger 候選時介入定位；若沒有，保留主檔輸出並提示警告。
  </Alert>
</Stack>
```

- [ ] **Step 2: Rename and normalize the summary card labels to match a compact KPI strip**

```tsx
const summaryCards = [
  {
    label: 'Uploaded Files',
    value: (activeCycle.uploadedFiles.length ? 1 : 0) + (activeCycle.repeatedFile ? 1 : 0),
    icon: <UploadFileOutlinedIcon fontSize="small" />,
  },
  {
    label: 'Results',
    value: activeCycle.results.length,
    icon: <CheckCircleOutlineOutlinedIcon fontSize="small" />,
  },
  {
    label: 'Partial Trace',
    value: activeCycle.results.filter((result) => result.trace_status === 'partial').length,
    icon: <WarningAmberOutlinedIcon fontSize="small" />,
  },
  {
    label: 'Analysis Mode',
    value: activeCycle.repeatedFile ? 'Case A / B' : 'Case A',
    icon: <RuleFolderOutlinedIcon fontSize="small" />,
  },
];
```

- [ ] **Step 3: Tighten the summary-card typography and spacing without changing page-level layout**

```tsx
<Card variant="outlined" sx={{ height: '100%' }}>
  <CardContent sx={{ p: 2 }}>
    <Stack direction="row" spacing={1} alignItems="center">
      {card.icon}
      <Typography variant="caption" color="text.secondary">
        {card.label}
      </Typography>
    </Stack>
    <Typography variant="h5" fontWeight={700} sx={{ mt: 1 }}>
      {card.value}
    </Typography>
  </CardContent>
</Card>
```

- [ ] **Step 4: Keep action buttons and chip rows visually secondary to the dropzones and KPI strip**

```tsx
<Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ alignItems: 'center' }}>
  {fileChips}
  <Button variant="contained" ...>Analyze Cycle</Button>
  <Button variant="outlined" ...>Upload Main File</Button>
  <Button variant="outlined" ...>Upload n_Repeated</Button>
</Stack>
```

- [ ] **Step 5: Run the focused CalculationView test and verify it passes**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/CalculationView.test.tsx
```

Expected: PASS

- [ ] **Step 6: Manual verification for `Q5` + `Q6`**

Run:

```bash
cd frontend
npm run dev
```

Check:

- Case A and Case B are readable as separate concepts instead of one dense paragraph.
- The KPI cards scan cleanly from left to right.
- Uploaded-file chips and action buttons no longer visually compete with the explanatory content.
- Empty cycle and populated cycle both look balanced.

### Task 3: Lock Down the Stagger Algorithm Dialog Structure

**Files:**
- Create or Modify: `frontend/src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx`

- [ ] **Step 1: Add a failing dialog smoke test for the revised content hierarchy**

```tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import StaggerAlgorithmDialog from '../StaggerAlgorithmDialog';

describe('StaggerAlgorithmDialog', () => {
  it('shows the staged explanation structure for the stagger algorithm', () => {
    render(<StaggerAlgorithmDialog open onClose={() => {}} />);

    expect(screen.getByText(/Step 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Step 4/i)).toBeInTheDocument();
    expect(screen.getByText(/K_eq/i)).toBeInTheDocument();
    expect(screen.getByText(/Allowable/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: If the dialog will embed a PNG, add a failing test for image presence**

```tsx
expect(screen.getByAltText(/Stagger calculation algorithm/i)).toBeInTheDocument();
```

- [ ] **Step 3: Run the focused dialog test and verify it fails before implementation**

Run:

```bash
cd frontend
npm test -- --run src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx
```

Expected: FAIL if the image or revised section semantics are not yet present.

### Task 4: Implement `E10` in `StaggerAlgorithmDialog`

**Files:**
- Modify: `frontend/src/components/Calculation/StaggerAlgorithmDialog.tsx`
- Test: `frontend/src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx`
- Optional asset import: `frontend/src/assets/...` or another existing frontend asset location

- [ ] **Step 1: Import the PNG through the frontend bundle instead of referencing the docs path directly**

```tsx
import staggerAlgorithmImage from '../../assets/stagger-calculation-algorithm.png';
```

If the project already keeps static assets elsewhere, use that existing directory instead of creating a new convention.

- [ ] **Step 2: Insert a dedicated visual-reference section that sits between explanation blocks, not above everything**

```tsx
<Box>
  <Typography variant="subtitle1" fontWeight={700} gutterBottom>
    Visual Reference
  </Typography>
  <Paper variant="outlined" sx={{ p: 2 }}>
    <Box
      component="img"
      src={staggerAlgorithmImage}
      alt="Stagger calculation algorithm"
      sx={{ width: '100%', height: 'auto', display: 'block', borderRadius: 1 }}
    />
  </Paper>
</Box>
```

- [ ] **Step 3: Tighten section hierarchy so each section has one job**

```tsx
<Stack spacing={3}>
  <Box>{/* Step cards */}</Box>
  <Divider />
  <Box>{/* Formula summary */}</Box>
  <Divider />
  <Box>{/* Visual reference image */}</Box>
  <Divider />
  <Box>{/* Term glossary */}</Box>
  <Divider />
  <Box>{/* Pass/fail decision rules */}</Box>
</Stack>
```

- [ ] **Step 4: Keep the current SVG concept graph only if it still adds value next to the PNG**

```tsx
{showConceptGraph && <ConceptGraph />}
```

If the SVG duplicates the PNG and makes the dialog noisy, remove the duplication instead of preserving both.

- [ ] **Step 5: Run the focused dialog test and verify it passes**

Run:

```bash
cd frontend
npm test -- --run src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx
```

Expected: PASS

- [ ] **Step 6: Manual verification for `E10`**

Check:

- The PNG loads correctly in dev mode.
- The dialog remains readable without excessive scrolling.
- The formulas, terms, and decision rules still feel connected to the visual.

### Task 5: Lock Down the History Compare Algorithm Dialog Cleanup

**Files:**
- Create or Modify: `frontend/src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx`

- [ ] **Step 1: Add a failing smoke test for the cleaned-up History Compare dialog structure**

```tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AlgorithmTutorialDialog from '../AlgorithmTutorialDialog';

describe('AlgorithmTutorialDialog', () => {
  it('renders matching criteria and visual case sections', () => {
    render(<AlgorithmTutorialDialog open onClose={() => {}} />);

    expect(screen.getByText(/Matching Criteria/i)).toBeInTheDocument();
    expect(screen.getByText(/CASE A/i)).toBeInTheDocument();
    expect(screen.getByText(/CASE B/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the focused test and verify it fails before implementation**

Run:

```bash
cd frontend
npm test -- --run src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx
```

Expected: FAIL if the current dialog headings are still inconsistent or not test-friendly.

### Task 6: Implement `Q4` in `AlgorithmTutorialDialog`

**Files:**
- Modify: `frontend/src/components/HistoryCompare/AlgorithmTutorialDialog.tsx`
- Test: `frontend/src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx`

- [ ] **Step 1: Normalize section spacing and stop mixing large section gaps with dense internal cards**

```tsx
<DialogContent sx={{ p: 3 }}>
  <Grid container spacing={3}>
    <Grid item xs={12}>{/* section */}</Grid>
  </Grid>
</DialogContent>
```

- [ ] **Step 2: Standardize case-card structure so the three scenario cards read as one family**

```tsx
<Paper
  variant="outlined"
  sx={{ p: 2, height: '100%', position: 'relative', overflow: 'hidden', borderRadius: 2 }}
>
  <Box sx={{ position: 'absolute', top: 0, right: 0, px: 1.5, py: 0.5, ...badgeSx }}>
    CASE A
  </Box>
  <Typography variant="subtitle2" fontWeight={700} gutterBottom>
    Valid Match
  </Typography>
  <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
    ...
  </Typography>
</Paper>
```

- [ ] **Step 3: Make headings testable and readable instead of relying on mixed decorative phrasing**

```tsx
<Typography variant="h6" color="primary" fontWeight={700}>
  Matching Criteria
</Typography>
```

- [ ] **Step 4: Run the focused History Compare dialog test and verify it passes**

Run:

```bash
cd frontend
npm test -- --run src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx
```

Expected: PASS

- [ ] **Step 5: Manual verification for `Q4`**

Check:

- Section rhythm is consistent.
- Scenario cards no longer feel visually cramped or uneven.
- Desktop and narrow widths still preserve readable diagrams and labels.

### Task 7: Lock Down About Page Cleanup

**Files:**
- Create or Modify: `frontend/src/views/__tests__/AboutView.test.tsx`

- [ ] **Step 1: Add a failing smoke test for the cleaned-up About page structure**

```tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AboutView from '../AboutView';

describe('AboutView', () => {
  it('renders the application modules section and product heading', () => {
    render(<AboutView />);

    expect(screen.getByText(/TOV Analyzer/i)).toBeInTheDocument();
    expect(screen.getByText(/Application Modules/i)).toBeInTheDocument();
    expect(screen.getByText(/Trend Analyzer/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the focused test and verify it fails only if new structure markers do not yet exist**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/AboutView.test.tsx
```

Expected: likely FAIL if the chosen heading structure or labels differ from the intended cleanup.

### Task 8: Implement `E9` in `AboutView`

**Files:**
- Modify: `frontend/src/views/AboutView.tsx`
- Test: `frontend/src/views/__tests__/AboutView.test.tsx`

- [ ] **Step 1: Reduce the “single large card” feeling by using a lighter page shell**

```tsx
<Box sx={{ p: 3, maxWidth: 1100, mx: 'auto' }}>
  <Stack spacing={3}>
    <Box>{/* title and version */}</Box>
    <Paper variant="outlined" sx={{ p: 3 }}>{/* product summary */}</Paper>
    <Box>{/* modules grid */}</Box>
  </Stack>
</Box>
```

- [ ] **Step 2: Keep module cards compact and scan-oriented**

```tsx
<Card variant="outlined" sx={{ height: '100%' }}>
  <CardHeader
    avatar={<Avatar sx={{ bgcolor: 'primary.light' }}><IconComponent /></Avatar>}
    title={<Typography variant="subtitle1" fontWeight={700}>{mod.name}</Typography>}
  />
  <CardContent sx={{ pt: 0 }}>
    <Typography variant="body2" color="text.secondary" paragraph>
      {mod.description}
    </Typography>
    <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
      {mod.features.map(...)}
    </Stack>
  </CardContent>
</Card>
```

- [ ] **Step 3: Run the focused About test and verify it passes**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/AboutView.test.tsx
```

Expected: PASS

- [ ] **Step 4: Manual verification for `E9`**

Check:

- About page reads as structured application information rather than one dense info wall.
- Module cards are easy to scan.
- Wide and narrow widths both look intentional.

### Task 9: Final Verification for Batch 2

**Files:**
- Modify: none

- [ ] **Step 1: Run the targeted Batch 2 test suite**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/CalculationView.test.tsx src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx src/views/__tests__/AboutView.test.tsx
```

Expected: PASS

- [ ] **Step 2: Run the frontend build to catch typing and asset-import fallout**

Run:

```bash
cd frontend
npm run build
```

Expected: build completes successfully

- [ ] **Step 3: Manual UI verification checklist**

Check:

- `CalculationView` now explains Case A and Case B with cleaner separation.
- Stagger KPI cards feel compact, aligned, and readable.
- `StaggerAlgorithmDialog` has a clearer learning flow and correctly loads the algorithm visual asset.
- `AlgorithmTutorialDialog` has consistent spacing and scenario hierarchy.
- `AboutView` feels like structured product information rather than a single dense panel.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/CalculationView.tsx frontend/src/views/__tests__/CalculationView.test.tsx frontend/src/components/Calculation/StaggerAlgorithmDialog.tsx frontend/src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx frontend/src/components/HistoryCompare/AlgorithmTutorialDialog.tsx frontend/src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx frontend/src/views/AboutView.tsx frontend/src/views/__tests__/AboutView.test.tsx docs/superpowers/plans/2026-05-08-web-ui-review-triage-batch-2.md
git commit -m "docs: add web ui review triage batch 2 plan"
```

## Self-Review

- Spec coverage: The plan covers the approved Batch 2 items only: `Q4`, `Q5`, `Q6`, `E9`, `E10`.
- Placeholder scan: No open-ended `TODO` placeholders remain; each task includes exact files, test intent, and verification commands.
- Scope check: This stays within low-risk presentation cleanup and avoids the deferred higher-risk work (`B1-B3`, `E1-E8` except `E9` and `E10`).
- Ambiguity check: The only implementation-time branch is how the PNG asset is bundled. The plan explicitly requires following the repo’s existing frontend asset convention rather than inventing a new one.
