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

- 最後同步：本次執行期間已使用 Linear MCP 更新 DAV-10、DAV-19。
- Issue 狀態：DAV-10、DAV-19 均為 `In Progress`；DAV-19 已確認是 DAV-10 子 issue。
- 同步結果：DAV-19 已記錄 row 387 新端點、字母 identity 規則、七線 batch-02 驗證與待確認 overlap；DAV-10 已同步摘要。
- Next action：使用者確認 ISL DT rows 80/84 與 KTL DT rows 50/306 的 interval overlaps，並決定是否接受 CSV 內 286 組一般 bracket 同位組。
- 阻塞／需要決策：metadata 仍維持 review-only；不得 promotion，直到使用者核准或修正待確認 overlap。

## 2026-10-22 使用者最新確認與第二批候選

### 最新人工確認

本節取代第一批 audit/request 對 ISL row 387、字母變體和四處暫定同位案例的待確認描述。

- 使用者已更新 `00 Reference Document/config/ISL metadata.xlsx` → `DT track type` → Excel row 387。目前 `startKM=99.5361`、`endKM=99.5369`；唯讀掃描確認 ISL DT 與 KTL DT 均沒有 `End < Start`。ISL source SHA-256 從舊 candidate manifest 的 `bcfdb6a4e475925db35d0440e596c746fc36f5998fa8010a525aa7637f6b0e8c` 更新為 `afa1b1e6246bb2d9c2096c36bb8a4cbfa16b36185bf8d357d57c6847f4e0a22f`。
- 字母位於 TL 前段數字之後或 Bracket 後段數字之後時，皆屬 physical Bracket identity；CR 編號中的字母同理。涵蓋 `001-002A`、`002A-001`、`002A-002A`、`CR001A-002` 等格式。
- 含字母變體的不同 physical Bracket identity 出現在同一 chainage，依使用者確認列為合法 tension-length overlap，不得當成 landmark 或錯誤；不含字母變體的同位組仍保留 review，因為既有規則只確認「可能」是合法 overlap。相同 Bracket identity 出現在多個 chainage 仍需納入衝突檢查。
- 先前確認仍有效：刻意移除重複 tension length、保留唯一一筆；刻意移除錯位 mapping；ISL DT C:N 輔助欄位可棄用；KTL/ISL DT 的 16 筆反向 interval 已修正；TWL DT row 46 `2-045` Location 已補齊。

### 第二批設計與範圍

- 擴充 validator 的 Bracket identity 格式，將已確認的字母變體納入一般 physical identity；字母變體參與 exact duplicate 與同 Bracket 多位置檢查。
- 含字母變體的不同 Bracket identity 同位置列為已確認 overlap；不含字母變體的同位組保留為 review。Landmark prefix 規則維持適用於 `SI`、`Mid Point`、`POA` 等名稱。
- 重新產生 ISL、KTL、LAR_AEL、LAR_TCL、TKL、TKS、TWL 七線 candidate、provenance、validation 與 audit，全部寫入 `outputs/metadata-review-2026-10-22/batch-02/`，不得覆寫既有 2026-09-23 或 2026-10-22 第一批產物。
- Candidate 維持 review-only；不寫回原始 workbook，不 promotion 至 runtime config。

### 第二批驗收條件

- ISL row 387 使用目前已修正的端點；ISL/KTL DT reversed interval 計數皆為 0。
- `211-1A`、`364A-001`、`CR185A-01`、`CR186-10A` 和使用者提供的 TL/Bracket 字母樣例都分類為 physical Bracket；`POA804-01` 等 POA landmark 仍列為 landmark。
- 相同 identity 多位置依既有錯誤規則檢查；含字母變體的同位組依使用者確認列為合法 overlap，不要求再確認；其他不同 identity 同位組保留人工 review。
- 七線 candidate digest/parity/provenance 與目前 sources/mapping 相符，targeted tests 通過，候選維持 review-only。

### 第二批執行狀態

