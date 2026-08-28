# History Compare 軟件版本差異圖設計規格

日期：2026-08-04
狀態：設計已獲使用者批准，等待書面規格審閱

## Design Read

Reading this as: 供鐵路維修及分析人員使用的操作型資料分析介面，以可信、密集、可掃描的產品語言為主，沿用現有 Material UI 與 Plotly。

- DESIGN_VARIANCE：3。維持現有 History Compare 的熟悉結構。
- MOTION_INTENSITY：2。只使用標準狀態切換及 Plotly zoom feedback。
- VISUAL_DENSITY：8。完整呈現長路段、多 channel 工程數據。

Taste Skill 的 landing page 模式不適用於本功能；只採用其層級、排版、可讀性及狀態完整性原則。Impeccable product register 是主要 UI 框架。

## 背景

同一路段以不同硬件軟件版本進行兩次獨立測試。兩次測試的 raw data 來自 Exception Report 的 `ChartData` sheet，包含相同物理路段，但相同 chainage marker 所代表的實際位置可能有小幅偏移。

現有 History Compare 可以比較 repeated exceptions，也會回傳各週期 `chart_data`，但 `ComparisonChart` 把不同週期放在不同 Y 軸，而且必須先選取 exception。這不適合整段路線的軟件版本 raw data 比較。

## 參考資料觀察

| 報告 | ChartData 筆數 | Chainage 範圍 | 資料順序 | 步距 |
| --- | ---: | --- | --- | ---: |
| `20260729_EAL_U2_FOT-TAP_Exception_Report.xlsx` | 32,507 | 113514 至 121640.5 | 遞增 | 0.25 m |
| `20260730_EAL_U2new_FOT-TAP_Exception_Report.xlsx` | 59,172 | 113478.75 至 120880 | 遞減 | 0.25 m |

兩份報告都有以下 raw channels：

- `height1` 至 `height4`
- `stagger1` 至 `stagger4`
- `wear1` 至 `wear4`

新版本資料的 chainage 排序方向與舊版本相反，因此演算法不能依賴 row order。

## 目標

1. 在 History Compare 中提供不依賴 exception selection 的整段測試路線比較。
2. Latest 與 Prev 1 在同一組 X-Y 軸疊圖。
3. 同一週期的四個 channel 使用相同顏色，channel 1 至 4 以線型區分。
4. 對 Height、Stagger、Wear 分別自動搜尋最佳 chainage shift。
5. 固定顯示四條 `Latest channel N - shifted Prev 1 channel N` 差值線。
6. 顯示 shift、normalized RMSE、有效點數及 overlap 長度，讓使用者可以判斷對齊可信度。
7. 保持現有 repeated exception、編輯、匯出、資料庫儲存及 exception chart 流程不變。

## 非目標

- 不改變 repeated exception matching 演算法。
- 不改寫現有 `ComparisonChart` 的 exception-focused 行為。
- 不比較 Prev 2 或更舊週期的差值。
- 不以 `height_min`、`wear_min` 或其他摘要欄位代替四個 raw channels。
- 不在第一版提供手動 shift slider 或自訂搜尋範圍。
- 不把缺失值補成 0，也不跨資料空白區段插值。
- 不在本功能內輸出新的 Excel report。

## 已批准的使用者決策

- UI 採用 B 方案：上方 raw overlay，下方固定 difference。
- 搜尋範圍為 `-50 m` 至 `+50 m`。
- 搜尋步距為 `0.25 m`。
- Height、Stagger、Wear 分別求最佳 shift。
- 差值圖顯示四條 channel 差值線。
- 工作範圍是整段測試路線，不需要先選 exception。
- 整合方式採用方案 A：現有 `/analyze/compare` 增加 optional alignment response。

## 架構

### Backend

新增獨立純函式模組：

`backend/app/core/calculation/chainage_alignment.py`

建議介面：

```python
build_aligned_comparison(
    latest_chart: dict[str, list],
    previous_chart: dict[str, list],
    *,
    max_shift_m: float = 50.0,
    step_m: float = 0.25,
) -> dict
```

