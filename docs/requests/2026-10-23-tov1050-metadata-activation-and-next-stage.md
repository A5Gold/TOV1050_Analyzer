# TOV1050 metadata 正式啟用與下一階段開發

- 日期：2026-10-23
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-19（metadata）、DAV-10（總計畫）、DAV-20（基線回歸）、DAV-21（metadata 語意相容）
- 負責人：Codex
- 狀態：Done（本次啟用與計畫交付；後續實作由 DAV-20 追蹤）

## 需求與目的

使用者明確批准最新 metadata 成為程式 config，授權替換 config folder；提供與現有 TOV640 Analyzer（EAL/TML）契約相容的下一階段開發計畫。

### 商業規則與限制

- 來源為已驗證的 batch-04 七份 wide candidate；保留原始 reference Excel 及歷史候選。
- 保留合法 bracket overlap、Support 衍生 interval、已確認的五筆外側範圍及 ISL DT row 298 更正。
- canonical chainage 為公尺；wide FromM/ToM 不再乘 1000，舊 long startKM/endKM 才換算。
- 先備份根目錄 config 七份，再替換；DRL 沒有本批核准候選，維持原檔。
- 不修改 TOV640 專案、使用者資料庫或未提交修改；不改 detector 核心與 chart/raw 邊界。

## 現況盤點

- branch master，HEAD 187c0a41d88cebf472dcf5b4d957ff5b22271570。
- 原有 dirty：五份 reference workbook、一份 9 月候選、batch-03，及 Excel lock files；全部排除於本次提交。
- 程式透過 get_config_dir() 讀取根 config；packaged 模式使用 resources/config。
- TOV1050MetadataManager 只讀 long interval sheets；threshold 已支援 wide，須補必要 wide interval adapter。
- TOV640 detector 與 legacy loader 與本 repo 對應檔案相同；完整端到端 parity 仍須下一階段建立。
- 已閱讀 PRODUCT.md、DESIGN.md、既有開發計畫、9 月核准設計及 TOV640 architecture。UI 設計不變。

## 設計

### 使用者補充：TOV640 / TOV1050 metadata 語意差異

使用者補充 TOV640 的 Overlap FromM/ToM、Overlap、Tension Length 與 Landmark FromM/ToM/Landmark 均為區間；TOV1050 則只有 Bracket FromM／Tension Length／Bracket 點資料，沒有明確 overlap 或 landmark 區間。要求提出匹配方式。先實際核對 detector／wear calculator 消費與目前資料，交付相容性設計及具體例子；不因格式對齊自動捏造物理端點，也不改已批准 config。

### 範圍與資料流

1. 重新核對來源 digest、候選驗證結果及實際 wide sheets。
2. adapter 明確區分 wide/long；wide boundary 使用 UT→UP、DT→DN，line/session alias 明確解析；必要 sheet/欄位錯誤明確回報。
3. 保留舊 long 與 DRL PL 行為；不將 bracket 點資料捏造成區間。
4. 不改歷史 candidate 的 review 狀態，以 promotion manifest 記錄使用者批准、來源/目的 SHA、舊版 SHA 與備份。
5. 修正開發計畫中過時的單位與 long-only 敘述；新增分階段交付與驗收門檻。

### 不在範圍

本次不實作整個下一階段、不發布新版 portable、不改 TOV640 或自動遷移資料庫。

### 驗收標準

- 七份根 config 與核准 candidate bytes/digest 一致，備份可追溯。
- 七份 wide workbook × UT/DT 可載入 boundary/track/threshold，公尺無重複換算；long/PL 回歸通過。
- 代表性 CSV 經 detector 可產生 report；相關既有回歸與 metadata validator 通過。
- 計畫列出 TOV640 相容性範圍、DRL/PL 缺口、raw/export 正確性、效能量測與發版門檻。

## 執行紀錄

### 實作

- 根 config 七份已替換為 batch-04 candidate bytes；正式批准記錄位於 config/tov1050-metadata-release.json 及 outputs/metadata-activation-2026-10-23/batch-01/promotion-manifest.json。
- 備份：config/backups/2026-10-23-batch-04-activation-01/；替換前先核對七份來源／mapping／candidate digest，逐方向 preflight，再全份備份及逐檔 atomic replace。若步驟失敗則回復已替換項目；本次無失敗。
- adapter 新增 wide/long boundary 辨識、line/session aliases、UT→UP／DT→DN、公尺 interval 解析、稀疏 bracket rows 排除；缺 sheet／欄位、錯 line、非有限／反向 wide interval 明確報錯。保留 long/PL 路徑。
- 新增 docs/plans/2026-10-23-tov1050-next-stage.md；修正舊 development-plan 中的單位、long-only 與 overlap 敘述；規則集記錄本次明確批准。
- 未改 detector、legacy loader、原始 Excel、歷史 candidate、TOV640 或使用者 DB。
- 已依 AGENTS.md 重新 fast index codebase-memory：5679 nodes／20554 edges，status indexed。
- 依使用者新增格式差異，補 docs/plans/2026-10-23-tov1050-metadata-compatibility.md。實際核對 detector 閾值條件不依 Overlap/Landmark，但 report enrichment 與 TL wear scope 仍有缺口；提出分離點／區間、capabilities、權威端點或確認後 observed-envelope、端點掃描導出 overlap 的方案。
- 唯讀核對14張方向表與已確認component分類：14,143點rows＝14,088 physical＋55 landmark，373組sheet+physical TL；ISL UT254、DT255各僅一點，不能猜範圍。CR289全31點觀察範圍99731–99991m。輸出 capability inventory 與 observed envelope CSV，未將新推導範圍啟用或改寫已批准config。

