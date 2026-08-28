# Calculation Module — Gap Analysis & Development Plan

## 1. Gap Analysis

### 1.1 wear_calculator.py — Current vs Expected

| Item | Current | Expected |
|------|---------|----------|
| Data source | External `lookup_table` DataFrame passed in | Read directly from `ChartData` sheet of uploaded Excel |
| Key metric | `mean_remaining` from wear1..wear4 columns | `wear_min` column from ChartData, grouped by `Tension Length` |
| Wear % formula | Circular cross-section geometry (legacy) | Still useful as reference, but NOT the primary output |
| Primary output | `mean_remaining`, `wear_percentage` | **avg `wear_min` per Tension Length** (SD, wear% are secondary) |
| TL boundary | Derived from external lookup_table (from_m/to_m) | Derived from `Tension Length` column in ChartData directly |
| Date | Not tracked | `task_run_date` from ChartData |

### 1.2 trend_analyzer.py — Current vs Expected

| Item | Current | Expected |
|------|---------|----------|
| Time axis | `DEFAULT_DAYS_PER_PERIOD = 30` (fixed integer days) | Actual `task_run_date` from each uploaded Excel file |
| Trend projection | Fixed 30-day intervals | Projected to next actual inspection date (line-specific cycle) |
| Input | Generic DataFrame | `Wire Wear` sheet from uploaded Excel |
| Exception date | Not captured | `Run Date` field from Wire Wear sheet |

### 1.3 API Layer — Current vs Expected

| Item | Current | Expected |
|------|---------|----------|
| Upload endpoint | Not implemented for Excel ingestion | POST `/api/calculation/upload` accepting Exception Report Excel |
| Wear result endpoint | Not implemented | GET `/api/calculation/wear/{line}/{track}` |
| Trend result endpoint | Not implemented | GET `/api/calculation/trend/{line}/{track}` |
| Multi-file trend | Not supported | Accept multiple Excels to build trend over time |

### 1.4 Frontend — Current vs Expected

| Item | Current | Expected |
|------|---------|----------|
| Calculation UI | None | New `CalculationView` with file upload + results display |
| Wear table | None | Table: TL / avg wear_min / SD / wear% / track_type |
| Trend chart | None | Line chart: date (x) vs avg wear_min (y) per TL |

---

## 2. Algorithm Design

### 2.1 Average Wear Calculation (Revised)

```
Input:  ChartData sheet from Exception Report Excel
        Columns used: task_run_date, Tension Length, Chainage, wear_min

Algorithm:
  1. Read ChartData sheet
  2. Drop rows where wear_min is NaN
  3. Group by Tension Length
  4. For each group:
     a. avg_wear_min = mean(wear_min)
     b. sd            = std(wear_min, ddof=1)
     c. wear_pct      = calculate_wear_percentage(avg_wear_min)  [reference only]
     d. chainage_min  = min(Chainage)
     e. chainage_max  = max(Chainage)
     f. track_type    = mode(Track Type)
     g. overlap       = mode(Overlap)
  5. Return list of WearResult per TL

Output: WearResult(
    tension_length, from_m, to_m,
    avg_wear_min,       ← PRIMARY
    sd,
    wear_percentage,    ← REFERENCE
    track_type, overlap,
    task_run_date
)
```

### 2.2 L2 Trend Analysis (Revised)

```
Input:  List of Exception Report Excels (multiple dates)
        Wire Wear sheet: Run Date, Tension Length, MaxValue, Level
        ChartData sheet: task_run_date, Tension Length, wear_min

Algorithm:
  1. For each uploaded Excel:
     a. Read task_run_date from ChartData (or Run Date from Wire Wear)
     b. Compute avg_wear_min per TL (from step 2.1)
     c. Store as (date, TL, avg_wear_min) record point

  2. For each TL with >= 2 record points:
     a. Convert dates to ordinal integers for regression
     b. Linear regression: slope, intercept = polyfit(dates, avg_wear_min)
     c. Project next N dates using line cycle:
        - EAL: +30 days
        - LMC/TML: +90 days
     d. Apply L2 logic:
        logic_1: trend_point_1 <= L2_THRESHOLD (10.2)
        logic_2: |max_value - trend_point_1| > TOLERANCE (0.2)

Output: TrendResult(
    exception_id, tension_length,
    record_points,   ← (date, avg_wear_min) tuples
    trend_points,    ← projected (date, value) tuples
    logic_1, logic_2, recommendation
)
```

