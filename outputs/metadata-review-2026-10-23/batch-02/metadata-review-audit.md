# TOV1050 metadata 審閱：2026-10-23 batch-02

本批以目前實際來源重新產生七線候選，規則版本 2026-10-23。候選全部維持 review-only，沒有 runtime promotion；技術 pass 不代表 metadata 核准。

## Git 與實際來源

- 開始時 master；HEAD／origin/master 均為 483b8e7a3883391f62e02ab19e501c852ca39713。
- 使用者原有四份 dirty Excel（mapping、ISL、KTL、2026-09-23 舊 ISL candidate）均保留，不納入本次 commit。
- Mapping SHA-256：`3e7954907508ee393d8541f0bcb9dbe1a79bea36fe9ccfe540666c0fa53af056`；前批：`b3e415f599c19b546cd1ae46085c92e6482fb2ab39354bfd9dac4314f7ecc3b2`。
- 相較前批，metadata source digest 改變 0 份；各檔完整 digest 見 audit-summary.json。
- 共用 mapping 全 16 sheets 核對；七線覆蓋 14 sheets，DRL UT／PL 另作唯讀診斷，未建立沒有 source 的 DRL candidate。

## 實際資料差異

相較前批 batch-01，Location／Bracket 多重集合差異 6 筆（刪除和新增分別列一筆，不代表相同數量的錯誤）；使用前批原始記錄快照，避免拆分、suffix 或移列影響。
[與上次審閱的完整差異](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/mapping-diff-since-previous-review.csv>)

本次來源更動詳上述 CSV；先前三列未分類命名已由使用者更新原檔並重新分類。候選另依 Support 政策重建 non-support；原始 metadata 未被流程寫回。
較早的刪除決策另以 9742a50 比較；2026-09-23 審閱檔以 dbce953 比較，完整 CSV 保留各歷史基準，不能把今日 HEAD 當作 9 月更新前版本。

## 已解決與已接受規則

- 不同 physical Bracket 同位置：共 343 組已依使用者規則接受，不再要求逐組確認；資料全保留。
- Slash 複合 mapping：40 個來源列拆分，增加 44 個輸出列；provenance 保留原串、各 component、位置及分類。
- 合法同名 termination：25 列候選加位置 suffix；未改來源。
- 全 16 sheets 的 normal 同名多位置、physical exact duplicate 與 invalid mapping 皆為 0。
- 所有 source reversed interval 共 0 列。舊內側 non-support 已 superseded，不再要求逐列確認其端點。
- AEL DT 350-001～350-042 各保留一次；KTL DT CR186-06／08 分別只在 98.368／98.382 km；TWL DT row 46 為 0.4 km／2-045；ISL DT C:N 輔助欄無非空值。

## Support 推導政策與結果

政策 `support-2026-10-23-v1`：Support 按位置排序，每對有效 anchor 建立 `[左Support.endKM+0.0001, 右Support.startKM-0.0001]` km，十進位計算並保留四位；canonical仍為m。Support、Curve／Tangent及location type不套用non-support重建。
首末 Support 外的原始 non-support 暫保留並列 review。異常 Support 原值保留、不自行更改單位或小數點，亦不參與推導；其餘有效 Support 仍推導。異常基準未處理前不得視為 metadata 核准。

| Line／source sheet | 舊內側 non-support superseded | 新衍生段 | 外側保留 | Anchor 問題 |
|---|---:|---:|---:|---:|
| ISL / UT track type | 323 | 323 | 1 | 0 |
| ISL / DT track type | 247 | 245 | 1 | 1 |
| KTL / UT track type | 214 | 214 | 2 | 0 |
| KTL / DT track type | 296 | 296 | 1 | 0 |

[每段雙側 Support 原始 row、端點及四位公里值](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/support-derived-intervals.csv>)
[來源列處置與原值](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/support-source-disposition.csv>)

## 優先人工操作表

| Workbook（完整路徑） | Sheet／Excel row | 欄位與原始值 | 問題／需要決策 |
|---|---|---|---|
| [ISL metadata.xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/00 Reference Document/config/ISL metadata.xlsx>) | DT track type / 298 | track type / startKM / endKM：{"code": "invalid_support_anchor", "source_row": 298, "label": "Support", "start": 99126.0, "end": 99126.0, "reason": "Support is outside the source location envelope (including ORCR); check units/value"} | Support 基準異常；確認 Support 基準值；不能按舊 non-support 端點推斷正確值 |

操作表另列外側 non-support 邊界政策及剩餘 2 組非重建範圍的 interval overlap。原始146組overlap仍保存在validator原始intervals證據；其中舊non-support端點不再列為修正待辦。候選有效interval另有effective_intervals檢查。
[完整人工操作表](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/manual-review-checklist.csv>)

## 實際驗證與候選

實際測試命令與數目見當日 request。Standardizer、validator結果與各候選parity／digest／provenance見JSON；source-to-candidate interval比對已納入Support推導政策，另核對anchor payload與衍生段數量。

| Line | Validator status | 新候選（全為 review-only） |
|---|---|---|
| ISL | review_required | [ISL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/candidates/ISL metadata (wide candidate).xlsx>) |
| KTL | review_required | [KTL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/candidates/KTL metadata (wide candidate).xlsx>) |
| LAR_AEL | review_required | [LAR_AEL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/candidates/LAR_AEL metadata (wide candidate).xlsx>) |
| LAR_TCL | review_required | [LAR_TCL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/candidates/LAR_TCL metadata (wide candidate).xlsx>) |
| TKL | pass | [TKL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/candidates/TKL metadata (wide candidate).xlsx>) |
| TKS | pass | [TKS metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/candidates/TKS metadata (wide candidate).xlsx>) |
| TWL | pass | [TWL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/candidates/TWL metadata (wide candidate).xlsx>) |

## 產物與 Linear

[規則集](<C:/Smart Maintanence/TOV1050_Analyzer/docs/tov1050-metadata-rules.md>)
[需求與實際執行命令](<C:/Smart Maintanence/TOV1050_Analyzer/docs/requests/2026-10-23-tov1050-support-intervals.md>)
[Validator JSON](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/validation-final/2026-10-23-tov1050-metadata-candidate-validation.json>)
[16 sheets 摘要](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/all-mapping-sheet-summary.csv>)
[Mapping 原始記錄快照](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/mapping-source-records.csv>)
[拆分及 termination 對照](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-02/mapping-components.csv>)

本工作階段 Linear MCP 實際掛載且成功讀取 DAV-19／DAV-10；實作前需求與設計已同步。結果與commit／push由當日request及Linear記錄。Next action：處理操作表的異常Support、外側邊界及location overlap；尚未取得metadata核准，不promotion。
