# Wire Wear Variable Threshold Levels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Wire Wear threshold levels metadata-driven so the Metadata Editor can persist L1-only Wire Wear thresholds and the detector only emits configured levels.

**Architecture:** Preserve the existing Metadata Editor table and backend workbook flow, but make blank/missing Wire Wear L2 values first-class data. Normalize threshold sheets without synthesizing missing levels, and update scalar detection to compute gatekeepers from available levels instead of assuming L1 and L2 always exist.

**Tech Stack:** Python, pandas, FastAPI service layer, pytest, React, TypeScript, MUI DataGrid, Vitest or the repository's existing frontend test runner.

---

## Impact Analysis Requirement

Before editing any function, class, or method below, run the project-required impact analysis:

```powershell
# Use codebase-memory MCP trace_path for each target symbol with risk_labels=true before editing.
```

Targets:

- `MetadataManager._normalize_thresholds`
- `MetadataService.save_configuration`
- `ExceptionDetector._detect_scalar`
- `MetadataEditorView.transformToGrid`
- `MetadataEditorView.transformToBackend`
- `MetadataEditorView.handleSave`

Report direct callers, affected process/API surface, and risk level before making edits. Existing exploration already found `_normalize_thresholds`, `_detect_scalar`, and `update_metadata/save_configuration` to be CRITICAL risk paths.

## File Structure

- Modify: `backend/app/core/metadata.py`
  - Preserve missing threshold level semantics in `MetadataManager._normalize_thresholds()`.
- Modify: `backend/app/core/analyzers.py`
  - Make `ExceptionDetector._detect_scalar()` use active levels from available threshold columns.
- Modify: `backend/tests/test_metadata.py` or create `backend/tests/test_metadata_threshold_levels.py`
  - Add normalization tests for Wire Wear L1-only rows.
- Modify: `backend/tests/test_metadata_service.py`
  - Add save/reload tests for blank Wire Wear L2 metadata.
- Modify: `backend/tests/test_analyzers.py` or `backend/tests/test_detection.py`
  - Add Wire Wear L1-only and L1/L2 regression detection tests.
- Modify: `frontend/src/views/MetadataEditorView.tsx`
  - Preserve blank level values in grid/backend transforms and clear stale tab cache after save.
- Create or modify: `frontend/src/views/__tests__/MetadataEditorView.test.tsx`
  - Add transform/cache behavior tests. If this project keeps tests elsewhere, place the test beside the current frontend view test pattern.
- Modify: `docs/architecture.md`
  - Update section 4.3 to state Wire Wear supports metadata-driven L1-only or L1/L2 levels.

---

### Task 1: Backend Test For Threshold Normalization

**Files:**
- Modify or create: `backend/tests/test_metadata_threshold_levels.py`
- Read: `backend/app/core/metadata.py`

- [ ] **Step 1: Run codebase-memory impact analysis for `MetadataManager._normalize_thresholds`**

Use codebase-memory MCP `trace_path` with `risk_labels=true`:

```powershell
trace_path target="MetadataManager._normalize_thresholds" risk_labels=true
```

Fallback with codebase-memory MCP:

```text
trace_path(function_name="C-Smart-Maintanence-TOV640_Analyzer.backend.app.core.metadata.MetadataManager._normalize_thresholds", direction="inbound", mode="calls", depth=2, risk_labels=true)
```

Expected: callers include `get_all_thresholds`, with downstream impact on `MetadataService.get_metadata` and `ExceptionDetector.analyze`.

- [ ] **Step 2: Write failing normalization tests**

Add this test file if no better existing metadata threshold test file exists:

