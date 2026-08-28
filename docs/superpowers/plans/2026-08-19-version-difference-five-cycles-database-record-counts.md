# Version Difference 五週期與 Database Record 完整數量開發計畫

日期：2026-08-19

設計來源：`docs/superpowers/specs/2026-08-19-version-difference-five-cycles-database-record-counts-design.md`

執行狀態：功能實作、資料 migration、regression、browser smoke 與 packaged-resource 驗證完成；implementation checkpoint commit 已建立

## 執行約定

本文件是實作期間的 canonical checklist。

1. 每個 phase 開始前重新閱讀本文件及對應設計章節。
2. 每完成一個 phase，立即把狀態與驗證結果寫回本文件，再進入下一 phase。
3. 若實作需要偏離已批准設計，先記錄差異、原因與影響；行為或資料口徑改變時先向使用者取得批准。
4. 所有 symbol 修改前使用 codebase-memory impact/context 查詢；修改後重新索引並驗證 affected scope。
5. 工作樹現有變更全部視為使用者工作。只 patch 本計畫列出的相關區域，不回復、不格式化、不提交無關檔案。
6. `frontend/src/types/api.ts`、`package.json`、EAL Excel、`PRODUCT.md` 與 `DESIGN.md` 已有未提交狀態，stage/commit 前逐檔確認 diff ownership。
7. 首次及每次獨立 `npm` / `npx` process 都設定 `$env:NODE_USE_SYSTEM_CA='1'`，保留 HTTPS registry 與 `strict-ssl=true`。
8. Root dev/package commands 只從 canonical checkout `C:\Smart Maintanence\TOV640_Analyzer` 的 `main` 執行。

## Phase 狀態

| ID | Phase | 狀態 | 完成證據 |
| --- | --- | --- | --- |
| P0 | 設計規格與開發計畫 | 完成 | 本文件與設計規格已建立並進行 self-review |
| P1 | Version Difference backend 與 contract tests | 完成 | 2026-08-19：固定角色 `previous_1` 至 `previous_4`；focused API tests 9 passed |
| P2 | Shared cycle descriptor、store 與 API client | 完成 | Shared descriptor、optional-gap FormData 與 store/API tests：25 passed；focused ESLint passed |
| P3 | 五槽 upload UI 與五週期 charts | 完成 | Version Difference view/chart focused tests：13 passed；五槽 responsive layout、共用 cycle colors、20 raw traces/4 comparisons contract covered |
| P4 | Database Record shared predicates 與 aggregates | 完成 | Database core/API focused tests：55 passed、16 skipped；完整 total 與 section aggregates 共用 parameterized predicates |
| P5 | Database Record frontend counts 與 server-side section | 完成 | Database Record focused frontend tests：27 passed；section fetch、完整 badges、loaded subset 語意 covered |
| P6 | Seed v2 assets 與一次性 v1 replacement | 完成 | Seed tests：16 passed；v2 manifest/hash/count validation、eligible-v1 savepoint replacement、rollback/idempotence covered |
| P7 | Product/design docs 與完整 regression | 完成 | 指定 frontend regression：48 passed；frontend build 成功；backend targeted regression：107 passed、28 skipped；唯一既有 failure 為 test 仍期待 schema 1.6，現行 baseline 為 1.7 |
| P8 | 實際 DB migration、UI 與 package 驗證 | 完成 | AppData DB v1→v2、backup、integrity/foreign-key、second-startup idempotence 與 package resources 驗證完成 |
| P9 | Codebase re-index、scope audit 與 handoff | 完成 | moderate graph re-index、changed-symbol trace、dirty-worktree ownership audit、diff check 與 focused implementation checkpoint 完成 |

## P0：文件關卡

### 工作

- 寫入已批准的 architecture、data contracts、UI、seed migration、錯誤處理與驗收條件。
- 建立本開發計畫，列出具體 files、tests、commands 與 stop conditions。
- 掃描未決標記、矛盾與範圍漂移。
- 只 stage/commit 兩份文件，保留所有既有 dirty changes。
- 請使用者審閱書面規格與計畫；未確認前不修改功能程式。

### 完成條件

