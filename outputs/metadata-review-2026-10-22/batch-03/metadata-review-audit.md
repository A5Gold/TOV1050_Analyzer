# TOV1050 metadata 人工審閱：2026-10-22 batch-03

本批取代 batch-02 作為目前審閱依據；保留所有舊產物。七線 candidate 均已重新產生，狀態為 review_required，沒有 error findings。原始 workbook、舊 candidate、runtime config 未由本流程寫入；本報告不是 metadata 核准。

## 實際來源與 Git 狀態

- 開始時 branch master，HEAD 與 origin/master 均為 8c98a3feb851b706501254d2735bf2b4a87cf862。
- 使用者既有修改：共用 mapping、ISL/KTL 原始 metadata、2026-09-23 的 ISL candidate；均保留且不納入本次 commit。
- 共用 mapping 有 16 張工作表；七線 candidate 覆蓋其中 14 張，DRL UT/PL 另作 mapping 唯讀診斷，沒有產生不存在來源的 DRL candidate。
- 原始 mapping：[共用 TL-BK workbook](<C:/Smart Maintanence/TOV1050_Analyzer/00 Reference Document/TOV1050 TL-BK No.xlsx>)。
- 最新 mapping SHA-256：d1651946e0dc96459323b089459f7c940883164d497fa65a04f8f37af41bea46。
- 2026-03-23-tov1050-metadata-review-update.md 不存在；實際前次報告是 2026-09-23 的 audit。

## 與上次審閱相比的實際變更

以 dbce953 取出的歷史來源逐一核對 2026-09-23 manifest digest（全部吻合），不是只比目前 HEAD 或沿用舊文字結論。

- ISL/KTL source digest 改變，其他五線 source digest 完全相同。值／公式儲存格差異僅發生於 ISL DT track type（1,011 格）與 KTL DT track type（1,144 格），包含整理移列和端點修正，不代表 2,155 個資料錯誤。完整逐格差異保留 old/current value 與 baseline commit。
- 相較 2026-09-23 mapping（SHA-256 a3fab7a2a12cfb8a5f52a9bd5a11098a362b00843299f865dca0af25a7486d19），Location/Bracket 多重集合唯一實質變更是 TWL DT row 46 的 2-045：Location 空白 → 0.4 km。CSV 以舊記錄減一、新記錄加一表示。
- 另以 9742a50（SHA-256 e1e008b334a0e13b2c10d496d5cca2b79eb6f94409660d8f3a12860da1e66656）比對 9 月更新前 mapping，保留 76 筆記錄計數差異。這個基準才用於舊 rows 370–411 等刪除問題，不把舊列號當成目前列號。
- 相較 2026-10-22 第一批，僅 ISL source digest 由 bcfdb6a4e475925db35d0440e596c746fc36f5998fa8010a525aa7637f6b0e8c 變為 afa1b1e6246bb2d9c2096c36bb8a4cbfa16b36185bf8d357d57c6847f4e0a22f。batch-02 與 batch-03 的來源 digest 相同；第三批補正未分類診斷。

## 已解決或已有使用者決定

- ISL DT row 387：A387=non-support，B387=startKM 99.5361，C387=endKM 99.5369；candidate ISL DT B387/C387 為 99536.1/99536.9 m，provenance 記錄 emitted。Excel 浮點儲存可出現 99536.90000000001，按驗證容差比較，單位維持公尺。
- ISL/KTL DT 的 End < Start 均為 0；七線所有來源 interval 亦無 reversed rows。
- TWL DT mapping row 46：Location=0.4 km、Bracket=2-045，正確輸出為 400 m，不是把空白當零。
- AEL DT 350-001 至 350-042 各保留一次；刪除的是重複記錄，整段 tension length 並未消失。
- KTL DT CR186-06 row 158 在 98.368 km；CR186-08 row 160 在 98.382 km，各只剩一個位置。使用者已確認其他錯位／重複 mapping 刪除的業務意圖。
- ISL DT C:N 非空儲存格為 0；使用者已確認可棄用。
- 132 筆字母變體納入 physical Bracket identity（TL 數字段後、Bracket 數字段後、CR 編號字母規則同理）。4 組含字母變體的同位組已按使用者規則確認為合法 overlap，無需再確認：AEL DT 451/454、452/455、471/475；KTL DT 109/163。

## 尚需業務決定：優先操作表

下列 interval 是同 label、同長度重疊的優先提示，不是已證實資料錯誤；其他 144 組仍完整保留於 overlap CSV，不能僅依 overlap 數量刪除。

| Excel 完整路徑 | Sheet／Excel row／欄位 | 原始值 | 問題／需要的決定 |
|---|---|---|---|
| [ISL metadata.xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/00 Reference Document/config/ISL metadata.xlsx>) | DT track type rows 80/84；A=track type，B=startKM，C=endKM | non-support；row 80：98.1181 → 98.1199 km；row 84：98.1171 → 98.1189 km | 各長 1.8 m、重疊 0.8 m；確認為預期 overlap，或修正端點 |
| [KTL metadata.xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/00 Reference Document/config/KTL metadata.xlsx>) | DT track type rows 50/306；A/B/C 同上 | non-support；row 50：98.6371 → 98.6459 km；row 306：98.6341 → 98.6429 km | 各長 8.8 m、重疊 5.8 m；row 50 已非反向，仍需確認重疊意義 |
| [共用 TL-BK workbook](<C:/Smart Maintanence/TOV1050_Analyzer/00 Reference Document/TOV1050 TL-BK No.xlsx>) | TKL UT rows 58/145；A=Location、B=Bracket | 64.561 / 63.302 km；579-BWA | 未確認代碼格式，相同標籤多位置；若屬設備 landmark 可保留，若屬同一 physical Bracket 須更正或說明 identity |
| [共用 TL-BK workbook](<C:/Smart Maintanence/TOV1050_Analyzer/00 Reference Document/TOV1050 TL-BK No.xlsx>) | DRL UT rows 12/37/82/83/209；DRL PL rows 12/31；B=Bracket（A 欄位置詳 CSV） | 481-A01、481-A02、482-A01、482-A02、486-A01 | 字母位於第二段數字之前，不在本次確認的數字後綴規則內；請確認是否為 physical Bracket |

