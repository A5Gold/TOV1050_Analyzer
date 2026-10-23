# TOV1050 契約回歸與 metadata 能力實作

- 日期：2026-10-23
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-20、DAV-21；關聯 DAV-10、DAV-19
- 負責人：Codex
- 狀態：本次實作與可用fixture驗收完成；業務資料缺口待補，DAV-20／DAV-21維持In Progress

## 需求與目的

承接使用者已批准的下一階段及 metadata 相容性設計，直接完成可獨立驗收的程式、測試、審閱產物與 commit/push。

### 使用者與流程

CSV 清洗 → canonical detector → API → report/raw export；metadata inspection → TL 邊界審閱 → 日後取得物理區間核准。

### 商業規則與限制

TOV640 唯讀；不修改 detector 核心與 legacy enrichment 語意。Chainage 公尺。observed envelope 不作核准 TL 範圍；點、區間與 unknown/known non-overlap 分離。不猜邊界、不平均分割 TL、不將 landmark 點當站台範圍。既有六份 dirty Excel 及 batch-03 不提交、不覆寫。七份 runtime config 不重建。

## 現況盤點

- TOV1050 master HEAD：5bc1a5c51d1528f4039b786965fd6e5bc23917d9。
- TOV640 main HEAD：cbca528f090152ec2c776ee04a4c30f0d371810f；既有 frontend/index.html 修改及 docs/TOV1050_Migration/ 保留。
- 已閱讀 PRODUCT/DESIGN、metadata rules、development plan、兩份批准計畫、activation request/release/manifest/smoke 與 TOV640 architecture。
- MCP graph 已重新索引；Linear get_issue 與四份承接留言成功。
- 相關程式碼：tov1050_metadata、metadata、analyzers、analysis API、calculation、exporter。
- 已知缺口：TOV1050 繼承 wear lookup 的空表 fallback；wide 點不提供 TL/Overlap/Landmark 區間；真 fixture coverage 須重新盤點。

## 設計

### 範圍

1. 分離 BracketPoint / LandmarkPoint，保留同位 multiplicity 及 workbook/sheet/Excel row provenance。
2. 能力契約 v1：thresholds、class/track intervals、bracket/TL/overlap/landmark，available/partial/unavailable 及明確缺口；API 回傳能力及 legacy enrichment 版本。
3. TL 消費者缺核准區間時 fail closed；不更改 TOV640 EAL/TML 路徑。
4. 新批次產出能力矩陣、含 termination/source row 的 TL 邊界審閱表、分頁 TOV640 相容 layout 候選；未知 interval 欄組留空並註明 review-only，禁止啟用。
5. 固定 TOV640 commit，分程序輸入相同 canonical fixture/metadata/context，逐欄比對 detector 及實際 Excel report，數值 atol=1e-9、rtol=0，字串/ID/欄序精確。
6. 真 CSV coverage 矩陣列出所有 line/session/direction；有資料者跑 API/report/raw，缺項 blocked。canonical 人工測例明標 synthetic，不能代替現場驗收。

### 不在範圍

不核准 observed TL 邊界、不 promotion 新候選、不發布 portable、不改資料庫與 TOV640。

### 資料流與錯誤處理

必需 detection metadata 載入失敗回明確錯誤；optional enrichment 缺失透過能力契約揭露。TL lookup/source rows 明確報 workbook/context/所缺區間。來源 digest drift 在審閱工具中記錄並停止套用舊證據。

### 驗收標準

同位多 bracket/landmark 保留；能力不可把 unknown 當 N；TL lookup 不猜唯一值；來源可回溯；跨程序比較非空例外、分級、分組、peak、ID與 report 欄位；真 raw 逐值與完整清洗 frame 相符；缺 fixture 明列。

## 執行紀錄

### 實作

能力v1、點資料分離、來源lineage、核准interval純函式sweep、API/readiness/report能力及wear 422阻擋已實作；detector未改。詳見 docs/tov1050-capability-contract.md。

大檔端到端實跑發現原Excel exporter在KTL 83萬保留rows下長時間未完成，該驗證程序觀察到private memory超過8GB，因此停止本次唯讀驗證程序，保留batch-03中途產物。新增僅TOV1050且>50,000 rows的ChartData write-only匯出路徑；Summary/exception仍由legacy exporter建立，不變更enrichment。EAL/TML維持legacy writer。新增逐格新舊契約及50,001 rows完整輸出測試，重新驗證canonical/EAL基線與真實大檔。這是完成已授權真CSV→完整report/raw驗證所需的針對性修正，非portable或全體效能SLA完成宣告。

batch-04 又發現直接傳 BytesIO 給 StreamingResponse 會按 newline 逐段交付，raw CSV 每行都需 thread-pool handoff。停止本次batch-04驗證程序，保留中途證據；TOV1050下載改64KiB固定分塊（report與raw、GET與POST），不改匯出位元組，EAL/TML保留原路徑。新增binary與大量newline資料的位元組完整性／分塊測試，最終改以batch-05重跑。

