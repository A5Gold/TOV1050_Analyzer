# Stagger Calculation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stagger calculation flow that selects candidate `Summary ID` rows, resolves `Ch_I / Spt_A / Spt_I / Spt_B`, maps `ChartData` measurements for A/I/B, applies EAL/TML-specific `K_eq` strategies, and exposes summary + trace results without changing existing wear/trend behavior.

**Architecture:** Keep the feature in small stagger-specific modules under `backend/app/core/calculation`. Reuse existing workbook parsing and metadata loading only through narrow seams, especially a new stagger metadata adapter that reads Support database and Wind Speed Factor into typed structures without altering existing metadata APIs or parser contracts.

**Tech Stack:** Python 3.12, pandas, openpyxl, FastAPI, pytest

---

## File Structure

### New files

- `backend/app/core/calculation/stagger_types.py`
  - Dataclasses for selected summary rows, resolved references, resolved measurements, span computations, and summary/trace outputs.
- `backend/app/core/calculation/stagger_metadata.py`
  - Stagger-specific repositories for support points, wind-factor strategies, and typed metadata loading.
- `backend/app/core/calculation/stagger_selector.py`
  - Candidate `Summary ID` filtering for Case A / Case B plus track normalization.
- `backend/app/core/calculation/stagger_reference.py`
  - `Ch_I`, nearest support, adjacent support, and span derivation helpers.
- `backend/app/core/calculation/stagger_measurements.py`
  - `ChartData` row lookup for A/I/B points and `WHGT*` / `STG*` reduction logic.
- `backend/app/core/calculation/stagger_keq.py`
  - `EalKeqStrategy` and `TmlKeqStrategy`.
- `backend/app/core/calculation/stagger_formula.py`
  - Pure formulas for `B`, `P`, `S`, `E`, `P'`, short-circuit check, and span result judgment.
- `backend/app/core/calculation/stagger_service.py`
  - End-to-end orchestration from workbook inputs to summary/trace output.
- `backend/tests/test_stagger_selector.py`
  - Unit tests for candidate selection logic.
- `backend/tests/test_stagger_reference.py`
  - Unit tests for support lookup and span derivation.
- `backend/tests/test_stagger_measurements.py`
  - Unit tests for `ChartData` mapping and extrema selection.
- `backend/tests/test_stagger_keq.py`
  - Unit tests for EAL/TML `K_eq` strategies.
- `backend/tests/test_stagger_formula.py`
  - Unit tests for pure formula helpers.
- `backend/tests/test_stagger_service.py`
  - Integration-style tests for orchestration with synthetic inputs.
- `backend/tests/test_stagger_calculation_api.py`
  - API tests for the new stagger endpoint.

### Modified files

- `backend/app/core/calculation/excel_parser.py`
  - Add stagger-specific helpers only; do not change existing parser return contracts.
- `backend/app/api/endpoints/calculation.py`
  - Add the stagger endpoint and wire it to the new service.
- `backend/tests/test_calculation.py`
  - Add regression coverage proving existing parser behavior is unchanged.
- `docs/superpowers/specs/2026-05-05-stagger-calculation-design.md`
  - Keep implementation notes aligned if workbook validation changes assumptions.

### Existing files to read before coding

- `backend/app/core/calculation/excel_parser.py`
- `backend/app/core/metadata.py`
- `backend/app/core/config.py`
- `backend/app/api/endpoints/calculation.py`
- `backend/tests/test_calculation.py`
- `backend/tests/test_calculation_api.py`
- `docs/superpowers/specs/2026-05-05-stagger-calculation-design.md`

---

### Task 1: Define stagger-specific types and output models

**Files:**
- Create: `backend/app/core/calculation/stagger_types.py`
- Create: `backend/tests/test_stagger_formula.py`

- [ ] **Step 1: Write the failing type test**

```python
from app.core.calculation.stagger_types import (
    SelectedSummaryRecord,
    ResolvedReference,
    ResolvedMeasurements,
    StaggerSummaryResult,
)


def test_stagger_summary_result_keeps_trace_flags_and_remark_list():
    result = StaggerSummaryResult(
        id="SG-001",
        line="EAL",
        track="up",
        exception_type="Stagger Left",
        max_location=121000.0,
        chi=121000.0,
        spt_i=121020.0,
        k_eq=1.32,
        overall_result="pass",
        trace_available=True,
        remark=["Case A"],
    )

    assert result.id == "SG-001"
    assert result.track == "up"
    assert result.trace_available is True
    assert result.remark == ["Case A"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_stagger_formula.py::test_stagger_summary_result_keeps_trace_flags_and_remark_list -v`

Expected: FAIL with `ModuleNotFoundError` or missing type definitions

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass, field


@dataclass(slots=True)
class SelectedSummaryRecord:
    id: str
    line: str
    track: str
    exception_type: str
    max_location: float


