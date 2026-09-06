# TOV1050 metadata、Exception Generator 效能與使用者導引

- 日期：2026-09-02
- Linear project：TOV1050_Analyzer（https://linear.app/david-chu/project/tov1050-analyzer-d897dfced2f1）
- Linear issue：DAV-10（TOV1050 metadata、效能與 UX 交付）
- 負責人：Codex + 使用者審閱
- 狀態：In Progress（candidate promotion/write-back 尚待使用者核准）

## 需求與目的

### 使用者與流程

鐵路接觸網維護分析人員在 Windows Electron 工作台中選擇 TOV1050 CSV、確認 line/track/session/station context、執行異常分析、檢視圖表並匯出報告。使用者需要：

- 以 TOV640 寬表 metadata 邏輯維持未來 integration 相容性。
- 快速選擇 TOV1050 run list 的 line、station start/end、task no.，同時保留手動輸入例外案例。
- 在大檔分析與 Excel 匯出期間知道目前進度、可預期等待時間與錯誤原因。
- 以圖像理解各模組資料流與演算法，而不是只閱讀文字 dialog。

### 商業規則與限制

- `00 Reference Document/config/DRL metadata.xlsx` 的 TOV640 寬表格式是外部權威範本；不可把它誤判為待淘汰的舊格式。
- TOV1050 仍使用既有 line/session/track、CSV `Km -> Chainage`、`1.#IO` 清洗、前後 100 rows trim 與 fail-closed metadata resolution 規則。
- TOV640 detector 語意可重用；TOV1050 adapter 只負責 CSV、欄位、metadata workbook 與 context 差異。
- `TKS` 是 `TKL` session；UI 顯示欄位使用 `Track`，不再使用 `Direction`。
- TOV1050 原始 CSV 的 `Km` 會在 adapter 邊界轉成公尺；graph、`FromM/ToM`、metadata interval 與 bracket mapping 統一使用 `m`，以貼合 TOV640。
- 不修改 `C:\Smart Maintanence\TOV640_Analyzer`，不覆蓋既有未提交修改。

## 現況盤點

- 相關程式碼：`frontend/src/views/ExceptionGeneratorView.tsx`（617 行單一視圖）、`frontend/src/components/ChartComponent.tsx`（Plotly scatter traces）、`frontend/src/views/MetadataEditorView.tsx`、`backend/app/api/endpoints/analysis.py`、`backend/app/core/tov1050_metadata.py`、`backend/app/core/tov1050_contract.py`。
- 相關 API／資料流程：`POST /analyze` 目前載入完整 DataFrame 並回傳 column-oriented `chart_data`；`GET /metadata-preview` 提供 metadata 預覽。分析結果由 `ExceptionDetector.analyze` 產生。
- 現有測試：`backend/tests/test_tov1050_adapter.py`、`test_tov1050_metadata_candidates.py`、`test_metadata_service.py`、`test_api_analysis.py`、`frontend/src/views/__tests__/ExceptionGeneratorView.test.tsx` 等；repo 尚有未提交修改。
- 已知風險或阻塞：`00 Reference Document/config/DRL metadata.xlsx` 與根目錄 `config/DRL metadata.xlsx` 格式不同，需明確分成 reference workbook 與 packaged runtime workbook。

## 設計

### 範圍

1. 建立寬表 metadata 外部契約與 TOV1050 workbook 標準化方案，涵蓋 ISL、KTL、LAR_AEL、LAR_TCL、TKL、TKS、TWL，並以 DRL/TOV640 EAL 對照及 `TOV1050 TL-BK No.xlsx` 驗證。
2. 建立大 CSV streaming/chunk、聚合後圖表取樣與 outlier 保留的效能方案。
3. 重新設計 Exception Generator 配置輸入：run list quick-fill、Track 選擇、Station/Task 可覆寫、檔名 fallback 與驗證狀態。
4. 為六個分析模組加入 skeleton/staged progress；匯出加入背景 processing 狀態。
5. 以 gpt-image-2 產生輸入表單概念稿及各模組/整體架構說明圖，整合至對應 Algorithm Explain dialog 與 About。
6. 保留現有 Graph／Table 結果版面，加入圖表多解析度效能最佳化、Graph/Table 選取同步與 FromM-ToM zoom 定位。

### 不在範圍

