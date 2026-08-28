# Version Difference、Check 1 Year Record 與 About 文件更新設計

日期：2026-08-20

狀態：使用者已核准

範圍：Version Difference、History Compare 的 Check 1 Year Record、About／操作指南／開發者參考

## 1. 背景

本次變更同時處理三組相互關聯的問題：

1. Version Difference 圖表在使用者調整 Y 軸後，再調整同步 X 軸時會把 Y 軸恢復為預設範圍。
2. Version Difference 同時分析五個大型 Excel 檔案時，會因 Excel 解析、中間資料結構、alignment 計算及大型 JSON／Plotly payload 而出現 `Network Error`。
3. History Compare 的 Check 1 Year Record 需要按 alarm family、level 及既有 ACTION 執行新的決策規則，並為需要人工複核的結果提供 staged edit 工作流。
4. About、操作指南與開發者參考尚未完整說明 Version Difference 及新的 Check 1 Year Record 行為。

目前產品是供維修及工程人員處理異常比較、判斷重複異常及保存處理結果的 operational interface。本設計保留現有分析、篩選、表格編輯、Export 及 Save to DB 工作流，不把介面改造成行銷式或卡片式流程。

`PRODUCT.md` 已審閱，產品目的、主要使用者、工作流程原則及 accessibility 期望不需修改。`DESIGN.md` 已審閱，既有 Material UI、字體、spacing、色彩 token 及資料表慣例不需修改。

## 2. 目標

- 使用者調整 X 軸時，每張圖的 Y 軸保持使用者設定。
- 支援最多五個 Version Difference 檔案；日常每檔約 50,000 列，單檔高峰約 300,000 列。
- 避免一次把所有 workbook、DataFrame、Python list、alignment array 及完整圖表 response 同時保留在記憶體。
- 保留現有 0.25 m alignment、±50 m shift、有效點數、跨度、coverage 及 RMSE 語義。
- 將 Check 1 Year Record 規則拆成可獨立測試的決策模組。
- Stagger Left 與 Stagger Right 視為同一 alarm family。
- Low Height 與 High Height 保持不同 family。
- Case 2b／3b 在人工接受前不寫入資料庫。
- 讓使用者能清楚分辨自動結果、需要人工複核的結果及已接受但尚未寫入 Database 的結果。
- 更新使用者及開發者文件，使內容與實際行為一致。

## 3. 非目標

- 不把 Version Difference 改成背景 job、WebSocket 或輪詢式非同步工作。
- 不改變 Version Difference 的最多五個 cycle 角色。
- 不改變 History Compare 的基本 repeated-exception 產生演算法。
- 不重新設計整個 History Compare 或 About 版面。
- 不改變現有人工 ACTION 選項或覆寫已有非 Pending ACTION。
- 不新增新的產品定位、品牌 token 或全域設計系統。

## 4. 已確認的業務規則

### 4.1 共通匹配條件

一筆目前異常只有在以下條件全部成立時，才可與既有 Database record 配對：

1. SQL 候選先按 `line + track` 取得。
2. `section` 去除首尾空白後必須完全相同。
3. Alarm identity 必須符合第 4.2 節。
4. 目前 `maxLocation` 必須落在既有 `from_m` 至 `to_m` 之間，包含兩端。
5. 既有紀錄日期必須介於目前異常日期及其前 365 日之間，包含兩端。
6. Dialog 的 `section`、`date_from`、`date_to` filter 只可縮窄候選集合，不可擴大 365 日窗口。
7. 目前列已有非空且非 `Pending` 的 ACTION 時，回傳 `skipped`，不修改任何欄位。
8. 排除目前 exception 與自己的 Database record 配對。

日期選擇順序維持：目前列 `task_run_date`，其次 `date_str`，最後 request 的 `current_date`。Database record 優先使用 `task_run_date`，其次 `date_str`。無法解析日期、位置或必要 identity 的列保持不變。

### 4.2 Alarm identity 與 level