- Linear MCP 已確認可用；DAV-10、DAV-19 已記錄使用者最新答案與本批結果。
- Validator/test 更新完成：字母變體按 physical identity 檢查；同位置診斷區分已確認變體 overlap 與未確認一般 bracket overlap；interval overlap 保留原始端點、來源 row，並標明範例清單是否完整。
- 七條新 candidate 位於 `outputs/metadata-review-2026-10-22/batch-02/candidates/`。只有 ISL source digest 相較第一批改變；mapping digest 不變。七線 source/mapping digest、threshold/track/bracket parity、provenance 均吻合；source/mapping invalid rows、reversed intervals、exact duplicate identity、同 Bracket 多位置與 provenance mismatch 皆為 0。
- 共識別 132 個字母變體；290 組不同 Bracket 同位置，其中 4 組含字母變體且已依使用者規則確認，286 組不含字母變體仍為 review，完整列於 `unconfirmed-same-location-overlaps.csv`。
- Interval overlap 共 146 組（ISL DT 12、KTL DT 132、LAR_AEL location type 1、LAR_TCL location type 1），完整來源列和端點列於 `interval-overlaps.csv`；其中仍有兩組同長度 ambiguous overlaps：ISL DT rows 80/84，KTL DT rows 50/306。
- Targeted tests 13 passed；validator exit 0，七線皆 `review_required`，無 error findings。Candidate 全部 review-only，未 promotion。
- Next action：使用者確認兩組 ambiguous interval overlaps；並決定 286 組不含字母變體的同位 Bracket 是否均可按 tension-length overlap 視為合法，或指定需修正的列。

### 補充分類風險與第三批設計（2026-10-22）

- 重新檢查 batch-02 validator 後發現：目前 `_is_landmark` 將所有不符合已知 Bracket regex 的值都歸類為 landmark。這會隱藏命名格式尚未確認的 identity 診斷，不符合「格式範例非完整規格」的審閱要求。
- 在 ISL UT/DT、KTL DT、TKL UT/DT、TKS UT/DT 發現 181 筆帶數字或複合格式的此類列。它們包含 slash 組合（如 `251-000 / 245-038`）、數字後接代碼（如 `579-BWA`）、括號 suffix（如 `549-007(T)`）及站／設備碼形式。尚未假設它們都是 Bracket 或 landmark。
- 對照現有列，12 組相同標籤出現在多個 chainage（共 25 列），4 組不同標籤同位置；暫未發現相同標籤同位置的 exact duplicate。這些是分類未定的 review 診斷，不直接新增 physical identity error，也不把不同標籤自動當合法 overlap。
- 設計：保留明確已知 Bracket（含使用者確認的 TL/Bracket/CR 字母變體）及已知 landmark 分類；對未匹配的帶數字／複合值標記 `unclassified`，輸出來源 workbook、sheet、Excel row、Location、原值與其潛在重複／同位關係。未分類值不被靜默當成 landmark，也不直接升格為 physical Bracket hard error。
- 以新 `outputs/metadata-review-2026-10-22/batch-03/` 重新輸出七線 candidate、provenance、validation、audit 與 unclassified mapping review list；保留 batch-02、原始 workbook 與 runtime config。Candidate 維持 review-only。
- 驗收：回歸測試涵蓋 letter-suffixed physical Bracket、known landmark、unclassified numeric/composite label 及潛在 identity conflicts；七線 parity/digest/provenance 仍吻合，validator 無 error，所有未解 classification 明確列為 review。
- Linear sync：DAV-10、DAV-19 更新為「待完成第三批 validator 修正及重跑」；完成後更新最終測試結果、產物及人工 next action。

### 第三批實作、驗收與交付（目前有效結果）

本節與 `outputs/metadata-review-2026-10-22/batch-03/metadata-review-audit.md` 取代以上第一／第二批待辦結論；舊產物保留作歷史依據。