- 設計與計畫均無未決策項目。
- Commit scope 只有本次兩份 docs。
- 使用者批准書面文件後才開始 P1。

## P1：Version Difference Backend 與 Contract Tests

### 先寫/擴充測試

檔案：

- `backend/tests/test_version_difference_api.py`

測試案例：

- Latest + Previous 1 的既有二檔 request 維持。
- 五檔 request 回傳 `previous_1` 至 `previous_4`，順序固定。
- Previous 2 空白而 Previous 3 存在時不重新編號。
- 每個 Previous cycle 獨立呼叫 alignment，file name 與 key 正確。
- Optional Previous 缺 ChartData 只令該 comparison unavailable。
- Latest 缺 ChartData 與 corrupt/unsupported workbook 維持既有 error contract。

### 實作

檔案：

- `backend/app/api/endpoints/version_difference.py`

步驟：

1. Impact/context lookup `analyze_version_difference` 與 `_load_chart_data`。
2. 新增 optional `previous_3`、`previous_4` multipart fields。
3. 以 ordered roles 組 uploads，避免多段 if/loop mapping 不一致。
4. 維持 additive response shape 與 partial-unavailable semantics。

### Gate

- `test_version_difference_api.py` 全綠。
- 二檔與三檔既有 tests 不需修改預期語意。
- 更新本文件 P1 狀態與測試結果。

完成證據（2026-08-19）：

- `python -m pytest backend/tests/test_version_difference_api.py -q` -> `9 passed in 6.44s`。
- `git diff --check -- backend/app/api/endpoints/version_difference.py backend/tests/test_version_difference_api.py` 無 whitespace error（僅 Windows LF/CRLF 提示）。
- Optional gap contract 已驗證：省略 `previous_2` 並提供 `previous_3` 時，response key 保持 `previous_3`，不重新編號。

## P2：Shared Cycle Descriptor、Types、Client 與 Store

### 先寫/擴充測試

檔案：

- `frontend/src/store/__tests__/useVersionDifferenceStore.test.ts`
- 新增 `frontend/src/api/__tests__/versionDifferenceClient.test.ts`

測試案例：

- 新 tab 初始化五個 roles。
- Previous 3/4 set/remove 清除 stale response/error。
- Compare 只要求 Latest/Previous 1。
- Optional gaps 保留 role；API client 只 append 有檔案的 exact form fields。
- Concurrent tabs、reverse completion、close-loading-tab 等既有 invariants 維持。

### 實作

檔案：

- 新增 `frontend/src/constants/versionDifferenceCycles.ts`
- `frontend/src/types/api.ts`
- `frontend/src/api/client.ts`
- `frontend/src/store/useVersionDifferenceStore.ts`

步驟：

1. 建立 approved five-color ordered descriptor，派生 file role 與 comparison key types。
2. 擴充 API comparison key union 到 `previous_4`。
3. Client 從 descriptor 建 FormData，不壓縮 optional gaps。
4. Store files record、snapshot 與 reset 使用同一 role set。
5. 只 patch `api.ts` 相關 interfaces，保留 wear projection 等無關 diff。

### Gate

- Store/API focused tests 全綠。
- TypeScript 不出現 duplicated role/color maps。
- 更新 P2 狀態。

完成證據（2026-08-19）：

- `npm --prefix frontend test -- --run src/api/__tests__/versionDifferenceClient.test.ts src/store/__tests__/useVersionDifferenceStore.test.ts` -> 25 passed。
- shared descriptor 位於 `frontend/src/constants/versionDifferenceCycles.ts`；client 與 store 均由 descriptor 派生欄位，optional gap 保留原 role。
- focused ESLint 通過；frontend build 於 P7 再次驗證。

## P3：五槽 Upload UI 與五週期 Charts

### 先寫/擴充測試

檔案：

- `frontend/src/views/__tests__/VersionDifferenceView.test.tsx`
- `frontend/src/components/VersionDifference/__tests__/VersionDifferenceChart.test.tsx`

測試案例：

- 五個 slots 與 role-specific accessible names。
- Latest/Previous 1 required，Previous 2-4 optional。
- Slot swatch/accent 與 descriptor colors 一致。
- 長檔名不移動 remove control。
- 五個 cycles 產生 20 raw traces。
- 四個 difference plots 各 4 traces，labels/colors 對應。
- Missing Previous 2 但有 Previous 3 時只顯示對應 difference。
- Visibility、opacity、trace order、zoom sync、unavailable state 回歸。