### 測試與 debug

最終相關 backend suite：131 passed（45.55s），包含新增的 capability、streaming report 與分塊下載測試。前端 `NODE_USE_SYSTEM_CA=1` 下 `npm exec tsc -- --noEmit` exit0；TLS 未放寬。七份 validator 重跑全 pass／findings0，七份相容候選逐格讀回全 pass／14,143點。四組跨程序 detector/report 比較，以及新 streaming writer 對固定 TOV640 證據比較全 pass。完整命令、容差、產物與來源限制見 `docs/tov1050-contract-regression-2026-10-23.md`。

### 驗收結果

能力契約／點資料及lineage／wear缺口明確拒絕／候選資料保留已通過驗證。373組 physical TL observed envelope 僅供審閱，沒有生成或啟用核准 interval。三份真資料完整 detection goldens：AEL 276 rows／0 exceptions、KTL 830,606 rows／160 exceptions、TKL 501,211 rows／69 exceptions；class/track uncovered rows均0。最終batch-05三組API/report/raw全部HTTP200，完整ChartData逐列／逐值、Summary逐值、raw共有數值欄全部通過。18 context中3組有已驗證真fixture，15組缺資料；DRL檔context未確認列unassigned。AEL零異常不作peak/level/ID現場證據。TKL raw reader的mixed-type警告已定位來源杆號欄，診斷及驗收範圍另記於成果報告。

## Linear 同步

- 本工作階段 Linear MCP 實際掛載，四個 issue 已讀並成功留言承接。
- DAV-19 維持 Done；DAV-10 In Progress；DAV-20/DAV-21 開始實作。
- Next action：業務資料負責人審閱373組TL邊界／scope及DRL Mainline/PL、UT/DT；開發端取得明確核准後接入interval與wear，並補其餘15組真fixture／TML datac。DAV-20／21維持In Progress，不宣稱全線或TL/wear parity完成。batch-05已完成，最終實測及阻塞同步Linear。
- 阻塞／需要決策：核准物理 TL 邊界及未具備的真 fixture，不阻擋能力/回歸基礎實作。

## 相關檔案

### 承接補充：DRL fixture context確認

使用者已明確回覆 `20260817_022959_olpar.csv` = DRL／PL／UT。範圍：加入有來源SHA與確認依據的fixture context registry，以新batch-06只重跑該context的清洗→API→detector→完整report/raw核對及mapping coverage；合併coverage時保留batch-05三組歷史驗證來源，不宣稱它們本次重跑。驗收需記錄實際筆數、異常及mapping缺口。此次確認只適用該檔案context，不擴大為PL雙方向metadata、TL物理邊界或scope核准；不改runtime Excel。實作前Linear DAV-20／21同步此承接與next action。

batch-06發現真實metadata缺口：252→52 rows，class覆蓋全、track覆蓋0；PL track type只有42,000–44,000m，sample約45,388–45,389.2m。歷史API fallback仍回200／零異常，不能驗收。必要修正範圍：TOV1050分析入口在detector前核對全部retained chainage的class/track interval coverage；缺少時HTTP400附workbook、sheet、缺少筆數與公尺位置，EAL/TML路徑及detector核心不變。驗證需包含真DRL fixture fail-closed、缺口審閱表與七份核准metadata/既有fixture相容性。不得延伸PL範圍來讓測試通過。

- docs/plans/2026-10-23-tov1050-next-stage.md
- docs/plans/2026-10-23-tov1050-metadata-compatibility.md
- docs/tov1050-contract-regression-2026-10-23.md（實測命令、成果及限制）
- docs/tov1050-capability-contract.md（程式與資料語意）
- outputs/metadata-capabilities-2026-10-23/batch-02/（能力矩陣、TL審閱表與七份review-only候選）
- outputs/contract-regression-2026-10-23/（固定基線、goldens、streaming parity與最終batch-05）
- 保留未提交使用者修改：五份reference Excel、一份9月候選及既有未追蹤metadata batch-03；TOV640並行工作修改不碰。
- 本次產生的草稿batch-01／中途中止batch-03、batch-04、preview／inspect／runtime／可重產layout payload留在本機，不納入提交；metadata batch-01僅提交正式validation證據。
- 程式／基線提交：51888008f29879714e9942b5864db485ec18169a；最終batch-05證據與驗收另提交，一併push origin/master。
- 最終TOV640 HEAD由並行annual-wear工作推進至33e77ab3c7afc72d0dd531d2b660baf08cf8fd63；四個比較core與EAL metadata仍等於保存的固定基線，SHA重新核對通過。沒有回退或更改其工作目錄；後續CLI重跑需獨立固定ref checkout。

### 使用者指定 DRL UT row11 的來源核對與隔離驗證設計