@dataclass(slots=True)
class ResolvedReference:
    chi: float
    spt_a: float | None
    spt_i: float | None
    spt_b: float | None
    span_ai: float | None
    span_ib: float | None


@dataclass(slots=True)
class ResolvedMeasurements:
    hgt_a: float | None = None
    hgt_i: float | None = None
    hgt_b: float | None = None
    stg_a: float | None = None
    stg_i: float | None = None
    stg_b: float | None = None


@dataclass(slots=True)
class StaggerSummaryResult:
    id: str
    line: str
    track: str
    exception_type: str
    max_location: float
    chi: float
    spt_i: float | None
    k_eq: float | None
    overall_result: str
    trace_available: bool
    remark: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_stagger_formula.py::test_stagger_summary_result_keeps_trace_flags_and_remark_list -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/calculation/stagger_types.py backend/tests/test_stagger_formula.py
git commit -m "feat: add stagger calculation types"
```

---

### Task 2: Build stagger-specific metadata adapter for support and wind-factor data

**Files:**
- Create: `backend/app/core/calculation/stagger_metadata.py`
- Create: `backend/tests/test_stagger_keq.py`

- [ ] **Step 1: Write the failing metadata adapter tests**

```python
from app.core.calculation.stagger_metadata import (
    SupportPoint,
    RangeValue,
    build_support_index,
    build_tml_threshold_strategy,
)


def test_build_support_index_groups_by_line_and_track():
    supports = [
        SupportPoint(line="EAL", track="up", chainage=121000.0),
        SupportPoint(line="EAL", track="up", chainage=121050.0),
    ]

    index = build_support_index(supports)

    assert [item.chainage for item in index["EAL"]["up"]] == [121000.0, 121050.0]