### 實作

檔案：

- `frontend/src/views/VersionDifferenceView.tsx`
- `frontend/src/components/VersionDifference/VersionDifferenceChart.tsx`

步驟：

1. Slots 由 descriptor map render。
2. 使用 cycle color outline、swatch、drag-active wash、neutral text 與 focus-visible treatment。
3. Layout 設定 xs/sm/lg/xl 的 1/2/3/5 columns，slot geometry 穩定。
4. Chart label/color lookup 全部轉用 descriptor。
5. 確認圖表容器與 Series popover 在四個 difference panels 下仍可用。

### Gate

- View/chart focused Vitest 全綠。
- `DESIGN_VARIANCE 3 / MOTION 2 / DENSITY 8` 未被無關 restyle 破壞。
- 更新 P3 狀態。

完成證據（2026-08-19）：

- Version Difference view/chart focused tests -> 13 passed。
- 五個 upload slots 使用 Latest/Previous 1-4 固定 role；Latest 與 Previous 1 required，其餘 optional；upload surface、swatch、raw trace 與 comparison trace 共用 descriptor colors。
- chart contract 覆蓋最多 20 raw traces、4 個 difference panels、optional gap 與 unavailable state。

## P4：Database Record Shared Predicates 與 Aggregates

### 先寫/擴充測試

檔案：

- `backend/tests/test_database.py`
- `backend/tests/test_database_records_api.py`

測試案例：

- 3 筆資料、`limit=2` 時 records 2、total 3。
- line/track/level/action/type/task/date/chainage filters 對 list 與 total 一致。
- Section aggregates 套用同一 non-section scope。
- Active section 影響 records/total，但 section_counts 保留所有 section navigation counts。
- `LOW`/`LOW S1` -> `low_s1`；NULL/unknown -> `unknown`。
- `all == mainline + rac + low_s1 + lmc + unknown`。
- offset 不影響 total/counts；empty query 全 0。

### 實作

檔案：

- `backend/app/core/database.py`
- `backend/app/api/endpoints/database_records.py`

步驟：

1. Impact/context lookup `query_repeated_records`、`count_repeated_records`、endpoint callers。
2. 抽取 parameterized predicate builder，保留所有既有 filter semantics。
3. 讓 list、count、section aggregate 共用 builder。
4. Aggregate query 排除 active section，但 records/total 包含 active section。
5. 擴充 Pydantic response model，於同一 connection 讀取三種結果。
6. 不提高預設 1,000 / max 5,000 limits。

### Gate

- Database core/API focused pytest 全綠。
- Query params 無 string interpolation of values。
- Existing export/import/check-one-year tests 維持。
- 更新 P4 狀態。

完成證據（2026-08-19）：

- `python -m pytest backend/tests/test_database_records_api.py backend/tests/test_database.py -q` -> 55 passed、16 skipped。
- `query_repeated_records`、`count_repeated_records` 與 `get_repeated_record_section_counts` 共用 `_build_repeated_record_predicates`；所有 filter values 經 SQLite parameters 傳入。
- API 在同一 read transaction 回傳 bounded `records`、完整 filtered `total` 與排除 active section 的 navigation `section_counts`。

## P5：Database Record Frontend Counts 與 Server-side Section

### 先寫/擴充測試

檔案：

- `frontend/src/components/DatabaseRecord/__tests__/LineTabPanel.test.tsx`
- `frontend/src/views/__tests__/DatabaseRecordView.test.tsx`
- 新增 `frontend/src/store/__tests__/useDatabaseStore.test.ts`

測試案例：

- Store 保存完整 total/section_counts，records 仍可只有 1,000。
- EAL badges 精確為 All 1,826 / Mainline 1,584 / RAC 132 / LOW S1 16 / LMC 94。
- Section click 觸發 API fetch 並帶 exact section。
- Header truncated/complete copy 分別正確。
- `Batch Edit Loaded (1000)`，不再宣稱 All。
- Accessible name 包含 count；Unknown count > 0 才顯示。
- Request failure 不以 local records 重算完整 badges。