輸入字串會先執行 trim、Unicode casefold，並將連續的空白、底線或連字號正規化為單一空格，再映射為以下 identity：

| 原始 alarm | 正規化 identity | 可匹配規則 |
|---|---|---|
| Stagger Left、Stagger Right | `stagger` | Left／Right 可互配 |
| Low Height | `low_height` | 只配 Low Height |
| High Height | `high_height` | 只配 High Height |
| Wire Wear | `wire_wear` | 只配 Wire Wear |

Level 會正規化為 `L1`、`L2`、`L3`。

| 目前異常 | 允許的既有 level |
|---|---|
| Stagger L3 | L3、L2、L1 |
| Stagger L2 或 L1 | L2、L1；必須排除 L3 |
| Low Height L2 或 L1 | L2、L1 |
| High Height L2 或 L1 | L2、L1 |
| Wire Wear L2 或 L1 | L2、L1 |

沒有列在上表的 alarm／level 組合保留既有行為：`exception_type` 必須 exact match、不新增 level 限制；命中後使用 legacy automatic verified action，並繼續保護目前列的非 Pending ACTION。

### 4.3 多筆候選

候選依有效日期由新至舊排序；日期相同時以 `record_id` 由大至小作穩定排序。系統使用最新的有效候選，不會為了取得允許的 no-action ACTION 而跳過較新的人工處理紀錄。

### 4.4 ACTION 分類

以下三個 ACTION 視為已確認的 no-action 結果，比較時執行 trim 及 case-insensitive canonical comparison，回傳時仍使用既有 canonical 字串：

- `No action required (Verified within 1 year)`
- `No action required (Overshoot)`
- `No action required (Overlapping area)`

決策矩陣如下：

| 目前異常 | Database 結果 | Decision | 表格 ACTION |
|---|---|---|---|
| Stagger L3 | 命中 Stagger L3/L2/L1 | `auto_verified` | `No action required (Verified within 1 year)` |
| Stagger L3 | 未命中 | `keep_monitoring` | `Keep monitoring` |
| Stagger L2/L1 | 命中 Stagger L2/L1，既有 ACTION 在允許清單 | `auto_verified` | `No action required (Verified within 1 year)` |
| Stagger L2/L1 | 命中 Stagger L2/L1，既有 ACTION 不在允許清單 | `review_required` | proposed verified action |
| Stagger L2/L1 | 未命中 | `unmatched` | 保持 `Pending` |
| Low/High Height L2/L1 | 命中同一 Height family 的 L2/L1，既有 ACTION 在允許清單 | `auto_verified` | `No action required (Verified within 1 year)` |
| Low/High Height L2/L1 | 命中同一 Height family 的 L2/L1，既有 ACTION 不在允許清單 | `review_required` | proposed verified action |
| Low/High Height L2/L1 | 未命中 | `unmatched` | 保持 `Pending` |
| Wire Wear L2/L1 | 命中 Wire Wear L2/L1，既有 ACTION 在允許清單 | `auto_verified` | `No action required (Verified within 1 year)` |
| Wire Wear L2/L1 | 命中 Wire Wear L2/L1，既有 ACTION 不在允許清單 | `review_required` | proposed verified action |
| Wire Wear L2/L1 | 未命中 | `unmatched` | 保持 `Pending` |
| 任意類型 | 目前 ACTION 非 Pending | `skipped` | 保持原值 |

Stagger L3 的命中不依賴既有 ACTION，符合已核准的 Case 1 規則。

## 5. Version Difference 架構

### 5.1 容量契約

- 最多五個檔案：Latest、Previous 1、Previous 2、Previous 3、Previous 4。
- 每檔最多 320,000 個 `ChartData` 資料列，為約 300,000 列高峰保留少量餘量。
- 每檔最多 64 MiB。
- 五個 uploaded file payload bytes 的總和最多 320 MiB；multipart framing／headers 不計入此 application-level limit。HTTP server/body middleware 如另有 body limit，必須設定為高於 320 MiB 並為 framing 保留空間。
- 超出 byte limit 回傳 HTTP 413。
- 超出 row limit、缺少必要 Chainage，或 sparse work budget 超限時回傳 HTTP 422。
- Excel 無法讀取、格式或 extension 不支援回傳 HTTP 400。