- Validator 新增 physical Bracket helper，讓已知數字／TL/Bracket/CR 字母變體參與 identity 檢查。未匹配帶數字／slash 的值另列 unclassified；不再一律當 landmark，也不自動升格為已確認 physical identity error。已知 landmark prefix 與純文字 marker 保留既有處理。
- 未分類診斷保留來源 row／原值／Location，檢查相同完整標籤多位置、同位置多標籤、exact duplicate，並將 slash 中可辨識的 Bracket 元件與同 track 已知 physical identity 比較；candidate 原值不拆分、不刪除。
- 全 16 張共用 mapping sheet 已檢查：physical 多位置、physical exact duplicate、invalid rows 皆 0。132 筆字母變體；4 組含字母變體的同位組已依使用者規則接受。一般未確認同位組共 295 組（七線 candidate 286、DRL UT/PL 另外 9）；不能把全部同位組數量當資料錯誤數。
- 未分類列共 189（七線 181、DRL 8）；12 組同名多位置共 25 列，11 組與其他標籤同位置，合計 23 組優先 review；沒有未分類 exact duplicate 或已辨識 slash 元件跨位置衝突。分類未定的 BWA／站碼／括號 suffix／第二段字母前綴等不視為已核准 landmark 或 Bracket。
- 與 2026-09-23 manifest 比較，ISL/KTL source digest 改變，其餘五線不變；以 `dbce953` 取出的歷史 sources digest 全匹配該 manifest。來源值／公式儲存格差異只在 ISL DT track type（1,011）及 KTL DT track type（1,144），包含移列／整理，不表示 2,155 個錯誤。
- 9 月審閱時 mapping SHA-256 `a3fab7a2a12cfb8a5f52a9bd5a11098a362b00843299f865dca0af25a7486d19` 可由 `dbce953` 重現；與目前 `d1651946e0dc96459323b089459f7c940883164d497fa65a04f8f37af41bea46` 相比，Location/Bracket 記錄唯一實質變更為 TWL DT row 46：空白 → 0.4 km。9 月更新前的舊列刪除另以 `9742a50` 比較並輸出獨立 CSV，避免混用舊列號與現有 HEAD。
- 最新 ISL source SHA-256 `afa1b1e6246bb2d9c2096c36bb8a4cbfa16b36185bf8d357d57c6847f4e0a22f`；ISL DT row 387 已輸出為 99536.1 → 99536.9 m，provenance emitted。ISL/KTL DT 反向數皆 0。
- 完整人工操作表：`unclassified-mapping-rows.csv`、`unclassified-identity-risks.csv`、`unconfirmed-same-location-overlaps.csv`、`interval-overlaps.csv`；全部包含完整 workbook 路徑、sheet、Excel row、原始值／位置。
- `python -m pytest backend/tests/test_tov1050_metadata_candidates.py -q` → **14 passed**。
- `python scripts/standardize_tov1050_metadata.py --root "00 Reference Document/config" --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir "outputs/metadata-review-2026-10-22/batch-03/candidates" --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL` → exit 0，七線候選與 manifest 已保存。
- `python scripts/validate_tov1050_metadata_candidates.py --source-root "00 Reference Document/config" --candidate-dir "outputs/metadata-review-2026-10-22/batch-03/candidates" --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir "outputs/metadata-review-2026-10-22/batch-03/validation-final" --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL` → exit 0；七線皆 review_required，無 error finding。
- threshold/location/track/bracket parity、source/mapping digest 全吻合；provenance 所有 mismatch/missing/unexpected/duplicate、invalid source/mapping rows 皆 0；儲存檔案 digest 再核對吻合。`git diff --check` 通過。
- 原始 mapping、ISL/KTL source 與 2026-09-23 舊 ISL candidate 的使用者修改均保留、不 stage。本次只提交 validator、targeted tests、本 request 與新批次產物；未 promotion。
- Next action：使用者優先確認 ISL DT rows 80/84（0.8 m overlap）、KTL DT rows 50/306（5.8 m overlap），以及未分類命名規則／23 組潛在 identity 關係；其他 interval／一般 Bracket 同位組按完整 CSV 審閱或確認通用業務政策。候選維持 review-only，無明確 metadata 核准不得 promotion。
- 第三批最終 Linear 同步已實際完成：DAV-19 更新於 2026-10-22 10:27:32 UTC，DAV-10 更新於 10:27:34 UTC；兩者維持 In Progress，已記錄上述 14 tests、七線驗證、16-sheet 範圍、分類風險、完整產物連結及使用者 next action。提交／push 完成後再補記 commit。

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
