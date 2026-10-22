# TOV1050 Metadata 人工審閱與重新驗證

- 審閱日期：2026-10-22
- Branch / HEAD：`master` / `dbce9535895ca20217bad4029b36316ee21aa7ff`
- 前次 mapping SHA-256：`a3fab7a2a12cfb8a5f52a9bd5a11098a362b00843299f865dca0af25a7486d19`
- 目前 mapping SHA-256：`d1651946e0dc96459323b089459f7c940883164d497fa65a04f8f37af41bea46`
- Candidates：`outputs/metadata-review-2026-10-22/candidates/`
- Validation JSON/Markdown：`outputs/metadata-review-2026-10-22/validation-final/`
- Candidate 狀態：七條線均 `review_required`；未 promotion。

## 結論

依目前共用 mapping、ISL metadata 與 KTL metadata 重新產生七條線 candidates。七份候選的 source/mapping digest 都吻合目前 workbook；threshold、boundary、track interval、mapping parity 均相符；provenance 的 missing、unexpected、duplicate、status、target mismatch 都是 0。Validator exit code 為 0，沒有 error finding；所有 candidate 仍需人工審閱。

目前有一個未解的反向 interval：ISL DT row 387 的 `startKM=99.5381`、`endKM=99.5349`。KTL DT 目前沒有 `End < Start`。此外，現行 ID regex 沒涵蓋 132 筆疑似字母變體；validator 已將它們獨立列入 review 診斷，不自動判定為 physical Bracket 或 landmark。

## 與前次資料比較

你在訊息開頭提到的 `2026-03-23-tov1050-metadata-review-update.md` 在 repo 中不存在；本次依你指定的實際路徑使用 `docs/audits/2026-09-23-tov1050-metadata-review-update.md`。

### 共用 mapping

目前 mapping 保留 16 張 sheet。HEAD workbook 的 SHA-256 與 2026-09-23 audit 記錄的 SHA-256 相同；相較該版，Location/Bracket 資料變更只有：

| 工作表 | Excel row | 前值 | 目前值 | 結果 |
|---|---:|---|---|---|
| TWL DT | 46 | Location 空白；Bracket `2-045` | Location `0.4 km`；Bracket `2-045` | 已補值；candidate/provenance parity 通過，invalid mapping rows 為 0 |

重新核對前次列出的 mapping 變更後，確定被移除的是重複／錯位 row occurrence，不是整段 identity 都消失：

- AEL DT 的 `350-001` 至 `350-042` 共 42 個 identity 目前各保留一次，位於 Excel rows 328–369。
- DRL UT 的 `481-034/035`、`482-011/012/013`、`487-001/002` 目前各保留一次；`487-004` 至 `487-007` 與 `487-BWA` 有 Location，位於 rows 211–215。
- DRL PL 的 `481-034/035`、`484-001/005`、`483-009` 目前各保留一次。
- KTL DT 的錯位 `CR186-06` at `98.371 km`、`CR186-08` at `98.378 km` 未保留；正確位置分別只保留在 row 158 `98.368 km`、row 160 `98.382 km`。
- 前次 ISL UT/DT 的 8 個空 Bracket rows 不再產生 invalid mapping；ISL DT 共用 mapping 的 C:N 輔助欄位目前 0 個非空儲存格。

### Metadata source

| Workbook / sheet | 前次 candidate 所記錄的 source digest | 目前 digest | 目前重新核對 |
|---|---|---|---|
| `ISL metadata.xlsx` / DT track type | `b2cc62f45846af81a874204fc09b039597467a2ec78fe8c715f0de536c313f97` | `bcfdb6a4e475925db35d0440e596c746fc36f5998fa8010a525aa7637f6b0e8c` | 546 筆降至 543 筆；前次 6 筆反向項目中仍有 row 387 一筆未修正 |
| `KTL metadata.xlsx` / DT track type | `e1d49d23615c678b82b1c22e90ed5d4241607c29ddbf076cbffb51fa0d0e938d` | `1f4f256906ccfdc934ebf4a9a4fccdf5deda8cc5b0255e67d81097688e6d99cf` | 668 筆降至 654 筆；前次列出的 10 筆反向項目目前皆不再有 `End < Start` |

KTL DT row 50 現為 `98.6371 -> 98.6459 km`；前次的 `98.6371 -> 97.6459 km` 大跨度已修正。

其他五條線的 source digest 與 2026-09-23 candidate manifest 相同。新批次完全以目前 raw source 產生，不讀取或覆寫 dirty 的 2026-09-23 ISL candidate。

## Bracket 分類風險

Mapping 中找到 132 筆不符合嚴格 ID regex、但符合近似編號樣式的 labels。Candidate 保留原字串；validator 只新增 review 診斷，並分別計算暫定的同名多位置、同位及 exact duplicate，沒有把未確認格式計入 hard identity errors。

| 工作表 | Excel rows | 變體例子 | 需確認 |
|---|---|---|---|
| ISL UT | 62–73、668–673 | `211-1A`、`251A-001` | `-` 後字母與前段數字後字母是否均屬 physical Bracket |
| ISL DT | 247、249、251、253、265、818–821 | `212-5A`、`250A-001` | 同上 |
| KTL UT | 90、92–120、1388、1435 | `CR185A-01`、`157-011A` | `CR` 編號中的字母與尾碼字母的 identity 規則 |
| KTL DT | 121–152、163、167、305–316、1201、1455、1457 | `CR184A-01`、`CR186-10A`、`102-1A` | 同上；另確認下方 row 109/163 同位案例 |
| AEL DT | 454–474 | `364A-001` 至 `364A-021` | 數字段後字母是否屬 identity；另確認下方三組同位案例 |
| TCL UT | 410 | `361-025A` | Bracket 尾碼字母規則 |
| TKL UT | 67、279、379、387、389 | `581-002A`、`569-001A` | Bracket 尾碼字母規則 |
| TKL DT | 262、645 | `568-002A`、`542-017A` | Bracket 尾碼字母規則 |