API endpoint `POST /analyze/compare` 增加 optional `include_alignment` boolean，預設為 `false`。未啟用時，現有 response shape 不變。啟用時，使用已載入的 `chart_data[0]` 與 `chart_data[1]` 計算並加入 `aligned_comparison`。

只比較 Latest 與 Prev 1。`olderPreviousFiles` 仍按現有流程參與 repeated exception chain comparison，亦保留於原有 `chart_data`，但不產生 difference。

### Frontend

`CompareSession` 增加 optional `alignedComparison` 欄位。`handleCompare` 在 `FormData` 加入 `include_alignment=true`，成功時同時儲存 `chartData` 與 `alignedComparison`。

結果工具列新增第三個頁籤：`Version Difference`。新增獨立元件：

`frontend/src/components/HistoryCompare/VersionDifferenceChart.tsx`

現有 `ComparisonChart.tsx` 及其 selected exception 流程保持不變。

## Chainage 對齊演算法

### 1. 正規化

1. 讀取 `Chainage` 及指定 metric 的四個 raw channels。
2. 使用 `tick = round(chainage / 0.25)` 建立整數 index，避免浮點比較誤差。
3. 對 tick 遞增排序，因此 ascending 或 descending raw row order 會得到相同物理順序。
4. 同一 tick、同一 channel 若有多個有限值，只在 alignment helper 內取平均。原始 `chart_data` 不改寫。
5. 非數值、NaN、Infinity 及 null 都視為缺失。

### 2. Shift 定義

正 `shift_m` 表示將 Prev 1 的 chainage 加上該值後與 Latest 對齊。

搜尋 tick 為 `-200` 至 `+200`，共 401 個候選值。每個候選只直接配對相同整數 tick，不進行 interpolation。

### 3. 有效配對

每個候選 shift 只使用以下資料：

- 相同 metric
- 相同 channel number
- Latest 與 shifted Prev 1 都有有限值

先計算 401 個候選各自的有效配對數。可參與 RMSE 排名的候選必須同時滿足：至少 100 個有效配對點、有效 chainage span 至少 25 m，以及不少於該 metric 候選最大有效配對數的 80%。這可避免以犧牲大部分路線 overlap 換取偶然較低的 RMSE。所有候選都未達要求時，該 metric 標記為 `unavailable`。

### 4. Normalized RMSE

每個 metric 在搜尋前，先由 Latest 及 Prev 1 整段路線的所有有限 raw values 計算一次固定 robust scale。Scale 不隨候選 shift 或其 overlap 改變，確保 401 個候選 score 可直接比較：

```text
scale = max(p95(values) - p5(values), epsilon)
```

每個 channel 的 score：

```text
channel_rmse = sqrt(mean((Latest - Prev shifted)^2)) / scale
```

Metric score 依各 channel 的有效點數加權：

```text
metric_score = sum(channel_rmse * valid_point_count) / sum(valid_point_count)
```

選擇 normalized RMSE 最小的 shift。若 score 相同，依序使用以下 tie-break：

1. `abs(shift_m)` 較小者
2. 有效配對點較多者
3. shift 數值較小者，確保結果完全 deterministic

### 5. Difference

最佳 shift 確定後，對 channel 1 至 4 分別計算：

```text
difference = Latest - shifted Prev 1
```

缺少任一側數值時輸出 null。Difference 不跨 null 連線。

## API Response

現有欄位維持不變，啟用 alignment 時額外加入：

```json
{
  "aligned_comparison": {
    "status": "ready",
    "latest_file": "latest.xlsx",
    "previous_file": "previous.xlsx",
    "step_m": 0.25,
    "max_shift_m": 50.0,
    "metrics": {
      "height": {
        "status": "ready",
        "shift_m": 8.25,
        "rmse": 9.42,
        "normalized_rmse": 0.11,
        "overlap_from": 113500.0,
        "overlap_to": 120875.0,
        "overlap_length": 7375.0,
        "valid_points": 25000,
        "chainage": [],
        "latest": [[], [], [], []],
        "previous": [[], [], [], []],
        "difference": [[], [], [], []]
      },
      "stagger": {},
      "wear": {}
    }
  }
}
```

