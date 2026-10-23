# TOV1050 契約回歸與 metadata 能力實作

- 日期：2026-10-23
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-20、DAV-21；關聯 DAV-10、DAV-19
- 負責人：Codex
- 狀態：In Progress

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

能力契約／點資料及lineage／wear缺口明確拒絕／候選資料保留已通過驗證。373組 physical TL observed envelope 僅供審閱，沒有生成或啟用核准 interval。三份真資料完整 detection goldens：AEL 276 rows／0 exceptions、KTL 830,606 rows／160 exceptions、TKL 501,211 rows／69 exceptions；class/track uncovered rows均0。大型真CSV完整 report/raw batch-05仍在驗證，完成後回填，不沿用早期小樣本作全線驗收。

## Linear 同步

- 本工作階段 Linear MCP 實際掛載，四個 issue 已讀並成功留言承接。
- DAV-19 維持 Done；DAV-10 In Progress；DAV-20/DAV-21 開始實作。
- Next action：完成batch-05真CSV匯出核對；業務資料負責人審閱373組TL邊界／scope及DRL Mainline/PL、UT/DT；開發端取得明確核准後接入interval與wear，並補其餘真fixture／TML datac。DAV-20／21維持In Progress，不宣稱全線或TL/wear parity完成。
- 阻塞／需要決策：核准物理 TL 邊界及未具備的真 fixture，不阻擋能力/回歸基礎實作。

## 相關檔案

- docs/plans/2026-10-23-tov1050-next-stage.md
- docs/plans/2026-10-23-tov1050-metadata-compatibility.md
- docs/tov1050-contract-regression-2026-10-23.md（實測命令、成果及限制）
- docs/tov1050-capability-contract.md（程式與資料語意）
- outputs/metadata-capabilities-2026-10-23/batch-02/（能力矩陣、TL審閱表與七份review-only候選）
- outputs/contract-regression-2026-10-23/（固定基線、goldens、streaming parity與最終batch-05）
- 保留未提交使用者修改：五份reference Excel、一份9月候選及既有未追蹤metadata batch-03；TOV640並行工作修改不碰。
- 本次產生的草稿batch-01／中途中止batch-03、preview／inspect／runtime／可重產layout payload留在本機，不納入提交；metadata batch-01僅提交正式validation證據。