錯誤 detail 必須指出檔案角色，例如 `previous_3 exceeds the 320,000 ChartData row limit`，讓前端可以直接向使用者呈現，不再退化為通用 `Network Error`。

### 5.2 Excel 解析

Version Difference parser 形成獨立邊界，不再把完整 DataFrame 轉成 Python column lists。

1. 使用 `UploadFile.file` 的 spooled file，而非 `await upload.read()` 建立完整 bytes copy。
2. `.xlsx`／`.xlsm` 使用 read-only streaming workbook parser；`.xls` 使用 pinned `xlrd` compatibility parser，受相同 byte guard 保護。傳統 `.xls` 自身最多 65,536 rows，因此仍低於本模組 row limit。
3. 只辨識：
   - `Chainage`
   - `height1` 至 `height4`
   - `stagger1` 至 `stagger4`
   - `wear1` 至 `wear4`
4. `Chainage` 為必要欄位。個別 metric 欄位缺失時，該 metric 回傳 partial/unavailable，維持現有 partial-result 行為。
5. 資料逐 row 放入 bounded/chunked numeric buffers；遇到第 320,001 個資料列立即停止並回傳 422。
6. Latest 解析後保留 compact prepared representation；Previous 檔案逐一解析、alignment、downsample，完成後立即釋放其 workbook、buffer 及中間陣列。
7. 不同 Previous 的結果只保留已壓縮、可序列化的 response，不保留完整 previous dataset。

Prepared representation 使用 normalized 0.25 m integer ticks、每個 metric 的四通道浮點陣列、finite mask、source row count 及有效 tick count。Latest 的 normalization 只執行一次並重用於四次 comparison。

### 5.3 Alignment

現有 scoring 契約保持不變：

- `STEP_M = 0.25`
- `max_shift_m = 50`
- 401 個 shift candidates
- 至少 100 paired values
- 至少 25 m span
- 至少達 maximum coverage 的 80%
- 以四通道各自 RMSE 按有效點數加權
- tie-break：normalized RMSE、絕對 shift、有效點數、shift direction

Normalized tick span 小於或等於 640,000 的資料使用 NumPy bounded-lag correlation：

1. finite mask、平方和及 cross-product 透過 NumPy FFT correlation 一次取得所有 bounded shifts 的 paired count 與 SSE。
2. 將符合有效點數、coverage 及 finite score 的候選按既有 tie-break 排序。
3. 按排序逐一使用現有直接 candidate calculation 驗證 span 及最終 RMSE；第一個完全合格候選為結果。
4. 小型資料的 shift、paired counts 必須與現行 direct scan 完全相同；RMSE／normalized RMSE 使用 `rtol=1e-8`、`atol=1e-8` 比較。

Dense correlation 的 hard limit 為 640,000 normalized ticks，即 160 km。Span 小於或等於此 limit 時必定使用 dense path；超過此 span 時必定使用 observed-tick sparse candidate path。Sparse path 的 hard work budget 為 `unique_observed_ticks × 401 <= 25,000,000` probes；小於或等於 budget 時必定計算，超出 budget 時必定回傳 422。Detail 包含角色、metric、tick span、observed tick count 及 limit。相同輸入不得因 runtime 狀態而在 result 與 422 之間改變。

Previous 中位於 Latest 可匹配範圍加減 50 m 之外的 ticks 不參與 candidate buffers，避免單一離群 previous Chainage 擴大工作陣列。

### 5.4 Response downsampling

Alignment shift、RMSE、coverage、overlap 及 difference 先使用完整有效資料計算。只有圖表 arrays 在序列化前被壓縮。