上例數字只說明 schema，不是預期測試結果。`status` 可為 `ready` 或 `unavailable`。單一 metric unavailable 不會令整個 compare request 失敗。

## UI 與互動

### Result Tab

History Compare 結果區保留：

1. `Repeated Table`
2. `Comparison Chart`
3. `Version Difference`

`Version Difference` 不依賴 `selectedRow`。Compare 成功後，使用者可立即進入整段路線比較。

### Chart Layout

- Metric segmented tabs：`Height`、`Stagger`、`Wear`，預設 `Height`。
- 上圖：Latest 與 Prev 1 shifted raw overlay。
- 下圖：四條 `Latest - Prev 1` difference。
- 兩圖共用 chainage X 軸 range，zoom 及 pan 同步。
- 初始 X 軸顯示兩份 shifted data 的 union route。
- Difference 只在有效配對位置繪製，union route 內無配對的區域保持空白。

### Visual Encoding

- Latest 與 Prev 1 使用固定且具對比的週期顏色。
- 同一週期的 channel 1 至 4 使用同一顏色。
- Channel 1：solid。
- Channel 2：dash。
- Channel 3：dot。
- Channel 4：dash-dot。
- Difference 的四條線沿用相同 channel line style。
- 顏色不是唯一識別方式，legend 同時顯示 cycle 及 channel line style。

### Summary and Hover

目前 metric 的工具列顯示：

- Best shift
- Normalized RMSE
- Valid points
- Overlap length

Raw hover 顯示 chainage、cycle、channel、value。Difference hover 顯示 chainage、channel、Latest、Prev 1 及 difference。

## 狀態與錯誤處理

### Loading

使用與最終兩圖相同尺寸的 skeleton，避免 layout shift。Compare button 維持現有 loading 行為。

### Empty

尚未執行 Compare 時，Version Difference 顯示目前既有 results empty state 語言，不顯示假資料。

### Missing ChartData

缺少 Latest 或 Prev 1 的 `ChartData` 時，`aligned_comparison.status` 為 `unavailable` 並提供明確 reason。Repeated Table 及其他 compare 結果仍可使用。

### Metric Unavailable

若只有部分 metric 缺少 raw channels 或有效 overlap 不足：

- 可用 metric 正常顯示。
- 無法使用的 metric tab 為 disabled 或顯示 unavailable reason。
- Raw overlay 若有資料仍顯示，difference 不補 0。

### Backend Failure

Unexpected alignment error 不應吞掉現有 compare 結果。API 將 alignment 標記為 unavailable 並記錄錯誤；只有原有 compare 本身失敗時才沿用整體 HTTP error。

## Performance

- Alignment 在 backend 執行，避免瀏覽器進行 401 次大陣列掃描。
- 內部使用整數 tick map 及 NumPy-compatible arrays，避免 DataFrame row loop。
- 每個 metric 最多掃描 401 個候選 shift，並重用已正規化資料。
- Frontend 繼續使用 Plotly `scattergl` 處理長路段 trace。
- Response 使用 columnar arrays，不回傳逐點 JSON objects。
- 第一版不自動 downsample，確保 raw comparison 與差值可追溯；若實測 payload 或 rendering 超過現有可接受範圍，再以保峰值 downsampling 作獨立優化。

## Accessibility and Responsive Behavior

- Metric tabs、legend controls 及 Reset Zoom 都有可讀 label。
- Cycle 以顏色區分，同時以文字 legend 標識；channel 以線型區分。
- Summary 數值使用固定字級，不以 viewport width 縮放。
- Desktop 及 mobile 都維持上下堆疊，避免圖表並排縮窄。
- 圖表容器使用穩定 `min-height`，控制列可在窄畫面換行。
- 所有 loading、unavailable 與 error 狀態以文字說明。

## Testing

