# Calculation Module — Frontend Design Proposal

## 1. Navigation

Add "Calculation" to the existing sidebar in `MainLayout.tsx`:

```
Sidebar
├── Exception Generator   (existing)
├── Database Record       (existing)
├── Metadata Editor       (existing)
├── History Compare       (existing)
├── Calculation           ← NEW
└── About                 (existing)
```

Route: `/calculation`

---

## 2. Page Layout — CalculationView

```
┌─────────────────────────────────────────────────────────────┐
│  Calculation Module                                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │  FileUploadPanel                                     │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │  Drag & drop Exception Report Excel files     │  │    │
│  │  │  (or click to browse)                         │  │    │
│  │  │  Supports multiple files for trend analysis   │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  │                                                      │    │
│  │  Uploaded files:                                     │    │
│  │  ✓ 20251128_TML_D3_MEF-HUH_Exception_Report.xlsx    │    │
│  │    Line: TML  Track: DN  Date: 2025-11-28  [✕]      │    │
│  │                                                      │    │
│  │  [ Analyze ]                                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  [ Average Wear ]  [ L2 Trend ]                      │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │  (tab content — see sections 3 & 4)                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Tab 1 — Average Wear

### WearResultTable

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Date: 2025-11-28   Line: TML   Track: DN          [ Export CSV ]            │
├────────────────┬──────────────┬───────┬──────────┬────────────┬──────────────┤
│ Tension Length │ Avg wear_min │  SD   │ Wear %   │ Track Type │   Overlap    │
├────────────────┼──────────────┼───────┼──────────┼────────────┼──────────────┤
│ 2              │ 12.906       │ 0.082 │ 2.1%     │ Tangent    │ —            │
│ 4              │ 12.768       │ 0.172 │ 3.4%     │ Tangent    │ —            │
│ 6              │ 12.826       │ 0.080 │ 2.8%     │ Tangent    │ —            │
│ 8              │ 12.620       │ 0.107 │ 4.9%     │ Curve      │ —            │
│ K16            │ 12.927       │ 0.089 │ 1.9%     │ Tangent    │ —            │
│ ...            │ ...          │ ...   │ ...      │ ...        │ ...          │
└────────────────┴──────────────┴───────┴──────────┴────────────┴──────────────┘
```

- Rows sorted by Tension Length (numeric first, then alphanumeric)
- Wear % column: color-coded
  - Green: < 5%
  - Amber: 5–10%
  - Red: > 10%
- avg_wear_min is the primary column (bold)

---

## 4. Tab 2 — L2 Trend

### 4.1 TrendChart

```
  avg_wear_min (mm)
  13.0 │                    ●
  12.8 │         ●                    ○ ─ ─ ─ ○
  12.6 │  ●                    ○ ─ ─
  12.4 │
  12.2 │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  L2 threshold (10.2)
       └──────────────────────────────────────────────────
         2025-08   2025-11   2026-02   2026-05

  ● Actual data point    ○ Projected point    --- Trend line
  Legend: [TL 4] [TL 6] [TL K16] ...  (toggle per TL)
```

- X-axis: actual `task_run_date` from uploaded files + projected dates
- Y-axis: avg_wear_min (mm)
- Horizontal dashed line at L2 threshold = 10.2 mm
- Each TL is a separate line (toggle visibility via legend)
- Projected points shown as dashed/hollow markers

### 4.2 TrendResultTable

```
┌──────────────────────┬────────┬──────────────┬──────────────┬─────────┬─────────┬──────────────────────┐
│ Exception ID         │   TL   │ Record Points│ Trend Points │ Logic 1 │ Logic 2 │ Recommendation       │
├──────────────────────┼────────┼──────────────┼──────────────┼─────────┼─────────┼──────────────────────┤
│ 20251128_TML_DN_W0   │ 6      │ 12.83        │ 12.71        │ ✓       │ ✗       │ confirmed valid L2   │
│ 20251128_TML_DN_W1   │ 04,06  │ 12.82        │ 12.68        │ ✓       │ ✓       │ verify on site       │
│ 20251128_TML_DN_W5   │ K16    │ 12.93        │ 12.80        │ ✓       │ ✗       │ confirmed valid L2   │
└──────────────────────┴────────┴──────────────┴──────────────┴─────────┴─────────┴──────────────────────┘
```

- Recommendation column color-coded:
  - Green: "confirmed valid L2"
  - Amber: "verify on site"
  - Grey: "no action required"
- Only L2 Wire Wear exceptions shown (L1 filtered out)

---

## 5. Component Tree

```
CalculationView.tsx
├── FileUploadPanel.tsx
│   ├── <DropZone> (MUI or react-dropzone)
│   ├── FileChip[] (filename, date, line, track, remove button)
│   └── <Button> Analyze
├── <Tabs>
│   ├── Tab "Average Wear"
│   │   └── WearResultTable.tsx
│   │       └── <DataGrid> (MUI X)
│   └── Tab "L2 Trend"
│       ├── TrendChart.tsx
│       │   └── <LineChart> (Recharts)
│       └── TrendResultTable.tsx
│           └── <DataGrid> (MUI X)
└── <Button> Export CSV
```

---

## 6. State Management

New Zustand store: `useCalculationStore.ts`

```typescript
interface CalculationStore {
  uploadedFiles: File[]
  isLoading: boolean
  error: string | null
  wearResults: WearResult[]
  trendResults: TrendResult[]

  addFile: (file: File) => void
  removeFile: (index: number) => void
  analyze: () => Promise<void>
  reset: () => void
}
```

---

## 7. API Client

Add to `frontend/src/api/client.ts`:

```typescript
// POST /api/calculation/upload
uploadCalculationFiles(files: File[]): Promise<CalculationResponse>
```

Types in `frontend/src/types/api.ts`:

```typescript
interface WearResult {
  task_run_date: string
  line: string
  track: string
  tension_length: string
  from_m: number
  to_m: number
  avg_wear_min: number       // PRIMARY
  sd: number
  wear_percentage: number    // reference
  track_type: string
  overlap: string | null
}

interface TrendResult {
  exception_id: string
  tension_length: string
  record_points: [string, number][]   // [date, avg_wear_min]
  trend_points: [string, number][]    // [projected_date, value]
  logic_1: boolean
  logic_2: boolean
  recommendation: 'confirmed valid L2' | 'verify on site' | 'no action required'
}

interface CalculationResponse {
  wear_results: WearResult[]
  trend_results: TrendResult[]
}
```

---

## 8. Files to Create / Modify

| Action | File |
|--------|------|
| CREATE | `frontend/src/views/CalculationView.tsx` |
| CREATE | `frontend/src/components/Calculation/FileUploadPanel.tsx` |
| CREATE | `frontend/src/components/Calculation/WearResultTable.tsx` |
| CREATE | `frontend/src/components/Calculation/TrendChart.tsx` |
| CREATE | `frontend/src/components/Calculation/TrendResultTable.tsx` |
| CREATE | `frontend/src/store/useCalculationStore.ts` |
| MODIFY | `frontend/src/App.tsx` — add `/calculation` route |
| MODIFY | `frontend/src/components/Layout/MainLayout.tsx` — add nav item |
| MODIFY | `frontend/src/api/client.ts` — add upload function |
| MODIFY | `frontend/src/types/api.ts` — add new types |
| CREATE | `backend/app/core/calculation/excel_parser.py` |
| MODIFY | `backend/app/core/calculation/wear_calculator.py` |
| MODIFY | `backend/app/core/calculation/trend_analyzer.py` |
| MODIFY | `backend/app/api/endpoints/calculation.py` — add upload route |