完整 189 筆未分類操作表：[unclassified-mapping-rows.csv](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/unclassified-mapping-rows.csv>)。每列含完整 workbook path、sheet、Excel row、Location、原始 Bracket 與需決定事項。
優先 23 組未分類 identity 風險：[unclassified-identity-risks.csv](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/unclassified-identity-risks.csv>)。其中 12 組同名多位置（25 列），11 組未分類值與其他值同位置；尚未認定為 physical identity error。
一般 physical Bracket 同位組：七線 286 組，另 DRL 9 組，共 295 組，[完整同位表](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/unconfirmed-same-location-overlaps.csv>) 包含全部 Excel rows。請確認是否可按 tension-length overlap 規則接受，或指出需修正列；本次字母變體的確認未自動延伸為全部一般同位組的核准。

## 未分類格式與潛在 identity 風險

已知 SI/Mid Point/POA 與一般純文字 marker 保持 landmark；未匹配的帶數字或 slash 值另列 unclassified，不再以 regex 不匹配直接宣告為 landmark。分類可能包括 physical Bracket、複合 mapping、站名或設備代碼，仍需業務規則。
- 七線 mapping 共 181 列未分類；加上 DRL 的 8 列，共 189 列。
- slash 複合格式共 40 列：ISL UT 6、ISL DT 10、KTL DT 24，例如 251-000 / 245-038。已把可辨識的 slash 元件與同 track 其他 physical Bracket 比較，未發現元件跨位置衝突；未拆分或改寫 candidate。
- 其他格式包括 579-BWA、549-007(T)、590-024-LA、HAH885、481-A01。設備／站碼是否為 landmark、suffix 是否改變 physical identity 仍需確認；不是要求逐一把設備代碼改成 Bracket。
- 已確認 physical Bracket 的同名多位置／exact duplicate 均為 0；這個零不代表未分類格式已獲核准。

## 實際測試與驗證

```text
python -m pytest backend/tests/test_tov1050_metadata_candidates.py -q
14 passed
python scripts/standardize_tov1050_metadata.py --root "00 Reference Document/config" --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir "outputs/metadata-review-2026-10-22/batch-03/candidates" --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
exit 0; 7 candidates + manifest
python scripts/validate_tov1050_metadata_candidates.py --source-root "00 Reference Document/config" --candidate-dir "outputs/metadata-review-2026-10-22/batch-03/candidates" --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir "outputs/metadata-review-2026-10-22/batch-03/validation-final" --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
exit 0; all seven lines review_required; no error findings
git diff --check: passed
```

- source/mapping digest、threshold/location/track/bracket parity 全吻合；source/mapping invalid rows、reversed intervals、physical duplicate/multiple-location、provenance missing/unexpected/duplicate/status/target mismatch 皆為 0。
- 保存的 candidate SHA-256 與 validation JSON 相符，來源 digest 在重跑後維持相同。
- 完整 16-sheet mapping 檢查無 invalid row、physical duplicate 或 multiple-location；DRL 只有 mapping 審閱，無 runtime/candidate promotion。
- 共 146 組來源 interval overlap（ISL DT 12、KTL DT 132、LAR_AEL location type 1、LAR_TCL location type 1），列表完整，保留兩端原值與 source rows。

## 產物

- [七線候選 manifest](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/candidates/manifest.json>)
- [完整 validator JSON](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/validation-final/2026-10-22-tov1050-metadata-candidate-validation.json>)
- [validator Markdown](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/validation-final/2026-10-22-tov1050-metadata-candidate-validation.md>)
- [全部 interval overlaps](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/interval-overlaps.csv>)
- [16-sheet 檢查摘要](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/all-mapping-sheet-summary.csv>)
- [來源儲存格差異](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/source-cell-differences.csv>)
- [相較 2026-09-23 mapping 差異](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/mapping-diff-since-2026-09-23.csv>)
- [相較 2026-09-23 更新前 mapping 差異](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/mapping-diff-before-2026-09-23.csv>)
- [ISL candidate](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/candidates/ISL metadata (wide candidate).xlsx>)
- [KTL candidate](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/candidates/KTL metadata (wide candidate).xlsx>)
- [LAR_AEL candidate](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/candidates/LAR_AEL metadata (wide candidate).xlsx>)
- [LAR_TCL candidate](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/candidates/LAR_TCL metadata (wide candidate).xlsx>)
- [TKL candidate](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/candidates/TKL metadata (wide candidate).xlsx>)
- [TKS candidate](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/candidates/TKS metadata (wide candidate).xlsx>)
- [TWL candidate](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-22/batch-03/candidates/TWL metadata (wide candidate).xlsx>)

## Linear 同步與下一步

Linear MCP 本工作階段已確認掛載；DAV-19 於 2026-10-22 10:27:32 UTC、DAV-10 於 10:27:34 UTC 已實際同步本批產物、14 tests、validator 結果、16-sheet mapping 範圍及待決策事項，兩者均維持 In Progress。提交／push 完成後補記 commit。下一步由使用者確認上述 interval 端點／overlap、未分類命名規則及一般同位 Bracket 政策；未獲明確核准前 candidate 維持 review-only。
