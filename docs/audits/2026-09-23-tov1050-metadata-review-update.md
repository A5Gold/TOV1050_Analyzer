# TOV1050 TL-BK Metadata 更新後審閱

- 審閱日期：2026-09-23
- 原始 mapping：`00 Reference Document/TOV1050 TL-BK No.xlsx`
- 原始 mapping SHA-256：`a3fab7a2a12cfb8a5f52a9bd5a11098a362b00843299f865dca0af25a7486d19`
- candidate：`outputs/metadata-review-2026-09-23/candidates/`
- validator JSON：`outputs/metadata-review-2026-09-23/validation-final/2026-09-23-tov1050-metadata-candidate-validation.json`
- validator Markdown：`outputs/metadata-review-2026-09-23/validation-final/2026-09-23-tov1050-metadata-candidate-validation.md`
- Linear：DAV-19（DAV-10 子 issue）

## 結論

這本是多線共用的 TL-BK mapping workbook，不是單一 `KTL metadata.xlsx`；它有 16 張線別／方向工作表，其中包含 `KTL UT`、`KTL DT`。本次以更新檔重新產生七條目前有 metadata source 的 candidate（ISL、KTL、LAR_AEL、LAR_TCL、TKL、TKS、TWL）。

一般 physical Bracket identity 的格式範例 `123-01`、`CR283-15` 會參與 identity 檢查；`SI`、`Mid Point`、`POA`（包括 `POA804-01`）、站名與設備代碼等 landmark 仍保留在 candidate 與 audit，但不再混入「同位置多 Bracket」診斷。Location 的來源單位為 Km，candidate 只在 adapter 邊界做 `Location * 1000 -> Bracket FromM` 公尺轉換；例如 `98.1502 km -> 98150.2 m`，不可把 `98150.2` 當作公里。

驗證器 exit code 為 0，七條線均為 `review_required`、沒有 error。七份 candidate 的 source/mapping SHA-256 均吻合目前檔案；source-row provenance 的 missing、unexpected、duplicate、status、target mismatch 都是 0。candidate 仍是 review-only，沒有複製至 runtime `config/`。

## 相較 Git HEAD 的 Location/Bracket 變更

下表的舊列號是 `HEAD` 版 mapping 的 Excel source row；新增列號是目前更新檔的 source row。舊值中的 Location 以 Km 表示。候選未出現的列代表該列被移除或因欄位無效而略過。

| 工作表 | 舊 source row／原始值 | 新 source row／candidate 值 | 影響 | 需要確認 |
|---|---|---|---|---|
| AEL DT | rows 370–411：`350-001`–`350-042`，Location `30.860`–`32.088 km` | 沒有對應列；candidate 不再輸出這 42 個 mapping rows | 42 個 bracket mapping 不再進入 candidate | 確認是否刻意刪除整段 `350` tension length |
| DRL UT | rows 40–41：`481-034`/`481-035`；rows 86–90：`482-011`–`482-013`（含重複列）；rows 217–218：`487-001`/`487-002`；rows 220–224：Location 空白的 `487-004`–`487-007`、`487-BWA` | rows 211–215 新增：`487-004` `44.9452 km -> 44945.2 m`、`487-005` `44.9654 -> 44965.4 m`、`487-006` `44.9856 -> 44985.6 m`、`487-007` `45.0058 -> 45005.8 m`、`487-BWA` `45.026 -> 45026 m` | 5 個缺 Location 的舊列獲得新位置；`481`/`482`/`487-001`/`487-002` 舊 mapping 消失；淨減 9 列 | 確認舊 bracket 刪除是否刻意，以及五個新 Km 位置是否正確 |
| DRL PL | rows 40–41：`481-034`/`481-035`；row 60：`484-001`；rows 62–63：重複 `484-005`；row 65：`483-009` | 沒有對應列 | 6 個 mapping rows 不再輸出 | 確認這些刪除與重複列處理是否刻意 |
| KTL DT | row 159：`98.371 km / CR186-06`；row 161：`98.378 km / CR186-08` | 已移除；candidate 仍保留 `CR186-06` at `98.368 km -> 98368 m`、`CR186-08` at `98.382 km -> 98382 m` | `CR186-06`、`CR186-08` 現各只在一個位置；同 Bracket 多位置由 2 組降至 0 | 確認移除的是錯位 mapping，而非有效 bracket |
| ISL UT | rows 61–64：Location `100.238`、`100.240`、`100.249`、`100.256 km`，Bracket 空白 | 沒有對應列 | 移除 4 筆無 bracket 的 mapping invalid rows | 確認這四筆是否可直接排除 |
| ISL DT | rows 242–245：Location `99.931`、`99.933`、`99.942`、`99.948 km`，Bracket 空白 | 沒有對應列 | 移除 4 筆無 bracket 的 mapping invalid rows | 確認這四筆是否可直接排除 |
| ISL DT | HEAD 版 C:N 共 12 欄有 1,090 個非空儲存格（包含公式／輔助值）；更新檔只保留 A:B 的 Location/Bracket | 無 candidate mapping 影響；standardizer 只讀 Location、Bracket | 舊輔助欄位不會進入 candidate；更新檔不再含這些 1,090 個儲存格 | 確認移除輔助欄位是刻意且資料可棄用；我沒有復原它們 |

其他工作表的 Location/Bracket 兩欄資料多重集合與 HEAD 相同；部分工作表移除的是空白額外欄位，不影響 mapping。

## 新 candidate 的檢查摘要

