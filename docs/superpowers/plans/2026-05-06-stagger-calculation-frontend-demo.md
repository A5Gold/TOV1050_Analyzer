# Stagger Calculation Frontend Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a frontend demo for the stagger calculation module with isolated parallel cycle tabs, summary/result views, and an algorithm explanation panel.

**Architecture:** Extend the existing `CalculationView` into a tabbed workspace where each cycle owns its own uploaded files, analysis state, selected result, and error state. Reuse the current MUI-based layout and add a dedicated cycle tab bar plus a richer algorithm drawer/dialog so the demo stays close to the current app structure while remaining isolated per cycle.

**Tech Stack:** React 18, TypeScript, MUI, Zustand, Vite

---

### Task 1: Add cycle workspace state

**Files:**
- Modify: `frontend/src/store/useCalculationStore.ts`
- Test: `frontend/src/store/__tests__/useCalculationStore.test.ts` (create if needed)

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from 'vitest';
import { useCalculationStore } from '../useCalculationStore';

describe('useCalculationStore cycle workspace', () => {
  it('creates independent cycle tabs', () => {
    const store = useCalculationStore.getState();
    store.createCycle('Cycle A');
    store.createCycle('Cycle B');

    const next = useCalculationStore.getState();
    expect(next.cycles).toHaveLength(2);
    expect(next.activeCycleId).toBeDefined();
  });

  it('keeps uploaded files and results isolated per cycle', () => {
    const store = useCalculationStore.getState();
    store.reset();
    store.createCycle('Cycle A');
    store.createCycle('Cycle B');

    const [cycleA, cycleB] = useCalculationStore.getState().cycles;
    store.addFileToCycle(cycleA.id, new File(['a'], 'a.xlsx'));
    store.addFileToCycle(cycleB.id, new File(['b'], 'b.xlsx'));

    const state = useCalculationStore.getState();
    expect(state.cycles[0].uploadedFiles).toHaveLength(1);
    expect(state.cycles[1].uploadedFiles).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- frontend/src/store/__tests__/useCalculationStore.test.ts -v`
Expected: fail because `cycles`, `createCycle`, and `addFileToCycle` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```ts
type CalculationCycle = {
  id: string;
  name: string;
  uploadedFiles: File[];
  isLoading: boolean;
  error: string | null;
  wearResults: WearResult[];
  trendResults: TrendResult[];
  selectedResultId: string | null;
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- frontend/src/store/__tests__/useCalculationStore.test.ts -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/useCalculationStore.ts frontend/src/store/__tests__/useCalculationStore.test.ts
git commit -m "feat: add isolated cycle state for stagger demo"
```

---

### Task 2: Build the demo page layout

**Files:**
- Modify: `frontend/src/views/CalculationView.tsx`
- Create: `frontend/src/components/Calculation/CycleTabBar.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import CalculationView from '../CalculationView';

describe('CalculationView demo', () => {
  it('renders cycle tabs and algorithm button', () => {
    render(<CalculationView />);
    expect(screen.getByText(/Cycle A/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /algorithm/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- frontend/src/views/__tests__/CalculationView.test.tsx -v`
Expected: fail because cycle tabs and the new button are not present.

- [ ] **Step 3: Write minimal implementation**

```tsx
// Replace the single-tab result area with:
// 1. a cycle tab bar
// 2. per-cycle upload/result state
// 3. a right-aligned algorithm explain button
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- frontend/src/views/__tests__/CalculationView.test.tsx -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/CalculationView.tsx frontend/src/components/Calculation/CycleTabBar.tsx
git commit -m "feat: add stagger calculation demo layout"
```

---

### Task 3: Add algorithm explanation panel

**Files:**
- Create: `frontend/src/components/Calculation/StaggerAlgorithmDialog.tsx`
- Modify: `frontend/src/views/CalculationView.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StaggerAlgorithmDialog from '../StaggerAlgorithmDialog';

describe('StaggerAlgorithmDialog', () => {
  it('shows flow, formula, parameters, and wind speed factor meaning', () => {
    render(<StaggerAlgorithmDialog open onClose={() => {}} />);
    expect(screen.getByText(/Algorithm Flow/i)).toBeInTheDocument();
    expect(screen.getByText(/Formula/i)).toBeInTheDocument();
    expect(screen.getByText(/Key Parameters/i)).toBeInTheDocument();
    expect(screen.getByText(/Wind Speed Factor Meaning/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- frontend/src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx -v`
Expected: fail because the dialog does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```tsx
// Build a dialog that explains:
// - data flow
// - formula equation
// - key parameter definitions
// - the wind speed factor's effect on stagger
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- frontend/src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Calculation/StaggerAlgorithmDialog.tsx frontend/src/views/CalculationView.tsx
git commit -m "feat: add stagger algorithm explanation dialog"
```

---

### Task 4: Verify the demo visually

**Files:**
- Review: `frontend/src/views/CalculationView.tsx`
- Review: `frontend/src/components/Calculation/CycleTabBar.tsx`
- Review: `frontend/src/components/Calculation/StaggerAlgorithmDialog.tsx`

- [ ] **Step 1: Run the frontend**

Run: `npm run dev`

- [ ] **Step 2: Open the calculation demo page**

Expected: a page showing upload area, cycle tabs, summary/result region, and algorithm explanation button.

- [ ] **Step 3: Check isolation behavior**

Expected: editing or analyzing one cycle does not change the other cycle tabs.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/CalculationView.tsx frontend/src/components/Calculation/CycleTabBar.tsx frontend/src/components/Calculation/StaggerAlgorithmDialog.tsx
git commit -m "feat: complete stagger frontend demo"
```

