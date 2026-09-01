# TOV1050 metadata、圖表效能與分析工作流設計

- 日期：2026-09-02
- 狀態：Approved by user
- 相關需求：`docs/requests/2026-09-02-tov1050-metadata-performance-ux-architecture.md`
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-9（功能增強總入口；Linear MCP issue 寫入工具目前未暴露）

## 1. 目標

在不改變 TOV640 detector 判定語意的前提下，讓 TOV1050 Analyzer：

1. 以 TOV640 寬表 metadata 作為外部維護與 integration 契約。
2. 將 TOV1050 CSV 的 `Km`、metadata interval、bracket mapping 統一成公尺，與 TOV640 的 `FromM/ToM` 一致。
3. 對 90 萬筆以上 raw data 提供全線 chainage overview，保留 overshoot，並在 zoom 時顯示更高解析度資料。
4. 將 Exception Generator 的輸入流程改為 run list quick-fill 加上可覆寫 context。
5. 保留現有 Graph／Table 結果版面，只增加效能、選取同步與 FromM-ToM zoom。
6. 讓分析與 Excel 匯出在六個模組中都有可追蹤的 staged loading 狀態。
7. 以 gpt-image-2 圖像加上程式驗證文字，更新 About 與 Algorithm Explain dialog。

## 2. 已批准的關鍵決策

### 2.1 Metadata 邊界

採用「寬表外部契約、typed canonical runtime model」：

- Reference workbook 的 `threshold` 使用 TOV640 寬表欄位，例如 `Stagger L1/L2/L3`、`Wire Wear L1/L2/L3`、`High Height`、`Low Height`。
- TOV1050 mapping workbook 以 TOV640 命名習慣維護 `Exception Boundarys`、`<LINE> UT`、`<LINE> DT`、DRL 的 `<LINE> PL` 等 sheet。
- adapter 在 workbook 讀取邊界轉成 `ThresholdRule`、`TrackInterval`、`LocationInterval`、`TensionBracket` 等 typed model，再交給既有 detector。
- reference workbook 與 packaged runtime workbook 必須明確標示版本；禁止看到長表或寬表時靜默猜測或 fallback。
- resolver 保留 workbook、sheet、source row、原始 interval 與 normalized interval，供診斷與 report lineage 使用。

### 2.2 Chainage 單位

TOV1050 CSV 的 `Km` 來源值在 adapter 入口轉成 `Chainage_m = Km * 1000`。所有下列欄位只使用 m：

- detector 輸入的 `Chainage`
- exception `FromM`、`ToM`、`maxLocation`
- graph x-axis 與 zoom range
- metadata track/location interval
- `TOV1050 TL-BK No.xlsx` 的 bracket location

來源 km 值必須保留在 diagnostics 或轉換紀錄中，不能以顯示格式掩蓋實際換算。

## 3. 效能與圖表資料流

### 3.1 不變量

取樣只允許發生在 detector 完成之後：

```text
CSV raw rows
  -> clean, lineage, Km-to-m normalization
  -> metadata mapping
  -> full-fidelity detector
  -> exception/report results
  -> chart LOD/envelope generation
  -> Graph/Table UI
```

不得將取樣後的資料交給 exception detector。`1.#IO`、invalid numeric、前後 100 rows trim 與 no-valid-measurement 規則維持現有契約。

### 3.2 Overview envelope

初始畫面顯示有效資料的完整 chainage range，分別對 Height、Stagger、Wire Wear 的四條 wire trace 建立 bucket。每個 bucket 至少保留：

- 第一個與最後一個有效點，維持線段連續感。
- 原始 min point 與 max point，保留正負 overshoot。
- `source_row_number`、原始 chainage、保留原因（`first`、`last`、`local_min`、`local_max`）。
- NaN 或 chainage gap 的 segment boundary，不跨缺測資料連線。

不使用平均值取代 extrema，也不使用簡單的每 N 筆取一筆。Overview 的目標是每條 trace 約為 viewport 寬度的 2 至 4 倍點數，而不是固定刪除比例。

### 3.3 Zoom LOD

Graph 監聽 Plotly x-axis range：

- Overview：低點數 envelope。
- 中度 zoom：以該 chainage window 產生更細 envelope。
- 高度 zoom：window 內點數低於解析度上限時回傳每一筆有效 raw point。

每次 response 都包含 `range_from_m`、`range_to_m`、`resolution`、`point_count` 與 `source_row_number`，讓 UI 能顯示目前解析度與追溯來源。Exception peak、threshold crossing、exception interval 邊界與 selected exception window 一律列入保留集合，即使它們不是該 bucket 的 min/max。

### 3.4 後端實作分期

第一期只改 chart payload：保留現有 full-fidelity detector，後端在 response 前建立 envelope，避免 renderer 收到 90 萬筆完整 trace。

第二期才把分析 pipeline 改成真正的 chunk state machine。chunk 必須保留 open exception groups、tail buffer 與所有 summary state；full-frame 與 chunk execution 必須在 parity tests 上得到相同 exception ID、level、FromM/ToM、maxValue、maxLocation、count 與 cleaning summary。失敗時不得靜默採用 chunk 結果。

## 4. Exception Generator input UX

### 4.1 版面

維持多 analysis tabs。設定頁改為三段式：

