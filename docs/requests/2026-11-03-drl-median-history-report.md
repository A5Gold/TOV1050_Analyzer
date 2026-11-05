# DRL 手修清單與 TOV1050 median 例外報表／歷史比較

> DRL 資料清單已由使用者同日新決策取代，請以 `docs/requests/2026-11-03-drl-wide-correction.md` 與 `outputs/metadata-review-2026-11-03/drl-wide-v2` 為準。OCS Wire Wear L1 已9.1；只有 UT／獨立 PL，沒有 DT；DRL TL 採支架最小／最大里程。下文缺DT／PL方向／缺Contact兩端的歷史審閱結論不再適用DRL，保留僅供追溯。History median 驗收紀錄不變。

- 日期：2026-11-03
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-28（median 報表／History）；DRL 資料決策沿用 DAV-21
- 負責人：Codex 主代理；DRL 與 History 子代理唯讀審查
- 狀態：程式實作與隔離整合驗收完成；DRL 資料手修／核准交資料負責人

## 需求與目的

### 使用者與流程

列出 DRL metadata 的具體差異，供資料負責人手動核對。TOV1050 的 Exception Generator 報表應以既有 chainage median 約 8 萬列寫入 ChartData；History Compare 直接使用該報表。兩份 TWL 完整 cleaned raw 各約 83 萬列，不應再成為報表 ChartData 及 History 的一般輸入。TOV640 EAL／TML 維持完整 raw 報表流程。

### 商業規則與限制

- ExceptionDetector、threshold crossing、overshoot、peak、Summary 與分型例外表仍取完整 cleaned raw；median 只用於 TOV1050 報表 ChartData 與圖表。獨立 raw CSV 匯出仍輸出完整資料。
- chainage 單位是公尺；來源標為 km 的欄位只能按 schema 明確轉一次，不能按數值猜測。
- 正式 DRL workbook、原始 CSV／DATAC、指定參考報表、使用者 SQLite DB 不自動覆寫。候選 metadata 未獲核准，Overlap／Tension Length／Landmark 未知值仍維持未知。
- 現有 dirty 工作樹含前輪成果；本輪不 reset，也不將其他改動歸入 DAV-28。

## 現況盤點

- 分析時完整 cleaned raw 送 detector；median 存在 session 的 analysis_df。報表的背景工作、GET /export/report 與 POST /export/report/generate 卻呼叫 _export_frame，按來源 SHA 重載完整 raw 寫 ChartData。
- History 已只接受 Exception Generator 的 xlsx 報表；read_history_report 逐列掃整張 ChartData 並建立數值圖表 cache。前輪兩份完整 raw TWL 報表真機比較約 895 秒；舊 median 報表約 169 秒，兩者不是同一偵測演算法，不能直接比較例外數量。
- 2026-09-07 TWL 完整 cleaned raw 838859 列、median 83963 列；2026-06-30 為 830792／83244 列。完整 raw 偵測的既有基線分別為 289／330 例外。
- DRL 正式 config workbook 是舊式四頁 long schema：threshold、UT track type、PL track type、location type；與 TOV640 相容的 wide threshold、方向頁、Exception Boundarys 及已核准區間不同。
- DRL 審閱證據：outputs/metadata-review-2026-11-03/batch-01/audit.md、drl-three-source-diff.csv、drl-context-capabilities.csv，以及 review-only 候選。25 份來源 SHA 未漂移；候選 4532 格 parity 通過。

### DRL 資料負責人手修／確認清單

下表「正式」指 `config/DRL metadata.xlsx`；「參考」指 `00 Reference Document/config/DRL metadata.xlsx`。兩檔本輪均保持原樣；最終 SHA 分別為 `641477e23e3f9afae7b4d63a4829286f2f93680153d077f987b538367a4902cc`、`a386100bb6f47ab9d2a61e7e80c40ad5e87a91cc614e1659584ea41a0161ecff`。