- 每個 comparison/metric 最多 8,000 個 display chainage points。
- 少於或等於 8,000 點時不壓縮。
- 壓縮使用 deterministic shared-index min/max envelope，Latest、Previous、Difference 的四通道使用同一組 chainage indices。
- 8,000 為不可超出的 hard cap。Anchor priority 為：首點與尾點、gap 邊界、bucket extrema。首尾先保留；若 unique gap-boundary candidates 超出剩餘 budget，按 chainage 排序後使用 deterministic evenly-spaced index selection 取滿 budget。只有仍有 budget 時才加入 extrema。其餘 index 分成連續 buckets；每個 bucket 由全部 returned series 提名各自 min/max index，再按相對該 series robust scale 的 normalized deviation 排序。Robust scale 定義為該 series 全部 finite values 的 `max(p95 - p5, 1e-12)`。保留該 bucket 配額內最高分的 unique indices；同分時保留較早 chainage。
- Response metric 新增：
  - `source_points`，定義為 downsampling 前的完整 output tick 數量
  - `display_points`
  - `downsampled`
- 現有 `chainage`、`latest`、`previous`、`difference` 欄位保留，因此 frontend 不需引入另一套 trace schema。

Backend 既有 GZip middleware 繼續負責 response compression。

## 6. Version Difference 前端狀態

Version Difference 主元件及仍保留的 History Compare legacy chart 使用相同 axis-state 規則：

- `xRange` 為所有 raw/difference plot 共用。
- `yRanges` 以穩定的 plot ID 保存，每張圖互不影響。
- `onRelayout` 同時處理 `xaxis.range`、`xaxis.autorange`、`yaxis.range`、`yaxis.autorange`；legacy subplot payload 的 axis alias 亦需支援。
- 更新 X 軸只更新 `xRange`，不得清除任何 `yRanges`。
- 更新某圖 Y 軸只更新該 plot ID。
- `Reset zoom` 同時清除共用 X 及全部 Y range。
- 切換 metric 或換入不同 response key 時清除全部 axis state。
- layout 與相關 axis 均使用穩定 `uirevision`。

API client 必須優先顯示 `error.response.data.detail`；只有沒有 HTTP response 時才顯示 network-level fallback。413/422 detail 會直接出現在 Version Difference error Alert。

## 7. Check 1 Year 後端設計

### 7.1 模組邊界

將 identity normalization、candidate eligibility、decision classification 及 response construction 移到獨立 pure rule module。Database layer 只負責：

- 取得 line/track candidates。
- 以單一 transaction 套用允許的 automatic writeback。
- 在 Save to DB transaction 中套用已核准的 review links。

此邊界讓完整決策矩陣可用小型 dictionaries 測試，不需要每一個規則測試都建立 SQLite fixture。

### 7.2 Check API contract

`POST /database/repeated-records/check-1-year` request 增加可選欄位：

- `section`
- `date_from`
- `date_to`

Response 增加：

- `checked_count`
- `match_count`，定義為 `auto_verified_count + review_required_count`
- `auto_verified_count`
- `review_required_count`
- `keep_monitoring_count`
- `unmatched_count`
- `skipped_count`

每筆 exception 增加 `check_1_year_status`。

所有 per-row statuses 的數量總和必須等於 response `exceptions` 數量。日期、位置、identity 或 level 無法解析的列使用 `skipped` 並附帶 machine-readable reason，不計入 `match_count`。

`auto_verified`：

- 回傳 canonical verified ACTION。
- 回傳 matched historical `exception_id` 作為目前列 `reoccurrence_id`。
- 在 Check transaction 中把目前 exception ID append 到 historical record。
- append 為 idempotent，會解析 comma-separated IDs、去重並保留既有順序。

`keep_monitoring`：

- 回傳 `Keep monitoring`。
- 不建立 historical recurrence link。

`review_required`：

