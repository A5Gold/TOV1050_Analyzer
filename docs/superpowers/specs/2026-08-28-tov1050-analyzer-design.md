# TOV1050 Analyzer 設計與資料契約

日期：2026-08-28  
狀態：已由使用者逐節批准，尚未進入 production implementation  
範圍：TOV1050 CSV 上傳、清洗/預處理、TOV640 exception algorithm 語意、報表與圖表

## 1. 目標與限制

建立獨立 Windows desktop analyzer：

```text
C:\Smart Maintanence\TOV1050_Analyzer
```

輸入流程：

```text
TOV1050 CSV
  -> streaming clean/preprocess
  -> metadata enrichment
  -> TOV640-compatible exception detection
  -> report/chart export
```

硬性限制：

- 不修改 `C:\Smart Maintanence\TOV640_Analyzer` 的任何檔案。
- 每次設計或實作 TOV640 演算法相關功能前，先閱讀：
  - `TOV640_Analyzer\docs\architecture.md`
  - `TOV640_Analyzer\docs\TOV1050_Migration\Background.md`
  - `TOV640_Analyzer\docs\TOV1050_Migration\Variable Mapping with TOV640_Analyzer.xlsx`
- migration raw data 與 metadata workbook 僅作唯讀參考。
- 第一階段採獨立專案與 adapter；不直接 import TOV640 runtime mutable state。

## 2. 已確認的命名與業務規則

### 2.1 Logical line

- `AEL` 使用 `LAR_AEL metadata.xlsx`。
- `TCL` 使用 `LAR_TCL metadata.xlsx`。
- 先前清單中的重複 `KTL` 視為 typo。
- `TKS` 不是獨立 line，而是 `TKL` 的 session。

### 2.2 Session 與 metadata

Session 是分析/報表業務上下文，不由 `SHO_AWE` 推斷。Metadata resolver 主要以 line + direction 查找；只有有專用 workbook/sheet 的 session 才切換來源。

| Logical line | Session | Workbook |
|---|---|---|
| `AEL` | `Mainline` 或其他已核准 session | `LAR_AEL metadata.xlsx` |
| `TCL` | `Mainline` 或其他已核准 session | `LAR_TCL metadata.xlsx` |
| `DRL` | `Mainline` | `DRL metadata.xlsx` |
| `DRL` | `PL` | `DRL metadata.xlsx` + `PL track type` |
| `KTL` | `Mainline` | `KTL metadata.xlsx` |
| `ISL` | 支援的 session | `ISL metadata.xlsx` |
| `TWL` | 支援的 session | `TWL metadata.xlsx` |
| `TKL` | `Mainline` | `TKL metadata.xlsx` |
| `TKL` | `TKS` | `TKS metadata.xlsx` |

若 session 尚無正式 metadata 定義，可建立 preview，但必須標示 `metadata_mapping_unconfirmed`，禁止靜默 fallback。

### 2.3 Direction 與檔名

方向固定為：

```text
UT -> metadata sheet "UT track type"
DT -> metadata sheet "DT track type"
DRL + PL + UT -> metadata sheet "PL track type"
```

`track` 保留 `UT`/`DT`；sheet 內的 `track type`（`Support`、`non-support`、`Tangent`、`Curve` 等）另存為 `track_type`。

輸入檔名預期格式：

```text
YYYYMMDD_<LINE>_<TRACK>_<STATION_START>_<STATION_END>.csv
```

例如 `20260822_AEL_UT_SHO_AWE.csv` 解析為：

```text
date=2026-08-22
line=AEL
track=UT
station_start=SHO
station_end=AWE
session=<user input>
```

`SHO_AWE` 是起站/終站，不是 session。檔名解析只作 UI 預填，使用者可覆寫。

輸出檔名：

```text
YYYYMMDD_<LINE>_<TRACK>_<SESSION>_<STATION_START>_<STATION_END>_<ARTIFACT>.<ext>
```

## 3. Canonical schema

### 3.1 Lineage 與診斷欄位

| 欄位 | 型別 | 定義 |
|---|---|---|
| `source_file_name` | string | 原始 CSV basename |
| `source_row_number` | integer | CSV physical row；header=1，第一筆資料=2 |
| `source_values` | optional object | 診斷模式才保存原始值 |
| `is_trimmed_boundary` | boolean | 是否屬於前/後 100 筆 |
| `exclusion_reason` | nullable enum | `startup_boundary`、`shutdown_boundary`、`invalid_chainage`、`no_valid_measurement`、`invalid_row` |