### Backend Unit Tests

- Ascending 與 descending chainage 得到相同結果。
- 已知 synthetic shift 可被準確恢復。
- 正 shift 定義符合 `Prev chainage + shift = Latest chainage`。
- 四個 channel 分別配對，不跨 channel matching。
- Null、NaN、Infinity 及資料 gaps 保持缺失。
- 重複 tick 的有限值平均是 deterministic。
- Height、Stagger、Wear 分別求 shift。
- Normalized RMSE 不受不同 metric 單位尺度支配。
- 最少有效點及 25 m span guard 生效。
- 80% relative coverage guard 排除低重疊候選。
- Tie-break 結果 deterministic。

### Backend API Tests

- `include_alignment` 預設 false，現有 response shape 不變。
- 啟用 flag 時回傳三個 metric contract。
- 缺少 ChartData 或 raw channel 時回傳 unavailable，不破壞 repeated results。
- 三份以上檔案仍只對 Latest 與 Prev 1 產生 alignment。
- 現有 export cache 及 compare globals 行為不變。

### Frontend Tests

- Compare request 帶 `include_alignment=true`。
- `CompareSession` 正確儲存及清除 alignment result。
- Version Difference 不需要 selected exception。
- Height、Stagger、Wear tab 切換正確 trace。
- Raw 圖每個週期的四 channel 同色、不同線型。
- Difference 固定四條 channel trace，null 不連線。
- 兩圖共用 X range 及 Reset Zoom。
- Loading、empty、partial unavailable、missing ChartData 狀態。
- 既有 Repeated Table 及 Comparison Chart 測試保持通過。

### Reference Integration Test

使用本規格列出的兩份 EAL U2 report 作慢速 integration test，驗證：

- 0.25 m tick 正規化。
- Descending new report 可被處理。
- 三個 metric 都回傳可解釋 summary 或明確 unavailable reason。
- Response size 及 runtime 在 desktop app 可接受範圍。

此測試標記為 slow，不放入每次快速 unit test。

## 影響範圍與隔離策略

Codebase graph 把 `HistoryCompareView` 與 `ComparisonChart` 影響標示為 HIGH/CRITICAL。為控制風險：

- 不修改 `ComparisonChart` 的 props 或 selectedRow 邏輯。
- 新 UI 放入獨立 `VersionDifferenceChart`。
- 新演算法放入純 backend module，endpoint 只負責 orchestration。
- API 新欄位是 optional，現有 consumers 可忽略。
- Store 只增加 optional state，不改既有 session update semantics。

## 驗收條件

1. 上傳兩份有 `ChartData` 的 report 並執行 Compare 後，可直接開啟 Version Difference。
2. Height、Stagger、Wear 各自顯示 Latest 與 shifted Prev 1 的同軸 raw overlay。
3. 每個週期的四 channel 顏色相同，線型可區分。
4. 三個 metric 各自在 `-50 m` 至 `+50 m`、0.25 m 步距內找到最佳 shift。
5. Difference 顯示四條 `Latest channel N - shifted Prev 1 channel N` 線。
6. UI 顯示 shift、normalized RMSE、valid points 及 overlap length。
7. Ascending 與 descending source row order 不影響結果。
8. Null 或無重疊資料不會被補 0 或跨 gap 連線。
9. 缺少部分 metric 時，其餘 metric 及 repeated exception workflow 仍可使用。
10. 現有 History Compare exception chart、編輯、匯出及資料庫流程沒有行為回歸。

## 風險

- Channel number 代表的物理 wire 必須在兩個軟件版本間保持同一語意。本設計依使用者批准，固定 channel N 對 channel N，不進行跨 channel 自動 matching。
- 大型 `chart_data` response 已存在，新增 difference arrays 會增加 payload。使用 columnar arrays 控制額外成本，並以 reference integration test 實測。
- 若未來 report 的 sample step 不是 0.25 m，第一版會以 unavailable reason 拒絕 alignment，而不是自動 interpolation。支援其他 sample step 應作為獨立功能。
