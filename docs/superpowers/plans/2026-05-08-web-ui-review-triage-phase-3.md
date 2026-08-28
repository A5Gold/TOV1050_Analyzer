# Web UI Review Triage Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the safe follow-up work after Batch 2 by first cleaning corrupted UI copy and fragile tests, then applying a small Phase 3 pass that improves Stagger Calculation trace/raw-data readability and cross-view wording consistency without entering broader layout refactors or cross-module bug fixes.

**Architecture:** Keep changes inside the existing frontend view and dialog boundaries that were already touched in Batch 2. Treat this work as two tightly scoped layers: `Phase 2.5` for text/test stabilization, then `Phase 3` for low-risk readability and consistency improvements. Avoid store-shape changes, backend changes, upload workflow redesign, sticky/frozen table behavior changes, and any new shared abstraction unless an existing local pattern already supports it.

**Tech Stack:** React 18, TypeScript, MUI 5, Vitest, Testing Library, Vite

---

## Scope Note

- This plan intentionally does **not** continue directly into broad UI redesign.
- The current repo state shows Batch 2 structure changes are mostly in place, but the affected files still contain corrupted strings and tests that assert against corrupted output.
- For that reason, this plan starts with a **Phase 2.5 stabilization pass** before any new UI polish.
- Phase 3 remains limited to high-value, low-to-medium risk improvements on the same frontend surfaces:
  - `CalculationView` wording consistency and trace/raw-data readability
  - `StaggerRawDataPanel` annotation/legend/help-text cleanup
  - `StaggerAlgorithmDialog` wording cleanup only
  - `AlgorithmTutorialDialog` wording cleanup only
  - `AboutView` wording cleanup and structure consistency only

## Explicitly Deferred For Later Batches / Roadmap

- `B1` web-mode upload compatibility
- `B2` summary frozen-column overlap / layering issue
- `B3` History Compare toolbar density / layout pressure
- `E1` Database Record information architecture refresh
- `E2` Metadata Editor interaction cleanup
- `E3` upload area redesign across modules
- `E4` results-first layout restructuring
- `E5` sticky / frozen chart-table coordination improvements
- `E6` Trend Analyzer recommendation presentation rework
- `E7` Trace tab deep redesign beyond copy/structure cleanup
- `E8` Raw Data chart annotation redesign beyond local label/help consistency

These items stay deferred because they either:

- span multiple modules,
- change interaction contracts,
- risk expanding into layout-heavy work,
- or deserve a separate batch with dedicated review and validation.

## Current State Summary

- Batch 1 is already complete.
- Batch 2 implementation is mostly present in code:
  - bilingual algorithm dialogs added,
  - Stagger concept graph removed,
  - visual PNG retained,
  - About page structure updated,
  - CalculationView hierarchy partially cleaned up.
- Focused verification already succeeded in the current workspace:
  - `CalculationView.test.tsx`
  - `StaggerAlgorithmDialog.test.tsx`
  - `AlgorithmTutorialDialog.test.tsx`
  - `AboutView.test.tsx`
  - `npm run build`
- Remaining blocker before true completion: several UI strings and tests still show mojibake/corrupted text and therefore should not be used as a stable baseline for future batches.

## Impact Analysis Summary

Per `AGENTS.md`, impact analysis was reviewed for candidate symbols before planning follow-up edits:

- `CalculationView` (`Function:frontend/src/views/CalculationView.tsx:CalculationView`) -> `LOW`
- `StaggerAlgorithmDialog` (`Function:frontend/src/components/Calculation/StaggerAlgorithmDialog.tsx:StaggerAlgorithmDialog`) -> `LOW`
- `AlgorithmTutorialDialog` (`Function:frontend/src/components/HistoryCompare/AlgorithmTutorialDialog.tsx:AlgorithmTutorialDialog`) -> `LOW`
- `AboutView` (`Function:frontend/src/views/AboutView.tsx:AboutView`) -> `LOW`

This supports continuing with the proposed localized UI stabilization and copy cleanup work.

## File Map

- Modify: `frontend/src/views/CalculationView.tsx`
  - Replace corrupted strings, normalize labels, and improve trace/raw-data helper copy without changing store behavior.
- Modify: `frontend/src/views/__tests__/CalculationView.test.tsx`
  - Replace corrupted-string assertions with stable wording/semantic assertions.
- Modify: `frontend/src/components/Calculation/StaggerRawDataPanel.tsx`
  - Clarify chart labels, range/selection helper text, and annotation wording if needed.