| 位置 | 已確認差異／缺口 | 需要的人工決策 |
|---|---|---|
| 正式 threshold!A1:F89 | Location Type／Track Type／Exc Type／min／max 的 long schema，與其他線 wide 欄組不同 | 決定標準化欄組及 threshold 每個 context 的對應；保留既有有效值 |
| 正式 UT track type!A2:C11、PL track type!A2:C8 | 分別 10／7 個 startKM/endKM 區間；沒有 Mainline DT 頁 | 提供 DT 真實來源，不以 UT 複製；確認 PL 適用 UT、DT 或其他方向 |
| 正式 location type!A2:C2 | 只有 Tunnel 40–46 km | 確認其他區段的類別與 coverage，不能把缺列當 Open |
| 正式 threshold!E18/E20/E22/E24 | Wire Wear L1 為 8.9；參考 wide threshold!G4/G9/G14/G19 為 9.1 | 決定權威值及生效版本；候選目前保留正式 8.9 |
| 參考 DRL UT!B2:C11、E2:E219；DRL PL!B2:C8、E2:E87 | 區間 B:C 已是公尺，Bracket FromM 的 E 欄卻是 41.455–44.925／41.455–43.609 km；標頭混用單位 | 按來源 schema 核實並將 E 明確換算為公尺，不把 41.455 當 41.455 m |
| 參考 Exception Boundarys!D2:G2 | UT 40000→46000 m、DN 46000→40000 m 的方向寫法不同 | 確認 DN／DT 方向與區間閉合語義 |
| DRL UT／PL Brackets 候選及 Boundary Review!A2:N10 | 點表分別 214／80 點，方向未定；第 6 列 TL487 只見 45026 m Contact 單端；列 2–10 配對 unresolved，L:N 核准欄空 | 核實 Contact 雙端、配對、方向、coverage；逐組核准後才建立 TL／Overlap 區間 |
| DRL UT／PL 候選 A:G | Overlap、Tension Length、Landmark 區間欄仍空；參考點表不是區間 | 提供 Landmark FromM／ToM、TL Contact 配對與 coverage；不得由普通 Bracket 點或最近點推定 N／區間 |

參考 DRL 點表與 TL-BK mapping 有差異，UT 參考多 7 組 9 筆、mapping 有 5 筆未入參考；PL 參考多 5 組 6 筆。差異表列明 row／TL／Bracket；尚不能斷言哪方錯。全線 382 組 TL 的配對缺口統計不得當作 DRL 專有問題。

## 設計

### 範圍

採用設計文件 docs/superpowers/specs/2026-11-03-median-report-history-design.md 與計畫 docs/plans/2026-11-03-median-report-history-plan.md。僅調整 TOV1050 報表 ChartData 的來源選擇及 provenance；History 既有讀取器沿報表鏈讀取，不重新計算 median。

### 不在範圍

不改 DRL 正式檔／核准 sidecar，不變更偵測演算法、Stagger 門檻、History 重複例外判斷或 TOV640 流程；不封裝／發布。

### 資料流與錯誤處理

TOV1050：完整 cleaned raw → detector → 例外表；同一次分析的 median frame → 報表 ChartData → History 串流／cache／圖表。若 session median frame 遺失，回明確 expired／需要重新分析，不以畫面 envelope 或完整 raw 靜默回填。舊完整 raw 報表仍可讀，但舊檔不會自動變快；使用者需重新產生 median 報表。

### 驗收標準

1. 三個報表入口的 TOV1050 ChartData 使用既有 median snapshot，不重新載入完整 raw；Summary／例外 ID、peak 與 raw 偵測基線一致。
2. 新報表 _Metadata 分開標示 detection_data_mode=cleaned_raw、報表資料模式 chainage_median、raw/source 與 chart/representative 列數；不將偵測演算法誤標 median。
3. EAL／TML 報表仍寫完整 raw；獨立 TOV1050 raw CSV 仍為完整 cleaned raw。來源或 session 失效時無錯誤 fallback。
4. 兩份 TWL 新報表分別約 83963／83244 ChartData 列；History 以兩報表成功比較，記錄實測 cold/warm、direct/proxy 耗時、rows、圖表／匯出驗證。目標避免舊單次約 15 分鐘；不虛構性能數據。
5. DRL 清單有精確來源位置及未決決策；正式 workbook SHA 不變。