```python
import pandas as pd

from backend.app.core.metadata import MetadataManager


def test_normalize_thresholds_preserves_wire_wear_l1_only_long_format():
    manager = MetadataManager.__new__(MetadataManager)
    raw = pd.DataFrame(
        [
            {
                "Class": "both",
                "Track Type": "both",
                "Exc Type": "Wire Wear L1",
                "min": None,
                "max": 9.1,
            },
            {
                "Class": "SCL",
                "Track Type": "both",
                "Exc Type": "Wire Wear L1",
                "min": None,
                "max": 7.44,
            },
        ]
    )

    result = manager._normalize_thresholds(raw)

    both = result[(result["Class"] == "both") & (result["Exc Type"] == "Wire Wear")].iloc[0]
    scl = result[(result["Class"] == "SCL") & (result["Exc Type"] == "Wire Wear")].iloc[0]

    assert both["Wire Wear L1"] == 9.1
    assert scl["Wire Wear L1"] == 7.44
    assert "Wire Wear L2" not in result.columns or pd.isna(both.get("Wire Wear L2"))
    assert "Wire Wear L2" not in result.columns or pd.isna(scl.get("Wire Wear L2"))


def test_normalize_thresholds_keeps_wire_wear_l2_when_present_long_format():
    manager = MetadataManager.__new__(MetadataManager)
    raw = pd.DataFrame(
        [
            {
                "Class": "both",
                "Track Type": "both",
                "Exc Type": "Wire Wear L1",
                "min": None,
                "max": 9.1,
            },
            {
                "Class": "both",
                "Track Type": "both",
                "Exc Type": "Wire Wear L2",
                "min": None,
                "max": 10.2,
            },
        ]
    )

    result = manager._normalize_thresholds(raw)
    row = result[(result["Class"] == "both") & (result["Exc Type"] == "Wire Wear")].iloc[0]

    assert row["Wire Wear L1"] == 9.1
    assert row["Wire Wear L2"] == 10.2
```

- [ ] **Step 3: Run the new tests and verify current behavior**

Run:

```powershell
pytest backend/tests/test_metadata_threshold_levels.py -v
```

Expected: The first test may fail if current normalization or surrounding assumptions synthesize Wire Wear L2. If both pass, keep them as regression coverage and continue.

- [ ] **Step 4: Commit the failing tests if following strict TDD**

```powershell
git add backend/tests/test_metadata_threshold_levels.py
git commit -m "test: cover wire wear l1-only threshold normalization"
```

If the repository workflow does not allow committing failing tests, defer the commit until Task 2 passes.

---

### Task 2: Preserve Missing Levels In Metadata Normalization

**Files:**
- Modify: `backend/app/core/metadata.py`
- Test: `backend/tests/test_metadata_threshold_levels.py`

- [ ] **Step 1: Re-open the implementation**

Read the current method before editing:

```powershell
python - <<'PY'
from pathlib import Path
path = Path("backend/app/core/metadata.py")
lines = path.read_text().splitlines()
for i in range(220, 301):
    print(f"{i + 1}: {lines[i]}")
PY
```

Expected: `_normalize_thresholds()` returns wide input unchanged and pivots long `Exc Type` values to level columns.

- [ ] **Step 2: Keep the implementation narrow**

Use `apply_patch` to adjust only `MetadataManager._normalize_thresholds()` if tests show it is needed. The intended behavior is:

```python
# Required behavior inside _normalize_thresholds():
# - Wide format input returns unchanged.
# - Long format only creates a level column when source row has a non-null numeric value.
# - No default Wire Wear L2 column/value is created when no Wire Wear L2 source row exists.
```

If current code already satisfies this, do not refactor. Leave the regression tests as the delivered change for this task.

- [ ] **Step 3: Run normalization tests**

Run:

```powershell
pytest backend/tests/test_metadata_threshold_levels.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Run nearby metadata tests**

Run:

```powershell
pytest backend/tests/test_metadata.py backend/tests/test_metadata_service.py -v
```

Expected: all tests pass, or failures are unrelated pre-existing failures documented with exact test names.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/core/metadata.py backend/tests/test_metadata_threshold_levels.py
git commit -m "fix: preserve wire wear missing threshold levels"
```

---

### Task 3: Backend Save/Reload Test For Blank Wire Wear L2

**Files:**
- Modify: `backend/tests/test_metadata_service.py`
- Read: `backend/app/core/metadata_service.py`

- [ ] **Step 1: Run codebase-memory impact analysis for `MetadataService.save_configuration`**

Use codebase-memory MCP `trace_path` with `risk_labels=true`:

```powershell
trace_path target="MetadataService.save_configuration" risk_labels=true
```

Fallback:

```text
trace_path(function_name="C-Smart-Maintanence-TOV640_Analyzer.backend.app.core.metadata_service.MetadataService.save_configuration", direction="inbound", mode="calls", depth=2, risk_labels=true)
```