### 實作

檔案：

- `frontend/src/types/api.ts`
- `frontend/src/store/useDatabaseStore.ts`
- `frontend/src/components/DatabaseRecord/FilterPanel.tsx`
- `frontend/src/components/DatabaseRecord/LineTabPanel.tsx`
- `frontend/src/views/DatabaseRecordView.tsx`

步驟：

1. 增加 typed section counts 與 store initial/reset state。
2. Fetch success 原子更新 records/total/section counts。
3. FilterPanel 將 section 放回 API filters，effect 在 line/section 改變時 fetch。
4. LineTabPanel 移除 local full-count inference，保留必要的 defensive display filtering。
5. Header/Batch copy 顯示 total vs loaded 真實語意。
6. 保留 EAL/TML global line counts API 與 filter panel workflows。

### Gate

- Focused store/component/view Vitest 全綠，既有 act warnings 不新增。
- 點選 LMC 不依賴原 1,000 筆 subset。
- 更新 P5 狀態。

完成證據（2026-08-19）：

- Database Record focused frontend suites -> 27 passed；新增 store contract 確認 records 可維持 1,000 筆而 total/section counts 仍為 server aggregates。
- Section filter 會重新 request exact section；header 顯示 `total · loaded`，Batch Edit 明確標示 `Loaded`。
- EAL seed v2 的 server aggregate contract 為 All 1,826、Mainline 1,584、RAC 132、LOW S1 16、LMC 94；Unknown 僅在 count > 0 時出現。

## P6：Seed v2 Assets 與一次性 v1 Replacement

### 先寫/擴充測試

檔案：

- `backend/tests/test_database_record_seed.py`

測試案例：

- Real loader 得到 EAL 1,826 / TML 974 / total 2,800。
- EAL section counts與 workbook hashes 正確。
- Empty DB seed v2，重開為 `skipped_up_to_date`。
- 精確 v1 metadata + actual counts 被 replace 成 v2。
- v1 metadata count drift、actual count drift、unknown non-empty DB 不被覆寫。
- Missing/corrupt/hash mismatch 在 delete 前失敗。
- Mid-insert/metadata failure rollback 後仍為完整 v1 baseline。
- Replacement 不改其他 tables。

### 實作

檔案：

- `config/database-records/database-record-seed-quality.json`
- `backend/app/core/database_record_seed.py`
- `backend/app/core/database.py` 只在需要記錄/處理新 result status 時作最小 patch。

步驟：

1. 更新 seed version/counts/hashes/provenance/section quality data。
2. Loader 在任何 destructive statement 前完整驗證 v2 bundle。
3. 實作 empty/up-to-date/eligible-v1/unknown-nonempty state machine。
4. Eligible v1 於 savepoint 內 delete + bulk insert + metadata update。
5. 記錄 replacement source version；保持第二次啟動 idempotent。
6. 以 `PRAGMA foreign_key_check` 與 table counts 驗證 transaction outcome。

### Gate

- Seed focused pytest 全綠。
- Failure injection 證明 v1 可 rollback。
- Manifest 與實際 workbook hashes/counts 一致。
- 更新 P6 狀態。

完成證據（2026-08-19）：

- `python -m pytest backend/tests/test_database_record_seed.py -q` -> 16 passed。
- v2 manifest、source/output SHA-256、headers、composite-key uniqueness、line/section counts 與 provenance 均經 loader 驗證。
- eligible v1 只在 metadata 與實際 counts 同時精確符合時，以 savepoint delete + bulk insert + metadata update；insert/metadata failure 會 rollback。

## P7：Design Docs 與完整 Regression

### 文件

- `PRODUCT.md`：再次審閱；預期不修改，於計畫/交付明記 reviewed unchanged。
- `DESIGN.md`：補五週期 palette、upload/chart shared-color rule、不可只靠色彩的規則。只 append/patch 相關段落，保留既有未提交內容。

### Backend Regression

使用 repository 可用 Python environment 執行至少：

```powershell
python -m pytest backend/tests/test_version_difference_api.py backend/tests/test_database_records_api.py backend/tests/test_database_record_seed.py backend/tests/test_database.py
```