- Modify: `frontend/src/components/Calculation/StaggerAlgorithmDialog.tsx`
  - Replace corrupted bilingual strings and preserve Batch 2 structure.
- Modify: `frontend/src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx`
  - Assert against stable headings, section labels, and image presence.
- Modify: `frontend/src/components/HistoryCompare/AlgorithmTutorialDialog.tsx`
  - Replace corrupted bilingual strings while preserving current section hierarchy and visual cases.
- Modify: `frontend/src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx`
  - Assert against stable wording and visible sections rather than mojibake fragments.
- Modify: `frontend/src/views/AboutView.tsx`
  - Replace corrupted strings and keep module-card scanability.
- Modify: `frontend/src/views/__tests__/AboutView.test.tsx`
  - Assert against stable product/module headings.

## Preconditions

- Do not touch `AGENTS.md` or `CLAUDE.md`.
- Do not modify backend, Electron, API contracts, Zustand store shape, or upload parsing logic.
- Do not redesign page layout beyond local spacing/label hierarchy already present.
- If manual UI verification is performed, treat it as smoke coverage only; do not expand this batch into exploratory redesign.

### Task 1: Stabilize Batch 2 Copy Baseline

**Files:**
- Modify: `frontend/src/views/CalculationView.tsx`
- Modify: `frontend/src/components/Calculation/StaggerAlgorithmDialog.tsx`
- Modify: `frontend/src/components/HistoryCompare/AlgorithmTutorialDialog.tsx`
- Modify: `frontend/src/views/AboutView.tsx`

- [ ] **Step 1: Inspect each touched file for corrupted visible strings before editing**

Run:

```bash
cd frontend
rg -n "�|嚗|蝯|撌|銝|憭|隞|瘥|閬" src/views/CalculationView.tsx src/components/Calculation/StaggerAlgorithmDialog.tsx src/components/HistoryCompare/AlgorithmTutorialDialog.tsx src/views/AboutView.tsx
```

Expected: visible evidence of corrupted UI copy that must be normalized before Phase 3 polish.

- [ ] **Step 2: Replace corrupted UI text in `CalculationView` with stable Traditional Chinese plus existing English where intentionally bilingual**

Normalize these areas:

- page title/subtitle
- summary card labels
- Case A / Case B alerts
- upload helper text
- cycle reset label
- action buttons
- detail tab labels
- Summary / Trace / Raw Data helper alerts
- trace-side labels and result wording

Keep the current behavior intact. Do not change store calls or conditional logic while editing copy.

- [ ] **Step 3: Replace corrupted UI text in both algorithm dialogs while preserving Batch 2 hierarchy**

For `StaggerAlgorithmDialog`:

- keep:
  - process overview
  - formula summary
  - visual reference image
  - key terms
  - decision rules
- fix:
  - section titles
  - bilingual step descriptions
  - key-term descriptions
  - close button text

For `AlgorithmTutorialDialog`:

- keep:
  - chain rule section
  - matching criteria section
  - multiple report matching section
  - visual scenarios section
- fix:
  - title
  - bilingual body copy
  - case descriptions
  - close button text

- [ ] **Step 4: Replace corrupted About page copy without changing the module-card layout**

Normalize:

- product subtitle
- overview paragraph
- module names/descriptions
- chip labels
- section heading

- [ ] **Step 5: Run focused tests and capture current failures if any appear**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/CalculationView.test.tsx src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx src/views/__tests__/AboutView.test.tsx
```

Expected: likely failures until test strings are updated to match the normalized copy.

### Task 2: Rebuild the Tests Around Stable Wording

**Files:**
- Modify: `frontend/src/views/__tests__/CalculationView.test.tsx`
- Modify: `frontend/src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx`
- Modify: `frontend/src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx`
- Modify: `frontend/src/views/__tests__/AboutView.test.tsx`

- [ ] **Step 1: Update `CalculationView` tests to assert on stable labels and semantics**

Replace fragile corrupted-string assertions with checks such as:

- `高低值計算`
- `上傳 Exception Report`
- `上傳 n_Repeated Report`
- `摘要`
- `追蹤`
- `原始資料`
- `Case A`
- `Case B`
- KPI labels that will remain intentionally stable

- [ ] **Step 2: Update `StaggerAlgorithmDialog` tests to assert on section structure, not broken glyph fragments**

Assert on:

- `Stagger Algorithm Explain`
- `流程概覽 Process Overview`
- `公式摘要 Formula Summary`
- `Visual Reference`
- `關鍵詞彙 Key Terms`
- `判定規則 Decision Rules`
- image alt text

- [ ] **Step 3: Update `AlgorithmTutorialDialog` tests to assert on stable visible section headings**

Assert on:

- `History Compare Algorithm Logic`
- `Chain Rule`
- `Matching Criteria`
- `Multiple Report Matching`
- `Visual Scenarios`
- `CASE A`
- `CASE B`
- `CASE C`

- [ ] **Step 4: Update `AboutView` tests to assert on stable product/module headings**

Assert on:

- `TOV Analyzer`
- module section heading
- one or two stable module names, not full long paragraphs

- [ ] **Step 5: Run the focused tests again and verify they pass**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/CalculationView.test.tsx src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx src/views/__tests__/AboutView.test.tsx
```

