# TOV1050 Metadata 人工審閱摘要

- 產生日期：2026-09-02
- 用途：供人工審閱原始 metadata workbook 或 candidate workbook，並記錄是否可進入下一輪標準化。
- 審閱原則：本文件與 validator 都不會自動修改原始 workbook；在明確核准前，所有 candidate 維持 review-only。

## 本次執行

執行命令：

```powershell
Set-Location 'C:\Smart Maintanence\TOV1050_Analyzer'
python scripts/validate_tov1050_metadata_candidates.py `
  --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
```

validator 產出：

- [完整 Markdown audit](2026-09-02-tov1050-metadata-candidate-validation.md)
- [完整 JSON audit](2026-09-02-tov1050-metadata-candidate-validation.json)

程序回傳 exit code `1`，原因是 ISL 與 KTL 仍有 `fail` finding；這不是程式崩潰。完整 JSON 才是逐筆資料的權威清單；本摘要只列總數與代表性列。

## 審閱檔案

每條線請並列開啟：

```text
原始來源：00 Reference Document/config/<LINE> metadata.xlsx
候選草稿：docs/audits/standardized-metadata-candidates/<LINE> metadata (wide candidate).xlsx
共用 mapping：00 Reference Document/TOV1050 TL-BK No.xlsx
```

請以原始 workbook 的 `source sheet + source row` 作為主鍵。candidate 只用來確認轉換結果與 row lineage，不應取代原始資料作為事實來源。

## 總覽

| Line | 狀態 | interval invalid | 同 label overlap | ambiguous overlap | mapping invalid | 同位置多 Bracket | 同 Bracket 多位置 | marker | 完全重複 identity | provenance status mismatch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ISL | `fail` | 6 | 29 | 3 | 8 | 47 | 1 | 3 | 0 | 6 |
| KTL | `fail` | 10 | 210 | 9 | 0 | 35 | 3 | 5 | 0 | 10 |
| LAR_AEL | `review_required` | 0 | 1 | 0 | 0 | 112 | 0 | 0 | 42 | 0 |
| LAR_TCL | `review_required` | 0 | 1 | 0 | 0 | 55 | 0 | 0 | 0 | 0 |
| TKL | `review_required` | 0 | 0 | 0 | 0 | 18 | 12 | 30 | 0 | 0 |
| TKS | `review_required` | 0 | 0 | 0 | 0 | 5 | 3 | 2 | 0 | 0 |
| TWL | `review_required` | 0 | 0 | 0 | 1 | 31 | 0 | 0 | 0 | 0 |

欄位說明：

- `interval invalid`：source interval endpoint 非數字或 `endKM < startKM`。
- `同 label overlap`：只在相同 track/location label 內計算，單位為公尺。
- `mapping invalid`：只統計 `tracks.*.mapping_invalid_rows`，例如 Location 非數字或 Bracket 空白；`source_invalid_rows` 是 interval invalid 的 lineage 診斷，不在此欄重複計算。
- `同位置多 Bracket`：同一 `from_m` 對應多個 Bracket。
- `同 Bracket 多位置`：同一 Bracket 對應多個 `from_m`。
- `marker`：Tension Length/Bracket 看起來不是一般 bracket identity，例如 `SI`、`Mid Point`、站名或設備代碼；不是自動判定錯誤，而是需要業務確認。
- `完全重複 identity`：同一 `from_m + Bracket` 的完全重複列。

## 必須先處理的 invalid rows

### ISL

`DT track type` 反向 interval：

| source row | startKM | endKM | 換算後 FromM / ToM | 判定 |
|---:|---:|---:|---:|---|
| 34 | 97.8911 | 97.8909 | 97891.1 / 97890.9 | `endKM < startKM` |
| 82 | 98.1201 | 98.1169 | 98120.1 / 98116.9 | `endKM < startKM` |
| 212 | 98.7091 | 98.7059 | 98709.1 / 98705.9 | `endKM < startKM` |
| 230 | 98.7711 | 98.7539 | 98771.1 / 98753.9 | `endKM < startKM` |
| 390 | 99.5381 | 99.5349 | 99538.1 / 99534.9 | `endKM < startKM` |
| 478 | 99.9281 | 99.8319 | 99928.1 / 99831.9 | `endKM < startKM` |

mapping invalid：`ISL UT` rows `61-64`、`ISL DT` rows `242-245`。這些列的 Location 有數字但 Bracket 為空。

provenance 同步問題：`DT track type` rows `34, 82, 212, 230, 390, 478` 預期 status 應為 `invalid`，candidate provenance 卻標成其他狀態。

### KTL

`DT track type` 反向 interval：

| source row | startKM | endKM | 換算後 FromM / ToM | 判定 |
|---:|---:|---:|---:|---|
| 50 | 98.6371 | 97.6459 | 98637.1 / 97645.9 | `endKM < startKM`，差距較大，優先確認 |
| 110 | 97.9061 | 97.9049 | 97906.1 / 97904.9 | `endKM < startKM` |
| 134 | 98.0031 | 98.0029 | 98003.1 / 98002.9 | `endKM < startKM` |
| 196 | 98.3061 | 98.3049 | 98306.1 / 98304.9 | `endKM < startKM` |
| 240 | 98.4891 | 98.4879 | 98489.1 / 98487.9 | `endKM < startKM` |
| 304 | 98.7651 | 98.3299 | 98765.1 / 98329.9 | `endKM < startKM`，差距較大，優先確認 |
| 312 | 98.3491 | 98.3089 | 98349.1 / 98308.9 | `endKM < startKM` |
| 446 | 99.2241 | 99.2229 | 99224.1 / 99222.9 | `endKM < startKM` |
| 546 | 99.6841 | 99.6829 | 99684.1 / 99682.9 | `endKM < startKM` |
| 602 | 99.9291 | 99.9279 | 99929.1 / 99927.9 | `endKM < startKM` |

provenance 同步問題：上述 10 列都應是 `invalid`，candidate provenance 目前未正確反映。

### TWL

`TWL DT` mapping row `46`：Location 為空、Bracket 為 `2-045`。請確認原始資料是否漏值；不可把空 Location 當成 0 或自動刪除。

## Interval overlap 審閱

重點規則：

1. `overlap_m > 0` 才算真正重疊；僅端點接觸會列為 `touching_count`。
2. 以同一 label 分組；不要把不同 track type 的相鄰區間誤合併。
3. 使用 `previous_source_row`、`current_source_row` 回到原始 sheet，確認是否為重複列、區間切分、方向錯誤或合法重疊。
4. 不可用 `min(start, end)` / `max(start, end)` 靜默修正反向 source row；先決定來源資料語意。

代表性 overlap：

| Line / sheet | source rows | label | overlap |
|---|---:|---|---:|
| ISL / DT track type | 78、84 | non-support | 0.8 m |
| ISL / DT track type | 80、84 | non-support | 0.8 m |
| ISL / DT track type | 80、86 | non-support | 0.8 m |
| KTL / DT track type | 48、52 | non-support | 8.8 m |
| KTL / DT track type | 48、54 | non-support | 9.8 m |
| KTL / DT track type | 48、56 | non-support | 9.8 m |
| LAR_AEL / location type | 2、3 | Open | 8.9 m |
| LAR_TCL / location type | 2、3 | Open | 8.9 m |

ISL DT 共 29 個 overlap、KTL DT 共 210 個 overlap；所有 overlap 的完整清單在 JSON 的 `intervals.*.overlap_examples`（Markdown 僅保留前 20 筆）。

## TL-BK mapping conflict 審閱

### 如何判定

- `location_conflicts`：同一公尺位置有多個 Bracket。可能是跨區段邊界、同一位置的多個合法元件，也可能是錯誤 mapping；需查工程圖或業務規則。
- `bracket_location_conflicts`：同一 Bracket 出現在多個公尺位置。可能是合法重複命名，也可能是 identity 錯誤。
- `marker_rows`：`SI`、`Mid Point`、`AFW`、`POA804`、`TIS903` 等值被放在 Tension Length/Bracket 欄位；請確認是 marker/設備代碼還是格式錯誤。
- `exact_duplicate_identity`：完全相同的 `from_m + Bracket` 重複列；除非能證明是有意保留的 duplicate，否則應修正來源或排除並記錄理由。

### 各線需要人工確認的重點

| Line | 代表性問題 | 審閱重點 |
|---|---|---|
| ISL UT | row 76 `SI/SI`；23 個同位置 conflict | 確認 SI 是否為 marker；確認同位置 bracket pair 是否代表合法邊界 |
| ISL DT | rows 16、271 `SI/SI`；24 個同位置 conflict；Bracket `SI` 出現在兩個位置 | 先處理反向 interval 與 candidate parity，再判定 SI 與跨位置 identity |
| KTL UT | rows 24、95、144、196 `Mid Point/Mid Point`；21 個同位置 conflict；`Mid Point` 重複於四個位置 | 確認 Mid Point 是否為合法 marker，不要當普通 bracket |
| KTL DT | row 167 `SI/SI`；14 個同位置 conflict；2 個同 Bracket 多位置 | 確認 SI 與 `CR186-06`、`CR186-08` 的位置是否為資料錯誤 |
| LAR_AEL UT/DT | 59/53 個同位置 conflict；DT 有 42 個完全重複 identity | 先確認 duplicates 是否是來源重複，再確認同位置多 bracket 是否為合法結構 |
| LAR_TCL UT/DT | 34/21 個同位置 conflict | 依工程圖確認跨 bracket 邊界，不能直接擇一刪除 |
| TKL UT/DT | 17/13 個 marker；6/12 個同位置 conflict；8/4 個同 Bracket 多位置 | 多數值像設備/站名代碼，需業務定義 marker 與 bracket 的差異 |
| TKS UT/DT | 1/1 個 marker；2/3 個同位置 conflict；1/2 個同 Bracket 多位置 | 確認 TKS 使用 TKL session 的 mapping 語意是否一致 |
| TWL UT/DT | 15/16 個同位置 conflict；DT row 46 invalid | 先補正或排除空 Location，再確認跨 bracket 邊界 |

完整 row、`from_m`、bracket 清單與 source row 位於 JSON 的：

```text
workbooks[].tracks[].mapping_diagnostics
```

## Canonical chainage 與候選差異

所有 `Km` 值都必須依下式轉換：

```text
Chainage_m = Km * 1000
```

例如 `98.1201 km` 是 `98120.1 m`，不是 `98.1201 m`。

ISL DT 與 KTL DT 的反向 source row 在 candidate 中造成 interval parity 差異：

- ISL DT：candidate 多出 6 個由反向列正規化而來的 interval。
- KTL DT：candidate 多出 10 個由反向列正規化而來的 interval。

這些 extra interval 不是可直接接受的修正；需先由 reviewer 決定「修正原始 start/end」、「排除該列並保留理由」或「確認資料方向定義後重新產生 candidate」。

## 人工決策表

請以每一個 source row 或 conflict group 填寫一列：

| decision id | line | source sheet / mapping sheet | source row(s) | finding type | 原始值摘要 | candidate 值摘要 | decision | 理由 / 依據 | reviewer / date |
|---|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  | `accept` / `correct_source` / `exclude_with_reason` / `needs_business_confirmation` |  |  |

建議 decision 定義：

- `accept`：確認為合法資料，candidate 可保留。
- `correct_source`：原始 workbook 應先修正，之後重新產生 candidate 與 audit。
- `exclude_with_reason`：不納入 runtime，但必須在 provenance/audit 保留 source row 與排除理由。
- `needs_business_confirmation`：目前資訊不足，禁止 promotion。

## 審閱後重跑

### 編輯原始 workbook 後

1. 保留原始檔備份與 reviewer 決策紀錄。
2. 重新產生 candidate：

```powershell
python scripts/standardize_tov1050_metadata.py --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
```

3. 重新驗證：

```powershell
python scripts/validate_tov1050_metadata_candidates.py --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
```

### 只編輯 candidate 草稿時

可以把 candidate 當作提案，但修改任何 row、sheet 或 provenance 後都必須重新執行 validator；若 source row lineage、status、target sheet 或 digest 不一致，validator 應維持 fail-closed。未完成重跑前，不可將 candidate 複製到 runtime `config/`。

## Promotion gate

目前沒有任何 candidate 可以直接 promotion。至少必須滿足：

- 所有反向 interval 都有明確決策，且不再以 `min/max` 靜默正規化。
- overlap 已逐組確認為合法區間切分，或已修正/排除並留下理由。
- TL-BK marker、同位置多 Bracket、同 Bracket 多位置、完全重複 identity 都有明確業務決策。
- invalid rows 已修正或以 provenance-preserving 方式排除。
- candidate interval/bracket parity、provenance status/target、source/mapping digest 全部通過。
- validator 報告不再是 `fail` 或未核准的 `review_required`。

在上述條件完成前，不要修改或覆蓋：

```text
config/*.xlsx
00 Reference Document/config/*.xlsx
```