以上各列皆位於 `C:\Smart Maintanence\TOV1050_Analyzer\00 Reference Document\TOV1050 TL-BK No.xlsx`；欄位為 `Location`（Km）與 `Bracket`。

暫定把疑似變體視為 Bracket 時，目前有 4 處與另一個 identity 同位置。這些是需確認的 mapping/overlap，不是自動刪除指令：

| Workbook | Sheet | Excel rows | Location / Bracket | 需決策 |
|---|---|---|---|---|
| `C:\Smart Maintanence\TOV1050_Analyzer\00 Reference Document\TOV1050 TL-BK No.xlsx` | AEL DT | 451、454 | `33.571 km`：`364-034` / `364A-001` | `364A-001` 是否為 physical Bracket；此換線／重疊位置是否正確 |
| `C:\Smart Maintanence\TOV1050_Analyzer\00 Reference Document\TOV1050 TL-BK No.xlsx` | AEL DT | 452、455 | `33.597 km`：`364-035` / `364A-002` | 同上 |
| `C:\Smart Maintanence\TOV1050_Analyzer\00 Reference Document\TOV1050 TL-BK No.xlsx` | AEL DT | 471、475 | `33.882 km`：`364A-018` / `370-001` | 同上 |
| `C:\Smart Maintanence\TOV1050_Analyzer\00 Reference Document\TOV1050 TL-BK No.xlsx` | KTL DT | 109、163 | `98.396 km`：`CR184-11` / `CR186-10A` | `CR186-10A` 是否為 physical Bracket；同位是否為合法 overlap |

132 筆完整 row-level diagnostics 位於 validation JSON 的各 `tracks.*.mapping_diagnostics.suspected_bracket_variant_rows`。目前疑似變體 exact duplicate、同名多位置皆為 0。

## 尚待人工確認

| Workbook 完整路徑 | Sheet | Excel row | 欄位與目前原始值 | 問題 | 需使用者決策 |
|---|---|---:|---|---|---|
| `C:\Smart Maintanence\TOV1050_Analyzer\00 Reference Document\config\ISL metadata.xlsx` | DT track type | 387 | `track type=non-support`；`startKM=99.5381`；`endKM=99.5349` | `End < Start` 仍存在；candidate 以 min/max 產生 `FromM=99534.9`、`ToM=99538.1`，provenance 註明 directional canonicalization | 請更正其中一端，或確認這是預期的 DT 方向順序並保留原始值 |
| `C:\Smart Maintanence\TOV1050_Analyzer\00 Reference Document\TOV1050 TL-BK No.xlsx` | AEL DT、KTL DT | 上表 8 個 rows | `Location`、`Bracket` | 4 組疑似變體造成的暫定同位置 pairs | 確認變體格式，以及每組同位是否為合法 overlap |
| `C:\Smart Maintanence\TOV1050_Analyzer\00 Reference Document\TOV1050 TL-BK No.xlsx` | 上表各 sheet | 共 132 筆 rows | `Location`、`Bracket` | 舊版 regex 會把部分字母變體當 landmark；新版將它們單獨列為 classification review | 確認表中列出的字母位置是否代表一般 physical Bracket；完整列在 validation JSON |

已解決且核對一致：KTL DT 前次列出的 10 筆反向 interval；ISL DT 前次 6 筆中除 row 387 外的 5 筆；TWL DT row 46；ISL DT 輔助欄位；以及前次 mapping row 移除的重複／錯位意圖。任何 overlap 都未自動刪除。

## 驗證

- Targeted tests：`python -m pytest backend/tests/test_tov1050_metadata_candidates.py -q` → 13 passed。
- Candidate generation：`python scripts/standardize_tov1050_metadata.py --root "00 Reference Document/config" --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir "outputs/metadata-review-2026-10-22/candidates" --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL`。
- Validator：`python scripts/validate_tov1050_metadata_candidates.py --source-root "00 Reference Document/config" --candidate-dir "outputs/metadata-review-2026-10-22/candidates" --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir "outputs/metadata-review-2026-10-22/validation-final" --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL` → exit 0；七條線均 `review_required`。
- 七線 threshold/location/track/bracket parity 全通過；digest 全匹配；provenance mismatch 0；source invalid rows 0；mapping invalid rows 0；exact duplicate identity 0；同 Bracket 多位置 0。
- 同位置多 bracket 與 interval overlap 仍列 review。依業務規則，它們可能是合法 tension-length changeover，不能僅憑計數判錯或刪除。
- 所有 candidate 僅供審閱；沒有 promotion 或 write-back。

## Git 與 Linear

- 保留原有 dirty workbooks 與 dirty 2026-09-23 ISL candidate；新增程式修改、測試、request 與本批次 outputs。
- DAV-19 與 DAV-10 已於 2026-10-22 更新，兩者狀態均維持 `In Progress`。
- DAV-19：<https://linear.app/david-chu/issue/DAV-19/重新審閱更新後的-tov1050-tl-bk-mapping>
- DAV-10：<https://linear.app/david-chu/issue/DAV-10/tov1050metadatagraph-效能exception-generator-ux-與-loadingarchitecture-視覺>
- Request/spec：`docs/requests/2026-10-22-tov1050-metadata-review.md`。
