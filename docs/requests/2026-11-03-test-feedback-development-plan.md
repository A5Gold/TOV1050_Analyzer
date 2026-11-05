# 測試回饋：Metadata、Stagger 與歷史比較設計／開發計畫

- 日期：2026-11-03
- Linear project：TOV1050_Analyzer（P-DAV-1）
- Linear issue：[DAV-27](https://linear.app/david-chu/issue/DAV-27)；相關 DAV-21／DAV-25／DAV-26
- 負責人：Codex 主代理；metadata、Stagger、History 三名子代理
- 狀態：In Review；核准後實作與整合驗收完成，metadata具體scope仍待資料批准

> 後續使用者已明確指定 TOV1050 報表／History 共用 median 檔案鏈。報表 ChartData 的完整 raw 設計由 `docs/requests/2026-11-03-drl-median-history-report.md`（DAV-28）取代：detector、peak、Summary 與獨立 raw CSV 仍完整 cleaned raw，TOV1050 ChartData 改為既有 chainage median；EAL／TML 維持完整 raw。

## 需求與目的

### 使用者與流程

依使用者實測回饋，先解釋 DRL metadata 格式差異、Exception Generator 的 Overlap／Tension Length／Landmark 缺資料與正值 Stagger Left 未見例外，並設計 History Comparison 全線儲存及大型報表比較的修正計畫。使用者明確要求使用子代理、先設計及草擬開發計畫再實作。

### 商業規則與限制

- 保留開始時全部未提交程式、來源、報表與候選；批准後依計畫修改程式，正式資料不覆寫，不提交既有改動。
- 來源資料、正式 metadata、SQLite DB 不寫入；候選不自動 promotion。
- 點資料不等於核准區間，未知 overlap 不等於 N；canonical chainage 為公尺。
- 延續無 C/M 分型 BWA／Fixed／Spring 視作 Contact、M 為 Messenger 的已記錄決策；不因此核准任意配對或 coverage。
- 新使用者指示要求 chart downsampling 僅供圖表，detector／crossing／overshoot／peak／export 用完整 raw。現況另有 DAV-24 median reduction 歷史設計，需在計畫明列差異，禁止把它當圖表抽樣或靜默更改基線。
- 使用者2026-11-03補充：所有線Stagger Left／Right共用相同門檻絕對值，正值Left、負值Right。設計採全線canonical magnitude，非僅補TWL單側，也非跨線套用同一數值。

## 現況盤點

- HEAD：4e50d90f175c607cf5a6937c4137f6933dc911dc，master；開始即有大量 modified／untracked（包含 DAV-26 實作）。
- 已讀 PRODUCT.md、DESIGN.md、docs/architecture.md、metadata 規則／approved interval 契約、10月29日 request 及 DAV-21／DAV-26。
- 本工作階段 Linear MCP 實際掛載，list_projects／list_issues／get_issue 成功；DAV-21 已追加本次承接狀態。
- codebase-memory 已索引：C-Smart-Maintanence-TOV1050_Analyzer；發現優先使用 graph，再核對磁碟現況。
- 已檢視指定 Exception Generator graph.png：畫面有 median reduction 標籤、160筆例外、Stagger Right 負值；截圖無法單獨證明正值漏報或比較程序失敗原因。
- 三名子代理完成唯讀核實；根因及精確程式路徑列於設計／計畫。DRL為初始long格式未遷移；ISL全頁已讀678點但不是核准區間；TWL缺Left配置確定造成NaN gate；九線Save已在現行source，需版本核對；History單請求重讀ChartData與300秒proxy是明確線索，未有當次日誌不能唯一歸因。

## 設計

### 範圍

Metadata schema／來源適配及安全遷移、Stagger 符號與真檔判定診斷、History 全線 context／持久化及比較工作生命週期。

### 不在範圍

不啟用未核准候選、不跨線借用門檻、不寫使用者DB、不封裝或發布。

### 資料流與錯誤處理

設計文件：`docs/superpowers/specs/2026-11-03-test-feedback-design.md`。
開發計畫：`docs/plans/2026-11-03-test-feedback-development-plan.md`。

### 驗收標準

每項回饋均有現況證據、確定／假設區分、方案比較、分階段修改位置、測試矩陣、完成條件及資料依賴。文件與 Linear 實際同步，功能及原始資料維持本次起點。

## 執行紀錄

### 實作

使用者 approve 後開始實作：

- P1：共用 magnitude adapter，legacy 單側鏡像，雙側衝突／非數值／非有限值阻擋；正式 workbook 未改。
- P2：detector 用完整 cleaned raw；同 Km median 僅供圖表。加入不縮減量測的 source/context/pass gap 標記；session 僅保留 compact chart，匯出依 SHA 重載完整來源。新增 detection_algorithm／detection_data_mode provenance，History 拒絕舊 median 與新 raw 混比。介面說明同步修正。
- P3：review-only batch-01 重驗完成，詳見 `2026-11-03-metadata-p3-revalidation.md`；25 來源 SHA 一致，DRL 4532／Contact 7152 格 parity 通過；未 promotion。
- P4：History 新增背景 job、例外 sheet 白名單、串流 scope 驗證、disk numeric chart cache、按需視窗、session/job export 隔離；前端輪詢／取消／網路恢復／stale guard。子代理已完成相關整合測試；主代理執行真檔與 Electron 驗收。

### 測試與 debug

實際執行（均為本次結果，套件有重疊，不相加）：

- P1 metadata/adapter/capabilities/chart：73 passed；metadata P3 隔離：77 passed。
- median snapshot/chart/Stagger/adapter：68 passed。
- API analysis/raw契約/background jobs/chart/context：89 passed；raw provenance＋chainage reducer：50 passed。
- History scope＋auto persistence：21 passed；History子代理 jobs/scope/compare/background：36 passed。
- Vitest ChartComponent：16 passed；ExceptionGenerator：10 passed（更正文案測試後通過，有既有 act warning）。
- `python -m pytest backend/tests -q` 曾執行；因大量既有長測試與早期契約差異而中止，不能宣稱全套通過。改執行上述風險相關套件；已修正 compact raw_df 相容 alias 及舊測試將匯出誤比 chart median 的期待。
- 三實檔固定 median P1 對照完成：TWL Left 0→116／109；Right保持94／111；TML全類型一致。初版 raw 對照發現缺segment會跨gap合併，已補 annotate_raw_samples，最後已重跑完整segment診斷：兩TWL raw數量與raw-integration一致，TML全類型一致。semantic-diff已更新，舊raw counts不作驗收。
- 相關 backend 13 套件：218 passed in 78.73s（targeted-pytest.log）；最終 preflight/raw/chart：39 passed in 33.59s；metadata enrichment：23 passed。套件有重疊，不相加。
- 前端相關 Vitest：4 files／52 passed（--maxWorkers=1）；TypeScript `npx tsc --noEmit` 與 `npm run build` 成功。存在既有 act／chunk／xlsx 提示。
- `scripts/validate_raw_history_20261103.py` 於獨立 outputs 生成完整 raw ChartData 報表並讀回驗證，不覆寫指定參考報表。九月完成：838859 raw／ChartData 列、289 例外（Low Height65、High Height2、Wear1、Left118、Right103），分析59.39秒；含完整xlsx匯出及逐列讀回共1158.13秒。六月完成：830792 raw／ChartData列、330例外（Low Height69、High Height9、Wear17、Left112、Right123）；含匯出讀回1193.2秒。兩份原始SHA均一致。
- `scripts/validate_history_http_20261103.py`：舊 median 報表 direct／Vite proxy 比較結果一致9筆；完成約169.8／169.3秒；submit0.606／2.210秒；status P95 0.08354／0.08446秒。proxy submit未達≤2秒目標。overview2373點／203507bytes；來源SHA一致。這些數值不代表新raw報表性能。
- 已補raw例外的三欄 enrichment 及JSON evidence，使用maxLocation按核准provider lookup。approved fixture通過；正式來源欠核准coverage時維持unknown。TML最終annotated raw Left20／Right46，與median一致。
- 最終來源基線：outputs/validation-2026-11-03/final-source-sha256.json；`git diff --check` exit0（既有LF／CRLF提示）。完整dirty清單含起點修改，不全部歸本次。

### 驗收結果

設計已獲批准，P1/P2/P4 軟體實作已有針對性回歸；P3 review-only 驗收完成。P5 完整 raw 新報表、背景比較、真 Electron、DB隔離 round-trip 已通過。取消／斷線恢復／stale guard以相關unit及API回歸驗證；本次真Electron未另做中途關閉程序或取消的破壞性演練。

## Linear 同步

- 最後同步日期：2026-11-03
- Issue 狀態：DAV-27 In Review；DAV-21 維持 In Progress；DAV-26 維持 In Review。Linear MCP本工作階段實際掛載，查詢與子代理P1/P3留言均成功。
- Next action：軟體變更交付審閱；資料負責人補DRL／TL／Landmark明確scope，未核准維持unknown。沒有自動封裝或發布。
- 阻塞／需要決策：DRL scope／方向、實體配對及 coverage 核准；比較斷線的實際程序／資源日誌未提供。

## 相關檔案

- 本 request、對應設計及開發計畫；既有未提交清單以本回合 git status 起點為準。

### 最後邊界回歸

- 子代理審查發現過期pending job的404／410會阻擋新compare，已只忽略取消舊工作時的這兩種狀態，其他錯誤照常處理；History View 8 passed。
- chart envelope保留跨抽樣間隔的缺值斷線，以有界額外null點避免跨缺值連線，保留各channel極值；History job／chart 8 passed，包含201點內部null回歸。
- Electron harness補建立比較步驟及ready後chart/detail／export／隔離DB讀回補驗，最終全部通過；初次selector／缺comparison步驟的逾時屬驗收腳本問題，已修正後重跑。

最終Stagger診斷：`python -u scripts/validate_stagger_policy_20261103.py` 成功；三檔來源均未改，兩TWL固定median除新增Left外其餘canonical完全一致，raw差異有來源列證據；TML全類型在三模式皆一致。

### 本次相關修改與工作樹界線

本次在既有dirty工作樹上修改：backend/app/api/endpoints/analysis.py；core/metadata.py、chainage_reduction.py、report_context.py、background_jobs.py；新增core/history_report_reader.py、tests/test_stagger_magnitude_policy.py、test_raw_detection_contract.py、test_history_compare_jobs.py，並更新test_api_analysis.py。前端相關：HistoryCompareView、ComparisonChart、useAnalysisStore、types/api、ExceptionGeneratorView、About說明及對應測試。新增2026-11-03驗收scripts、request／plan／spec與outputs證據。

完整未提交清單：outputs/validation-2026-11-03/final-dirty-status.txt；其中含大量起點已存在的程式／資料修改與未追蹤檔，不能全部歸本次。本次沒有commit、封裝或發布。14來源最終SHA核對：source-final-recheck.json，全部unchanged=true。

### 最終 Electron 大檔驗收

`node scripts/validate_history_electron_20261103.mjs` 使用真source Electron、backend與Vite proxy，沒有攔截API，DB明確隔離在outputs。

- 兩raw新報表背景比較成功：worker877.641秒；含上傳／UI取回895.158秒（約14分55秒）。HTTP202提交含約164MB上傳12.977秒，未達≤2秒工程目標；狀態查詢P95 0.474秒達標。不能宣稱總時間即時或全部效能目標達成。
- 重複例外15筆：Low Height4、Stagger Left6、Stagger Right5；九線EAL/TML/AEL/TCL/KTL/ISL/TWL/TKL/DRL均出現在Save選單。
- UI save HTTP200、15筆；API讀回15筆；補驗重存後仍15筆，新的read-only SQLite連線核實每筆區間與峰值一致、無重複。
- overview來源838859／830792點，回傳1469／1493點；detail2784／2820點皆完整raw，包含例外peak；比較Excel7904bytes，全部15個ID一致。
- 證據：electron-history/validation.json、postchecks/validation.json、result.json、nine-line-save-dialog.png、history-ready.png、memory-summary.json。
- 資料／效能限制：完整xlsx匯出讀回約19–20分鐘，大檔比較約15分鐘，工作背景執行並可輪詢；正式metadata未核准coverage仍unknown。原始資料及正式DB未覆寫；尚未封裝／發布。

最終 production build 再驗成功：`npm run build`（NODE_USE_SYSTEM_CA=1），3m27s，既有chunk/assert/xlsx提示；TypeScript成功。Linear DAV-27已實際更新為In Review並重寫最終實作、測試、性能限制及next action。