| Line | 狀態 | 同 Chainage 多一般 Bracket（UT/DT 等方向合計） | Landmark rows | 同 Bracket 多位置 | 完全重複 identity | 反向 interval | Mapping invalid |
|---|---|---:|---:|---:|---:|---:|---:|
| ISL | review_required | 47 | 43 | 0 | 0 | 6（DT） | 0 |
| KTL | review_required | 34 | 108 | 0 | 0 | 10（DT） | 0 |
| LAR_AEL | review_required | 109 | 21 | 0 | 0 | 0 | 0 |
| LAR_TCL | review_required | 55 | 1 | 0 | 0 | 0 | 0 |
| TKL | review_required | 7 | 140 | 0 | 0 | 0 | 0 |
| TKS | review_required | 3 | 28 | 0 | 0 | 0 | 0 |
| TWL | review_required | 31 | 0 | 0 | 0 | 0 | 1（DT row 46） |

「同 Chainage 多一般 Bracket」仍完整列在 JSON；依使用者確認，它可能代表 tension-length changeover 的合法邊界，不是自動錯誤，也不應因此刪列。所有線別的「同 Bracket 多位置」與「完全重複 identity」目前都是 0。

### 仍要確認的 interval／invalid mapping

| Line / source sheet | Source row | 原始 StartKM → EndKM | Candidate FromM → ToM | 判斷／需決定 |
|---|---:|---:|---:|---|
| ISL / DT track type | 34 | 97.8911 → 97.8909 | 97890.9 → 97891.1 m | End 小於 Start；確認方向排序是否可按 min/max 正規化 |
| ISL / DT track type | 82 | 98.1201 → 98.1169 | 98116.9 → 98120.1 m | 同上 |
| ISL / DT track type | 212 | 98.7091 → 98.7059 | 98705.9 → 98709.1 m | 同上 |
| ISL / DT track type | 230 | 98.7711 → 98.7539 | 98753.9 → 98771.1 m | 同上 |
| ISL / DT track type | 390 | 99.5381 → 99.5349 | 99534.9 → 99538.1 m | 同上 |
| ISL / DT track type | 478 | 99.9281 → 99.8319 | 99831.9 → 99928.1 m | 同上 |
| KTL / DT track type | 50 | 98.6371 → 97.6459 | 97645.9 → 98637.1 m | 反向且跨度 991.2 m，優先確認原始端點 |
| KTL / DT track type | 110 | 97.9061 → 97.9049 | 97904.9 → 97906.1 m | End 小於 Start；確認同一規則是否適用 |
| KTL / DT track type | 134 | 98.0031 → 98.0029 | 98002.9 → 98003.1 m | 同上 |
| KTL / DT track type | 196 | 98.3061 → 98.3049 | 98304.9 → 98306.1 m | 同上 |
| KTL / DT track type | 240 | 98.4891 → 98.4879 | 98487.9 → 98489.1 m | 同上 |
| KTL / DT track type | 304 | 98.7651 → 98.3299 | 98329.9 → 98765.1 m | 反向且跨度 435.2 m，優先確認原始端點 |
| KTL / DT track type | 312 | 98.3491 → 98.3089 | 98308.9 → 98349.1 m | End 小於 Start；確認同一規則是否適用 |
| KTL / DT track type | 446 | 99.2241 → 99.2229 | 99222.9 → 99224.1 m | 同上 |
| KTL / DT track type | 546 | 99.6841 → 99.6829 | 99682.9 → 99684.1 m | 同上 |
| KTL / DT track type | 602 | 99.9291 → 99.9279 | 99927.9 → 99929.1 m | 同上 |
| TWL / TWL DT mapping | 46 | Location 空白；Bracket `2-045` | candidate 略過，provenance `invalid` | 補正 Location，或確認以有理由的排除方式保留 lineage |

Validator 仍計數 interval overlap pair：ISL 56、KTL 449、LAR_AEL 1、LAR_TCL 1。這些是 pair 數，不是唯一列數；使用者已說明 tension-length changeover 的 overlap 可合法存在，因此不得將數量直接解讀為錯誤或刪除指令。另有 ISL 3 組、KTL 9 組「等長重疊」heuristic 例子，完整 source row pairs 在 JSON 的 `intervals.*.ambiguous_overlap_examples`；這只是 validator 的提示，不代表已證實資料錯誤。

## 目前最需要人工確認的項目

1. 確認 AEL DT、DRL UT/PL、KTL DT、ISL UT/DT 表格列的刪除／修補是否都是刻意變更，尤其 AEL DT 整段 42 個 `350-*` bracket 與 DRL UT 的 `487-001/002` 移除。
2. 確認 ISL DT 的 C:N 輔助欄位是否可棄用；更新檔已不含該 1,090 個非空儲存格。
3. 確認 16 筆反向 interval 是否可依同一 UT/DT 規則使用 min/max 轉為公尺範圍；先看 KTL DT rows 50、304 的大跨度。
4. 決定 TWL DT row 46 的 `2-045` 缺少 Location 要補值，或以理由排除。
5. 確認完成後再要求重新生成候選。當前候選只適合審閱，未核准前不可 promotion。

## 產物與驗證

- 更新後 candidate 檔、manifest 與 provenance：`outputs/metadata-review-2026-09-23/candidates/`
- 完整 JSON/Markdown validator audit：`outputs/metadata-review-2026-09-23/validation-final/`
- Targeted tests：`python -m pytest backend/tests/test_tov1050_metadata_candidates.py -q` → 12 passed。
- Validator：`python scripts/validate_tov1050_metadata_candidates.py --candidate-dir outputs/metadata-review-2026-09-23/candidates --output-dir outputs/metadata-review-2026-09-23/validation-final --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL` → exit 0，七條線均 `review_required`，無 error。
- 原始 TL-BK workbook 與 runtime metadata 均未由本次流程寫入；原 workbook 的現有修改完整保留。