`source_row_number` 不因 chunk、filter 或 reset index 改變。

### 3.2 Canonical measurement/context 欄位

```text
line: string
track: UT | DT
date: ISO date
session: string
section: string
task_no: string
station_start: string
station_end: string
chainage: decimal/float64
height1..height4: nullable float64
stagger1..stagger4: nullable float64
wear1..wear4: nullable float64
height_min/max: nullable float64
wear_min/max: nullable float64
location_type: nullable string
track_type: nullable string
overlap: nullable string
landmark: nullable string
tension_length: nullable string/decimal
```

Canonical layer 使用 snake_case；報表層才映射至 TOV640 相容的 `FromM`、`ToM`、`maxValue` 等欄位。

## 4. CSV 清洗契約

固定順序：

1. Streaming 讀取 CSV，建立 physical row number。
2. 去除 header 欄位名稱前後空白。
3. 空字串、全空白字串、`1.#IO` 轉為 missing。
4. 數值欄位 strict numeric conversion；失敗者變 NaN 並記錄。
5. `Km` 直接轉成 `chainage`；不合併 `KM`/`LOCATION`。
6. 前 100 筆標記 `startup_boundary` 並排除。
7. 保留最多 100 筆 tail buffer，EOF 時標記 `shutdown_boundary` 並排除。
8. 對保留資料計算 wire aggregates。
9. 所有量測 wire 都無有效值的 row 標記 `no_valid_measurement`，不進 detector。
10. 執行 metadata enrichment，再交給 detector。

不變量：

- TOV1050 Height 不加 `5300`。
- `Km == chainage`。
- `1.#IO` 不得形成 exception。
- 不套用 TOV640 wear `6.56` sentinel，除非另有正式 TOV1050 規格。
- 不使用 nearest metadata interval 或靜默 fallback。

## 5. Cleaning summary contract

每次分析輸出：

```text
cleaning_summary:
  input_data_rows
  retained_rows
  startup_rows_removed
  shutdown_rows_removed
  invalid_chainage_rows
  invalid_numeric_cells
  io_sentinel_cells
  no_valid_measurement_rows
  metadata_unresolved_rows
  metadata_ambiguous_rows
  column_stats:
    <canonical_column>:
      non_null_count
      null_count
      io_sentinel_count
      invalid_numeric_count
```

各 exclusion count 必須可 reconciliation；invalid row 不可被錯誤計入 startup/shutdown trim。

## 6. Metadata resolver

Workbook 的實際 sheet：

- `threshold`
- `UT track type`
- `DT track type`
- `location type`
- DRL 額外有 `PL track type`

Resolver 步驟：

1. 依 line/session 決定 workbook。
2. 依 direction/session 決定 direction sheet。
3. 用 chainage 查 direction interval。
4. 用 chainage 查 `location type` interval。
5. 以 `location_type + track_type + exception_type` 查 threshold。
6. 任何一層 0 命中為 `metadata_unresolved`；多命中為 `metadata_ambiguous`。

每個命中保留 workbook、sheet、source row、interval bounds。重疊時不採第一筆、最短 interval 或最近邊界；preview 可顯示候選，但正式 report/export 必須 blocked。

## 7. Detector 重用邊界

保留 TOV640 的：

- Height min/max aggregate。
- Wear min aggregate。
- Stagger 左右方向規則。
- threshold gatekeeper。
- L1/L2/L3 分級。
- consecutive-mask grouping。
- 每組取最嚴重點。
- exception report 欄位語意與 deterministic ID 語意。

只在 TOV1050 adapter 實作差異：CSV、欄位 mapping、sentinel 清洗、Km chainage、前後 100 筆、metadata workbook resolver、streaming。

本專案以複製的 TOV640 codebase 為基底，直接重用既有 `ExceptionDetector`、grouping、threshold gatekeeper、level classification、exception ID 與 exporter。TOV1050 差異集中在 adapter 邊界：CSV loader、metadata workbook adapter、request/file-name parsing，以及大檔案分批載入與診斷欄位。除非 parity 測試證明必要，不另建第二套 detector 語意，也不修改來源 `TOV640_Analyzer`。

## 8. Chunk processing 與跨 chunk grouping

建議預設 chunk size：`50,000` rows，可由 benchmark 調整。正式 pipeline：