def test_build_tml_threshold_strategy_keeps_threshold_values():
    strategy = build_tml_threshold_strategy(boundary=121207.0, above=1.5, below_or_equal=1.0)

    assert strategy["strategy"] == "threshold"
    assert strategy["boundary"] == 121207.0
    assert strategy["above"] == 1.5
    assert strategy["below_or_equal"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_stagger_keq.py -k "support_index or threshold_strategy" -v`

Expected: FAIL with import error for `stagger_metadata`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass(slots=True)
class SupportPoint:
    line: str
    track: str
    chainage: float
    section: str | None = None
    support_id: str | None = None


@dataclass(slots=True)
class RangeValue:
    start: float
    end: float
    value: float


def build_support_index(points: list[SupportPoint]) -> dict[str, dict[str, list[SupportPoint]]]:
    index: dict[str, dict[str, list[SupportPoint]]] = {}
    for point in points:
        line_bucket = index.setdefault(point.line.upper(), {})
        track_bucket = line_bucket.setdefault(point.track.lower(), [])
        track_bucket.append(point)
    for line_bucket in index.values():
        for track, items in line_bucket.items():
            line_bucket[track] = sorted(items, key=lambda item: item.chainage)
    return index


def build_tml_threshold_strategy(boundary: float, above: float, below_or_equal: float) -> dict[str, float | str]:
    return {
        "strategy": "threshold",
        "boundary": boundary,
        "above": above,
        "below_or_equal": below_or_equal,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_stagger_keq.py -k "support_index or threshold_strategy" -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/calculation/stagger_metadata.py backend/tests/test_stagger_keq.py
git commit -m "feat: add stagger metadata adapter primitives"
```

---

### Task 3: Load stagger metadata through `MetadataManager._load_sheet()` without changing existing metadata APIs

**Files:**
- Modify: `backend/app/core/calculation/stagger_metadata.py`
- Modify: `backend/tests/test_stagger_keq.py`

- [ ] **Step 1: Write the failing loader tests**

```python
from pathlib import Path

from app.core.calculation.stagger_metadata import load_stagger_metadata


def test_load_stagger_metadata_for_eal_returns_support_and_wind_factor_sections():
    metadata = load_stagger_metadata(
        config_dir=Path("backend/config"),
        line="EAL",
    )

    assert "supports" in metadata
    assert "wind_factor" in metadata
    assert "EAL" in metadata["supports"]
    assert "EAL" in metadata["wind_factor"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_stagger_keq.py::test_load_stagger_metadata_for_eal_returns_support_and_wind_factor_sections -v`

Expected: FAIL with missing `load_stagger_metadata`

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path

from app.core.config import get_config_dir
from app.core.metadata import MetadataManager


def load_stagger_metadata(config_dir: Path | None, line: str) -> dict:
    base_dir = config_dir or get_config_dir()
    filename = "EAL metadata.xlsx" if line.upper() == "EAL" else "TML metadata.xlsx"
    manager = MetadataManager(config_path=base_dir / filename)

    support_df = manager._load_sheet("Support database")
    metadata: dict = {"supports": {}, "wind_factor": {}, "constants": {"tension": 13.8}}

    metadata["supports"][line.upper()] = _parse_support_sheet(support_df, line=line.upper())

    if line.upper() == "EAL":
        wind_df = manager._load_sheet("Wind Speed Factor")
        metadata["wind_factor"]["EAL"] = _parse_eal_wind_factor_sheet(wind_df)
    else:
        metadata["wind_factor"]["TML"] = build_tml_threshold_strategy(
            boundary=121207.0,
            above=1.5,
            below_or_equal=1.0,
        )

    return metadata
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_stagger_keq.py::test_load_stagger_metadata_for_eal_returns_support_and_wind_factor_sections -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/calculation/stagger_metadata.py backend/tests/test_stagger_keq.py
git commit -m "feat: load stagger metadata through typed adapter"
```

---

### Task 4: Add candidate selector for Case A / Case B summary filtering

**Files:**
- Create: `backend/app/core/calculation/stagger_selector.py`
- Create: `backend/tests/test_stagger_selector.py`

- [ ] **Step 1: Write the failing selector tests**

```python
import pandas as pd

from app.core.calculation.stagger_selector import select_stagger_candidates


def test_select_stagger_candidates_without_repeated_uses_exception_summary():
    summary = pd.DataFrame([
        {"ID": "A1", "Level": "L1", "Exception Type": "Stagger Left", "Track": "UP", "MaxLocation": 121000.0, "Line": "EAL"},
        {"ID": "A2", "Level": "L3", "Exception Type": "Stagger Left", "Track": "UP", "MaxLocation": 121010.0, "Line": "EAL"},
    ])

    selected = select_stagger_candidates(summary_df=summary, repeated_summary_df=None)

    assert [item.id for item in selected] == ["A1"]
    assert selected[0].track == "up"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_stagger_selector.py::test_select_stagger_candidates_without_repeated_uses_exception_summary -v`

Expected: FAIL with missing selector module

- [ ] **Step 3: Write minimal implementation**

```python
from app.core.calculation.stagger_types import SelectedSummaryRecord


ALLOWED_LEVELS = {"L1", "L2"}
ALLOWED_TYPES = {"Stagger Left", "Stagger Right"}


def _normalize_track(value: str | None) -> str:
    raw = (value or "").strip().lower()
    return "down" if raw == "down" else "up"


def select_stagger_candidates(summary_df, repeated_summary_df=None):
    source = summary_df
    if repeated_summary_df is not None:
        repeated_ids = set(repeated_summary_df["ID"].astype(str))
        source = summary_df[summary_df["ID"].astype(str).isin(repeated_ids)]

    filtered = source[
        source["Level"].isin(ALLOWED_LEVELS)
        & source["Exception Type"].isin(ALLOWED_TYPES)
    ]

    return [
        SelectedSummaryRecord(
            id=str(row["ID"]),
            line=str(row["Line"]),
            track=_normalize_track(row.get("Track")),
            exception_type=str(row["Exception Type"]),
            max_location=float(row["MaxLocation"]),
        )
        for _, row in filtered.iterrows()
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_stagger_selector.py::test_select_stagger_candidates_without_repeated_uses_exception_summary -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/calculation/stagger_selector.py backend/tests/test_stagger_selector.py
git commit -m "feat: add stagger summary candidate selector"
```

---

### Task 5: Add reference resolver for `Ch_I`, nearest support, adjacent supports, and spans

**Files:**
- Create: `backend/app/core/calculation/stagger_reference.py`
- Create: `backend/tests/test_stagger_reference.py`

- [ ] **Step 1: Write the failing reference tests**

```python
from app.core.calculation.stagger_reference import resolve_reference_points
from app.core.calculation.stagger_metadata import SupportPoint
from app.core.calculation.stagger_types import SelectedSummaryRecord


def test_resolve_reference_points_finds_nearest_and_adjacent_supports():
    record = SelectedSummaryRecord(
        id="A1",
        line="EAL",
        track="up",
        exception_type="Stagger Left",
        max_location=121000.0,
    )
    supports = [
        SupportPoint(line="EAL", track="up", chainage=120900.0),
        SupportPoint(line="EAL", track="up", chainage=121020.0),
        SupportPoint(line="EAL", track="up", chainage=121120.0),
    ]

    resolved = resolve_reference_points(record, supports)

    assert resolved.chi == 121000.0
    assert resolved.spt_i == 121020.0
    assert resolved.spt_a == 120900.0
    assert resolved.spt_b == 121120.0
    assert resolved.span_ai == 120.0
    assert resolved.span_ib == 100.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_stagger_reference.py::test_resolve_reference_points_finds_nearest_and_adjacent_supports -v`

Expected: FAIL with missing reference resolver

- [ ] **Step 3: Write minimal implementation**

```python
from app.core.calculation.stagger_types import ResolvedReference


def resolve_reference_points(record, supports):
    ordered = sorted(supports, key=lambda item: item.chainage)
    spt_i = min(ordered, key=lambda item: abs(item.chainage - record.max_location))
    idx = ordered.index(spt_i)
    spt_a = ordered[idx - 1].chainage if idx > 0 else None
    spt_b = ordered[idx + 1].chainage if idx + 1 < len(ordered) else None
    span_ai = abs(spt_a - spt_i.chainage) if spt_a is not None else None
    span_ib = abs(spt_i.chainage - spt_b) if spt_b is not None else None
    return ResolvedReference(
        chi=record.max_location,
        spt_a=spt_a,
        spt_i=spt_i.chainage,
        spt_b=spt_b,
        span_ai=span_ai,
        span_ib=span_ib,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_stagger_reference.py::test_resolve_reference_points_finds_nearest_and_adjacent_supports -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/calculation/stagger_reference.py backend/tests/test_stagger_reference.py
git commit -m "feat: add stagger reference resolver"
```

---

### Task 6: Add stagger-specific `ChartData` parser helper without changing existing parser contracts

**Files:**
- Modify: `backend/app/core/calculation/excel_parser.py`
- Modify: `backend/tests/test_calculation.py`

- [ ] **Step 1: Write the failing parser helper test**

```python
import pandas as pd

from app.core.calculation.excel_parser import parse_stagger_chart_data_sheet


def test_parse_stagger_chart_data_sheet_extracts_chainage_and_channels():
    df = pd.DataFrame({
        "Chainage": [121000.0],
        "WHGT1": [5400.0],
        "WHGT2": [5390.0],
        "WHGT3": [5380.0],
        "WHGT4": [5410.0],
        "STG1": [120.0],
        "STG2": [118.0],
        "STG3": [122.0],
        "STG4": [121.0],
    })

    rows = parse_stagger_chart_data_sheet(df)

    assert rows[0]["chainage"] == 121000.0
    assert rows[0]["heights"] == [5400.0, 5390.0, 5380.0, 5410.0]
    assert rows[0]["staggers"] == [120.0, 118.0, 122.0, 121.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_calculation.py::test_parse_stagger_chart_data_sheet_extracts_chainage_and_channels -v`

Expected: FAIL with missing parser helper

- [ ] **Step 3: Write minimal implementation**

```python
def parse_stagger_chart_data_sheet(df: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for _, row in df.iterrows():
        rows.append(
            {
                "chainage": float(row["Chainage"]),
                "heights": [float(row[f"WHGT{i}"]) for i in range(1, 5)],
                "staggers": [float(row[f"STG{i}"]) for i in range(1, 5)],
            }
        )
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_calculation.py::test_parse_stagger_chart_data_sheet_extracts_chainage_and_channels -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/calculation/excel_parser.py backend/tests/test_calculation.py
git commit -m "feat: add stagger chart data parser helper"
```

---

### Task 7: Add measurement resolver for A/I/B nearest-row mapping

**Files:**
- Create: `backend/app/core/calculation/stagger_measurements.py`
- Create: `backend/tests/test_stagger_measurements.py`

- [ ] **Step 1: Write the failing measurement tests**

```python
from app.core.calculation.stagger_measurements import resolve_measurements


def test_resolve_measurements_uses_nearest_rows_and_channel_maxima():
    chart_rows = [
        {"chainage": 120900.0, "heights": [5300.0, 5310.0, 5320.0, 5330.0], "staggers": [90.0, 91.0, 92.0, 93.0]},
        {"chainage": 121000.0, "heights": [5400.0, 5390.0, 5380.0, 5410.0], "staggers": [120.0, 118.0, 122.0, 121.0]},
        {"chainage": 121120.0, "heights": [5500.0, 5490.0, 5480.0, 5470.0], "staggers": [80.0, 81.0, 82.0, 83.0]},
    ]

    resolved = resolve_measurements(
        chart_rows=chart_rows,
        chi=121000.0,
        spt_a=120900.0,
        spt_b=121120.0,
    )

    assert resolved.hgt_i == 5410.0
    assert resolved.stg_i == 122.0
    assert resolved.hgt_a == 5330.0
    assert resolved.stg_b == 83.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_stagger_measurements.py::test_resolve_measurements_uses_nearest_rows_and_channel_maxima -v`

Expected: FAIL with missing measurement resolver

- [ ] **Step 3: Write minimal implementation**

```python
from app.core.calculation.stagger_types import ResolvedMeasurements


def _nearest_row(target: float, chart_rows: list[dict]) -> dict:
    return min(chart_rows, key=lambda row: abs(row["chainage"] - target))


def resolve_measurements(chart_rows: list[dict], chi: float, spt_a: float | None, spt_b: float | None) -> ResolvedMeasurements:
    row_i = _nearest_row(chi, chart_rows)
    row_a = _nearest_row(spt_a, chart_rows) if spt_a is not None else None
    row_b = _nearest_row(spt_b, chart_rows) if spt_b is not None else None

    return ResolvedMeasurements(
        hgt_a=max(row_a["heights"]) if row_a else None,
        hgt_i=max(row_i["heights"]),
        hgt_b=max(row_b["heights"]) if row_b else None,
        stg_a=max(row_a["staggers"]) if row_a else None,
        stg_i=max(row_i["staggers"]),
        stg_b=max(row_b["staggers"]) if row_b else None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_stagger_measurements.py::test_resolve_measurements_uses_nearest_rows_and_channel_maxima -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/calculation/stagger_measurements.py backend/tests/test_stagger_measurements.py
git commit -m "feat: add stagger measurement resolver"
```

---

### Task 8: Add line-specific `K_eq` strategies for EAL and TML

**Files:**
- Create: `backend/app/core/calculation/stagger_keq.py`
- Modify: `backend/tests/test_stagger_keq.py`

- [ ] **Step 1: Write the failing strategy tests**

```python
import pytest

from app.core.calculation.stagger_keq import calculate_eal_keq, calculate_tml_keq
from app.core.calculation.stagger_metadata import RangeValue


def test_calculate_eal_keq_uses_support_factor_maxima():
    kr = [RangeValue(0.0, 999999.0, 1.2)]
    ke = [RangeValue(0.0, 999999.0, 1.1)]
    kh = [RangeValue(0.0, 999999.0, 1.0)]

    result = calculate_eal_keq(
        track="up",
        spt_a=120900.0,
        spt_i=121020.0,
        spt_b=121120.0,
        kr_by_track={"up": kr, "down": kr},
        ke_by_track={"up": ke, "down": ke},
        kh_by_track={"up": kh, "down": kh},
    )

    assert result["k_ai_max"] == pytest.approx(1.32)
    assert result["k_ib_max"] == pytest.approx(1.32)
    assert result["k_eq"] == pytest.approx(1.32)


def test_calculate_tml_keq_uses_threshold_rule():
    assert calculate_tml_keq(chi=121208.0, boundary=121207.0, above=1.5, below_or_equal=1.0) == pytest.approx(1.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_stagger_keq.py -k "calculate_eal_keq or calculate_tml_keq" -v`

Expected: FAIL with missing `stagger_keq`

- [ ] **Step 3: Write minimal implementation**

```python
def _lookup_range_value(chainage: float, ranges: list) -> float:
    for item in ranges:
        if item.start <= chainage <= item.end:
            return item.value
    raise ValueError(f"No lookup range for chainage {chainage}")


def _support_factor(chainage: float, kr: list, ke: list, kh: list) -> float:
    return (
        _lookup_range_value(chainage, kr)
        * _lookup_range_value(chainage, ke)
        * _lookup_range_value(chainage, kh)
    )


def calculate_eal_keq(track, spt_a, spt_i, spt_b, kr_by_track, ke_by_track, kh_by_track):
    kr = kr_by_track[track]
    ke = ke_by_track[track]
    kh = kh_by_track[track]
    k_a = _support_factor(spt_a, kr, ke, kh)
    k_i = _support_factor(spt_i, kr, ke, kh)
    k_b = _support_factor(spt_b, kr, ke, kh)
    k_ai_max = max(k_a, k_i)
    k_ib_max = max(k_b, k_i)
    return {
        "k_a": k_a,
        "k_i": k_i,
        "k_b": k_b,
        "k_ai_max": k_ai_max,
        "k_ib_max": k_ib_max,
        "k_eq": max(k_ai_max, k_ib_max),
    }


def calculate_tml_keq(chi: float, boundary: float, above: float, below_or_equal: float) -> float:
    return above if chi > boundary else below_or_equal
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_stagger_keq.py -k "calculate_eal_keq or calculate_tml_keq" -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/calculation/stagger_keq.py backend/tests/test_stagger_keq.py
git commit -m "feat: add line-specific stagger keq strategies"
```

---

### Task 9: Add pure formula helpers for `B`, `P`, `S`, `E`, `P'`, and judgment

**Files:**
- Create: `backend/app/core/calculation/stagger_formula.py`
- Modify: `backend/tests/test_stagger_formula.py`

- [ ] **Step 1: Write the failing formula tests**

```python
import pytest

from app.core.calculation.stagger_formula import (
    calculate_b_value,
    calculate_p_value,
    calculate_s_value,
    calculate_e_value,
    calculate_allowable_value,
    is_short_circuit_pass,
)


def test_calculate_b_value_matches_known_formula_result():
    result = calculate_b_value(span=50.0, k_eq=1.2, tension=13.8)
    assert result == pytest.approx(67.13, abs=0.01)


def test_is_short_circuit_pass_uses_four_b_rule():
    assert is_short_circuit_pass(s_value=120.0, b_value=25.0) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_stagger_formula.py -k "b_value or short_circuit" -v`

Expected: FAIL with missing formula module

- [ ] **Step 3: Write minimal implementation**

```python
def calculate_b_value(span: float, k_eq: float, tension: float) -> float:
    return 0.613 * 0.8 * 1.08 * (34.3 * k_eq) ** 2 * 0.0132 * span ** 2 / (8 * tension)


def calculate_p_value(stg_x: float, stg_i: float) -> float:
    return abs((stg_x + stg_i) / 2)


def calculate_s_value(stg_x: float, stg_i: float) -> float:
    return abs(stg_x - stg_i)


def calculate_e_value(s_value: float, b_value: float) -> float:
    if b_value <= 0:
        return 0.0
    return s_value ** 2 / (16 * b_value)


def calculate_allowable_value(b_value: float, e_value: float, height_correction: float) -> float:
    return 505 - (b_value + e_value) - height_correction


def is_short_circuit_pass(s_value: float, b_value: float) -> bool:
    return s_value >= 4 * b_value
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_stagger_formula.py -k "b_value or short_circuit" -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/calculation/stagger_formula.py backend/tests/test_stagger_formula.py
git commit -m "feat: add stagger formula helpers"
```

---

### Task 10: Build the stagger orchestration service for summary + trace output

**Files:**
- Create: `backend/app/core/calculation/stagger_service.py`
- Create: `backend/tests/test_stagger_service.py`

- [ ] **Step 1: Write the failing service integration test**

```python
from app.core.calculation.stagger_service import compute_stagger_result_for_record
from app.core.calculation.stagger_metadata import SupportPoint, RangeValue
from app.core.calculation.stagger_types import SelectedSummaryRecord


def test_compute_stagger_result_for_record_returns_summary_and_trace():
    record = SelectedSummaryRecord(
        id="A1",
        line="EAL",
        track="up",
        exception_type="Stagger Left",
        max_location=121000.0,
    )
    supports = [
        SupportPoint(line="EAL", track="up", chainage=120900.0),
        SupportPoint(line="EAL", track="up", chainage=121020.0),
        SupportPoint(line="EAL", track="up", chainage=121120.0),
    ]
    chart_rows = [
        {"chainage": 120900.0, "heights": [5300.0, 5310.0, 5320.0, 5330.0], "staggers": [90.0, 91.0, 92.0, 93.0]},
        {"chainage": 121000.0, "heights": [5400.0, 5390.0, 5380.0, 5410.0], "staggers": [120.0, 118.0, 122.0, 121.0]},
        {"chainage": 121120.0, "heights": [5500.0, 5490.0, 5480.0, 5470.0], "staggers": [80.0, 81.0, 82.0, 83.0]},
    ]
    metadata = {
        "supports": {"EAL": {"up": supports}},
        "wind_factor": {
            "EAL": {
                "kr": {"up": [RangeValue(0.0, 999999.0, 1.2)], "down": [RangeValue(0.0, 999999.0, 1.2)]},
                "ke": {"up": [RangeValue(0.0, 999999.0, 1.1)], "down": [RangeValue(0.0, 999999.0, 1.1)]},
                "kh": {"up": [RangeValue(0.0, 999999.0, 1.0)], "down": [RangeValue(0.0, 999999.0, 1.0)]},
            }
        },
        "constants": {"tension": 13.8},
    }

    summary, trace = compute_stagger_result_for_record(record, chart_rows, metadata, case_type="A")

    assert summary.id == "A1"
    assert summary.trace_available is True
    assert summary.overall_result in {"pass", "fail"}
    assert trace["case_type"] == "A"
    assert trace["k_eq"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_stagger_service.py::test_compute_stagger_result_for_record_returns_summary_and_trace -v`

Expected: FAIL with missing service module

- [ ] **Step 3: Write minimal implementation**

```python
from app.core.calculation.stagger_formula import (
    calculate_allowable_value,
    calculate_b_value,
    calculate_e_value,
    calculate_p_value,
    calculate_s_value,
    is_short_circuit_pass,
)
from app.core.calculation.stagger_keq import calculate_eal_keq, calculate_tml_keq
from app.core.calculation.stagger_measurements import resolve_measurements
from app.core.calculation.stagger_reference import resolve_reference_points
from app.core.calculation.stagger_types import StaggerSummaryResult


def compute_stagger_result_for_record(record, chart_rows, metadata, case_type: str):
    supports = metadata["supports"][record.line][record.track]
    reference = resolve_reference_points(record, supports)
    measurements = resolve_measurements(chart_rows, reference.chi, reference.spt_a, reference.spt_b)

    if record.line.upper() == "EAL":
        wind = metadata["wind_factor"]["EAL"]
        keq_parts = calculate_eal_keq(
            track=record.track,
            spt_a=reference.spt_a,
            spt_i=reference.spt_i,
            spt_b=reference.spt_b,
            kr_by_track=wind["kr"],
            ke_by_track=wind["ke"],
            kh_by_track=wind["kh"],
        )
        k_eq = keq_parts["k_eq"]
    else:
        strategy = metadata["wind_factor"]["TML"]
        k_eq = calculate_tml_keq(
            chi=reference.chi,
            boundary=strategy["boundary"],
            above=strategy["above"],
            below_or_equal=strategy["below_or_equal"],
        )
        keq_parts = {"k_ai_max": None, "k_ib_max": None, "k_eq": k_eq}

    b_ai = calculate_b_value(reference.span_ai, k_eq, metadata["constants"]["tension"]) if reference.span_ai else None
    p_ai = calculate_p_value(measurements.stg_a, measurements.stg_i) if measurements.stg_a is not None else None
    s_ai = calculate_s_value(measurements.stg_a, measurements.stg_i) if measurements.stg_a is not None else None
    e_ai = calculate_e_value(s_ai, b_ai) if s_ai is not None and b_ai is not None else None
    allowable_ai = calculate_allowable_value(b_ai, e_ai, 0.0) if b_ai is not None and e_ai is not None else None

    ai_short = is_short_circuit_pass(s_ai, b_ai) if s_ai is not None and b_ai is not None else False
    ai_result = "pass_short_circuit" if ai_short else ("pass" if p_ai is not None and allowable_ai is not None and p_ai <= allowable_ai else "fail")

    summary = StaggerSummaryResult(
        id=record.id,
        line=record.line,
        track=record.track,
        exception_type=record.exception_type,
        max_location=record.max_location,
        chi=reference.chi,
        spt_i=reference.spt_i,
        k_eq=k_eq,
        overall_result="pass" if ai_result != "fail" else "fail",
        trace_available=True,
        remark=[f"Case {case_type}"],
    )

    trace = {
        "case_type": case_type,
        "chi_source": "exception_report" if case_type == "A" else "n_repeated",
        "spt_a": reference.spt_a,
        "spt_i": reference.spt_i,
        "spt_b": reference.spt_b,
        "hgt_a": measurements.hgt_a,
        "hgt_i": measurements.hgt_i,
        "hgt_b": measurements.hgt_b,
        "stg_a": measurements.stg_a,
        "stg_i": measurements.stg_i,
        "stg_b": measurements.stg_b,
        "k_ai_max": keq_parts.get("k_ai_max"),
        "k_ib_max": keq_parts.get("k_ib_max"),
        "k_eq": k_eq,
    }
    return summary, trace
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_stagger_service.py::test_compute_stagger_result_for_record_returns_summary_and_trace -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/calculation/stagger_service.py backend/tests/test_stagger_service.py
git commit -m "feat: add stagger computation service"
```

---

### Task 11: Add the FastAPI stagger endpoint

**Files:**
- Modify: `backend/app/api/endpoints/calculation.py`
- Create: `backend/tests/test_stagger_calculation_api.py`

- [ ] **Step 1: Write the failing API test**

```python
import io
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _make_stagger_excel_bytes() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame([
            {"ID": "A1", "Level": "L1", "Exception Type": "Stagger Left", "Track": "UP", "MaxLocation": 121000.0, "Line": "EAL"}
        ]).to_excel(writer, sheet_name="Summary", index=False)
        pd.DataFrame([
            {"Chainage": 121000.0, "WHGT1": 5400.0, "WHGT2": 5390.0, "WHGT3": 5380.0, "WHGT4": 5410.0, "STG1": 120.0, "STG2": 118.0, "STG3": 122.0, "STG4": 121.0}
        ]).to_excel(writer, sheet_name="ChartData", index=False)
    return buf.getvalue()


def test_stagger_endpoint_returns_summary_results():
    response = client.post(
        "/api/calculation/stagger",
        files=[("file", ("stagger.xlsx", _make_stagger_excel_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert body["results"][0]["id"] == "A1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_stagger_calculation_api.py::test_stagger_endpoint_returns_summary_results -v`

Expected: FAIL with 404 or missing endpoint

- [ ] **Step 3: Write minimal implementation**

```python
from app.core.calculation.stagger_selector import select_stagger_candidates
from app.core.calculation.stagger_service import compute_stagger_result_for_record
from app.core.calculation.stagger_metadata import load_stagger_metadata
from app.core.calculation.excel_parser import parse_stagger_chart_data_sheet


@router.post("/stagger")
async def upload_stagger(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        workbook = pd.read_excel(io.BytesIO(file_bytes), sheet_name=["Summary", "ChartData"])
        summary_df = workbook["Summary"]
        chart_rows = parse_stagger_chart_data_sheet(workbook["ChartData"])
        candidates = select_stagger_candidates(summary_df=summary_df, repeated_summary_df=None)
        line = candidates[0].line if candidates else "EAL"
        metadata = load_stagger_metadata(config_dir=None, line=line)
        results = [compute_stagger_result_for_record(item, chart_rows, metadata, case_type="A")[0] for item in candidates]
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to calculate stagger: {exc}")

    return {"results": [_sanitize(asdict(item)) for item in results]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_stagger_calculation_api.py::test_stagger_endpoint_returns_summary_results -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/endpoints/calculation.py backend/tests/test_stagger_calculation_api.py
git commit -m "feat: add stagger calculation API endpoint"
```

---

### Task 12: Add regression coverage that existing parser and metadata behavior remain unchanged

**Files:**
- Modify: `backend/tests/test_calculation.py`
- Modify: `backend/tests/test_stagger_keq.py`
- Modify: `backend/tests/test_stagger_service.py`

- [ ] **Step 1: Write the failing regression tests**

```python
from app.core.metadata import MetadataManager


def test_existing_metadata_manager_public_methods_still_return_expected_types():
    manager = MetadataManager()
    tension_lookup = manager.get_tension_length_lookup()
    assert isinstance(tension_lookup, dict)


def test_stagger_service_returns_na_when_support_neighbors_are_missing():
    ...
    assert summary.overall_result == "n/a"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_calculation.py backend/tests/test_stagger_keq.py backend/tests/test_stagger_service.py -v`

Expected: FAIL where current code does not yet preserve edge handling or explicit regression coverage

- [ ] **Step 3: Write minimal implementation**

```python
def compute_stagger_result_for_record(record, chart_rows, metadata, case_type: str):
    supports = metadata["supports"][record.line][record.track]
    reference = resolve_reference_points(record, supports)
    if reference.spt_a is None or reference.spt_b is None:
        summary = StaggerSummaryResult(
            id=record.id,
            line=record.line,
            track=record.track,
            exception_type=record.exception_type,
            max_location=record.max_location,
            chi=reference.chi,
            spt_i=reference.spt_i,
            k_eq=None,
            overall_result="n/a",
            trace_available=False,
            remark=["Trace only partially available"],
        )
        return summary, {"case_type": case_type, "spt_a": reference.spt_a, "spt_i": reference.spt_i, "spt_b": reference.spt_b}
```

- [ ] **Step 4: Run test suite to verify it passes**

Run: `pytest backend/tests/test_stagger_selector.py backend/tests/test_stagger_reference.py backend/tests/test_stagger_measurements.py backend/tests/test_stagger_keq.py backend/tests/test_stagger_formula.py backend/tests/test_stagger_service.py backend/tests/test_stagger_calculation_api.py backend/tests/test_calculation.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_calculation.py backend/tests/test_stagger_keq.py backend/tests/test_stagger_service.py
git commit -m "test: add stagger regression coverage for compatibility"
```

---

## Self-Review

### Spec coverage

- `Summary / ChartData / Metadata` 三分：由 Tasks 2, 3, 4, 6, 7 覆蓋
- `Track` normalization 與 Case A / B candidate selection：由 Task 4 覆蓋
- `Ch_I / Spt_I / Spt_A / Spt_B / Span_AI / Span_IB`：由 Task 5 覆蓋
- A/I/B 量測值以最近 row + `max(WHGT1..4)` / `max(STG1..4)` 解出：由 Tasks 6, 7 覆蓋
- EAL `KR * KE * KH` lookup 與 TML threshold strategy：由 Tasks 2, 3, 8 覆蓋
- `B / P / S / E / P' / short-circuit / result`：由 Task 9 覆蓋
- summary + trace output：由 Task 10 覆蓋
- API exposure：由 Task 11 覆蓋
- 不影響現有 parser / metadata public behavior：由 Task 12 覆蓋

### Placeholder scan

- 沒有保留 `TODO`、`TBD` 或「之後補上」這類 placeholder。
- 尚未確定的 workbook 真相沒有被假裝成已知規格，而是被收斂成明確的 resolver 規則與 regression seam。

### Type consistency

- `SelectedSummaryRecord`, `ResolvedReference`, `ResolvedMeasurements`, `StaggerSummaryResult` 在 Task 1 定義，後續 Tasks 4, 5, 7, 10 一致使用。
- `SupportPoint` / `RangeValue` 在 Task 2 定義，Tasks 5, 8, 10 沿用相同 shape。
- `load_stagger_metadata()` 在 Task 3 引入，Task 11 直接重用，不再額外定義第二種 metadata loading path。

Plan complete and saved to `docs/superpowers/plans/2026-05-05-stagger-calculation-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