### 測試與 debug

```text
venv/Scripts/python.exe scripts/validate_tov1050_metadata_candidates.py --candidate-dir outputs/metadata-review-2026-10-23/batch-04/candidates --output-dir outputs/metadata-activation-2026-10-23/batch-01/validation --review-corrections outputs/metadata-review-2026-10-23/batch-04/reviewed-corrections.json --accepted-outer-ranges outputs/metadata-review-2026-10-23/batch-04/accepted-outer-ranges.json
exit 0；七份皆 pass，findings 0。

# 每個測試／smoke 程序指定獨立 TEMP DB_PATH，不使用使用者 DB
venv/Scripts/python.exe -m pytest backend/tests/test_tov1050_adapter.py backend/tests/test_tov1050_metadata_candidates.py backend/tests/test_api_analysis.py backend/tests/test_metadata.py backend/tests/test_metadata_manager.py backend/tests/test_metadata_service.py backend/tests/test_metadata_threshold_levels.py backend/tests/test_metadata_data_cleaning.py backend/tests/test_metadata_tension_length.py backend/tests/test_api_metadata.py backend/tests/test_analyzers.py backend/tests/test_exporter_standalone.py backend/tests/test_exporter_field_injection.py -q --tb=short
127 passed in 28.88s；僅 malformed 測試 fixture 的 dtype FutureWarning，已修正。

venv/Scripts/python.exe -m pytest backend/tests/test_tov1050_adapter.py -k malformed -q --tb=short
3 passed, 26 deselected in 1.47s，無 warning。

git diff --check
exit 0。
```

真實 AEL UT sample 經 /api/analyze→/api/export/report→/api/export/raw/generate（TestClient）均 HTTP 200。476 原始 rows、前後各 trim100、保留276、1.#IO count3309；所有276筆映射 Open／Curve，未 fallback 成 both。report 含 Summary／五類異常 sheets／ChartData276；本 fixture 五類 exception 均0，因此不代表完成 peak/level golden parity。

raw export 刻意傳入一筆 chart payload，但指定 client_session_id 後仍取得完整276筆；逐值核對 Chainage、height1、source_row_number 與重新清洗的來源相同。實測存於 outputs/metadata-activation-2026-10-23/batch-01/runtime-smoke.json。

### 驗收結果

- 七份 × UT/DT＝14組 runtime contract 通過；舊 long 與 DRL PL 測試通過。
- 啟用、digest、備份及代表性分析／匯出達成本次驗收。未建立或發布新版 portable。
- 與 TOV640 的 analyzers.py SHA-256 相同：06b2014471904a3487c41d07815565230cfa84bf930ec586d445bcc222838b90；legacy data_ingestion.py 同為 db36a0ff09d3cb3bcbbe8b4dcfe9ed604bbd011f0faed8a1d40cde4aa6fafa85。
- TOV640 git status 維持既有 frontend/index.html 修改及未追蹤 docs/TOV1050_Migration/；TOV1050 使用者原有 reference／舊候選／batch-03 修改保留，不 stage。Excel lock files 隨使用者開關 workbook 變化，未碰觸。
- 下一階段為 DAV-20 的 S0/S1 契約與真資料 golden regression；DRL/PL 未涵蓋本次核准，90萬筆效能、Settings internal sheet 保護、跨程式完整 parity、portable 驗收仍屬後續計畫。
- 使用者最新補充的 matching-format 需求已交付具體語意相容設計；DAV-21 Todo 承接實作及TL邊界審閱。Schema相容不等於已有Overlap／Landmark物理範圍，不把unknown變成N或空白無事件。此次promotion批准僅涵蓋已驗證七份內容，不自動涵蓋未經確認的TL推導政策。

## Linear 同步

- 本工作階段實際掛載 Linear MCP；已讀 DAV-19、DAV-10，均 In Progress。
- 實作前已成功同步需求／批准／adapter 缺口至 DAV-19、DAV-10；已建立 DAV-20，Todo，parent DAV-10。
- 結果同步：DAV-19 完成 metadata 啟用，DAV-10 維持 In Progress；下一階段實作由 DAV-20 追蹤。
- 已建立 DAV-21 Todo，parent DAV-10、related DAV-20，處理最新格式差異與語意契約。
- Next action：DAV-20 建立真資料 coverage／canonical 比較；DAV-21 補能力狀態及TL邊界審閱／相容輸出。TL/wear完整驗收依賴核准TL區間；不修改TOV640。
- 阻塞／需要決策：本次無；後續缺 fixture／DRL 審閱由下一階段盤點。

## 相關檔案

- backend/app/core/tov1050_metadata.py
- backend/tests/test_tov1050_adapter.py
- outputs/metadata-review-2026-10-23/batch-04/
- docs/development-plan.md
- docs/plans/2026-10-23-tov1050-next-stage.md
- docs/plans/2026-10-23-tov1050-metadata-compatibility.md
- docs/tov1050-metadata-rules.md
- config/tov1050-metadata-release.json
- outputs/metadata-activation-2026-10-23/batch-01/