已唯讀核實 reference `00 Reference Document/config/DRL metadata.xlsx`（SHA a386100bb6f47ab9d2a61e7e80c40ad5e87a91cc614e1659584ea41a0161ecff）`DRL UT` Excel row11 = Curve 44887–45500m。根 config 是舊 long workbook，PL sheet 到44000m；不得繼續說所有來源皆缺該段資料。使用者指定 DRL UT row11 適用本 sample，允許以此來源做隔離回歸，不擴大為整份DRL promotion。

實作前範圍：回歸CLI新增 real-only/context/metadata-dir，僅顯式單context允許替代metadata目錄，程序內還原CONFIG_DIR，保留來源SHA及能力snapshot。以reference wide既有adapter讀DRL UT，核對52筆Class/Curve、API與完整report/raw；輸出標示 isolated_reference_only，不合併成正式runtime pass。另盤點DRL PL頁、Bracket疑似公里與DN反向邊界；不推定全PL方向對應、不修原workbook、不批准TL或point分類。舊runtime coverage guard及HTTP400證據保留。

### 本輪實作與驗收收尾

- 新增實際保留量測的Class/Track覆蓋guard及兩項測試，包含真DRL阻擋、detector不得執行、上次成功state保留。缺口回具體HTTP400；detector、EAL/TML與report enrichment不改。
- context registry鎖定DRL sample SHA；回歸CLI支援單context、隔離metadata與blocked診斷，成功隔離狀態不混入runtime pass。新增唯讀逐列／來源interval及歷史證據digest合併工具。
- batch-07確認root舊PL資料52/52未覆蓋，HTTP400且不匯出。batch-09使用指定reference DRL UT row11：252→52筆，Tunnel／Curve全覆蓋，API/report/raw200，完整52筆ChartData與raw21個數值欄核對通過；0例外不能當現場peak/level/ID證據。原workbook與七份正式config沒有改動。
- 最新18組矩陣：3 runtime已驗證（batch-05完整匯出SHA重查）、1 isolated reference通過（batch-09）、14缺fixture。root DRL正式分析仍blocked，尚未promotion。
- 完整相關11檔backend suite重跑：133 passed in38.42s。`coverage-preflight-goldens`重跑AEL/KTL/TKL完整清洗/API/detector，來源SHA、清洗、mapping、所有exceptions/ID/peak/level、能力與chart resolution同原golden完全一致，JSON SHA也相同；沒有再次跑大型匯出或跨程序TOV640比較。命令及限制列於成果文件。
- runtime七份SHA與release批准SHA全部相同；TOV640 HEAD仍33e77ab3c7afc72d0dd531d2b660baf08cf8fd63，本輪未修改。batch-08保留本機為隔離流程初稿，正式採用batch-09。batch-06僅作舊fallback錯誤成功的診斷證據。
- 下一個可執行工作：產出DRL來源標準化候選與來源稽核，釐清DRL UT／獨立DRL PL頁的session選擇、Bracket混合單位、DN反向邊界後提出明確啟用範圍；不再向使用者重索已存在row11區間。TL邊界373組及scope仍需核准，14組真fixture及TML datac仍待補。DAV-20/21維持In Progress。
- Linear MCP本輪可用，已同步使用者兩次確認、版本差異、實作與驗收；commit/push後再附實際SHA。所有原始Excel、歷史候選、使用者DB、未提交修改及新出現未追蹤Raw data目錄均保留，不納入本次提交。


### 新增原始資料承接（2026-10-23）

使用者通知 Raw data 新增 TML/TCL/TKS；三份來源 SHA/size 分別記於 outputs/contract-regression-2026-10-23/batch-10。

- TKS 檔名 `20260902_TKS_DT.csv` 可辨識 DT；產品契約確認 TKS 為 TKL session。已建立只適用該檔案的 SHA registry context，再跑真CSV清洗→API→detector→report/raw。
- TML `.datac` 內容 TRACK=DN、TOV640 Mainline流程；需用TOV640固定核心唯讀執行並與TOV1050相同legacy路徑比較，不修改TOV640。
- TCL OLPAR filename及`ORANGE LINE`不能辨識direction/session；只做清洗與UT/DT假設的區間coverage診斷，不以coverage推斷業務context、不執行detector或列正式通過。
- TCL實測CSV token `Km=32.431` 經二進位float×1000產生`Chainage=32430.999999999996`，而metadata track start為32431m，形成浮點假性缺口。設計修正：依原始十進位token使用Decimal乘1000一次，輸出float canonical metres；不調整metadata邊界、不四捨五入物理測值。另TKS Excel端點實存64522.00000000001m，按明訂atol=1e-9m僅正規化低於容差的二進位表示誤差；大於容差的差異原樣保留。加入來源與metadata端點回歸及重跑TKS/TCL和既有真資料goldens。

Linear MCP工具可見，但本輪同步回覆`Authentication required`。標記 `Linear sync blocked`：影響新fixture進度與本次精度修正尚不能同步DAV-20/21；重新登入並在新session驗證Linear MCP後，第一步補同步本request、batch-10結果、差異及commit/push。