若 targeted tests 揭示 shared database regressions，再擴展至完整 backend suite。

### Frontend Regression

首次 npm process：

```powershell
$env:NODE_USE_SYSTEM_CA='1'; npm --prefix frontend test -- --run src/api/__tests__/versionDifferenceClient.test.ts src/store/__tests__/useVersionDifferenceStore.test.ts src/store/__tests__/useDatabaseStore.test.ts src/views/__tests__/VersionDifferenceView.test.tsx src/components/VersionDifference/__tests__/VersionDifferenceChart.test.tsx src/components/DatabaseRecord/__tests__/LineTabPanel.test.tsx src/views/__tests__/DatabaseRecordView.test.tsx
$env:NODE_USE_SYSTEM_CA='1'; npm run build:frontend
```

視修改範圍再執行完整 frontend Vitest。不得變更 `strict-ssl` 或 registry。

### Gate

- Focused suites 與 frontend build 全綠。
- 無新增 lint/type errors、unhandled promise 或 console runtime errors。
- 更新 P7 狀態及實際 commands/results。

完成證據（2026-08-19）：

- 指定 frontend regression -> 48 passed；`$env:NODE_USE_SYSTEM_CA='1'; npm run build:frontend` 成功。
- backend targeted regression -> 107 passed、28 skipped；唯一 failure 是既有 `backend/tests/test_database.py` schema assertion 仍寫 `1.6`，而 repository current migration baseline 已為 `1.7`，未納入本次 feature scope。
- `PRODUCT.md` 已審閱，產品目的、使用者、定位與 workflow principles 未改變，因此保持 unchanged。
- `DESIGN.md` 已更新 Version Difference 五週期 palette、upload/chart shared-color rule 與 color-independent labeling；commit `53a8a7d` 已保存設計文件。

## P8：實際 DB、UI 與 Package 驗證

### Canonical AppData DB Replacement

已解析的 exact target：

`C:\Users\chusiukd\AppData\Roaming\TOV640_Analyzer\data\analysis.db`

執行前只讀確認：seed version v1、metadata 2,706、actual EAL 1,732/TML 974。以 SQLite backup API 建立同目錄明確命名的 pre-v2 backup，再透過實際 `DatabaseManager` startup path 執行 migration，不用 ad-hoc DELETE script。

執行後驗證：

- seed version v2
- total 2,800
- EAL 1,826 / TML 974
- EAL Mainline 1,584 / RAC 132 / LOW 16 / LMC 94
- `PRAGMA integrity_check == ok`
- `PRAGMA foreign_key_check` 無 rows
- 第二次 startup 不再次 replace

### UI Workflow

從 canonical root 啟動受支援的 dev command；若 port 已使用則依 root script 行為處理，不直接啟動 Vite/Electron builder。

Version Difference 驗證：

- Desktop 五欄、medium 三欄、narrow 一/二欄 screenshots。
- 五檔 upload、optional gap、Compare、20 raw traces、4 differences。
- Slot/trace colors、long filenames、keyboard focus、Series controls、zoom。
- Canvas/Plotly 非空，無 overlap 或 clipped text。

Database Record 驗證：

- EAL header、All/section counts、LMC records。
- Active track/level/date/chainage filters 的 total/counts。
- `total · loaded` copy 與 Batch Edit Loaded。
- EAL/TML switch、section switch、clear filters、error/loading states。

### Package

```powershell
$env:NODE_USE_SYSTEM_CA='1'; npm run package
```

驗證 generated `dist/**/resources/config/database-records/` 包含：

- `EAL-1-year-database-record.xlsx`
- `TML-1-year-database-record.xlsx`
- `database-record-seed-quality.json`

再由 packaged config path 呼叫 loader，確認仍為 2,800 筆與正確 hashes。

### Gate

- 實際資料庫、desktop/narrow workflow 與 package resources 全部通過。
- 記錄 backup path 與 migration 結果，讓覆寫可追溯/可復原。
- 關閉所有 verification server/session 後更新 P8。

完成證據（2026-08-19）：