- 原 `action`、`reoccurrence_id` 保持不變。
- 回傳 `proposed_action`、`proposed_reoccurrence_id`。
- 回傳 review proposal metadata：target `record_id`、target `exception_id`、observed ACTION 及 target version。
- Check transaction 不修改 target record。

`unmatched`／`skipped`：保持原資料。

所有 automatic writebacks 在同一 transaction 中完成。若同一 historical target 同時被 automatic result 及 review proposal 命中，系統先彙整並執行該 target 的 automatic idempotent append，然後重新讀取 target。Response proposal 的 target version 必須來自所有 automatic writes 後的狀態。任一 unexpected database error 會 rollback 整次 Check 的 automatic writes。

### 7.3 Review proposal concurrency

Review proposal 使用 target `record_id` 及 target version 作 optimistic concurrency guard。Target version 取 Database record 的 `last_updated`；如 legacy record 沒有可用 timestamp，使用由持久欄位建立的 deterministic version hash。Save to DB 時：

- target 不存在，或目前 target version 與 proposal 不同：回傳 HTTP 409。
- 409 不保存目前 batch，也不附加 historical IDs。
- 前端保留所有已接受但未保存內容，提示使用者重新執行 Check 1 Year。

### 7.4 Save to DB transaction

Save repeated records request 增加 `approved_recurrence_links`。每個 link 包含目前 exception ID、target record identity 及 target version。

Save to DB 必須在同一 database transaction 中：

1. 依 target `record_id` 將 approved links 分組；在任何 write 前，每個 unique target 只驗證一次 version。
2. 建立／更新目前 History Compare records。
3. 對每個 target 收集全部 current exception IDs、去重，並在單次 update 中 idempotently append。
4. commit。

任何步驟失敗會 rollback 全部 current records 及 historical links。

## 8. History Compare 前端設計

### 8.1 狀態

保留既有 `pendingChanges`，另外維護：

- `pendingReviewProposals`：Check 後尚未由使用者接受的 review proposals。
- `approvedReviewProposals`：已經 Save Edit 接受、但尚未 Save to DB 的 proposals。
- `check1YearSummary`：最後一次檢查的分類數量。

API 結果處理：

- `auto_verified` 及 `keep_monitoring` 直接更新 active comparison session。
- `review_required` 將 proposed ACTION／Reoccurrence ID 合併到 `pendingChanges`，proposal metadata 放入 `pendingReviewProposals`。
- `unmatched`／`skipped` 不修改列。
- `pendingChanges` 或 `approvedReviewProposals` 尚未處理時停用 Check 1 Year，要求使用者先 Save Edit／Discard，並在需要時完成 Save to DB；因此 Check 只處理穩定的 active-session values，也不會覆寫未處理的人工 edits。

### 8.2 視覺狀態

`review_required` row：

- 整列使用可讀的淺 neon-pink fill。
- 使用較強 magenta 左邊框。
- Pink review class 優先於 L1/L2/L3 row background。
- Proposed ACTION／Reoccurrence ID 使用現有 pending orange 語彙，但需提高前景對比以符合 WCAG AA。
- ACTION 或 Reoccurrence ID cell 顯示 warning icon／label，不能只以顏色表示需要複核。

表格上方顯示 persistent warning Alert，內容包含 review-required 數量並提醒使用者查看 Database Records。最後一次 Check 的其他分類以精簡 summary 呈現。

### 8.3 Save Edit、Discard、Save to DB

`Save Edit`：

1. 把 `pendingChanges` 套用到 active session。
2. 將對應 `pendingReviewProposals` 移至 `approvedReviewProposals`。
3. 清除 pink/orange pending review 狀態。
4. 顯示「已確認、尚未寫入 Database」數量。
5. 不呼叫 database write API。

`Discard`：

- 移除 staged proposed values 及其 pending proposal。
- 恢復執行 Check 前的原始 ACTION 與 Reoccurrence ID。
- 不影響先前已存在的 manual session values。

`Save to DB`：