## 執行紀錄

### 實作

- `backend/app/api/endpoints/analysis.py` 新增線別辨識的報表資料選擇與 metadata helper，供背景 report job、`GET /export/report`、`POST /export/report/generate` 共用。TOV1050 報表的 ChartData 取本次分析 session 的 chainage median frame；EAL／TML 報表沿用完整 cleaned raw。獨立 raw CSV 仍載入完整來源，無可用 median frame 時回 410。
- 報表 `_Metadata` 分別標示 `detection_data_mode=cleaned_raw`、`export_data_mode=chainage_median`、raw／chart 列數，避免將偵測誤認為 median。History 既有報表 reader 沿相同 XLSX 鏈讀取，沒有第二次 median 計算。
- 更新 API／匯出回歸測試、About 說明與報表 writer 註解；未修改正式 DRL、核准 sidecar、原始資料、指定參考報表或使用者 DB。

### 測試與 debug

- `python -m py_compile scripts/validate_median_history_http_20261103.py`：通過。
- 先前相關 backend 四套回歸：48 passed；另五套：58 passed；補充兩套：15 passed。套件有重疊，數量不可相加。`npx tsc --noEmit` 及 `git diff --check` 通過，後者僅既有行尾警告。
- `python scripts/validate_median_history_20261103.py`：兩份 TWL 真檔完成報表產生與 History 直接比較；實測資料在 `outputs/validation-2026-11-03/median-report-followup/validation.json`。
- `python scripts/validate_median_history_http_20261103.py`：兩份 median XLSX 經 HTTP background job 上傳、輪詢、讀結果、overview chart 與 comparison Excel 匯出均成功；實測 JSON 為 `outputs/validation-2026-11-03/median-report-followup/http-validation.json`。
- TML DATAC 真檔以隔離路徑產報表、用 openpyxl 讀回；證據為 `outputs/validation-2026-11-03/tml-median-regression/validation.json`。
- `$env:NODE_USE_SYSTEM_CA='1'; npx vitest run src/views/__tests__/HistoryCompareView.test.tsx src/views/__tests__/ExceptionGeneratorView.test.tsx src/components/HistoryCompare/__tests__/SaveToDBDialog.test.tsx` 初輪平行 fork worker 啟動逾時，未執行任何測試；改用 `--maxWorkers=1 --pool=threads` 重跑，3 files／38 tests passed。測試 stderr 有既有 React `act(...)` 警告；模擬 Backend unavailable 是預期的失敗路徑。
- `$env:NODE_USE_SYSTEM_CA='1'; npm run build`：通過；Vite 僅回報既有 browser externalization、xlsx 匯入方式與大型 chunk 警告。`git diff --check` exit 0，僅既有 LF／CRLF 行尾警告。
- `node --check scripts/validate_history_electron_20261103.mjs`、`python -m py_compile scripts/validate_history_postchecks_20261103.py`：通過。驗證腳本可選擇隔離輸出與 median 來源，並記錄 cached chart request 耗時。
- Electron 命令：`$env:NODE_USE_SYSTEM_CA='1'; $env:HISTORY_VALIDATION_OUTPUT='outputs/validation-2026-11-03/median-electron-history-retry'; $env:HISTORY_REPORT_SOURCE='outputs/validation-2026-11-03/median-report-followup'; node scripts/validate_history_electron_20261103.mjs`：exit 0。真 Electron／backend／Vite proxy，未攔截 API；overview、detail、匯出、UI 保存、重複保存及 read-only SQLite reopen 全通過。
- Debug：首次 Electron compare 已成功（205.230 秒、九線選單可見），但其後 Playwright screenshot 等待 90 秒失敗。將非必要截圖改成 5 秒、有警告紀錄且不中斷功能驗證，再跑完整鏈成功；重跑無 screenshot warning。首次證據保留在 `median-electron-history`，成功證據在 `median-electron-history-retry`。