- target DB：`C:\Users\chusiukd\AppData\Roaming\TOV640_Analyzer\data\analysis.db`。
- pre-v2 backup：`C:\Users\chusiukd\AppData\Roaming\TOV640_Analyzer\data\backups\analysis.db.pre-v2-20260819-215758.bak`。
- migration 後 seed version `2025-2026-v2`；EAL 1,826、TML 974、total 2,800；EAL Mainline 1,584、RAC 132、LOW 16、LMC 94；`PRAGMA integrity_check` 為 `ok`，foreign-key check 無 violations。
- 第二次 startup 回傳 `skipped_up_to_date`，其他 user tables row counts 未改變。
- `$env:NODE_USE_SYSTEM_CA='1'; npm run package` 成功；`dist/win-unpacked/resources/config/database-records/` 含 EAL/TML workbook 與 `database-record-seed-quality.json`。Packaged workbook SHA-256 與 source 相同：EAL `ddc3d385c65e5a2475e8a1070fe8eff401f7967866cef11fc370c0a975f80fad`、TML `1d9d989663f9ee67bd60c4bc7d9496a823d263fd3be67e341838d780d1a94165`。
- 真實 browser smoke check 以 canonical Vite `http://127.0.0.1:5173/` + Uvicorn `http://127.0.0.1:8000` 完成：Version Difference desktop `1440x1000` 與 narrow `700x900` 均顯示五個 slots；Database Record 顯示 `1,826 total · 1,000 loaded`、EAL section badges，點選 LMC 後 server-side result 為 `94 records`、`1–50 of 94`。
- Smoke screenshots 暫存於 `output/playwright/version-difference-desktop.png`、`output/playwright/version-difference-narrow.png`、`output/playwright/database-record-lmc.png`；browser session 與 dev server 已關閉。Console 唯一 error 為既有 `/favicon.ico` 404，無 workflow/runtime error。

## P9：Graph Re-index、Scope Audit 與交付

### 工作

1. `index_repository(mode="moderate", persistence=true)` 更新 graph。
2. 對所有 changed symbols 執行 impact/context trace。
3. 比對 `git diff --name-only` 與本計畫 scope；逐檔確認無使用者變更被覆寫。
4. 執行 `git diff --check`、檢查 staged scope，再建立 focused implementation commit。
5. 在本文件填入最終 phase 狀態、測試/視覺/package evidence 與任何 residual risk。

完成證據（2026-08-19）：

- codebase-memory project `C-Smart-Maintanence-TOV640_Analyzer` 已 moderate re-index；以 `search_code`/`search_graph`/`trace_path` 核對 version-difference route、database predicates/aggregates、seed loader 與前端入口/consumers。
- `git diff --check` 無 whitespace errors（只有 Windows LF/CRLF normalization warning）。
- 本次 implementation scope 已分離為 backend API/database/seed、frontend Version Difference/Database Record、相關 tests、EAL seed workbook/manifest 與 `DESIGN.md`；既有 wear projection/stagger/screenshot/AGENTS dirty changes 不納入 commit。
- residual risk：完整 backend suite 保留一個既有 schema `1.6` assertion failure；不影響本次新增 contract，應由後續 schema test maintenance 單獨處理。

### 最終交付內容

- 五週期 Version Difference 行為與色彩。
- 完整 filtered counts、server-side section 與 loaded subset 語意。
- Seed v2/LMC 一次性 replacement 結果與 backup location。
- Tests/build/package/UI verification 摘要。
- `PRODUCT.md` / `DESIGN.md` 更新狀態。
- 未處理或與本次無關的既有 dirty-worktree 變更清單不納入 commit。

## Stop Conditions

遇到以下情況停止 destructive/expansive action並回報：

- Actual DB 不再符合已核實的 v1 version + metadata + actual counts。
- 新 EAL workbook hash、row counts、headers 或 composite-key uniqueness 改變。
- Seed replacement 會觸及 `saved_repeated_exceptions` 以外的 user data。
- Root package command要求關閉使用者正在使用的 app 或會刪除非 `dist` target。
- 已有 dirty change與本次同一行/同一 contract 衝突，無法在不覆寫使用者工作的情況下合併。
- 實作需要改變已批准的 count scope、five-cycle roles、1,000 loaded limit 或 replacement eligibility。