```text
CSV reader
  -> row numbering
  -> normalization
  -> sentinel/numeric cleaning
  -> boundary buffer
  -> metadata enrichment
  -> detector state machine
  -> finalized exceptions/report rows
```

不保留完整 raw DataFrame；只保留目前 chunk、100-row tail buffer、open groups 與必要 summary/chart aggregates。

每種 exception type 維護 `OpenGroup`：

```text
exception_type
group_start_row
group_end_row
from_chainage
to_chainage
worst_value
worst_source_row
worst_chainage
class/location/track metadata
```

chunk 邊界不得 finalize open group。遇到 mask false、exception type/metadata partition 改變、chainage 不符合連續性規則或 EOF 時才 finalize。full-frame 與 chunk execution 必須得到相同 exception ID、bounds、worst point、metadata context 與 cleaning summary。

## 9. Desktop workflow、diagnostics 與 exports

流程：

```text
選 CSV
  -> 檔名預填
  -> 使用者確認 line/session/track/date/section/task/stations
  -> clean + metadata preview
  -> cleaning summary/diagnostics
  -> exception analysis
  -> report/chart
  -> export
```

Blocking 條件：缺 Km、全被 trim、unsupported line/session/track、缺 workbook/sheet、metadata unresolved/ambiguous、缺必填欄位、CSV read/schema failure。

`1.#IO`、部分 wire 缺測與 invalid numeric cell 本身不 blocking，但必須可見。

Report 至少包含：

```text
Exception ID, Exception Type, Level, FromM, ToM, Length,
MaxValue, MaxLocation, Line, Session, Track, Date, Section,
Task Number, Station Start, Station End, Location Type, Track Type,
Tension Length, Overlap, Landmark, Source Start Row, Source End Row,
Worst Source Row
```

Chart 至少包含 height/stagger/wear wire series、threshold lines、exception intervals、metadata boundaries，並支援 source row/exception detail。

## 10. 測試策略

### 10.1 Unit tests

- 欄位 mapping、Km chainage、Height 不加 5300、`1.#IO`。
- 前/後 100 rows、lineage、summary reconciliation。
- filename parsing 與 session 不由檔名推斷。
- 所有 workbook/sheet resolver、UT/DT、DRL PL、TKL TKS。
- missing/overlap/ambiguous fail closed。
- threshold 邊界、L1/L2/L3、scalar/stagger grouping、exception ID。

### 10.2 Contract/regression

- 使用 AEL sample CSV 與各 metadata workbook 代表 interval。
- 使用 TOV640 canonical fixture 做 differential comparison。
- 相同 canonical input 的 exception type、level、bounds、worst point、group count 與 ID semantics 必須一致。

### 10.3 Chunk equivalence

同一 fixture 執行 full-frame、chunk 1,000、50,000、100,000；結果必須一致，特別涵蓋 exception 跨 chunk 邊界。

### 10.4 Real files

AEL sample 目前 476 data rows，trim 後預期 276 rows；HeightWire3/4 等欄位全為 NaN 不得 crash；`1.#IO` 不得產生 exception。缺少可用 fixture 的 line 記為 unavailable，不自行捏造人工結果。

## 11. 效能與驗收

以約 900,000 rows、150 MB CSV 建立 benchmark，記錄：

- total duration
- peak RSS
- rows/sec
- exception count
- diagnostic count

第一階段先建立可重現基準；正式秒數/記憶體上限在 benchmark 後固定，不預先杜撰數字。

Desktop 驗收必須確認：

1. AEL sample 預填 AEL、UT、日期、SHO、AWE。
2. 使用者選 Mainline 後解析 `LAR_AEL metadata.xlsx` + `UT track type`。
3. 顯示清洗統計，保留 276 rows。
4. Height 顯示約 4288 至 4295，不出現 +5300 結果。
5. 可產生 report/chart，檔名包含 session。
6. 不同 chunk size 結果一致。
7. metadata ambiguity/missing 時禁止正式匯出並顯示 actionable diagnostics。
8. TOV640 目錄保持未修改。

## 12. 下一階段邊界

本文件完成的是設計與資料契約，不包含 production implementation。使用者審閱本 spec 並確認無修改後，下一步才建立 implementation plan；實作時每次涉及 TOV640 演算法語意，必須重新閱讀指定三份來源文件並進行 codebase graph impact analysis。