- 有任何 unresolved `pendingChanges` 時停用，tooltip 說明需先 Save Edit 或 Discard。
- 將 `approvedReviewProposals` 放入 save request。
- 成功後清除 approved proposals 及 unsaved indicator。
- 失敗或 409 時保留 session data 及 approved proposals，讓使用者修正或重試。

Selection、Batch Edit、filter、Export、chart navigation 及既有 ACTION option 保持不變。

## 9. About、操作指南與開發者參考

About 模組沿用現有 tabs、section navigation、visual guide 元件及 Material UI 組件。

更新內容：

1. 模組總覽加入 Version Difference 的用途及最多五個 cycle roles。
2. 操作指南加入：
   - 檔案角色及必要 ChartData 欄位。
   - 50,000 日常列數、320,000 hard row limit、64 MiB/file、320 MiB/request。
   - X 同步、Y 獨立、Reset zoom。
   - Downsampling 只影響顯示，不影響 alignment statistics。
   - 413／422 錯誤的處理方式。
3. Check 1 Year 操作指南加入：
   - 365 日 window。
   - family／level／ACTION matrix。
   - Pink review row、orange proposed field、warning icon。
   - Save Edit、Discard、Save to DB 的不同作用。
4. 更新 One Year window visual 及 decision flow visual。
5. Developer Reference 加入：
   - Version Difference API limits、recognized columns 及 response metadata。
   - Alignment prepared representation、bounded-lag calculation 及 downsampling contract。
   - Check decision statuses、counts、proposal metadata、409 concurrency 及 atomic save contract。

文件使用既有中英混合慣例及既有 typography／spacing，不新增另一套 visual system。

## 10. 錯誤處理

### Version Difference

- 400：extension／workbook 無法讀取。
- 413：單檔或總 request bytes 超限。
- 422：Latest 無 ChartData、缺少 Chainage、row limit、無可用 metric、異常 sparse/span。
- Partial previous／metric 仍使用現有 `unavailable` result，不令整個 request 失敗。
- 前端保留已存在 response 時，可同時顯示新的 role-specific error。

### Check 1 Year

- 400：exceptions 為空。
- 422：filter 日期無法解析或有效 window 為空。
- 409：approved review target 在 Check 後已變更或刪除。
- 500：unexpected database error；automatic Check writeback 或 Save transaction 全部 rollback。

## 11. 測試與驗收

### 11.1 Version Difference backend

- Parser 只輸出 recognized columns。
- 320,000 rows 接受；第 320,001 row 回 422。
- 64 MiB/file 及五個 file payload sum 320 MiB boundary tests，另驗證 multipart framing 不計入 application-level sum。
- Latest normalization 在四個 comparisons 間只執行一次。
- Previous 逐檔釋放，不把全部 full datasets 放入 response state。
- Direct-scan golden tests 比較 shift、RMSE、normalized RMSE、coverage、overlap 及 difference。
- NaN、duplicate ticks、ascending／descending chainage、missing metric、partial workbook。
- Span 小於或等於 640,000 ticks 必定走 dense path；較大 span 且 sparse work budget 合格時必定走 sparse path；超出 budget 時必定 422。
- Downsampled metric 不超過 8,000 points，保留 gaps、首尾及各通道測試 spikes。
- 五個 50,000-row workbooks 的 slow/API smoke test。
- 單個約 300,000-row workbook 的 slow/parser-alignment test。
- 五個各約 300,000-row workbooks 的 manual/resource acceptance benchmark；必須完成四個 comparisons、維持 bounded response、且不得因 process OOM 或 connection reset 失敗。此極端案例不作一般 CI 的 wall-clock gate。
- 使用實際大型 fixtures 執行手動 benchmark，記錄總時間、response bytes 及 process RSS；不以容易受機器影響的嚴格 wall-clock threshold 作一般 CI gate。

### 11.2 Version Difference frontend