Expected: callers include `update_metadata`; risk is high or critical because it writes configuration workbooks.

- [ ] **Step 2: Add save/reload regression test**

Append a test using `tmp_path` and a real workbook:

```python
import pandas as pd

from backend.app.core.metadata_service import MetadataService


def test_save_and_reload_threshold_preserves_blank_wire_wear_l2(tmp_path):
    config_dir = tmp_path
    workbook = config_dir / "metadata.xlsx"
    original = pd.DataFrame(
        [
            {
                "Class": "both",
                "Track Type": "both",
                "Exc Type": "Wire Wear",
                "Wire Wear L1": 9.1,
                "Wire Wear L2": 10.2,
            },
            {
                "Class": "SCL",
                "Track Type": "both",
                "Exc Type": "Wire Wear",
                "Wire Wear L1": 7.44,
                "Wire Wear L2": 8.16,
            },
        ]
    )
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        original.to_excel(writer, sheet_name="threshold", index=False)

    service = MetadataService(config_dir=config_dir)
    payload = [
        {
            "Class": "both",
            "Track Type": "both",
            "Exc Type": "Wire Wear",
            "Wire Wear L1": 9.1,
            "Wire Wear L2": None,
        },
        {
            "Class": "SCL",
            "Track Type": "both",
            "Exc Type": "Wire Wear",
            "Wire Wear L1": 7.44,
            "Wire Wear L2": None,
        },
    ]

    service.save_configuration("metadata.xlsx", payload, sheet_name="threshold")
    reloaded = service.get_metadata("metadata.xlsx", sheet_name="threshold")

    by_class = {row["Class"]: row for row in reloaded}
    assert by_class["both"]["Wire Wear L1"] == 9.1
    assert by_class["SCL"]["Wire Wear L1"] == 7.44
    assert by_class["both"].get("Wire Wear L2") is None
    assert by_class["SCL"].get("Wire Wear L2") is None
```

If `MetadataService.__init__` uses a different argument name, adapt only the constructor line after reading the current signature.

- [ ] **Step 3: Run the metadata service test**

Run:

```powershell
pytest backend/tests/test_metadata_service.py::test_save_and_reload_threshold_preserves_blank_wire_wear_l2 -v
```

Expected: fails before the persistence fix if blank L2 is restored, otherwise passes and becomes regression coverage.

- [ ] **Step 4: Implement minimal service/persistence fix if needed**

If the test fails, fix the smallest responsible layer:

```python
# Required behavior:
# - DataFrame built from the save payload must retain blank Wire Wear L2 as blank.
# - Replacing the threshold sheet must not preserve old values from the previous sheet.
# - get_metadata() must return blank L2 as None, not the old numeric value.
```

Do not alter backup or atomic replace behavior.

- [ ] **Step 5: Run service tests**

Run:

```powershell
pytest backend/tests/test_metadata_service.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/core/metadata_service.py backend/tests/test_metadata_service.py
git commit -m "fix: persist blank wire wear l2 thresholds"
```

---

### Task 4: Make Scalar Detection Use Active Levels

**Files:**
- Modify: `backend/app/core/analyzers.py`
- Modify: `backend/tests/test_analyzers.py` or `backend/tests/test_detection.py`

- [ ] **Step 1: Run codebase-memory impact analysis for `ExceptionDetector._detect_scalar`**

Use codebase-memory MCP `trace_path` with `risk_labels=true`:

```powershell
trace_path target="ExceptionDetector._detect_scalar" risk_labels=true
```

Fallback:

```text
trace_path(function_name="C-Smart-Maintanence-TOV640_Analyzer.backend.app.core.analyzers.ExceptionDetector._detect_scalar", direction="both", mode="calls", depth=2, risk_labels=true)
```

Expected: callers include `ExceptionDetector.analyze`; affected API surface includes analysis generation.

- [ ] **Step 2: Add Wire Wear L1-only detection test**

Add to the existing detector test file that already constructs an `ExceptionDetector` with mock metadata. Use the repository's fixture pattern. The core assertion should be:

