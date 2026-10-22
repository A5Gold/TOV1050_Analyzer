# 重新產生 TOV1050 metadata candidates

- 日期：2026-10-22
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-19（DAV-10 子 issue；已由 Linear MCP 查證）
- 負責人：Codex
- 狀態：In Review

## 需求與目的

使用者已完成一輪 metadata Excel 人工修改，要求依目前原始 workbook 重新產生獨立 candidate，重跑驗證，並提供仍需人工查看的 workbook、sheet、Excel row 與欄位。不得沿用 2026-09-23 audit 的結論，也不得覆寫原始 workbook、既有 candidate、runtime metadata 或舊 audit。

### 使用者與流程

使用者直接檢查 metadata workbook。Codex 對照 Git HEAD 與前次 audit，重新標準化與驗證目前資料，交付 review-only candidate、provenance 和 validation/audit，並整理剩餘的人工決策。

### 商業規則與限制

- Chainage canonical unit 為公尺；來源 Km 僅於 adapter 邊界乘以 1000。
- UT/DT 反向 interval 可依既有規則以 min/max 產生 canonical 範圍，但要保留來源列和方向排序 provenance；不代表原始端點已核准。
- 同位置多 bracket 可為合法 overlap；不得自動刪除或推定為錯誤。
- Bracket 變體若不符合現行 regex，不可直接認定為 landmark；新增疑似變體診斷與暫定衝突檢查，保持 review-only，等待使用者確認命名格式。
- 未取得明確 metadata 核准，不得 promotion 至 runtime config。

## 現況盤點

- branch / HEAD：`master` / `dbce9535895ca20217bad4029b36316ee21aa7ff`，與 `origin/master` 相同。
- 已有未提交修改：共用 mapping、ISL metadata、KTL metadata，以及舊 2026-09-23 ISL candidate；四者均須保留。
- 目前程式碼：`scripts/standardize_tov1050_metadata.py`、`scripts/validate_tov1050_metadata_candidates.py`。
- 現有測試：`backend/tests/test_tov1050_metadata_candidates.py`。
- codebase-memory 索引已就緒。工作開始時 Linear 工具尚未出現在清單中；後續工具掛載後已讀取並更新 DAV-10、DAV-19。
- 實際唯讀檢查：mapping 相較 HEAD 只有 TWL DT row 46 從空白 Location 更新為 `0.4 km`；AEL DT `350-001` 至 `350-042` 目前各保留一次；ISL DT C:N 共用 mapping 輔助欄位目前皆空。
- KTL DT 目前沒有 `End < Start` interval；ISL DT 仍有 Excel row 387：`99.5381 -> 99.5349 km`（前次列為 row 390）。
- 共用 mapping 有 132 個疑似 Bracket 變體；若視為實體 bracket，AEL DT 33.571、33.597、33.882 km 三處會與一般 bracket 同位。132 個疑似標籤本身目前沒有同名多位置案例。變體類型與來源列將進一步寫入 validator audit。

## 設計

### 範圍

- 為不符合目前嚴格 ID regex、但符合近似 bracket 樣式的 mapping rows 加上獨立 review 診斷；產生暫定同名多位置及同位置衝突統計，不自動把它們當成實體 bracket 或 landmark。
- 增加針對 `211-1A`、`364A-001`、`CR185A-01` 等變體及暫定衝突的測試。
- 以目前七條 metadata source（ISL、KTL、LAR_AEL、LAR_TCL、TKL、TKS、TWL）在 `outputs/metadata-review-2026-10-22/` 建立新 candidate、provenance 與 validator JSON/Markdown。
- 將目前 source/mapping digest、差異、驗證結果、人工待確認項目與 Linear 同步結果更新至本紀錄。

### 不在範圍

- 修改原始 Excel、既有 2026-09-23 candidate/audit、runtime metadata，或自動修正任何來源列。
- 自動決定疑似 Bracket 變體、tension-length overlap 或 ISL DT row 387 的正確端點。
- promotion / write-back。

