# TOV1050 Metadata Manual Review Audit - Batch 02

## 結論

- 依目前來源重新產生 ISL、KTL、LAR_AEL、LAR_TCL、TKL、TKS、TWL 七線 candidate、provenance、validation 和本 audit；所有候選均維持 review-only，沒有寫回來源 workbook 或 promotion 至 runtime config。
- 你提到的 `2026-03-23-tov1050-metadata-review-update.md` 在 repo 不存在；本次以存在的 [2026-09-23 audit](../../../docs/audits/2026-09-23-tov1050-metadata-review-update.md) 對照。
- 與第一批 2026-10-22 candidate 相比，只有 ISL metadata source digest 改變；mapping digest 不變。ISL DT row 387 已更新，ISL/KTL DT 的反向 interval 計數均為 0。

## 人工確認及來源差異

- ISL metadata.xlsx → `DT track type` → Excel row 387：目前 `startKM=99.5361`、`endKM=99.5369`。ISL source SHA-256 從第一批的 `bcfdb6a4e475925db35d0440e596c746fc36f5998fa8010a525aa7637f6b0e8c` 更新為 `afa1b1e6246bb2d9c2096c36bb8a4cbfa16b36185bf8d357d57c6847f4e0a22f`。
- 共用 mapping SHA-256 為 `d1651946e0dc96459323b089459f7c940883164d497fa65a04f8f37af41bea46`，與第一批相同；其他六線 metadata source digest 亦與第一批相同。
- 你確認重複 tension length 是刻意刪除並保留唯一一筆、錯位 mapping 是刻意刪除而非有效 Bracket、ISL DT C:N 輔助欄位可棄用、16 筆反向 interval 已修正，以及 TWL DT row 46 已補 Location。實際核對：AEL DT `350-001` 至 `350-042` 各保留一次；ISL DT C:N 非空儲存格為 0；KTL DT `CR186-06` row 158 在 98.368 km、`CR186-08` row 160 在 98.382 km；TWL DT row 46 為 Location 0.4 km / Bracket `2-045`。
- 字母在 TL 前段數字後、Bracket 後段數字後、或 CR 編號中的值均分類為 physical Bracket identity；涵蓋 `211-1A`、`364A-001`、`CR185A-01`、`CR186-10A` 及 `001-002A`、`002A-001`、`002A-002A`、`CR001A-002` 等格式。`SI`、`Mid Point`、`POA` 等仍是 landmark。

## Validator 結果

- `python -m pytest backend/tests/test_tov1050_metadata_candidates.py -q`：13 passed。
- Standardizer 為七線產生候選及 manifest，exit 0。
- Validator exit 0；七線均為 `review_required`，無 error findings。所有 source/mapping digest 和 threshold/track/bracket parity 均吻合；provenance mismatch、source/mapping invalid rows、reversed interval、exact duplicate identity、同一 Bracket 多位置皆為 0。
- 132 個字母變體均納入 physical identity 檢查。共 290 組不同 Bracket identity 同位置：4 組含字母變體，依你確認視為合法 overlap；286 組不含字母變體，仍保留 review。沒有自動刪除或修正任何 mapping。
- Source interval overlap 共 146 組：ISL DT 12、KTL DT 132、LAR_AEL location type 1、LAR_TCL location type 1。全部列於 [interval-overlaps.csv](interval-overlaps.csv)，包含來源 workbook、sheet、Excel rows、原始端點及 overlap 長度。

## 仍需人工判定

| Excel workbook | Sheet / row | 原始值 | 問題 | 需要的決定 |
|---|---|---|---|---|
| `00 Reference Document/config/ISL metadata.xlsx` | `DT track type` rows 80, 84 | row 80: `non-support`, 98.1181 → 98.1199 km；row 84: `non-support`, 98.1171 → 98.1189 km | 同 label、各長 1.8 m，重疊 0.8 m | 確認這是預期的區間 overlap/changeover，或指出需更正的端點 |
| `00 Reference Document/config/KTL metadata.xlsx` | `DT track type` rows 50, 306 | row 50: `non-support`, 98.6371 → 98.6459 km；row 306: `non-support`, 98.6341 → 98.6429 km | 同 label、各長 8.8 m，重疊 5.8 m。row 50 已非反向，但仍與 row 306 重疊 | 確認這是預期 overlap/changeover，或指出需更正的端點 |
| `00 Reference Document/TOV1050 TL-BK No.xlsx` | 七線 mapping sheet，286 組 Excel rows 見 [unconfirmed-same-location-overlaps.csv](unconfirmed-same-location-overlaps.csv) | CSV 提供每組的 Location、Bracket、sheet 和所有 Excel row | 不含字母變體的不同 Bracket identity 同位置；未套用字母變體的已確認例外 | 確認這些組是否均屬合法 tension-length overlap/changeover，或指出需修正的列；不得自動刪除 |

下列四組含字母變體的同位組已按你的規則視為合法 overlap，無需再確認：

| Mapping sheet / rows | Location / Bracket values |
|---|---|
| AEL DT rows 451 / 454 | 33.571 km: `364-034` / `364A-001` |
| AEL DT rows 452 / 455 | 33.597 km: `364-035` / `364A-002` |
| AEL DT rows 471 / 475 | 33.882 km: `364A-018` / `370-001` |
| KTL DT rows 109 / 163 | 98.396 km: `CR184-11` / `CR186-10A` |

## 產物

- Candidates / manifest：[candidates](candidates/)；[manifest.json](candidates/manifest.json)
- Validation：[JSON](validation-final/2026-10-22-tov1050-metadata-candidate-validation.json)；[Markdown](validation-final/2026-10-22-tov1050-metadata-candidate-validation.md)
- 完整 interval overlap 列表：[interval-overlaps.csv](interval-overlaps.csv)
- 未確認一般 Bracket 同位組：[unconfirmed-same-location-overlaps.csv](unconfirmed-same-location-overlaps.csv)
- Request/spec：[docs/requests/2026-10-22-tov1050-metadata-review.md](../../../docs/requests/2026-10-22-tov1050-metadata-review.md)

## Linear

- Linear MCP 本工作階段可用；DAV-10、DAV-19 已更新本次使用者確認與 batch-02 進度。
- DAV-10、DAV-19 均維持 `In Progress`。Next action：使用者確認 ISL DT rows 80/84、KTL DT rows 50/306，並決定 286 組一般 Bracket 同位組的處理方式。
- 在上述決策完成前，候選維持 review-only，不 promotion。