### 驗收結果

- 2026-09-07 TWL：838,859 raw → 83,963 ChartData；289 筆 Summary（Stagger Left 118、Right 103）；新報表 21,105,386 bytes。
- 2026-06-30 TWL：830,792 raw → 83,244 ChartData；330 筆 Summary（Stagger Left 112、Right 123）；新報表 20,862,853 bytes。
- 兩份新報表直接 History Compare 得 15 筆重複例外，187.539 秒；先前兩份完整 raw 報表 worker 約 877.641 秒。新兩報表約 42 MB，先前約 164 MB。此為本機真檔單次量測，不視為固定 SLA。
- 同一兩報表的 HTTP background job：提交 0.611 秒，ready 192.911 秒，poll p95 0.039 秒；圖表 overview 1,376 點，comparison Excel 7,903 bytes，重複例外仍為 15 筆（Left 6、Right 5、Low Height 4）。
- TML 2026-04-10 DATAC：完整 raw 41,138 列，報表 ChartData 41,138 列，Summary 152 筆，`export_data_mode=cleaned_raw`；DATAC 與 TML metadata SHA 前後相同。
- Electron／Vite proxy 第二次完整執行：提交 1.797 秒、compare ready 113.952 秒、poll p95 0.206 秒；15 筆例外保存及重新讀取一致。第一次 compare 為 205.230 秒；重跑可能受 OS cache 影響，不能當成固定效能保證。兩 cycle overview 1,378／1,427 點，detail 為報表 median window 的完整 279／282 列，peak chainage 保留；cached detail 請求 0.045／0.025 秒，comparison 匯出 0.154 秒。
- 來源 SHA 與指定參考檔已在驗證腳本前後比對無漂移；正式 DRL 保持待人工核准。

## Linear 同步

- 最後同步日期：2026-11-03
- Issue 狀態：DAV-28 已同步為 Done；DRL 資料決策 DAV-21 In Progress
- 最終同步：DAV-28 description／state 已更新；DAV-27 comment `dd76edd8-a5b0-4997-8b38-4fd07a12809a` 記錄 median 決策及驗收，DAV-21 comment `4f6962e7-813b-4ff5-bb1b-862626f211f4` 記錄 DRL 人工 next action。
- Next action：資料負責人依 DRL 表核對／手修並提供核准方向、門檻與區間；若之後要求 promotion，開發端另按核准 scope 驗證。median 軟體工作完成；未提交、未重新打包或發布。
- 阻塞／需要決策：DRL DT／PL 方向、8.9／9.1、Contact 配對／coverage、Landmark 區間。這些不阻塞 median 報表程式修正。

## 相關檔案

- 本輪程式：`backend/app/api/endpoints/analysis.py`、`backend/app/core/tov1050_report_export.py`、`backend/tests/test_api_analysis.py`、`backend/tests/test_export_raw_generate.py`、`backend/tests/test_median_analysis_snapshot.py`；About 的 `DeveloperReference.tsx`／`aboutGuideContent.ts`。
- 本輪驗證：`scripts/validate_median_history_20261103.py`、`scripts/validate_median_history_http_20261103.py`、`scripts/validate_history_electron_20261103.mjs`、`scripts/validate_history_postchecks_20261103.py`；新增 request／design／plan，以及原 DAV-27 三文件的後續決策註記。
- 沿用前輪 History reader／background job／前端九線選單與隔離流程，並非本輪重建。工作樹包含多項既有未提交修改；本輪未提交或 reset。最終完整 status 另存 `outputs/validation-2026-11-03/median-report-followup/worktree-status-final.txt`。
