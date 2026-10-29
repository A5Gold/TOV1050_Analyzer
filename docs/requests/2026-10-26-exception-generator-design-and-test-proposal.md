# Exception Generator：實作前設計與測試提案

- 日期：2026-10-26
- Linear：[DAV-23](https://linear.app/david-chu/issue/DAV-23/exception-generator大型-twl-excel-匯出效能真實進度與里程折返診斷)
- 需求與診斷依據：[需求紀錄](2026-10-26-exception-generator-large-export-and-chainage.md)
- 狀態：本提案先於 production code 修改完成並同步 DAV-23，使用者 approve 保留。使用者其後明確選擇「圖表與精簡匯出取平均；例外偵測保留原始值，另保留 min/max」。目前已依提案實作；以下保留實作前設計，實際驗證結果見第 8 節及需求紀錄。
- 範圍：Exception Generator 的分析、含完整 ChartData 的報表匯出、進度與圖表。原有 raw export 及其他模組維持契約；不封裝／發布。

## 1. 問題、證據與選擇

完整 TWL 有 843,623 raw rows，117,229,324 bytes。現有部分檔產物為 50,904 retained rows，分析 80.809s、匯出 57.530s；不是完整資料成功基準。現有八項 writer／sampling 測試通過。完整程式退出原因與 Electron console error 尚未取得，故不將 timeout 判為唯一根因。

| 方案 | 效果與代價 | 決定 |
| --- | --- | --- |
| 優化既有 openpyxl／sampler，加背景工作與進度 | 保留 workbook 與 detector 契約，降低重複處理，解除長 HTTP 等待；需生命週期與狀態整合 | 採用 |
| 僅延長 Vite timeout | 不會加速、不解決記憶體／錯誤／進度 | 只供短期診斷 |
| 更換 XLSX engine／增加 native XML 依賴 | 潛在效能改善尚未量測，增加格式／打包相容風險 | 待本方案 full 實測後再評估 |

本階段不預先承諾倍數或完成秒數。先驗證完整資料可以正確完成，再以相同機器、資料、context 比較時間與記憶體。

## 2. 不可變更的資料契約

1. detector、threshold crossing、overshoot、exception peak、報表的例外工作表一律使用完整有效 raw frame。overview 的 envelope 不得回流到分析或匯出。精簡報表的 ChartData 可依本文件第 7 節平均化；完整報表仍保留全部 raw rows。
2. 既有清理規則、metadata mapping、完整報表的 31 欄 ChartData、sheet 順序、hidden metadata、數值本體及 `0.####` 顯示相容；來源缺失不得靜默少列。精簡報表明確另存、標示聚合方式，並附統計／來源追溯資料。
3. canonical chainage 為公尺。CSV 原 Km 截位造成多筆不同量測落在同一可見座標，保留全部樣本與來源身分。
4. 不自行依「每十筆」補位：真實 TWL 為下降方向且步距與示意不同；未驗證精確還原規則前不改 Km、exception 位置或 metadata 對應。DATAC 不套用 CSV 推測規則。
5. 新分析失敗／取消保留上一份成功結果；既有 dirty files、來源、參考輸出與 metadata 不覆寫。

## 3. 模組設計

### 3.1 Writer 與 sampler

- 沿用 openpyxl write-only writer，預先解析欄位、共用已建立的 cell style，避免每格重做格式設定。大檔輸出至 job 專屬暫存檔；舊呼叫介面仍可取得既有格式的結果。
- 寫列以 chunk 更新真實計數及檢查取消；最後壓縮／存檔獨立顯示為 `finalizing`，不以「寫列 100%」代表可下載。
- sampler 對 numeric fields 一次轉 NumPy arrays，再按原 source-position buckets 選 first/last／各欄 extrema。保持原始列順序與真實值。
- 保留里程查找避免每個里程全量 argsort；相同距離固定採最早來源列，並以測試鎖定規則。既有相等距離若未定義順序，允許只改 tie 選列；不得改最近距離、數值或遺失必要 extrema。

### 3.2 工作服務及容量

- 抽出可被舊 API 與新工作共用的同步分析／匯出 service，背景執行只負責排程、狀態與產物生命週期。
- 單一 thread worker，另設 admission limit：最多一項執行、一項等待，超額回 429 並提示稍後重試。不能只依賴 ThreadPoolExecutor 的無界 queue。
- 先取得容量再保存大型工作輸入；raw frame 在分析發布後視為不可變。job 持有該版本參照，小型 params／exceptions／metadata 另固定快照，避免不必要 deep copy。
- session cache 必須識別 job pin：不能刪除執行中工作所需的 frame；容量／TTL 清理後釋放參照。保留既有 session 數量界線，避免把 queue 變成額外無界 raw cache。
- CPU 工作移出 async endpoint；thread 主要解決 event loop 阻塞，不能宣稱 CPU 加速。需實測 status endpoint 在 full 工作期間仍能回應。
- 服務重啟不自動重跑工作；前端顯示工作已失效並可重新分析。啟動時僅清理服務管理的 job 暫存目錄殘留，禁止掃除其他輸出。

### 3.3 Session 與 revision

- 每次成功分析產生新的 `analysis_revision`，以原子操作發布 raw／results／params／revision。
- export create 必須帶 `client_session_id + analysis_revision`；不符目前成功版本時回 409，raw 已過期回 410／可讀重新分析訊息，不能 fallback 到 request.chart_data。
- 建立成功後，即使使用者重新分析，既有 export 仍用建立時固定的版本；輸出檔名及 metadata 同樣來自該快照。
- 新分析尚未成功前，舊的成功結果可檢視；其匯出必須明確使用舊 revision，不能混入正在編輯的參數。
- detail window 也綁定 revision，避免圖表套用另一份分析資料。

### 3.4 擬議 API

統一使用 `/api` 下列路徑，具體 router 命名可依既有規範調整，語意與錯誤契約須保持。

| 方法／路徑 | 輸入／輸出 | 行為 |
| --- | --- | --- |
| POST `/analysis/jobs` | 現有 AnalyzeRequest；回 202 + job_id/status | 快速建立，不等待分析完成 |
| POST `/export/report/jobs` | session_id、analysis_revision；回 202 + job_id/status | 只接受完整 raw 快照 |
| GET `/jobs/{job_id}` | session identity；回狀態與進度 | 不等待 worker；跨 session 不可讀取 |
| GET `/jobs/{job_id}/result` | session identity；成功分析結果及 revision | 未完成回 409；expired 回 410 |
| GET `/jobs/{job_id}/download` | session identity；XLSX FileResponse | 僅 ready export 可下載；由伺服器決定路徑 |
| POST `/jobs/{job_id}/cancel` | session identity；回目前狀態 | 排隊可取消，執行中合作取消 |

狀態：`queued → running → ready | failed | cancelled | timed_out`；執行中的取消請求先進入 `cancelling`，worker 確認停止才進 terminal state。expired 是終止工作清理後的讀取結果。不存在／跨 session 回 404；服務重啟遺失的 job 顯示失效，不猜測已完成。

狀態資料包含 `job_id, kind, client_session_id, analysis_revision, status, stage, processed, total, unit, elapsed_seconds, error`。只有 total 可信且大於零時才計算 `stage_percent`，明確為當前階段百分比，不代表總工作完成比例。

前端 create／poll／detail 使用可設定的短 timeout（初始 30 秒），poll 間隔初始 1 秒，短暫網路失敗退避到最多 5 秒，不建立第二份 job。下載使用獨立狀態與可重試請求，不套用生成的長 HTTP 等待。

### 3.5 取消、逾時、TTL 與下載

- Python thread 無法安全強制終止。取消在讀取區塊、通道、bucket、寫列等檢查點處理；無檢查點的函式／ZIP 收尾可能延遲取消。
- worker 尚未退出不可釋放執行名額或刪除其暫存檔；逾時同樣先要求合作停止。不得開第二個 worker 繞過未停止工作。
- 初始 terminal job TTL 為 60 分鐘（可設定），從終止時間計；active job 不用 TTL 清除。工作執行上限獨立設定，數值依 full 驗收後記錄，不以未量測數值作保證。
- 下載前持有產物引用，完成／中斷後釋放；TTL 清理略過有下載引用的檔案，避免 Windows 檔案鎖衝突。ready 檔案在 TTL 內可重新下載。
- failed／cancelled／timed_out 在 worker 真正退出後釋放 frame、未完成檔案及容量，保留小型錯誤紀錄供前端讀取。

### 3.6 進度與前端

- 每個分析分頁保存自己的 job identity、revision 與進度；poll 可繼續，但舊結果必須核對 job/session/revision 才可更新 UI。
- 階段包含 queued、reading、cleaning、metadata_mapping、detecting、preparing_chart、exporting、finalizing。只在實際可觀測時計 bytes／rows／channels／buckets；現有 monolithic loader 無可信讀取計數時先顯示不定進度，不能為百分比而猜測。
- 範例：`寫入 ChartData：250,000 / 843,000 列（本階段 29.7%） · 已用 02:10`。實際分母為清理後可匯出的列數，不硬編 raw 行數。
- 未知進度顯示階段及經過時間；ready 表示檔案已完成，下載成功／失敗另顯示。百分比可在換階段重設，但同階段不可倒退。
- TaskLoadingState 新增可選進度 props，保留其他模組的舊用法。重複點擊同一任務不建立多份工作。

### 3.7 圖表與細節查核

- 更新：預設 overview 依第 7 節使用同 Km 的 channel 平均值，並可顯示各 channel 原始 min/max；若仍過大才作 envelope。例外峰值用完整 detector 結果的獨立精確 marker。
- 提供 raw 原採樣順序連線模式供核查，說明 CSV 可見 Km 截位／定位回跳，因此線段可折返；此 raw 查核模式不將相同 Km 平均、去重或全域排序後連線。預設 derived mean 另按第 7 節處理。
- hover 帶 SampleCount／source row identity，讓同 Km 的不同樣本可追查；優先沿用既有 provenance，無欄位時才新增明確來源列號。
- 任意縮放後 debounce（初始 250ms）載入 detail；切換 session/revision／新視窗時取消舊請求並忽略過期回應。選取例外的 detail 流程仍可用。
- detail 範圍足夠小才標 raw；大窗仍採 envelope 時顯示 source／returned points 及抽樣標示。

## 4. 實作前測試提案

以下為實作前制定的測試矩陣；通過結果需以第 8 節及需求紀錄的實際執行紀錄為準。

| 編號／層級 | 情境與方法 | 通過條件 |
| --- | --- | --- |
| T1 writer 契約 | 小 fixture 與既有 writer 比較；涵蓋 >50,000 列分支、null、NaN、無窮值及高精度 float | 所有 sheet 值、順序、ChartData 列／欄數、格式、metadata hidden 相容；不把顯示精度當資料精度 |
| T2 sampling | 有效值／NaN／常數／重複與反向 x／等距候選；對既有與新 sampler 核對來源 index | 保留 first/last、各欄 extrema、例外／邊界；回傳皆真實 rows、保序；tie 依文件固定，非 tie 一致 |
| T3 detector 回歸 | 相同 raw、context、metadata 跑既有契約測試與整合分析 | threshold crossing、overshoot、peak、例外欄位／順序不變；sampling 大小不影響偵測或匯出 |
| T4 API 可回應 | 以事件同步控制測試 worker，再以真實 full 工作量測 create/status latency | create 回 202；worker 忙時 status 仍回應；自動測試有界等候，真實環境記錄 median/p95/max，初始目標 p95 < 2s |
| T5 容量／競態 | 一執行一排隊再送第三份；重複點擊；worker failure 後再送工作 | 第三份明確拒絕；不多複製 raw；終止後容量可重用；無名額洩漏 |
| T6 session/revision | A/B 分頁交錯分析、export、detail；export 後 A 再分析；新分析失敗 | 結果與檔案皆屬固定快照；stale create 409；失敗不抹去舊成功版本；舊 poll/detail 不覆蓋新 UI |
| T7 缺 raw／錯誤 | cache 過期、無 session、revision 不符、writer exception、下載失敗 | 新 export 不讀 overview fallback；錯誤可操作且可區分；下載重試不重建報表 |
| T8 生命週期 | 排隊取消、寫列取消、finalize 取消、合作 timeout；TTL 與下載競態、中斷、服務重啟殘留 | 未停止前仍佔 worker；未完成檔不可下載；清理不刪下載中檔案；不刪使用者資料 |
| T9 progress UI | 有／無 total、跨 stage、poll retry、切分頁、ready 到下載失敗 | 真實計數與階段百分比；無 total 不造百分比；finalize 不提早成功；支援舊 loading props |
| T10 圖表互動 | 重複 Km／反向 Km／噪聲極值；縮放快速往返；選例外；切分頁 | 預設散點、可切原序線、例外位置和值精確；最新 detail 才可套用，raw／envelope 標示正確 |
| T11 真實 partial/full | 使用提供的兩份 TWL，context TWL/UT/Mainline/20260907/CEN/TSW/U1；透過新 HTTP jobs 完成 | 兩檔分析與含完整 ChartData 匯出成功；ZIP testzip 通過；所有 ChartData 資料列逐列對照完整 retained frame，無少列或抽樣 |
| T12 工程回歸 | 執行相關 backend/frontend tests、TypeScript/build，檢查現有 sticky start action 行為 | 新舊測試通過；既有未提交功能保留；依實際 package scripts 記錄命令與結果 |

### 真實資料驗證細節

- 執行前先保存本次相關程式差異與 source／metadata digest；輸出另建唯一 batch，不覆寫既有 `outputs/exception-performance-2026-10-26/` 產物。
- ChartData 用 openpyxl read_only 逐列串流核對 schema、row count、null、字串及數值；數值依 XLSX 儲存精度比較，容差須明列且遠小於既有顯示精度，不能只比較首末或平均值。
- 小 fixture 對所有工作表逐格比較；真實資料的 Summary／exception sheets 對完整 raw detector 結果及既有 export 契約核對。沒有可信 full 舊基準時明確記錄，以 detector 契約測試與 raw 正確性為依據，不宣稱 full before/after 完全等價已測。
- 記錄 reading／cleaning／metadata／detector／sampling／writer／finalize／download 的 wall time（僅可觀測分段）、retained rows、file bytes，以及固定頻率抽測的 process peak RSS；說明 sampled peak 可能低估瞬間峰值。
- 性能比較使用相同環境／context，先 warm-up，再 partial 重複量測；full 至少完成一次。時間不足或程序退出視為未通過，保留 log，不宣稱修復完成。
- 執行記錄包含 Python／openpyxl／XML engine 版本、背景 CPU／磁碟負載限制；不得把帶 cProfile 的耗時當正常性能。

## 5. 實作與驗證順序

1. 本提案及測試矩陣先完成、同步 DAV-23；保留先前 approve。
2. writer／sampler 效能改善與 T1–T3 契約測試，先確認資料未變。
3. 共用 service、bounded jobs、revision、progress callback、檔案生命週期與 T4–T8。
4. 前端 per-session 工作／進度及圖表／detail 整合，完成 T9–T10；保留原有 UI 修改。
5. 新 HTTP 路徑跑 partial，再 full，完成 T11–T12，記錄所有差異與失敗；完成後更新需求文件與 Linear。

子代理可依 writer/sampler、backend jobs、chart 分工；先固定 callback／API 契約，界定檔案所有權避免同檔互改。主代理負責前端工作整合與驗收，不以各子代理單測通過替代整合測試。

## 6. Timeout 建議與完成標準

開發環境目前 Vite 為 300 秒，與使用者五分鐘現象吻合，但缺少實際 console error。提案初期的 30 分鐘僅作診斷容忍值，並非最大安全時間。實作後生成走背景 job，HTTP 只做短 create／poll 與完成後下載，不依賴長生成 timeout。依完整報表 1310.18 秒實測，若需要工作硬上限，先建議 3600 秒作本機保守起點；不是通用上限或完成保證。未設定時不設硬上限，完成後 TTL 預設 3600 秒，兩者用途不同；本次未改使用者環境。

完成必須同時滿足：partial/full 真實匯出成功、完整 ChartData 正確、例外契約未變、真實進度與錯誤可見、session/revision 不污染、worker 忙時狀態可讀、取消／清理可控，以及針對性回歸通過。只延長 timeout、只跑 partial 或只通過單元測試均不足以結案。

## 7. 使用者確認的同 Km 平均化設計（實作前補充）

### 範圍與資料分流

使用者已選擇：圖表與精簡匯出採同 Km／channel 平均值，例外偵測保留原始值，另存 min/max 供尖峰查核。本節取代先前「圖表不平均」的限制；完整 raw、detector 及完整報表的正確性要求仍適用。

- 整理出獨立 derived frame；不得就地覆寫 raw frame。先完成 raw 偵測及 metadata mapping，才建立平均圖表／精簡報表。
- 按實際相同 canonical Chainage 分組，不以固定每 10 列切塊、不對 Chainage 額外 rounding。不足／超過十筆均正常處理。
- grouping 包含 task context 與 metadata 區段，避免不同 Class／Track Type／Overlap／Tension Length／Landmark 混合。相同 chainage 若屬不同區段仍可有多筆，UI 不承諾跨區段全域一點。
- 各 height1..4、stagger1..4、wear1..4 獨立計算有限有效值的 mean、min、max、valid_count；全部無效則 null。缺測 channel 不以零補值、不平均不同 channel。
- 聚合後 stg_max/stg_min、height_min/max、wear_min/max 若需要，從平均後各 channel 重新推導；原始極值另存且命名清楚，不混用兩種語意。
- 保留 sample_count、source row first/last 及 group identity；range 是查核範圍，不宣稱每個範圍內 row 都屬該組。SampleCount 顯示範圍，不取平均。
- 圖表預設平均散點，可顯示每組真實 min/max 供查噪聲；原始模式仍可載 detail。exception markers 永遠是完整 raw 偵測的真實峰值，與平均線不重合屬正常。
- 新增明確「精簡報表（同里程平均）」匯出選項，獨立檔名後綴 `_ChainageMean`。完整報表仍可選，原 raw CSV 不變。精簡 ChartData 使用均值且明確記錄 raw／grouped rows；另附統計 sheet，保存每 channel min/max/count 及來源範圍。
- 新 export 不接受前端 sampled chart_data 作聚合來源，必須由該 session/revision 的完整 raw frame 生成。聚合規則與模式記入 hidden metadata，避免下游誤以為 raw。

### 測試提案與限制

| 編號 | 測試情境 | 通過條件 |
| --- | --- | --- |
| M1 | 10 筆同 Km、2／11 筆同 Km、不同 channel、混合 null／非有限值 | 每欄 mean/min/max/count 正確；非固定十筆切塊；all-invalid 為 null |
| M2 | 同 Km 在不同 metadata/context；非相鄰重訪同里程 | 僅相同 group identity 合併，來源範圍正確，沒有跨區段混合 |
| M3 | 單一超標尖峰，其餘正常，使平均不超標 | raw exception／maxValue／maxLocation 保留；min/max 能查得尖峰；圖表明示均值 |
| M4 | 原 raw 與完整匯出前後比較 | 原 frame 不變；完整報表保留全部列；精簡報表明確命名、統計、metadata |
| M5 | 實際 TWL partial/full 平均化及匯出 | 記錄 raw／grouped rows、實際減量比例及耗時；逐組核對各 channel mean/min/max/count，不預先宣稱恰好十倍或解決所有 bug |

平均化主要減少圖表／匯出工作量；因 raw 偵測保留，讀檔與偵測成本不會一起縮小十倍。平均化不是排除 bug 的保證；背景工作、進度及錯誤處理仍需完成。

## 8. 實作／驗證進度（2026-10-26）

- T1–T3／M1–M4：85 項核心、detector、writer、sampling、aggregation 回歸通過。另 30 項背景工作及 API 回歸通過，涵蓋 T4–T8 的容量、revision、取消、逾時、TTL、下載 lease、cache missing、event-loop 可回應，以及最後新增的同 revision detail 快取與單一 limiter。
- T9–T10：前端 View 8 項（含最後顯式鎖定日期／Task／站碼補充）、ChartComponent 6 項、進度及 poll 共 5 項已通過。Chart 單元測試 mock Plotly，真實圖形互動另作瀏覽器 QA，不能互相替代。
- T11／M5：新 HTTP 路徑 partial 暖機及正式執行兩種報表均已逐列與獨立平均 oracle 核對通過。full raw 成功生成／下載，838,859 列 ×31 欄核對通過；batch01 舊精簡已完成，首次統計驗證因空字串／None 表示差異失敗。舊版統計 86 欄、缺兩個 counter range 欄及 sample_counter_column metadata，batch02 補驗舊成品並以最終 88 欄版本走真實 HTTP jobs 驗收，不把 batch01 原失敗改列成功。
- T12：TypeScript 及 production build 成功；三種 viewport 的 Playwright Start Analysis 可操作性重跑均通過。首次冷載入 timeout 及 Vitest worker 啟動 timeout 已記於需求紀錄，不當作測試通過。
- 執行上限 `TOV1050_JOB_TIMEOUT_SECONDS` 目前未設定時不設硬上限；create／poll 使用 30 秒。Terminal 檔案 TTL 預設 3600 秒。取消／逾時為合作停止，finalize 等無檢查點區段可能延遲，worker 未退出前不釋放名額。
- production／venv／requirements 未新增依賴；outputs 隔離 target 已安裝 lxml 6.0.2、XlsxWriter 3.2.9 作概念評估，決定本輪不採納。未封裝／發布／提交。最終 batch02 exit 0，全部必要驗收完成；詳見下方最終結果，DAV-23 同步為 Done。

### 最終驗收中發現與修正範圍

- 原生 CSV 計數欄為 `SampleCount [n.]`；聚合現已兼容它與 canonical `SampleCount`，metadata 記錄實際欄名，保留原計數 first/last。兩者同時存在時 canonical 優先。11 項聚合／成品回歸通過。獨立 counter audit 證實兩份檔經 loader 前後各裁 100 列後均無 counter 下降，因此先前分組／均值不受 alias 修復影響；仍須以最終程式補驗完整精簡 XLSX 的 counter 範圍與 metadata。
- 真實 Plotly QA：初次 390×844 發現固定側欄遮擋控制項，低高度三組 y 軸標題亦重疊。已以最小圖高 540px／可捲動容器及窄寬上下布局修正，最終 1280×720、1033×640、390×844 均通過平均/min-max/raw、raw peak、zoom、stale detail、Graph/Table 及控制項操作驗收，無 pageerror／非法軸 warning。證據在 browser-qa-2026-10-26T03-30-55-667Z；不以 Start Analysis viewport 測試替代 Plotly QA。
- 唯讀生命週期 review 發現 Windows 刪檔 PermissionError 可能跳過 finished_at 或使 cleanup 500，以及普通 atexit 晚於 executor join 的退出限制；已補刪檔重試／可靠釋放名額及 FastAPI shutdown close，22 項背景工作回歸通過，之後 13 項 API/detail 回歸通過。
- Writer 無明顯 O(n²)；成品只有 3 個 style。主要成本仍為純 Python 逐格 XML 寫入；精簡報表還包含完整 min/max/count 統計，不能從分組減少約十倍推論整份 XLSX 生成必定快十倍。production 未安裝 lxml 或替換 engine，隔離概念評估如下，不外推未測 full 收益。

### XML engine 補充評估提案（實作前）

Full raw 寫入超過 15 分鐘仍未完成，因此原需求的匯出效能另評估 lxml：先以獨立 target directory 安裝相容 Windows/Python 3.12 wheel，不改現有 venv 或執行中程序。以相同 writer／固定 deterministic 10,000×31 fixture，在兩個新程序分別確認 LXML=False/True，暖機後重複量測，核對所有 sheets／cell values／number formats／metadata、null／inf／日期／字串，並保留測試腳本和數據。若確有收益再納入 backend 與封裝依賴及文件，跑 writer／取消清理回歸，再用最終 engine 補驗真實 full 成品。尚未量測前不預設收益，不採 openpyxl 私有 writer override，也不更換報表欄位契約。

評估結果：隔離安裝 lxml 6.0.2，8 份工作簿逐格內容／型別／全部樣式及 ZIP 等價，stdlib 正式 15.418／18.480／15.914s，lxml 13.475／15.703／15.313s；中位數只快 3.8%，負載及順序有混雜，**未納入依賴**。詳見 `outputs/exception-performance-2026-10-26/xml-engine-01/summary.json`。之後亦完成下述 XlsxWriter constant_memory 概念評估，未更換 production writer。

XlsxWriter 3.2.9 隔離概念試驗結果：同 fixture、warmup＋交錯正式三次，openpyxl median 19.703s、candidate 12.262s（1.607 倍）；8 份成品全部 9 sheets 值／nonblank type／數字格式／順序／hidden／ZIP 通過。首次 fingerprint 失敗源自缺省空白格式 None 與 General、blank XML 表示，正規化後逐格無實質差異，原失敗紀錄保留。未驗完整樣式／layout、公式 cached value、取消與 Windows 清理／ZIP64／封裝／真實 full，因此本輪**不採納**，不外推 full 收益。詳見 `xlsxwriter-01/validated-summary.json` 及 README；venv／requirements／production writer 均未改。

## 9. 最終驗收結果

T1–T12／M1–M5 的本機工程驗收完成；沒有宣稱已完成使用者 Electron 手動 UAT、封裝驗收或可信舊 full detector 歷史等價比較。詳細命令、失敗與修正及未提交檔案清單見需求紀錄。

| 實測項目 | 結果 |
| --- | --- |
| partial 正式 | 50,904 raw → 4,949 groups；分析 14.40s、完整 98.03s、精簡 43.22s，兩份全列驗證通過 |
| full raw | 分析 94.11s；838,859 列 ×31 欄，98,655,329 bytes，生成 1310.18s；下載／ZIP／全列／例外／metadata 通過 |
| full 最終精簡 | 82,144 列 ×31 欄 ChartData＋88 欄統計，43,675,125 bytes；HTTP 生成 367.51s、下載 4.79s、讀回核對 196.43s；全部通過 |
| full 獨立平均 oracle | 12 channel mean/min/max/count、來源列及 SampleCount first/last 通過，raw／例外 frames 不變 |
| full 舊精簡補驗 | 86 欄舊 schema 全列通過；精確容許舊 counter 欄／metadata 差異；原 batch01 空字串失敗保留 |
| 狀態回應 | create 0.027s；340 次 status median 0.0543s／p95 0.0979s／max 0.1540s，該次 localhost 觀測 |
| 圖形與回歸 | 三尺寸真實 Plotly QA、frontend tests／TypeScript／build，以及最後背景 22 項與 API/detail 13 項均通過 |

證據：outputs/exception-performance-2026-10-26/batch-jobs-02/full-summary.json、full-events.jsonl、final-source-integrity.json；完整 raw 與 partial 證據在 batch-jobs-01，失敗摘要另存 batch01-recovered-summary.json。來源 CSV 及 TWL metadata 最後 SHA256 均與執行前一致。測試用服務已停止。

約 10.21 倍僅指列數減量。保留 88 欄統計的精簡 XLSX 不會同比縮小；完整 raw writer 仍約 21 分 50 秒。本次環境負載未控制，不宣稱嚴謹 before/after 速度倍數。無工作硬上限為預設；如需設定，3600 秒可作本機保守起點，完成檔 TTL 3600 秒另計。DAV-23 結案，下一步為使用者重啟開發服務後進行 Electron UAT；進一步替換 writer 可另立後續設計與驗證。