Expected: PASS

### Task 3: Phase 3 Low-Risk Readability Pass for Trace and Raw Data

**Files:**
- Modify: `frontend/src/views/CalculationView.tsx`
- Modify: `frontend/src/components/Calculation/StaggerRawDataPanel.tsx`
- Test: `frontend/src/views/__tests__/CalculationView.test.tsx`

- [ ] **Step 1: Review the existing Trace tab labels and identify low-risk wording improvements only**

Targets:

- trace summary panel labels
- span check labels
- partial-trace warning copy
- empty-state copy

Do not redesign trace layout, reorder data contracts, or rename backend fields.

- [ ] **Step 2: Tighten Trace tab wording for faster scanning**

Examples of acceptable scope:

- consistent label style (`案例`, `追蹤狀態`, `允許值`, `結果`)
- shorter helper alert copy
- clearer phrasing around partial trace and `n/a`

Avoid changing calculation semantics or hidden data assumptions.

- [ ] **Step 3: Improve `StaggerRawDataPanel` labels and help text if they are inconsistent with the rest of the page**

Possible low-risk changes:

- normalize chart title wording
- clarify selected range text
- clarify alarm-range/max-location legend labels
- align button/empty-state wording with `CalculationView`

Do not change plotting logic, file parsing logic, or chart window calculation.

- [ ] **Step 4: Add or adjust tests only where the new wording is intentionally stable**

Prefer:

- visible alert text
- tab-empty-state text
- chart panel headings

Avoid snapshot-style tests and avoid over-asserting on transient details.

- [ ] **Step 5: Run the focused Calculation/Stagger tests**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/CalculationView.test.tsx src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx
```

Expected: PASS

### Task 4: Final Verification for the Stabilized Phase 3 Batch

**Files:**
- Verify only

- [ ] **Step 1: Run the full targeted frontend test set for touched files**

Run:

```bash
cd frontend
npm test -- --run src/views/__tests__/CalculationView.test.tsx src/components/Calculation/__tests__/StaggerAlgorithmDialog.test.tsx src/components/HistoryCompare/__tests__/AlgorithmTutorialDialog.test.tsx src/views/__tests__/AboutView.test.tsx
```

Expected: PASS

- [ ] **Step 2: Run production build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS

- [ ] **Step 3: Manual smoke verification**

Run:

```bash
cd frontend
npm run dev
```

Check:

- `CalculationView`
  - no visible corrupted strings
  - Case A / Case B copy reads cleanly
  - Summary / Trace / Raw Data labels are consistent
  - trace partial warning is understandable
- `StaggerAlgorithmDialog`
  - all section headings are readable
  - image loads correctly
- `AlgorithmTutorialDialog`
  - all section headings and case labels are readable
  - spacing hierarchy remains intact
- `AboutView`
  - heading, overview, and module cards display readable Traditional Chinese

- [ ] **Step 4: Run GitNexus change detection before commit**

Run:

```bash
npx gitnexus detect-changes
```

Expected: changed scope remains limited to the intended frontend UI surfaces.

If the CLI is unavailable in the workspace, use the MCP `detect_changes` tool instead before committing.

## Exit Criteria

This batch is complete when all of the following are true:

- Batch 2 touched files no longer display corrupted visible text
- related tests no longer assert on corrupted strings
- Phase 3 wording/readability improvements stay local to Stagger Calculation, History Compare dialog copy, and About copy
- focused tests pass
- frontend build passes
- manual smoke check finds no obvious text corruption on the touched screens

## Out of Scope Reminder

Do **not** let this batch expand into:

- upload workflow redesign,
- data-grid sticky/frozen fixes,
- History Compare toolbar compaction,
- Database Record or Metadata Editor redesign,
- Trend Analyzer recommendation redesign,
- cross-module architecture cleanup.