- 不重寫 TOV640 detector 的判定語意。
- 不把 reference workbook 直接當成 packaged runtime 檔案；runtime 是否採寬表或 adapter 轉換需在設計審批後決定，且所有 TOV1050 km 來源值必須明確轉成 m 並記錄來源。
- 不在未完成 benchmark 前承諾固定秒數或記憶體上限。
- 不引入第二套 UI design system；沿用 MUI/Plotly、既有 token 與 Electron workflow。
- 不以 Graph／Table 子頁重新設計取代既有工作流；只加入可驗證的 performance、selection sync 與 zoom enhancement。

### 資料流與錯誤處理

候選資料流：

`CSV stream (Km) -> row lineage/cleaning -> Km-to-m normalization -> metadata wide-table adapter (m) -> detector state -> exception summaries (FromM/ToM) -> chart decimation + exact outlier points -> UI/export`

任何 schema、metadata sheet、interval overlap/ambiguity 或必要 context 錯誤都 fail closed；`1.#IO`、部分 wire 缺測與可計數的 invalid numeric cell 顯示在 cleaning summary，但不靜默產生 exception。圖表取樣不可刪除 exception peak、threshold crossing、區間邊界或 selected exception 附近資料。

### 驗收標準

- 八份 TOV1050 metadata workbook 的寬表 schema、sheet 命名、欄位型別與 interval 資料可被檢查並產生差異報告；DRL 與 TOV640 EAL/TML 的對照結果可追溯。
- `TOV1050 TL-BK No.xlsx` 的 line/track/chainage/bracket mapping 可被 resolver 或報告引用，重複與空白資料會被診斷。
- TOV1050 `Km` 來源值與標準化後的 `m` 值可互相追溯；`98150.2` 類型的 graph 座標與 `FromM/ToM`、metadata boundary 單位一致。
- 116 MB KTL CSV 與 32 KB DRL CSV 都可完成分析；chunk/full-frame 結果在代表性 fixture 上一致。
- Plotly UI 在取樣後仍保留所有異常峰值與選取定位，互動不因完整 raw trace 阻塞主執行緒。
- Exception Generator 可由 run list 快速填入 line、track、station start/end、task no.，且每個文字欄位仍可覆寫並通過 validation。
- 六個模組的分析與匯出 loading 狀態可辨識 stage、percentage、取消/錯誤/完成結果，並尊重 reduced-motion。
- About 與每個 Algorithm Explain dialog 顯示與現行 code/data contract 一致的架構、資料流、工作流與演算法圖。

## 執行紀錄

### 實作

- 2026-09-02：確認本工作階段實際掛載 Linear MCP 與 codebase-memory MCP；已重新 index current worktree。
- 2026-09-02：完成七份 TOV1050 metadata candidate 的初步產生與來源 audit；來源 workbook 維持唯讀。
- 2026-09-02：開始審核 ISL、KTL、LAR_AEL、LAR_TCL、TKL、TKS、TWL candidate，重點為 wide schema、interval overlap、invalid rows、TL-BK mapping 與來源 row lineage。
- 2026-09-02：完成 provenance-preserving validator 強化；修正 location parity tuple 與 provenance target 契約，並將 reversed interval、TL-BK marker、exact duplicate identity、location/bracket conflict、provenance mismatch 納入可追溯診斷。七份 candidate 重新驗證結果為 ISL/KTL `fail`，LAR_AEL/LAR_TCL/TKL/TKS/TWL `review_required`；所有候選仍維持 review-only。新增 90 萬筆 benchmark 腳本與摘要，確認 detector 使用 899,800 筆完整資料、chart 僅送出 12,000 個 envelope 點。
- 2026-09-02：完成 detail chart session/tab isolation review；`ChartComponent` 以 session key remount，detail request 帶入 `file_path`/`line`，後端若來源不同於最近一次分析則重新載入該 CSV，避免全域 raw cache 汙染其他 tab。清除選取時恢復 overview payload。
- 2026-09-02：依使用者要求唯讀重跑 `scripts/validate_tov1050_metadata_candidates.py --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL`；因 ISL/KTL 仍有 `fail` finding，程序回傳 exit code `1`，但已正常產生完整 JSON/Markdown audit。新增 `docs/audits/2026-09-02-tov1050-metadata-review-summary.md`，整理逐線 overlap、反向 interval、TL-BK marker/conflict、invalid row、provenance 與人工決策表；原始與 candidate workbook 均未覆寫。
- 2026-09-02：使用 A6API `gpt-image-2` 產生四張模組演算法圖，並接入 Exception Detector、Trend Analysis、Wear Calculation、History Compare 四個 Algorithm Explain dialog；原有 Stagger 圖一併納入，五個 dialog 均具備圖像、caption/legend 與可測試 alt text。圖片同時保存在 `docs/visual-guide-assets/` 與前端 assets，未以圖中文字取代程式規格。