### 資料流與錯誤處理

目前 metadata source 與共用 TL-BK mapping → standardizer 產生 metre-based review candidate、digest 與 provenance → validator 比較 source/candidate parity、mapping identity、invalid rows 與 provenance。疑似變體列只產生 review 診斷；candidate 任何錯誤或待確認 finding 都不寫入 runtime。

### 驗收標準

- 所有七線 candidate 均由目前 source 和 mapping 產生，source/mapping digest 與目前檔案相符。
- 端點轉為公尺、candidate 保留 source row/provenance；source invalid rows、parity、identity 與 provenance finding 均清楚呈現。
- 132 個疑似變體和可能被現行分類漏掉的 identity 衝突有可追溯診斷；不以未確認格式改變既有硬錯誤分類。
- targeted tests 通過；候選僅 review-only；人工操作表只保留需要決策或格式確認的項目。
- 原始 workbook、舊 candidate/audit 與 runtime metadata 未被覆寫。

## 執行紀錄

### 實作

Validator 新增 `_is_suspected_bracket_variant` 與獨立 review diagnostics，列出每筆疑似變體、暫定 exact duplicate、同名多位置及同位衝突；未確認變體不會升格為 physical identity hard error，也不會混入 landmark rows。更新 targeted tests。以目前七條 source 產生 candidates、manifest、validation JSON/Markdown 與本批次 audit；未修改原始 workbook、舊 candidate、runtime config。

### 測試與 debug

```text
python -m pytest backend/tests/test_tov1050_metadata_candidates.py -q
13 passed

python scripts/standardize_tov1050_metadata.py --root "00 Reference Document/config" --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir "outputs/metadata-review-2026-10-22/candidates" --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
exit 0; 7 candidates and manifest generated

python scripts/validate_tov1050_metadata_candidates.py --source-root "00 Reference Document/config" --candidate-dir "outputs/metadata-review-2026-10-22/candidates" --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir "outputs/metadata-review-2026-10-22/validation-final" --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
exit 0; all seven lines review_required, no error findings
```

### 驗收結果

七線 threshold/location/track/bracket parity 全通過；source/mapping digests 全匹配；provenance mismatch、source invalid rows、mapping invalid rows、exact duplicate identity 與同 Bracket 多位置皆為 0。Candidate 仍為 review-only。剩餘人工決策為 ISL DT row 387，以及 132 筆 suspected variant 的命名規則和 4 處暫定同位案例，詳見 `outputs/metadata-review-2026-10-22/metadata-review-audit.md`。

## Linear 同步

- 最後同步時間：2026-10-22 17:31 HKT。
- Issue 狀態：DAV-10、DAV-19 均為 `In Progress`；DAV-19 已確認是 DAV-10 子 issue。
- 同步結果：已將本 request、候選重生、validator 修正、13 項 targeted tests、七線驗證摘要及剩餘 row 387 / bracket 變體決策更新至 DAV-19，並將子 issue 摘要同步至 DAV-10。
- Next action：使用者確認 ISL DT row 387 的正確端點，以及字母變體是否屬 physical Bracket、4 處暫定同位是否為合法 overlap；收到答覆後更新 DAV-19 並重跑相關驗證。
- 阻塞／需要決策：Linear 同步已完成；metadata 仍維持 review-only，待上述人工決策。

## 相關檔案

- `00 Reference Document/TOV1050 TL-BK No.xlsx`
- `00 Reference Document/config/ISL metadata.xlsx`
- `00 Reference Document/config/KTL metadata.xlsx`
- `scripts/standardize_tov1050_metadata.py`
- `scripts/validate_tov1050_metadata_candidates.py`
- `backend/tests/test_tov1050_metadata_candidates.py`
- `docs/audits/2026-09-23-tov1050-metadata-review-update.md`
- `outputs/metadata-review-2026-10-22/`
- `https://linear.app/david-chu/issue/DAV-19/重新審閱更新後的-tov1050-tl-bk-mapping`