1. **Select run**：line tabs 或 select、可搜尋的 `TOV1050 Run List.xlsx` 清單。
2. **Confirm context**：Track（UT/DT）、Date、Station Start、Station End、Task No.、Session；由 run list 或檔名預填，但每欄可覆寫。
3. **Analyze readiness**：CSV path、metadata workbook、chainage m range、清洗摘要、必要欄位與 metadata preview 狀態；通過 blocking validation 才可開始分析。

文字輸入欄位使用 autocomplete + free text。覆寫後顯示與 run list 預設值不同，但不阻止特殊案例。`Direction` 顯示與型別改為 `Track`，API 仍維持既有 `track` 欄位。

### 4.2 Graph／Table 結果

現有 Graph／Table 版面、Exceptions panel、filters 與 Plotly 三段圖維持不變，只增加：

- 工具列顯示 `Overview`／`Detail` resolution 與目前 `Chainage FromM–ToM`。
- Graph 選取 exception 時同步 table row。
- Table 選取 row 時同步 graph highlight 與 FromM-ToM zoom。
- `Zoom to range` 使用 m 單位，且保留目前 view mode、filter 與 tab 狀態。

概念稿：

- `docs/design-concepts/tov1050-exception-generator-input-concept.png`
- `docs/design-concepts/tov1050-exception-result-subtabs-concept.png`

## 5. Loading 與匯出狀態

建立共用 task contract：

```text
queued -> reading/uploading -> cleaning -> metadata_mapping
       -> detecting/calculating -> preparing_chart
       -> complete | error | cancelled
```

每個 stage 可帶 `processed`、`total`、`percentage`（未知時為 null）、`message` 與 `error_code`。前端使用 skeleton rows、chart placeholder 與 determinate progress；不以假百分比取代未知狀態。匯出使用：

```text
preparing -> writing_workbook -> finalizing -> complete | error | cancelled
```

六個模組共用狀態元件與 reduced-motion 行為：Exception Generator、History Compare、Version Difference、Wear Calculator、Stagger Calculation、Trend Analyzer。取消、錯誤與完成狀態必須保留可操作訊息。

## 6. About 與 Algorithm Explain 視覺資產

產生九張 `gpt-image-2` 圖像：

- About：overall architecture、data flow、operator workflow。
- 六個模組各一張演算法／資料流概念圖。

圖像只作視覺層；實際欄位、門檻、stage、錯誤條件由程式中的 verified content、caption 與 alt text 提供。每張圖標註來源 contract 版本或更新日期，避免圖片文字與 code drift 時誤導使用者。不可把 AI 圖像中的字串直接當成測試或規格來源。

## 7. 測試與驗收

### 7.1 Metadata

- 八份 TOV1050 workbook 都能辨識寬表 threshold schema、sheet 命名、欄位型別與 m interval。
- DRL 寬表與 TOV640 EAL/TML 對照報告可追溯到 workbook/sheet/row。
- `TOV1050 TL-BK No.xlsx` 的 line/track/location/bracket mapping 檢查重複、空白、排序與 m 轉換。
- interval overlap/ambiguity、缺 sheet、缺必要欄位時 fail closed。

### 7.2 Detector safety

- 取樣前的 full-fidelity detector 結果與現有 fixture 完全一致。
- 建立單列 overshoot、threshold crossing、exception peak 位於 bucket 邊界與 chunk 邊界的 adversarial fixtures。
- full-frame/chunk parity 比對 exception IDs、levels、FromM/ToM、maxValue/maxLocation、counts 與 cleaning summary。

### 7.3 Graph

- 全線 overview 顯示完整 m chainage range。
- 每條 wire 的 local min/max overshoot 在 overview 可見。
- zoom range 能取得更細 envelope；足夠小的 window 顯示每筆 raw point。
- graph 與 table 選取同步，且 source row 可追溯。
- 116 MB KTL 與 32 KB DRL 檔案都能完成分析；記錄 duration、rows/sec、peak RSS、chart payload bytes。

### 7.4 UI/loading

- run list 可快速填入 line、track、date、station start/end、task no.；每欄可覆寫。
- `Direction` 不再出現在 Exception Generator 使用者介面。
- 六個模組分析與匯出都有 skeleton、stage、成功、錯誤與取消狀態。
- keyboard focus、contrast、reduced-motion 與 existing MUI/Plotly conventions 通過檢查。

## 8. 分期交付

1. Metadata contract audit 與 m normalization，先輸出差異報告與未決 workbook 問題。
2. Chart envelope/LOD 與 Graph/Table sync，不改 detector。
3. Exception Generator input components 與 run list quick-fill。
4. Shared analysis/export task status 與六模組 loading UI。
5. About／Algorithm Explain verified content 與九張圖像資產。
6. Chunk detector、window query/cache 與 full benchmark，只有 parity 通過才啟用。

## 9. 未決事項

- packaged runtime 是否直接使用寬表 workbook，或在 build step 產生明確版本的 canonical cache；不得在 runtime 靜默轉換。
- TOV1050 原始 `Km` 與所有現有 metadata 檔案的 m 轉換是否要以一次性 migration 產生新檔，或由 adapter 每次讀取時轉換；需配合 checksum/version 策略決定。
- Linear MCP 寫入工具未暴露，需由使用者或環境補上 issue 更新權限後，才能將本 spec 拆分同步至 DAV-9 及子 issue。