- 先調整 Y，再調整 X，Y range 保持。
- X range 同步到所有 plots。
- 每張圖 Y range 獨立。
- `xaxis.autorange` 只重設 X；`yaxis.autorange` 只重設來源 plot Y。
- Reset 清除 X 及所有 Y。
- metric／response change 清除 axis state。
- 413／422 detail 正確呈現。
- 五個 cycles 的 traces 及 layer controls 保持正常。

### 11.3 Check 1 Year backend

- Stagger Left／Right 雙向匹配。
- Low Height 不匹配 High Height，反之亦然。
- Stagger L3 可匹配 L3/L2/L1，且不依賴既有 ACTION。
- Stagger L2/L1 不匹配 L3。
- Height／Wire Wear L2/L1 level scope。
- 三個允許 ACTION 各自 auto verify。
- 其他 ACTION 產生 review proposal，且 Check 不寫 DB。
- 未命中 L3 產生 Keep monitoring；未命中 L2/L1 保持 Pending。
- 非 Pending current ACTION 保持不變。
- 365 日兩端、location 兩端、self-match、section、line/track、filter narrowing。
- 多候選選最新，日期相同以 record_id 穩定排序。
- Automatic append 及 approved append 均 idempotent。
- 同一 target 同時出現 automatic writeback 與 review proposal時，proposal 使用 post-automatic-write version。
- 同一 target 有多個 approved links 時只驗證／更新一次，並附加全部去重 IDs。
- 409 concurrency guard 及全 transaction rollback。

### 11.4 History Compare frontend

- 各 decision status 正確映射。
- Review row 套用 pink class 且優先於 level class。
- Proposed fields 為 orange 並有非顏色 warning affordance。
- Warning Alert 顯示正確數量。
- Save Edit 移動 proposal、清除 review styling，但不呼叫 DB。
- Discard 恢復原值且不寫 DB。
- 有 unresolved pending changes 時 Save to DB disabled。
- Save to DB payload 包含 approved links。
- Success 清除 approved state；409／error 保留 state。
- 現有 manual edit、selection、Batch Edit、filter、Export 不回歸。

### 11.5 About

- Version Difference section 可由 guide navigation 到達。
- User guide 顯示 limits、zoom semantics 及 error guidance。
- Check decision matrix 及 staged workflow 內容存在。
- Developer Reference 顯示 API contract、metadata 及 concurrency behavior。

### 11.6 驗證命令

- Backend targeted tests，之後執行完整 backend test suite。
- Frontend targeted Vitest，之後執行可行的完整 frontend suite。
- TypeScript check 及 production build。
- 所有 root `npm`／`npx`／`npm exec` 命令只在 canonical checkout 執行，並為該 process 設定 `NODE_USE_SYSTEM_CA=1`；不得關閉 TLS 驗證。
- 完成程式碼新增／移動後重新 index codebase-memory，並在提交前驗證受影響 scope。

## 12. 實作順序

1. 建立 regression tests，鎖定 Y range、現有 alignment golden output 及新的 recurrence matrix。
2. 完成 Version Difference streaming parser、容量 guard、prepared representation、bounded alignment 及 downsampling。
3. 完成主圖及 legacy 圖的 axis-state 修正，並整合 role-specific errors。
4. 建立 pure recurrence rules，調整 Check API response 及 automatic writeback。
5. 完成 History Compare pending／approved review state、row styling、notice 及 Save transaction。
6. 更新 About、操作指南、visuals 及 Developer Reference。
7. 執行 targeted、full、large-data benchmark、build 及 codebase-memory impact verification。

## 13. 相容性與移交

- Version Difference 現有 request roles 及主要 response arrays 保留；新增 metadata 為 additive。
- Missing previous ChartData／missing metric 的 partial-result 語義保留。
- Check response 的既有 `status`、`message`、`match_count`、`exceptions` 保留，新增分類 counts 及 per-row status。
- Manual ACTION protection 保留。
- 不涉及新的 packaged runtime asset，因此不需要修改 `package.json build.extraResources`。
- `PRODUCT.md` 與 `DESIGN.md` 已審閱並維持不變。
