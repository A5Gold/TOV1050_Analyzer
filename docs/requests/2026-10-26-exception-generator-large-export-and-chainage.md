# Exception Generator 大型資料匯出、進度與里程圖表

- 日期：2026-10-26
- Linear project：TOV1050_Analyzer
- Linear issue：[DAV-23](https://linear.app/david-chu/issue/DAV-23/exception-generator大型-twl-excel-匯出效能真實進度與里程折返診斷)
- 負責人：Codex
- 狀態：Done（設計與測試提案先完成並獲批准，實作與本機整檔驗收完成；未提交／封裝／發布）

## 需求與目的

### 使用者與流程

使用者載入 TWL 約 84 萬列、23 欄 CSV，可分析並顯示圖表及例外表，但匯出含 ChartData 的 Exception Report 超過五分鐘仍無檔案且 Electron console 報錯。約五萬列的部分檔可在約三十秒匯出。要求改善一般 100MB raw CSV 的分析／匯出效能、顯示百分比進度、評估 timeout，並調查同 channel 同 chainage 多值／折返。

### 商業規則與限制

- detector、threshold crossing、overshoot、exception peak 及完整報表保留完整有效 raw rows；降採樣只供前端圖表。使用者另批准的精簡報表可按第 7 節生成 derived mean，不取代 raw。
- Chainage canonical unit 為公尺。不得以取平均／去重靜默刪除量測或噪聲峰值。
- overview 保留 first/last、各量測欄 extrema、exception chainage、FromM/ToM；detail 可回查原始資料。
- 保留多分頁 session isolation、metadata、檔名、欄序、數值精度及既有 UI 工作區修改。
- 不覆寫來源 CSV、參考 workbook 或使用者既有輸出；診斷產物另存 outputs。

## 實作前現況盤點（歷史診斷）

- 相關程式碼：backend/app/api/endpoints/analysis.py、backend/app/core/exporter.py、backend/app/core/chart_sampling.py、frontend/src/views/ExceptionGeneratorView.tsx、frontend/src/components/ChartComponent.tsx、frontend/src/api/client.ts。
- 資料流程：POST /analyze → session raw frame + overview payload；POST /export/report/generate → 完整 session raw frame → ExcelExporter → XLSX response。
- 現行 TOV1050 超過 50,000 retained rows 已走 write-only writer；逐 cell 建立 WriteOnlyCell／格式化仍需量測。生成在 async endpoint 同步執行，並在完成後才回傳 XLSX。
- Codebase Memory MCP 已掛載且 repo 已索引；部分 snippet 行號與現行檔案不一致，須以工作區內容驗證。
- 來源：00 Reference Document/Raw data/TWL/test file full.csv（117,229,324 bytes）；test file partial.csv（7,073,160 bytes）。
- 截圖：01 Screenshot/zigzag graph.png。部分原始 CSV 最前面已直接存在相同 Km、多筆不同量測值，需統計與比對。
- 現有測試：chart sampling、analysis chart-data、API analysis、export field injection、raw generate、frontend Exception Generator。
- 已有未提交修改：ExceptionGeneratorView.tsx／其測試、metadata workbook、前次 request 與大量參考／驗收產物；本工作不還原或混入。

## 設計

### 範圍

完成診斷後提出下列具體設計，使用者已回覆 approve；其後要求實作前必須備妥設計與測試提案，已依此順序完成。詳細介面、生命週期、測試矩陣及實作順序見 [設計與測試提案](2026-10-26-exception-generator-design-and-test-proposal.md)。下列比較保留當時提案；實作及驗收結果見後段。

### 方案比較與建議

1. **建議：現有 writer 優化＋背景工作＋真實進度＋散點顯示**。保留 openpyxl 與既有 workbook 契約，先消除逐 cell 重複格式建構、每 bucket 重複 pandas slicing／conversion，以及每個保留里程的全量排序。背景工作解決長 HTTP 與狀態查詢阻塞，散點顯示解決真實一對多里程被連成折返線的問題。需增加工作狀態與生命週期測試。
2. **只延長 timeout**。改動最少，可暫時用 30 分鐘作診斷容忍值，但不會加速或提供進度，不能保證避免記憶體／生成錯誤，不作正式方案。以 partial 57.53 秒線性推估 full raw rows 約 16 分鐘，只是容量估算，並非完整檔實測或 SLA。
3. **更換 XLSX engine／增加 native XML dependency**。提案時列為第二階段候選，後已完成隔離 lxml／XlsxWriter 概念評估，本輪不採納；量測及相容性限制見設計提案第 8 節，不外推 full 收益。

### 建議設計：背景工作及資料正確性

- Exception Generator 的分析與 Report export 使用短 HTTP create → job status polling → result/download；不讓一次 HTTP 等待整份 workbook。保留舊 API 相容路徑。
- 共用單一有界 worker executor 執行同步工作，狀態查詢保留在 event loop；限制同時執行大型工作數，排隊狀態明確顯示。單純把同步函式放進 async background task 不足以解決阻塞。
- job 綁定 client_session_id、分析 revision 與當次 raw snapshot；重新分析／切分頁不得改寫既有 job 的輸入。建立 snapshot 後不在 worker 修改共享 DataFrame／exception objects；需要寫入時只複製必要小資料。
- 新匯出流程缺少完整 raw snapshot 時回傳明確重新分析錯誤，不能以 overview chart_data 靜默代替完整 ChartData。
- XLSX 寫入 job 專用暫存檔，完成後獨立下載；取消／失敗／過期時清理，進行中下載不刪檔。完成檔保留期限與工作逾時獨立處理。
- 既有 openpyxl writer 預計算欄位及共用格式，保留所有 raw rows、欄序、Summary／各例外 sheet、hidden metadata、0.#### 顯示及完整數值精度。不做 raw 去重或平均。

### 建議設計：進度及錯誤

- 每個 session 保存 job identity/status，切換分頁／離開 view 後不得把舊 job 結果套到新分析。
- 回報 stage、processed、total、unit、elapsed、狀態與可讀錯誤。CSV reading/cleaning 依實際 bytes／rows，detector 依已完成通道／工作階段，chart 依已處理 buckets，Excel 依已寫列計算「該階段百分比」。
- UI 明確標示階段百分比，不把不同工作量當作等時進度。ZIP finalize／總量未知階段顯示不定進度與已經過時間；workbook 完成才標 ready，下載另顯示狀態。禁止假計時進度或寫列完成即宣稱下載完成。
- create／poll 使用短 timeout；單次 poll 失敗可重試且不自動重建 job，生成錯誤、cache 過期、逾時與下載失敗分開顯示。工作上限需完成 full 實測後決定，沒有可保證成功的通用最大 timeout。

### 建議設計：分析效能與圖表

- **使用者2026-10-26補充**：CSV來源系統截掉Km下一位小數，連續十筆相同Km對應十個連續更精細的位置；DATAC無此限制。因此同Km多值應解讀為來源座標精度損失，不是同一實際位置重複測量。使用者範例9.99980…9.99989為遞增示意；實際TWL開頭每10筆由9.9998降到9.9996再到9.9994，顯示方向／步距仍需確認，不能直接按示例+0.00001km補位。
- 保留CSV原Km及sample identity；未驗證座標還原規則前不改canonical Chainage／metadata mapping／例外位置。若後續提供可驗證的重建規則或同次DATAC，另明確記錄derived chainage、方法與provenance；不可將估算座標冒充原始精度。散點為目前忠於CSV精度的顯示方案，非最終否定可重建座標。
- sampler 先將量測欄位轉成 NumPy arrays 一次，再依既有 source-position bucket 計算 extrema；維持 first/last、各 channel min/max、boundary／exception chainage，保留真實列及原順序。
- 保留里程查找避免每值全量 argsort；對重複與等距候選明確固定真實來源列的決定規則並回歸驗證，不對 detector／export 套用任何 sampling。
- 預設 overview 使用現有 envelope 選出的真實量測散點，避免按非單調 x 連出折返線；例外峰值另保留精確 marker。提供原始採樣順序線的查核模式，清楚說明 raw chainage 可回跳。
- 任意 zoom 經 debounce 請求 session/revision 對應 detail window；取消／忽略過時回應。細節保留原始散點，hover 包含 source_row_number／SampleCount；單窗過大仍標示 envelope 而非誤標 raw。
- raw 查核模式不承諾同里程只有一個 y；不全域排序再連線，不改 raw 或原始 Km。預設 derived mean 模式按已批准規則平均並保留 min/max/count，不跨 context／metadata／pass 合併。

### 不在範圍

不變更 detector 商業判定、不修改 raw data／metadata、不重構無關模組、不封裝／發布。

### 資料流與錯誤處理

匯出必須維持 session raw source；進度需代表實際階段／工作量。缺少來源、生成失敗及下載失敗要可區分，不能用假計時百分比掩蓋錯誤。評估避免長時間 HTTP request 與 backend event loop 阻塞。

### 驗收標準

1. 完整與部分 TWL 匯出可讀、ChartData 行數及各量測值與完整有效 raw frame 相符；metadata／exception 欄序與精度相容。
2. 記錄分析、圖表、匯出時間與 peak memory；大型資料無遺失／截斷。
3. 進度包含實際階段、已完成／總量及百分比，生成／下載／錯誤可辨識。
4. 解釋重複 chainage 的來源；圖表避免跨不同掃描段折返，保留噪聲 extrema 與例外點的真實數值及 detail 查核。
5. 完成針對性的 backend／frontend 回歸驗證並記錄實際命令；timeout 建議以量測為依據。

## 執行紀錄

### 實作

已先完成設計／測試提案並同步 DAV-23，再依使用者 approve 實作。使用者其後明確選擇「圖表與精簡匯出取平均；例外偵測保留原始值」。本文件前段為診斷當時的方案比較；若與平均化決策衝突，以設計提案第 7 節及以下實作摘要為準。既有 ExceptionGeneratorView 與其測試的 sticky Start Analysis 修改已保留。

- 新增背景分析及匯出 jobs：短請求建立／查詢、單一 worker 與一個排隊名額、真實階段計數、合作取消、固定 session/revision、完成檔案獨立下載與 TTL／下載租約清理。
- 同 canonical Chainage／context／metadata／SampleCount pass 建立獨立平均資料，保留各 channel min/max/valid count、來源範圍及聚合版本；不按固定十列切分，也不改寫來源 Km。
- 圖表預設平均散點，可顯示原始 min/max、raw detail 及原採集順序線；例外 marker 一律使用完整 raw 偵測結果。縮放使用 revision 快取、單一 detail limiter、debounce、abort 及過時回應隔離。
- 完整報表保留 31 欄完整 raw ChartData；新增 `_ChainageMean` 精簡報表及 ChainageStatistics；writer 共用格式並串流寫檔，僅圖表 payload 可 downsample。
- UI 顯示階段百分比／未知總量進度、重試原工作、取消與重新下載；分析期間鎖定設定，結果工具列可換行。Raw CSV 生成移至 threadpool。

### 測試與 debug

已檢查 git status、最近五次 commits、PRODUCT.md、DESIGN.md、architecture 及既有完整 raw export contract，並完成截圖、CSV及現行程式診斷。

#### 2026-10-26 診斷證據

- 使用者確認執行 `npm run dev`；Vite `timeout`／`proxyTimeout` 均為 300000ms，因此適用本次執行環境。尚未收到 console error 文字或完成 HTTP 重現，五分鐘限制是吻合的失敗因素，不能斷言為唯一根因。axios instance 無 timeout。
- 原有 `outputs/exception-performance-2026-10-26/diagnose.py` 程序及產物在接續前已存在；本次未啟動／停止該程序。讀到 partial：51,170 raw rows → 50,904 retained rows，analysis 80.809s、export 57.530s、5,979,458-byte XLSX。full 程序後來退出且 log 沒有 full analysis_done／export_start，原因未明，不能聲稱完整分析或匯出成功。
- 子代理以 openpyxl read_only 檢查原有 partial XLSX：ChartData 50,904資料列、31欄，首／末 chainage 9997.8／9002.2，格式 0.####，_Metadata 隱藏。尚未做完整逐格 raw equality。
- 診斷時環境 openpyxl 3.1.5、LXML=False。production／venv／requirements 未新增依賴；後續僅在 outputs 隔離 target 安裝 lxml 6.0.2、XlsxWriter 3.2.9 作評估，未套用到本次成品。短測 2,000×31 欄、BytesIO：逐 cell number_format 6.297s，共用預建 style 3.111s；單次、順序與暖機未控制，不能推論 full 加速倍數。
- 原始 CSV inline pandas 欄位統計（未 trim）：partial 51,170 rows，里程相鄰上升19／下降5,091／相等46,059，distinct chainage 4,974；full 843,623 rows，上升495／下降83,853／相等759,274，distinct chainage 82,516。
- 使用者解釋重複Km來自來源系統截位；上述統計只反映CSV可見座標，不表示同一真實位置多次量測。截位本身不能解釋下降序列中1–2m級向上回跳，需分開查核。
- 9120–9145m 兩檔皆1,720 raw rows、6次相鄰上升。partial CSV第43922列（含header）9138.4→9140.4m，SampleCount 392469→392470。這證明來源定位回跳，不能直接認定列車實際倒退。
- 9144.2m 共30 raw samples，HeightWire1 3998.031–3998.780mm；9138.4m也有3999.381／4010.874mm等真實多值。raw／detector 必須保留各值；獨立 derived mean 可按已批准規則平均並保留 min/max/count。
- 對既有9137–9145m保存窗口850 rows呼叫現行 sampler（max_points=200），500個回傳點的 chainage／height1／stagger1／wear1 與來源列完全一致、順序保留，仍有6次上升；envelope沒有創造假x/y，現有scattergl lines連線放大折返視覺。
- 目前僅既存程序觀察到約1.08GB RSS，非 peak RSS；尚無可信完整效能基線或性能 SLA。
- 子代理 inline Python：partial loader 50,904 rows 1.239s、metadata coverage 1.791s（class／track 皆0缺口）；10,000 rows／600 buckets／14 numeric fields／16 preserve 的 cProfile 耗時7.959s（含profile成本）。3,082,947 calls，其中iloc/take cumulative3.83s、8,401次to_numeric cumulative1.91s，支持重複pandas操作為熱點；不能將profile時間當無儀器正常耗時。

實際執行的既有契約基線測試：

```text
.\venv\Scripts\python.exe -m pytest -q backend/tests/test_tov1050_report_export.py backend/tests/test_chart_sampling.py
8 passed in 14.97s
```

#### 實作後驗證計畫

- Backend：既有 report／chart sampling／analysis session tests；新增真實進度、event-loop可回應、snapshot/revision isolation、排隊、失敗／逾時／清理、缺少raw拒絕匯出及下載完整性測試。
- Frontend：進度百分比與未知階段、錯誤／重試、切分頁、防止舊回應覆蓋、重複x／反向x／缺值／極值、zoom detail／exception marker。
- 真實 partial與full：分階段wall time、processed rows、RSS觀察、HTTP路徑、Excel ZIP完整性與所有ChartData數值逐列對照；Summary／例外結果與修正前語意相同。full沒有完成前不能宣稱修復。

### 驗收結果

實作及 partial/full 真實 HTTP 匯出驗收已完成，完整 raw 與最終精簡成品均通過全列核對。實際 Electron console 錯誤仍未取得；不得把五分鐘 proxy 判為唯一根因。瀏覽器 QA 使用 API fixture，真實大型 API／下載另在 localhost HTTP 驗證，沒有宣稱已完成使用者 Electron 手動 UAT 或封裝驗收。

#### 實作後已執行的回歸（2026-10-26）

```text
.\venv\Scripts\python.exe -m pytest -q backend/tests/test_analyzers.py backend/tests/test_analyzers_task_run_data.py backend/tests/test_detection.py backend/tests/test_tov1050_adapter.py backend/tests/test_export_raw_generate.py backend/tests/test_tov1050_report_export.py backend/tests/test_chainage_aggregation.py backend/tests/test_chart_sampling.py
85 passed in 39.26s

.\venv\Scripts\python.exe -m pytest -q backend/tests/test_background_analysis_jobs.py backend/tests/test_analysis_chart_data.py backend/tests/test_api_analysis.py
30 passed in 31.21s（含最後 revision cache／detail limiter／Raw CSV event-loop 回歸）

npx vitest run src/views/__tests__/ExceptionGeneratorView.test.tsx
8 passed（含最後顯式鎖定設定補充，單一 threads worker 重跑）

npx vitest run src/components/__tests__/ChartComponent.test.tsx
6 passed

進度與 analysisJobs 兩檔測試：5 passed
npx tsc --noEmit：exit 0
npm run build：exit 0（既有 browser externalization／xlsx import／bundle size warnings）

$env:TOV1050_E2E_URL='http://127.0.0.1:5179'; npx playwright test tests/exception-generator.spec.ts --reporter=line
3 passed (1.1m)，viewport 1280×720／1033×640／390×844
```

瀏覽器測試首次冷載入在 1280×720 的 page.goto 超過 30 秒，其餘 2 項通過；Vite 暖機後重跑 3 項皆通過。最後 View 測試曾遇 Vitest fork worker 啟動逾時（未執行測試），改單一 threads worker 重跑，8 passed in 142.16s。上述環境失敗保留紀錄，不列為通過。

#### 真實 HTTP 驗收

最後補充回歸：

```text
.\venv\Scripts\python.exe -m pytest backend/tests/test_background_analysis_jobs.py -q
22 passed in 11.82s（原 17 項加 5 項 Windows 鎖檔／lifespan）

.\venv\Scripts\python.exe -m pytest -q backend/tests/test_analysis_chart_data.py backend/tests/test_api_analysis.py
13 passed in 22.40s（最後 lifespan 修正後）
```

原生 `SampleCount [n.]` alias、finite reset pass、統計 first/last 及 hidden metadata 共 11 項相關測試通過；未改 raw。兩份原始 CSV 的有限 counter 無下降，獨立紀錄於 `counter-alias-audit.json`；最終 full 精簡成品另由 batch-jobs-02 補驗，避免把執行中的 batch-jobs-01 舊 counter metadata 當成最終版。

真實 React／Plotly／WebGL QA（資料由 API fixture 提供）：最初 390×844 因固定側欄遮擋控制項失敗，低高度 y 軸標題亦重疊；已修圖表最低 540px、graph 區捲動、窄寬上下清單，保留 Table 原本 bounded layout。最終三尺寸 1280×720／1033×640／390×844 全通過，含 mean/minmax/raw、raw exception peak、滑鼠縮放、stale detail、Graph/Table 切換、控制項可操作、無 pageerror／非法軸 warning；文件與截圖在 `browser-qa-2026-10-26T03-30-55-667Z/`。6 項 Chart tests（含 counter hover）及最後 TypeScript exit 0。測試用 Vite 5179 服務已停止，未停止使用者原有程序。

執行腳本：`outputs/exception-performance-2026-10-26/batch-jobs-01/validate_http_jobs.py`。以真實 localhost FastAPI HTTP 執行建立／poll／結果／下載，獨立 NumPy oracle 核對每組每 channel mean/min/max/count；驗證項目含 XLSX ZIP、31 欄 ChartData、統計、Summary／例外、hidden metadata／revision 及 raw hash。partial 兩種報表與 full raw 全部核對通過；batch01 full 精簡 ChartData 通過，統計首次於空字串表示失敗，另以 batch02 補驗，不能將原批次列為全通過。數值容差為 XLSX `rtol=1e-14, atol=1e-9`，均值 oracle `rtol=1e-13, atol=1e-9`。

- partial 暖機：50,904 retained → 4,949 groups；分析 5.99s，完整報表 70.98s，精簡報表 42.42s，兩份逐列驗證通過。
- partial 正式：50,904 retained → 4,949 groups，分析 14.40s；完整報表 98.03s／5,979,989 bytes，驗證 54.93s；精簡報表 43.22s／2,568,453 bytes，驗證 27.17s。兩份逐列核對均通過，該 case sampled peak RSS 209,567,744 bytes。
- full 來源 843,623 rows／117,229,324 bytes；分析 94.11s，838,859 retained → 82,144 groups（約 10.21 倍列數減量）。完整報表成功生成並下載，98,655,329 bytes、1310.18s；下載 13.09s，838,859 列全部核對通過（驗證 626.26s）。batch01 舊精簡已生成 42,769,806 bytes／job elapsed 336.766s，其統計 86 欄缺 SampleCount_first/last，metadata 缺 sample_counter_column；不能視作最終 88 欄契約。兩檔 counter 無 reset，舊均值分組不受 alias 修復影響。最終結果由 batch02 另記。
- Python 3.12.8／pandas 2.3.3／openpyxl 3.1.5／LXML=False；本次未新增 XML／XLSX engine 依賴。並行開發及測試負載未控制，因此結果是本機觀測，不能據此宣稱嚴謹加速倍數或 SLA。
- RSS 每 250ms 取樣；範圍包含同程序 server、HTTP client 及驗證，並非純 server 峰值。沒有可信舊版 full detector baseline；以完整 raw snapshot、既有 detector 契約及例外 writer 契約核對，不冒稱完成歷史 full 等價比較。

首次 full 精簡統計驗證未通過：`Last Pole Code [---]` 的來源空字串在 XLSX 讀回為 None，驗證器未處理該 Excel 空白表示。原 batch-jobs-01 events／失敗保持不改，不產生冒充成功的 summary；完整 raw 成功紀錄不受影響。後以 batch-jobs-02 的精確空字串規則（只接受 expected==空字串與 actual None，不正規化空白字元或數值），先合成 smoke，再以同完整 raw 重驗舊 compact 及最終 counter alias 成品，均通過。最終生成走真實 HTTP export jobs，狀態每次 latency 即時存盤；原 batch 的 LATENCIES 因異常未保存，不能從 poll 間隔猜造 p95。

#### 最終 batch-jobs-02 驗收（exit 0）

```text
.\venv\Scripts\python.exe outputs/exception-performance-2026-10-26/batch-jobs-02/validate_final_compact.py --write-compact --existing-compact outputs/exception-performance-2026-10-26/batch-jobs-01/full-normal-chainage_mean.xlsx
```

- full 重載分析 90.22s；獨立 NumPy 分組／各 channel mean/min/max/count／來源列／counter 範圍核對 15.73s，838,859 raw → 82,144 groups。原生 SampleCount [n.] 的有限值無下降，整體 first=214／last=843636。
- 舊 compact 86 欄全列補驗通過，223.27s；只明確容許既知的兩 counter 欄缺失及舊 metadata 差異，不把舊 schema 當成最終契約。
- 最終 compact 生成 367.51s（約 6 分 8 秒），下載 4.79s；43,675,125 bytes。ChartData 82,144 列 ×31 欄、ChainageStatistics 82,144 列 ×88 欄、Summary／各例外／hidden metadata／ZIP 全部核對通過，讀回驗證 196.43s。
- HTTP create 0.027s；340 次 status 查詢 median=0.0543s、p95=0.0979s、max=0.1540s，均 200。這是該次 localhost client request wall time（含排程／GIL），不代表遠端網路或全機負載 SLA。
- raw frame 及各 exception frame digest 在聚合／匯出前後一致；完整來源 CSV 與 TWL metadata 最後 SHA256 亦與執行前一致，見 final-source-integrity.json。
- 最終成品 SHA256：a83f96b145f312cc87287601240ddfa5b235a4c28cfb4dc2d9470a219324c960。成功摘要 full-summary.json；原批次部分成功與失敗摘要 batch01-recovered-summary.json，原始 events／失敗未修改。
- batch01 每 250ms 抽樣的同程序 server＋client＋驗證 sampled peak RSS=1,078,661,120 bytes，不能稱純 server peak；batch02 沒有另量 peak RSS。完整報表仍約 21 分 50 秒，精簡約 6 分 8 秒；純 Python writer 仍為效能限制，未宣稱整體加速十倍。
- 最後 git diff --check exit 0，只有既有 LF／CRLF 提示。測試用服務與 batch02 HTTP server 已停止，未停止使用者原程序。

## 操作與 timeout 說明

- 重新啟動開發服務後使用新流程。分析及 Excel 生成以背景工作進行；建立／查詢請求各有 30 秒網路限制，並非整個工作的生成期限。Vite 原本 300 秒長請求限制不再決定背景生成是否完成。
- 「完整報表」保留所有 retained raw ChartData；「精簡報表（同里程平均）」以同里程／context／metadata／pass 的各 channel 均值輸出，另保留來源範圍及 min/max/count。兩者的例外結果均使用完整 raw，原始 CSV 亦不改寫。
- 進度顯示本階段已處理／總量與百分比，換階段可重設；沒有可信總量時顯示不定進度與經過時間。`finalizing` 完成前不能視為可下載。
- 網路查詢失敗可按「重試查詢」接續原工作，不重建報表。完成後下載失敗可重新下載；終止工作檔預設保留 3600 秒，過期需重建。
- 可在啟動 backend 的同一程序環境設定 `TOV1050_JOB_TIMEOUT_SECONDS` 為正秒數，未設定時無硬執行上限；`TOV1050_JOB_TTL_SECONDS` 控制終止工作的保留時間。取消／逾時於安全檢查點生效，不會強殺正在寫 ZIP 的 thread。依本機完整報表 1310.18 秒實測，若必須設執行上限，建議先以 3600 秒為保守起點；這不是最大安全時間，也不保證所有電腦或更大資料都能完成。本次沒有修改使用者的環境設定。
- 圖表預設同里程平均散點；開啟 Raw min/max 可查原始範圍，切 raw detail 查個別樣本。原序線模式仍可能顯示 CSV 座標回跳及截位造成的折返。例外 marker 使用原始峰值，因此不必落在平均點上。

## Linear 同步紀錄

- 同步紀錄：已透過 Linear MCP 建立 DAV-23（In Progress），連結本需求紀錄（working tree 尚未提交），並以留言同步子代理診斷、具體設計及 next action；2026-10-26 接續更新設計與測試提案。
- 工具狀態：起初未掛載，曾標記 Linear sync blocked；之後實際工具清單出現 mcp__linear，已成功查詢 project/issues/statuses 及建立 issue，阻塞解除。
- 完成條件已達：partial/full 兩模式成品、最終 alias、數值與原始極值、生命週期、回歸及真實 Plotly QA 均驗收。DAV-23 同步最終結果並設 Done。使用者下一步：重啟 npm run dev 後作實際 Electron UAT；完整 writer 進一步加速可另立後續工作。
- 阻塞／需要決策：無新的核准阻塞；缺少實際 Electron console 錯誤及 full 成功基準仍為診斷限制，不能將五分鐘 proxy 視為唯一原因。
- 相容 API 限制：本次 snapshot/revision 保證針對新版 Excel jobs／detail。既有 Raw CSV 僅 session、舊 GET /export/report 仍走 legacy writer；現代前端未用舊 GET，沒有將所有歷史 API 宣稱為不可變快照契約。

## 相關檔案

- 本需求紀錄為本次新增未提交檔案。
- 詳細設計及測試矩陣：`2026-10-26-exception-generator-design-and-test-proposal.md`。
- 修改：backend 的 analysis.py、analyzers.py、tov1050_data_ingestion.py、chart_sampling.py、tov1050_report_export.py、main.py；新增 background_jobs.py、chainage_aggregation.py。測試包含 test_tov1050_report_export.py、test_background_analysis_jobs.py、test_chainage_aggregation.py。frontend 修改 ExceptionGeneratorView／ChartComponent／TaskLoadingState／useAnalysisStore／types/api，新增 api/analysisJobs.ts 及 View／Chart／進度／API 測試；瀏覽器驗收腳本為 tests/exception-generator.spec.ts、tests/exception-chart-browser-qa.mjs。需求／提案、驗收 scripts／產物亦未提交。既有 dirty files 保留，沒有封裝或發布。
- 同工作區另有預先存在的同主題 request `2026-10-26-exception-generator-large-export-and-chart.md` 及 diagnose.py／outputs；保留不覆寫，本次整合以本文件與DAV-23為準。