目前階段只允許產生候選 workbook、validation、audit 與 provenance 報告；未經使用者批准不得 write-back `config/*.xlsx` 或 `00 Reference Document/config/*.xlsx`。

### 測試與 debug

```text
既有 backend targeted tests（20 passed）、frontend TypeScript 與 production build 已完成；validator/adapter/chart focused suite 19 passed；七份 candidate validation 已產生 JSON/Markdown；900,000-row benchmark 已完成。
Benchmark：load 10.971s（82,016.9 rows/s）、detect 5.697s（157,931.4 rows/s）、chart 3.674s、peak RSS 353,013,760 bytes、raw detector parity=true。
Candidate validation：ISL `fail`（DT 反向 interval 6 列、同軌 overlap 29、provenance invalid mismatch 6）；KTL `fail`（DT 反向/overlap 與 provenance invalid mismatch 10）；LAR_AEL/LAR_TCL/TKL/TKS/TWL `review_required`（TL-BK identity/location conflicts 或 invalid mapping 需人工核准）。
Isolation focused tests：backend chart-data reload test 通過；metadata/adapter/chart targeted suite 15 passed；frontend production build 通過。ExceptionGeneratorView Vitest 在本機執行超過 90 秒無輸出，已中止並列為待查測試環境／runner hang，非功能失敗判定。
Algorithm Explain focused tests：Trend、Wear、History Compare 3 個 test files／4 tests 以 Vitest fork pool 單 worker 全部通過；threads pool 曾因 worker 啟動逾時而未完成，視為 runner 環境限制，非功能 assertion 失敗。ExceptionGeneratorView multi-tab focused test 亦以 fork pool 單 worker 通過（4 tests）；執行耗時 178 秒，主要成本在 import/environment，並出現既有 MUI Tabs `act(...)` warnings，沒有 assertion failure。
```

### 驗收結果

部分驗收完成。候選 workbook 的 wide schema/row parity、LAR mapping alias、provenance row parity、status/target mismatch、digest guard、reversed interval 與 TL-BK diagnostics 已有自動驗證；ISL/KTL 的來源 overlap/反向列與所有 mapping marker/conflict 仍需使用者核准，候選不得直接啟用。Detail chart 已完成跨 tab source isolation；About 與五個 Algorithm Explain dialog 的視覺素材已補齊並完成 focused assertions。

## Linear 同步

- 最後同步時間：2026-09-02
- Issue 狀態：DAV-10 為 In Progress；本工作階段已確認 Linear MCP 可用，將同步本階段 audit、validation、測試與下一步。
- Next action：由使用者審閱 ISL/KTL 的 DT overlap/反向 interval、ISL/KTL provenance invalid mismatch、TL-BK marker/identity/location conflicts 與 TWL invalid Location，再決定是否批准 candidate promotion；批准前維持 review-only。threads pool runner hang 已以 fork pool 單 worker 驗證替代；ExceptionGeneratorView focused multi-tab 已通過，仍可另行處理其測試中的 `act(...)` warnings 與 import/environment 慢速問題。
- 阻塞／需要決策：candidate 尚未獲准 write-back；ISL/KTL 的 overlap 與 TL-BK invalid rows、以及 wide threshold adapter 啟用時機仍需使用者審閱。
- Linear sync：本階段已透過 Linear MCP 更新 DAV-10，附上 validation、benchmark、測試與下一步。

## 相關檔案

- `00 Reference Document/config/DRL metadata.xlsx`
- `00 Reference Document/config/TOV640_Analyzer/EAL metadata.xlsx`
- `00 Reference Document/TOV1050 TL-BK No.xlsx`
- `00 Reference Document/TOV1050 Run List.xlsx`
- `frontend/src/views/ExceptionGeneratorView.tsx`
- `frontend/src/components/ChartComponent.tsx`
- `backend/app/api/endpoints/analysis.py`