```python
def test_wire_wear_l1_only_threshold_emits_l1_only(detector):
    df = pd.DataFrame(
        {
            "Chainage": [100.0, 101.0, 102.0],
            "Class": ["both", "both", "both"],
            "height1": [5000, 5000, 5000],
            "height2": [5000, 5000, 5000],
            "height3": [5000, 5000, 5000],
            "height4": [5000, 5000, 5000],
            "wear1": [9.0, 9.2, 9.3],
            "wear2": [9.0, 9.2, 9.3],
            "wear3": [9.0, 9.2, 9.3],
            "wear4": [9.0, 9.2, 9.3],
            "wear_min": [9.0, 9.2, 9.3],
        }
    )
    thresholds = pd.DataFrame(
        [
            {
                "Class": "both",
                "Track Type": "both",
                "Exc Type": "Wire Wear",
                "Wire Wear L1": 9.1,
                "Wire Wear L2": None,
            }
        ]
    )

    result = detector._detect_scalar(
        df=df,
        col_prefix="wear",
        exc_type="Wire Wear",
        thresholds=thresholds,
        mode="min",
        date_str="20260630",
        track="DN",
        line="TML",
        section_name="Mainline",
    )

    assert not result.empty
    assert set(result["level"]) == {"L1"}
    assert set(result["Threshold Value"]) == {9.1}
```

If `_group_consecutive()` requires additional mapped columns, add only the minimal columns used by the existing tests.

- [ ] **Step 3: Add two-level regression test**

Add this assertion using the same fixture style:

```python
def test_wire_wear_two_level_threshold_still_emits_l2(detector):
    df = pd.DataFrame(
        {
            "Chainage": [100.0, 101.0, 102.0],
            "Class": ["both", "both", "both"],
            "wear1": [9.8, 9.9, 10.3],
            "wear2": [9.8, 9.9, 10.3],
            "wear3": [9.8, 9.9, 10.3],
            "wear4": [9.8, 9.9, 10.3],
            "wear_min": [9.8, 9.9, 10.3],
        }
    )
    thresholds = pd.DataFrame(
        [
            {
                "Class": "both",
                "Track Type": "both",
                "Exc Type": "Wire Wear",
                "Wire Wear L1": 9.1,
                "Wire Wear L2": 10.2,
            }
        ]
    )

    result = detector._detect_scalar(
        df=df,
        col_prefix="wear",
        exc_type="Wire Wear",
        thresholds=thresholds,
        mode="min",
        date_str="20260630",
        track="DN",
        line="TML",
        section_name="Mainline",
    )

    assert not result.empty
    assert "L2" in set(result["level"])
    assert 10.2 in set(result["Threshold Value"])
```

- [ ] **Step 4: Run tests to verify failure**

Run:

```powershell
pytest backend/tests/test_analyzers.py backend/tests/test_detection.py -k "wire_wear or Wire Wear" -v
```

Expected: the L1-only test fails or exposes current L1/L2 assumptions.

- [ ] **Step 5: Implement active-level scalar detection**

In `ExceptionDetector._detect_scalar()`, replace the fixed L1/L2 gatekeeper block with a helper pattern equivalent to:

```python
level_names = ["L1", "L2"]
level_series = {
    level: self._get_vectorized_threshold(df, thresholds, exc_type, f"{exc_type} {level}")
    for level in level_names
    if f"{exc_type} {level}" in thresholds.columns
}
level_series = {
    level: series
    for level, series in level_series.items()
    if series.notna().any()
}

if not level_series:
    return pd.DataFrame()

threshold_frame = pd.DataFrame(level_series)
if mode == "min":
    gatekeeper = threshold_frame.max(axis=1, skipna=True)
    mask = df[agg_col] <= gatekeeper
else:
    gatekeeper = threshold_frame.min(axis=1, skipna=True)
    mask = df[agg_col] >= gatekeeper
mask = mask & gatekeeper.notna()
```

Then update the classification loop to iterate configured levels in severity order:

```python
for level in ["L1", "L2"]:
    raw = self._manual_threshold_lookup(thresholds, exc_type, f"{exc_type} {level}", cls)
    threshold = float(raw) if raw is not None and not pd.isna(raw) else None
    if threshold is None:
        continue
    if mode == "min" and val <= threshold:
        final_level = level
        final_thresh = threshold
        break
    if mode == "max" and val >= threshold:
        final_level = level
        final_thresh = threshold
        break
```

Keep the supported scalar levels at `["L1", "L2"]` for this task. Do not change stagger.