---

## 3. Architecture

```
frontend/src/
  views/
    CalculationView.tsx          ← new main view
  components/
    Calculation/
      FileUploadPanel.tsx        ← drag-drop multi-file upload
      WearResultTable.tsx        ← avg wear_min per TL
      TrendChart.tsx             ← recharts line chart
      TrendResultTable.tsx       ← logic_1/2 + recommendation

backend/app/
  api/endpoints/
    calculation.py               ← extend with upload + result routes
  core/calculation/
    excel_parser.py              ← NEW: parse Wire Wear + ChartData sheets
    wear_calculator.py           ← REVISE: use wear_min from ChartData
    trend_analyzer.py            ← REVISE: use task_run_date
    __init__.py
  tests/
    test_excel_parser.py         ← NEW
    test_wear_calculator.py      ← UPDATE
    test_trend_analyzer.py       ← UPDATE
```

---

## 4. Data Flow

```
User uploads Excel(s)
        │
        ▼
POST /api/calculation/upload
        │
        ▼
excel_parser.py
  ├── parse_wire_wear_sheet()  → WireWearRecord[]
  └── parse_chart_data_sheet() → ChartDataRecord[]
        │
        ▼
wear_calculator.py
  └── calculate_average_wear(chart_data) → WearResult[]
        │
        ▼
trend_analyzer.py
  └── analyze_trend(wear_results_by_date) → TrendResult[]
        │
        ▼
JSON response → Frontend
  ├── WearResultTable (avg wear_min per TL)
  └── TrendChart (date vs avg wear_min)
```

---

## 5. API Specification

### POST `/api/calculation/upload`
- Body: `multipart/form-data`, field `files[]` (one or more Excel files)
- Response:
```json
{
  "wear_results": [
    {
      "task_run_date": "20251128",
      "line": "TML", "track": "DN",
      "tension_length": "6",
      "from_m": 109060.0, "to_m": 110177.75,
      "avg_wear_min": 12.826,
      "sd": 0.080,
      "wear_percentage": 4.21,
      "track_type": "Tangent",
      "overlap": null
    }
  ],
  "trend_results": [
    {
      "exception_id": "20251128_TML_DN_W0",
      "tension_length": "6",
      "record_points": [["20251128", 12.826]],
      "trend_points": [["20260227", 12.71]],
      "logic_1": true,
      "logic_2": false,
      "recommendation": "confirmed valid L2"
    }
  ]
}
```

### GET `/api/calculation/health`
- Response: `{"status": "ok"}`

---

## 6. Field Mapping

### ChartData → WearResult

| ChartData field | WearResult field | Notes |
|----------------|-----------------|-------|
| task_run_date | task_run_date | Date of inspection |
| Tension Length | tension_length | Group key |
| Chainage (min) | from_m | |
| Chainage (max) | to_m | |
| wear_min (mean) | avg_wear_min | **Primary metric** |
| wear_min (std) | sd | Reference |
| Track Type (mode) | track_type | |
| Overlap (mode) | overlap | |

### Wire Wear → TrendResult

| Wire Wear field | TrendResult field | Notes |
|----------------|-----------------|-------|
| ID | exception_id | |
| Run Date | task_run_date | Used as x-axis for trend |
| Tension Length | tension_length | |
| MaxValue | max_value | Point wear value |
| Level | level | L1 / L2 filter |
| FromM | from_m | |
| ToM | to_m | |

---

## 7. Component Tree

```
CalculationView
├── FileUploadPanel
│   ├── DropZone (drag-drop)
│   ├── FileList (uploaded files with dates)
│   └── AnalyzeButton
├── ResultTabs
│   ├── Tab: "Average Wear"
│   │   └── WearResultTable
│   │       columns: TL | avg_wear_min | SD | wear% | track_type | overlap
│   └── Tab: "L2 Trend"
│       ├── TrendChart
│       │   └── LineChart (x: date, y: avg_wear_min, per TL)
│       └── TrendResultTable
│           columns: exception_id | TL | record_pts | trend_pts | logic_1 | logic_2 | recommendation
└── ExportButton (CSV/Excel)
```
