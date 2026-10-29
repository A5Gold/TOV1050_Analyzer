# Exception Generator：可追溯極值連線、完整 raw 與縮放還原設計／測試提案

- 日期：2026-10-26
- Linear project：TOV1050_Analyzer
- Linear issue：[DAV-24](https://linear.app/david-chu/issue/DAV-24)
- 負責人：Codex；使用者審閱資料呈現語意
- 狀態：Superseded — 使用者改為共識中位樣本作偵測／圖表／報表；本文件極值方案未實作。現行提案見 `2026-10-26-exception-consensus-median-proposal.md`，本文件的 reset／hover／cancel 診斷仍有效。
- 前置工作：DAV-23 已完成；本提案處理其後的使用者實測回饋，不重開或覆寫前次驗收結果。

## 需求與目的

### 使用者與流程

使用者以 npm run dev 啟動 Electron，匯入 TWL CSV，查看 Height、Stagger、Wire Wear，放大噪訊／例外後雙擊回全線，再追溯例外峰值的原始 CSV 紀錄。

1. 量測改用連線，合併 Raw sample points／Raw acquisition lines 選項。
2. 提供明確切換精簡資料／原始資料；平均值未必適合作 audit，需要評估真實極值代表點。
3. 修正雙擊還原後全線 X 軸搭配局部曲線；不應等待全線請求才恢復畫面。
4. 修正 customdata[1]/[2] hover warning，正常取消不列為 API Error；真正 timeout 必須可見、可重試。
5. 評估一次載入整份 raw 的可行性，量測實際 Electron／Plotly 成本。

證據：[使用者截圖](../../01%20Screenshot/graph%20%28dot%2C%20missing%20after%20zoom%20out%29.png)。圖中 X 軸約 9100–9500 m，例外點涵蓋整段，但量測曲線僅約 9450–9490 m。另有使用者提供的 30000ms timeout、canceled、Plotly missing customdata console logs。

### 商業規則與限制

- canonical chainage 為公尺；CSV Km 截位造成同座標多筆真實樣本，不固定每組十筆、不補造小數位。DATAC 不套用 CSV 補位推測。
- detector、threshold crossing、overshoot、例外 peak、完整匯出繼續使用完整有效 raw；本輪不修改 threshold／清理規則。
- 使用者偏好 Height minimum、Stagger minimum + maximum、Wear minimum；High Height 偵測及其 raw marker 仍保留。
- 原始檔、metadata、既有報表不覆寫。既有平均精簡報表明確維持 ChainageMean 語意，不能靜默以極值覆蓋其 ChartData。
- 本輪新設計尚未批准；前次 approve 及選擇平均方案不視為已批准改用極值。

## 現況盤點

已讀 PRODUCT.md、DESIGN.md、request 模板與 DAV-23 設計／驗收紀錄。優先使用 codebase-memory-mcp 尋找 ChartComponent、get_chart_data；圖譜行數／signature 部分過時，已以目前工作區程式確認。

| 現象 | 已確認原因／限制 |
| --- | --- |
| raw reset 後只剩局部 | ChartComponent.tsx:61–66 只有 mean + 無 detail window 立即恢復 result overview；:430–433 reset 清空 window。raw 仍保留局部 chartData，等待 :72–103 新的全範圍 GET；失敗後仍保留局部。例外 marker 獨立使用全段 result.exceptions。 |
| hover missing variable | analysis.py:223–232 的 _chart_columns 漏掉 source_row_number／SampleCount；ChartComponent.tsx:160–161 補 null，:189 模板仍引用。安裝版 Plotly nested property 將 null 當未定義。 |
| canceled 被列為 error | ChartComponent.tsx:104 正常 abort；client.ts:71–89 僅排除既有 wear conflict，沒有排除 Axios cancellation。 |
| 30 秒 timeout | 前端固定 timeout 30000ms；detail 共用 DETAIL_LIMITER(1)，瀏覽器取消不會立即停止已開始的同步計算。cache 只保存 mean derived frame，未保存全線／window payload。尚未量測此次 timeout 的 queue、sampling、serialization 分別耗時，不宣稱唯一原因已確定。 |
| 點數可能遠超 12000 | chart_sampling.py 將 max_points 視為 bucket 數，每 bucket 保留 first/last 及多欄 extrema；不是 returned rows 硬上限。以名稱辨識量測欄還會把 mean 統計欄納入掃描。 |
| 舊測試漏網 | ChartComponent unit reset 只測 mean；browser QA 同樣未測 raw 真正雙擊 reset。Plotly mock 與自帶 source_row_number 的 raw fixture 遮蔽實際 API 缺欄。 |

相關程式碼：frontend/src/components/ChartComponent.tsx、frontend/src/api/client.ts、frontend/src/types/api.ts、backend/app/api/endpoints/analysis.py、backend/app/core/chainage_aggregation.py、chart_sampling.py、tov1050_data_ingestion.py。

## 設計

### 方案比較與建議

| 方案 | 優點 | 代價／限制 |
| --- | --- | --- |
| 平均／群集中心 | 趨勢平順，點數較少 | mean／centroid 並非真實樣本；medoid 雖為真實樣本，也可能省略危險尖峰，不作唯一 audit 主視圖。 |
| 真實極值連線 + raw 明細（建議） | 符合三類量測用途；每個點可查來源；保留噪訊尖峰 | Stagger 每 channel 需要 min/max 兩條線；它表示範圍邊界，不表示原始採集軌跡。 |
| 預設全量 raw 同時繪製 | 所有樣本直接可見 | 全檔 838,859 × 12 = 10,066,308 個 channel 頂點，需另加座標、provenance、JS／Plotly／GPU 複本；可能阻塞互動，須先量測。 |

建議主切換為「里程極值」／「原始資料連線」。保留平均功能於次要的「平均趨勢」選項，仍用連線；明確標示非原始值。既有 ChainageMean 精簡匯出不因主圖模式改變而改寫。

### 真實極值資料契約

| 類別 | 精簡顯示 | 追溯 |
| --- | --- | --- |
| Height 1–4 | 每組有限值 minimum，一 channel 一條線 | 各自的原始值、source row、SampleCount |
| Stagger 1–4 | 每組 minimum 與 maximum，分兩條線 | min／max 各自來源；可能是不同 raw 列 |
| Wear 1–4 | 每組有限值 minimum，一 channel 一條線 | 各自來源，原 threshold 可比對 |

- 沿用 exact chainage + context/metadata + finite SampleCount decrease pass 的群組隔離；canonical SampleCount 優先，其次 SampleCount [n.]。不只依數值 Km 跨 context 合併。
- 新增獨立 derived extrema 契約／version，不覆寫現有 mean frame。每 channel／stat 保存 value、source_row_number、retained_position、原始 SampleCount、group_id、pass_id；回應含 session/revision、來源檔識別與來源列號單位。
- 每點來源必須指向真正 raw 樣本；極值並列時固定取最早採集位置，並保留 tied count。該點的其他 channel 值須由該 raw row 查回，不能把不同 channel 的 extrema 拼成一列假 raw。
- 非有限值不參與 extrema；全空群組為 gap，不補零。各 channel 的有效樣本數分開列出。
- raw source_row_number 為 CSV 資料紀錄序號（含 header 偏移），不是遇到 quoted multiline 仍保證等同實體文字行號；若舊來源只有 retained row，必須明確標示，不能冒充 CSV row。
- Stagger min／max 分別連線，以同 channel 顏色配實／虛線與名稱區分；不將同 X 的兩個 extreme 串為垂直鋸齒。若 min=max，hover 仍分辨來源，視覺可重疊。
- 連線依原群組／採集次序；pass／不相容 context 切換斷線。不能透過排序、移動 X 或插值隱藏真實 raw 的重複 Km／里程回跳。
- overview 額外減量只作用圖表 payload，保留 first/last、量測 extrema、例外 chainage、FromM/ToM。例外 markers 始終用真實 raw peak；High Height 例外也必須可見。
- 現有 sampler 只按最近 chainage 保留一列，重複 Km 可能取到第一列而非 peak；detector 已知 worst_idx 但既有輸出沒有來源身分。新增不改判定的 peak provenance sidecar（來源位置／row／channel／SampleCount），以 source identity 強制保留真正 peak／邊界候選，不能僅依最近 Km。多來源平手明列候選與穩定主來源。
- 點選例外提供「原始樣本明細」：例外範圍、精確 peak 候選行、channel、Km/Chainage_m、SampleCount、來源紀錄序號與完整同列量測。相同 peak 有多個來源時列出候選，不假定單一列。從極值 hover／明細可定位原始紀錄；不聲稱例外報表現有 ID 已含唯一 raw row。

### 繪圖、狀態與載入

- 保留現有單一 React-owned Plotly 圖、三個共用 chainage X 軸的面板。raw 12 條量測線；極值 16 條（Height4 + Stagger8 + Wear4），加獨立例外 markers。Plotly scattergl 處理密集線，無須增加 renderer 依賴。
- 以 session + revision + mode 分開保存全段 overview 與 detail；overview 不被 detail 覆蓋。bounded window cache 同時納入 range、resolution、contract version，建議最多 4 個 detail windows，切換 revision 釋放舊資料。
- reset／雙擊／回全段按鈕：立即取消 debounce／HTTP、增加 request generation、清除受控 axis range，直接換回相應模式的全段 cache；不發起無範圍 detail 作為恢復前提。例外選取與可見 range 明確分離，保留選取時也不能因舊回應再強制跳回局部。
- overview 尚未載入的模式，先顯示清楚載入狀態；上一模式若保留顯示，其 badge 必須仍標示實際模式。detail 在背景載入；逾時仍顯示涵蓋目前視窗的 overview，標示 detail 未完成並提供重試。
- response 套用前核對 identity、mode、range、request generation；reset、連續 zoom、mode switch、重新分析後的舊回應不可覆蓋目前畫面。
- raw 全線 overview 若取樣，必須顯示「原始資料概覽（取樣）」及實際 returned/source 數；只有該範圍所有 retained raw 都載入才標「完整原始樣本」。不把 max_points 當完整性保證。
- 新增明確「載入全段完整 raw」操作，按固定 revision、採集順序分頁／分塊載入全部有效 raw，無 sampling，顯示實際 loaded/total 百分比，可取消；載入期間全段 overview 保持可見。避免每點十欄重複 customdata，採共享 provenance／按需查 row；typed arrays 與單次完整呈現需納入實測。
- full-raw 分頁契約：cursor 為 retained position，不是 chainage；每次最多 50,000 rows、包含 next_cursor/total/revision，序號連續核對、無重複／遺漏；410 過期、409 revision 不符，不能串接兩版資料。只保留目前 session 的一份全量前端 cache；離開／重分析可釋放。每頁短請求，不能新增無界背景 queue。
- full preload 的效能結論先以 partial/full 實測作 gate：若未達互動目標，不把全量同時渲染設為預設或宣稱流暢，明確記錄限制；仍提供可核對的 raw detail／完整匯出。任何 fallback 必須標示為概覽，不悄悄降低「完整 raw」資料量。不得只用 fixtures 宣稱 full Electron 成功。

### 錯誤處理與效能工作

- raw payload 帶 source row／canonical counter；hover 契約先驗證各陣列長度。缺值用「—」文字或省略欄位，不以 null 供 Plotly 模板索引。marker／range／raw／mean／extrema 各自使用對應 hover schema。
- Axios 只針對確認為 cancellation 的類型／ERR_CANCELED 略過 error log；不吞 timeout、HTTP error、offline。保留既有 wear conflict 規則。
- 分段記錄 queue wait、sampling、serialization、transfer、JSON/array 準備、Plotly render；量測實際 returned_points、payload bytes、記憶體與 main-thread long task。
- sampler 使用明確量測白名單，mean count／provenance 不作 extrema channels；按可見圖寬／每 channel 預算決定 bucket，mandatory preservation 超出目標需誠實回報。
- revision cache 保存可重用 overview／群組，合併重複請求；新請求排隊前／計算檢查點確認仍有效，避免已被取代的 detail 長時間阻塞最新請求。不用增加無界 worker 迴避問題。
- 暫保留 detail 的 30 秒失敗保護，先消除 reset 依賴與重複計算，再依實測調整。此次錯誤來自 detail GET，與已改背景工作的 Excel job timeout 是不同路徑。沒有通用最大 timeout；提高數值不等於修復。

### 範圍與不在範圍

本輪涵蓋圖表連線／mode、可追溯極值、raw 明細／全載評估與路徑、縮放狀態、hover／取消／detail 效能；包含相關 API 契約及風險相稱測試。

不更換 XLSX engine、不重跑 21 分鐘 full writer作無關回歸、不改 detector、threshold、原始來源或 metadata、不自動重建截掉的小數。不將極值塞入既有 ChainageMean 匯出；如日後需要極值 workbook，另定獨立格式，避免混淆。

### 驗收標準與測試提案

以下為待執行計畫，不能視為已通過。

| 層級 | 測試與通過條件 |
| --- | --- |
| extrema 正確性 | 10 個同Km且每channel extreme來自不同列；Height/Wear min、Stagger min/max 完全等於 raw；ties 選列穩定；查回同列12channel正確。每組筆數1/9/10/11亦成立，不假定十筆。 |
| 隔離與缺值 | counter reset（含 native alias）、context/metadata改變、非相鄰同Km、descending/reversal、NaN/Inf/全空、單點群組；不得跨pass連線或補造值。 |
| 例外與來源 | raw frame/detector結果digest前後一致；Low/High Height、兩方向Stagger、Wear的peak及FromM/ToM保留。相同Km/peak多候選全部可查；來源紀錄序號與CSV／SampleCount對上。 |
| raw API | 真正API帶provenance，缺欄明確標示。全量分頁串接後 rows/order/digest 等於完整 retained raw；取消、revision換版、410/409、最後不足一頁、空檔均正確。 |
| component race | raw與extrema各自zoom→reset；pending/debounce/timeout/失序回應皆立即回全段cache；切模式／session/revision／例外選取後舊回應不能覆蓋。 |
| console/hover | 真實Plotly＋真實API payload，實際hover各類trace（含缺counter/來源）；零 missing-customdata warnings。正常 abort 不列API Error；模擬timeout仍有可讀訊息與重試，不因抑制取消而漏錯。 |
| 真正操作E2E | 原截圖情境：raw放大後真正雙擊，並測modebar reset與回全段按鈕；全段曲線左右端與例外點同時可見。不能只呼叫 mocked onRelayout。 |
| partial/full量測 | 用提供的partial/full CSV，分冷／暖cache，單一測試負載，記錄環境。各3次zoom/reset/mode switch；reset不等待網路，目標p95≤500ms；cached detail目標≤1s、冷detail目標≤5s。數值為待驗證目標，未達需回報證據／限制。 |
| full-raw gate | 全部838,859 retained rows / 12channels與provenance核對；量測下載/parse/render/heap/longtasks，原生Electron亦需實測；期望互動p95≤500ms、單次main-thread阻塞≤1s，無WebGL context loss／OOM。未通過不能聲稱順暢或悄悄取樣。 |
| 相容與介面 | TypeScript/build，背景分析／匯出短流程回歸；既有mean export契約不變。1280×720、1033×640及窄390px保持控制與原始明細可達；鍵盤可切mode／回全段，線型及文字不僅靠顏色。 |

預定命令：backend venv pytest（chainage／chart sampling／detail API 與新增針對測試）；frontend 設 NODE_USE_SYSTEM_CA=1 後執行 vitest 相關 suites、npm run build；Playwright 真實Plotly／API情境與實檔性能腳本。實作後記錄確切命令、pass數、產物及失敗，不預填通過結果。

### 實作順序（批准後）

1. 先修正與鎖定 raw reset、provenance、hover／cancel錯誤測試。
2. 定義版本化 extrema／raw page 契約與來源查核，保留raw detector／mean export。
3. 建立mode overview cache、detail generation/race處理、連線與明細。
4. 完整raw載入與記憶體優化，跑partial/full gate；根據證據紀錄可用性及限制。
5. 真實hover／雙擊與跨模式／revision驗收，更新本文件與Linear，交付可檢閱差異。

## 執行紀錄

### 實作

本輪只新增此提案文件；未修改 production code、未提交、未封裝／發布。工作區已有 DAV-23 與其他工作的 dirty files，保持原樣；完整列表以 git status --short 為準。

### 測試與 debug

- 已實際讀取使用者截圖，對照目前 ChartComponent／client／backend payload、sampler及現有測試。
- 兩個唯讀子代理分別檢查圖表reset/hover及極值追溯契約。
- 已確認前三個問題的程式原因；detail 30秒耗時分解與全載流暢度尚待實測。
- 本輪未執行 production 測試／benchmark；DAV-23 的舊測試結果不當作本輪驗收。

### 驗收結果

設計與測試提案可供審閱；功能修正及上述驗收尚未執行。待確認：以可追溯極值作主精簡視圖、保留平均趨勢／既有平均匯出，以及完整raw全載路徑與實測gate。

## Linear 同步

- 本工作階段已確認 Linear MCP 實際掛載；已讀 DAV-23、查找相關issues並建立 DAV-24（In Progress），關聯DAV-23。
- Next action：使用者審閱本提案，確認新資料語意後開始實作與執行測試。
- 最後同步日期：2026-10-26；提案摘要、確定根因、未量測項目與下一步同步至 DAV-24，issue 維持 In Progress。
- 阻塞／需要決策：新設計待確認；非環境或權限阻塞。

## 相關檔案

- 本文件（本輪唯一新增需求／設計檔）。
- 01 Screenshot/graph (dot, missing after zoom out).png（使用者提供，未修改）。
- docs/requests/2026-10-26-exception-generator-design-and-test-proposal.md（前次設計，未修改）。
- docs/requests/2026-10-26-exception-generator-large-export-and-chainage.md（前次完成紀錄，未修改）。