- [ ] **Step 6: Run detector tests**

Run:

```powershell
pytest backend/tests/test_analyzers.py backend/tests/test_detection.py -v
```

Expected: all detector tests pass.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/core/analyzers.py backend/tests/test_analyzers.py backend/tests/test_detection.py
git commit -m "fix: detect wire wear using configured threshold levels"
```

---

### Task 5: Frontend Preserve Blank Level Values

**Files:**
- Modify: `frontend/src/views/MetadataEditorView.tsx`
- Create or modify: `frontend/src/views/__tests__/MetadataEditorView.test.tsx`

- [ ] **Step 1: Run codebase-memory impact analysis for frontend transform and save functions**

Use codebase-memory MCP:

```text
trace_path(function_name="C-Smart-Maintanence-TOV640_Analyzer.frontend.src.views.MetadataEditorView.transformToBackend", direction="both", mode="calls", depth=2, risk_labels=true)
trace_path(function_name="C-Smart-Maintanence-TOV640_Analyzer.frontend.src.views.MetadataEditorView.transformToGrid", direction="both", mode="calls", depth=2, risk_labels=true)
trace_path(function_name="C-Smart-Maintanence-TOV640_Analyzer.frontend.src.views.MetadataEditorView.handleSave", direction="both", mode="calls", depth=2, risk_labels=true)
```

Expected: `handleSave` calls `transformToBackend` and `metadataApi.saveMetadata`; `loadData` calls `transformToGrid`.

- [ ] **Step 2: Make transform helpers testable if needed**

If `transformToGrid` and `transformToBackend` are currently nested inside `MetadataEditorView`, extract them to named exported helpers in the same file:

```typescript
export const transformMetadataToGrid = (data: any[]): MetadataRow[] => {
  return data.map((item, index) => {
    const excType = item['Exc Type'] || item.exception_type || '';
    const prefix = excType.includes('Stagger') ? 'Stagger' : excType;
    return {
      ...item,
      id: item.id ?? `${Date.now()}-${index}`,
      L1: item[`${prefix} L1`] ?? null,
      L2: item[`${prefix} L2`] ?? null,
      L3: item[`${prefix} L3`] ?? null,
      _prefix: prefix,
    };
  });
};

export const transformGridToMetadata = (gridRows: MetadataRow[]): any[] => {
  return gridRows.map(row => {
    const { id, L1, L2, L3, _prefix, ...rest } = row;
    return {
      ...rest,
      [`${_prefix} L1`]: L1 ?? null,
      [`${_prefix} L2`]: L2 ?? null,
      [`${_prefix} L3`]: L3 ?? null,
    };
  });
};
```

Then keep existing local names as wrappers or replace call sites:

```typescript
const gridRows = transformMetadataToGrid(rawData);
const payload = transformGridToMetadata(rows);
```

This explicit-null payload prevents stale workbook values from being implied by omitted properties.

- [ ] **Step 3: Add frontend transform tests**

Create a test with the repository's frontend test utilities:

```typescript
import { describe, expect, it } from 'vitest';
import { transformGridToMetadata, transformMetadataToGrid } from '../MetadataEditorView';

describe('MetadataEditorView threshold transforms', () => {
  it('keeps blank Wire Wear L2 blank when loading grid data', () => {
    const rows = transformMetadataToGrid([
      {
        Class: 'both',
        'Track Type': 'both',
        'Exc Type': 'Wire Wear',
        'Wire Wear L1': 9.1,
        'Wire Wear L2': null,
      },
    ]);

    expect(rows[0].L1).toBe(9.1);
    expect(rows[0].L2).toBeNull();
    expect(rows[0]._prefix).toBe('Wire Wear');
  });

  it('sends explicit null when Wire Wear L2 is cleared', () => {
    const payload = transformGridToMetadata([
      {
        id: 'row-1',
        Class: 'both',
        'Track Type': 'both',
        'Exc Type': 'Wire Wear',
        L1: 9.1,
        L2: null,
        L3: null,
        _prefix: 'Wire Wear',
      },
    ] as any);

    expect(payload[0]['Wire Wear L1']).toBe(9.1);
    expect(payload[0]['Wire Wear L2']).toBeNull();
    expect(payload[0]['Wire Wear L3']).toBeNull();
  });
});
```

- [ ] **Step 4: Clear stale cache after save**

In `handleSave`, after a successful `metadataApi.saveMetadata(...)`, update the active sheet cache:

```typescript
tabsDataCache.current[currentSheet] = transformMetadataToGrid(payload);
setRows(tabsDataCache.current[currentSheet]);
```

Alternatively delete the cache entry and force reload:

```typescript
delete tabsDataCache.current[currentSheet];
await loadData(true);
```

Choose the option that best fits the current component without causing double toasts. The key requirement is that switching tabs cannot restore pre-save row data from `tabsDataCache`.

- [ ] **Step 5: Run frontend tests**

Run from the frontend directory:

```powershell
npm test -- MetadataEditorView
```

If the project uses another script, inspect `frontend/package.json` and run the equivalent targeted test command.

Expected: MetadataEditorView tests pass.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/views/MetadataEditorView.tsx frontend/src/views/__tests__/MetadataEditorView.test.tsx
git commit -m "fix: preserve blank wire wear thresholds in metadata editor"
```

