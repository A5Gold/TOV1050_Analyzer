# Stagger Calculation 前端設計規格

## 1. 目標

為 `stagger calculation` 模組建立一個給「數據分析人員」使用的工作台式介面，讓使用者可以：

1. 上傳 Excel 文件並立即看到檔案狀態。
2. 以平行 tab 方式分析不同 report cycle，彼此狀態完全獨立。
3. 檢視計算摘要、明細表、圖表與 trace。
4. 一鍵打開演算法說明，理解資料流、公式、參數定義，以及 wind speed factor 對 stagger 的意義。

## 2. 介面原則

- 高密度資訊，但維持清楚分區。
- 主工作流優先：上傳 -> 驗證 -> 分析 -> 檢視結果。
- tab state must be isolated: 每個 cycle 的分析結果、選中項目、圖表焦點與錯誤訊息都只能影響當前 tab。
- 說明內容採「按需開啟」，不干擾主畫面。
- 盡量沿用現有 `CalculationView`、`FileUploadPanel`、`WearResultTable`、`TrendChart`、`TrendResultTable`、`WearAlgorithmDialog`、`TrendAlgorithmDialog` 的結構。

## 3. 版面架構

```text
Calculation Page
├─ Page Header
├─ Upload & Control Zone
│  ├─ Drag/drop upload panel
│  ├─ file chips / validation hints
│  └─ Analyze button
├─ Cycle Tabs Zone
│  ├─ tab strip: Cycle A / Cycle B / ...
│  └─ add / close / duplicate actions
├─ Result Overview Zone
│  ├─ summary cards
│  └─ algorithm explain button
└─ Detail Zone
   ├─ Tabs within current cycle: Summary / Trace / Chart / Raw Data
   └─ right-side algorithm drawer/dialog
```

## 4. 上傳區設計

### 4.1 互動方式

- 支援拖拉上傳。
- 支援點擊選檔。
- 支援多檔批次上傳。
- 顯示已選檔案 chip，可單筆移除。

### 4.2 驗證與狀態

- 顯示檔名、大小、日期與基本格式檢查結果。
- 若缺少必要工作表或欄位，直接在上傳區顯示錯誤。
- Analyze 按鈕在沒有文件時停用。
- 分析中顯示 loading 狀態與不可重複送出。

## 5. 結果呈現

### 5.1 摘要卡

分析完成後先顯示 3 到 5 張摘要卡，建議包含：

- 已處理檔案數
- 有效 stagger 筆數
- 異常筆數
- 平均 `K_eq`
- 命中規則數量

### 5.2 主內容 Tabs

#### Cycle Tabs

- 每個 cycle 使用獨立 tab 容器。
- 每個 tab 保留自己的上傳文件、分析結果、圖表選擇與錯誤狀態。
- 切換 tab 時不重新清空其他 cycle。
- 支援：
  - 新增 cycle tab
  - 關閉目前 tab
  - 複製目前 tab 內容建立新 cycle
  - 重新分析單一 cycle，不影響其他 tab

#### Tab A: Summary

- 顯示 stagger 結果表。
- 欄位建議：
  - `Summary ID`
  - `Line`
  - `Track`
  - `Exception Type`
  - `Ch_I`
  - `Spt_A / Spt_I / Spt_B`
  - `K_eq`
  - `Result`
  - `Remark`

#### Tab B: Trace

- 顯示逐步推導過程。
- 讓分析人員能回看：
  - 來源檔案
  - `Summary ID` 選取規則
  - `Ch_I / Spt_*` 對應
  - `ChartData` 取值
  - `K_eq` 策略
  - 最終公式輸出

#### Tab C: Chart

- 顯示 stagger 圖表或結果比較圖。
- 建議支援點選某筆資料並同步更新右側說明。

#### Tab D: Raw Data

- 顯示解析後的原始資料預覽。
- 用於核對欄位、sheet、與 mapping 正確性。

## 6. 演算法說明按鈕

### 6.1 放置位置

- 放在結果區標題列右側。
- 使用 `info` 圖示按鈕，tooltip 顯示「演算法說明」。

### 6.2 開啟形式

優先採用右側 drawer；若現有元件慣例偏向 dialog，也可延續 dialog。  
建議內容分成 4 區：

1. Algorithm Flow
2. Formula
3. Key Parameters
4. Wind Speed Factor Meaning

### 6.3 說明內容

- `Algorithm Flow`：Input -> Select Summary -> Resolve `Ch_I` -> Lookup `Spt_*` -> Map `ChartData` -> Compute `K_eq` -> Calculate stagger result
- `Formula`：顯示主要公式與代入關係
- `Key Parameters`：解釋 `Ch_I`、`Spt_A`、`Spt_I`、`Spt_B`、`Span_AI`、`Span_IB`、`K_eq`
- `Wind Speed Factor Meaning`：用簡圖說明風速因子如何影響 stagger 計算，標示它在公式中的位置與輸出影響

## 7. 資料流

1. 使用者上傳 Excel。
2. 使用者可建立一個或多個 cycle tab。
3. 前端對當前 tab 送出分析請求。
4. 後端回傳 stagger summary、trace、chart data。
5. 前端先渲染當前 tab 的摘要卡，再渲染 tab 內容。
6. 點選任一筆結果時，只同步更新目前 tab 的圖表與說明內容。

## 8. 錯誤處理

- 檔案格式錯誤：顯示在上傳區。
- 後端驗證失敗：顯示在 page alert。
- 部分資料缺失：結果表標註 `warning` 或 `incomplete` 狀態。

## 9. 介面元件建議

- `FileUploadPanel`
- `CycleTabBar`
- `StaggerSummaryCards`
- `StaggerResultTable`
- `StaggerTracePanel`
- `StaggerChart`
- `AlgorithmExplainDrawer`

## 10. 驗收標準

- 可以透過拖拉或選檔上傳文件。
- 上傳後能看見摘要與結果表。
- 能切換檢視 summary / trace / chart / raw data。
- 可以一鍵打開演算法說明。
- 說明內容能清楚對應公式、資料流與 wind speed factor。