---

### Task 6: Update Architecture Documentation

**Files:**
- Modify: `docs/architecture.md`
- Read: `docs/superpowers/specs/2026-06-30-wire-wear-variable-threshold-levels-design.md`

- [ ] **Step 1: Update section 4.3 level table**

Change the Wire Wear row from fixed `L1, L2` to metadata-driven wording:

```markdown
| `Wire Wear` | `wear_min` | 值越低越嚴重 | metadata-driven: L1 or L1/L2 |
```

- [ ] **Step 2: Update scalar gatekeeper wording**

Replace the fixed scalar gatekeeper wording with:

```markdown
Scalar detection gatekeeper：

- Min mode：使用可用 levels 中最寬鬆的 threshold。若 L1/L2 都存在，等同 `max(L1, L2)`；若只存在 L1，則使用 L1。
- Max mode：使用可用 levels 中最寬鬆的 threshold。若 L1/L2 都存在，等同 `min(L1, L2)`；若只存在 L1，則使用 L1。
```

- [ ] **Step 3: Update level判定 wording**

Add:

```markdown
若某 level 在 metadata 中為 blank/NaN，該 level 不參與 gatekeeper 或 level 判定。Wire Wear 因此可用於 L1-only simulation。
```

- [ ] **Step 4: Commit**

```powershell
git add docs/architecture.md docs/superpowers/specs/2026-06-30-wire-wear-variable-threshold-levels-design.md docs/superpowers/plans/2026-06-30-wire-wear-variable-threshold-levels.md
git commit -m "docs: plan wire wear variable threshold levels"
```

---

### Task 7: Full Regression And Change Detection

**Files:**
- No code edits unless failures identify a scoped bug.

- [ ] **Step 1: Run backend regression**

Run:

```powershell
pytest backend/tests/test_metadata_threshold_levels.py backend/tests/test_metadata_service.py backend/tests/test_analyzers.py backend/tests/test_detection.py -v
```

Expected: all selected backend tests pass.

- [ ] **Step 2: Run frontend regression**

Run:

```powershell
cd frontend
npm test -- MetadataEditorView
```

Expected: targeted frontend tests pass.

- [ ] **Step 3: Run broader tests if time allows**

Backend:

```powershell
pytest backend/tests -v
```

Frontend:

```powershell
cd frontend
npm test
```

Expected: pass, or document unrelated existing failures with exact test names.

- [ ] **Step 4: Run required change detection before final commit/PR**

Use codebase-memory MCP `trace_path` with `risk_labels=true`:

```powershell
trace_path risk_labels=true
```

Fallback with codebase-memory MCP:

```text
detect_changes(project="C-Smart-Maintanence-TOV640_Analyzer", depth=2)
```

Expected affected scope:

- metadata threshold normalization
- metadata save/reload
- scalar exception detection
- Metadata Editor threshold transforms/cache
- architecture docs

Unexpected affected flows should be reviewed before completion.

- [ ] **Step 5: Final status**

Summarize:

- Whether Wire Wear L1-only reload is fixed.
- Whether Wire Wear L1-only detection emits only L1.
- Whether existing L1/L2 behavior remains intact.
- Exact backend/frontend tests run.
- Change detection results and risk notes.
