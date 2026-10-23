# TOV1050 metadata 審閱：2026-10-23 batch-04

本批以目前實際來源重新產生七線候選，規則版本 2026-10-23。候選全部維持 review-only，沒有 runtime promotion；技術 pass 不代表 metadata 核准。

## Git 與實際來源

- 產生時 branch：master；HEAD：e8361bb850036b46d7fb1d28ecdc1ab451f25f3e。
- 使用者六份 dirty Excel（mapping、ISL、KTL、LAR_AEL、LAR_TCL、2026-09-23 舊 ISL candidate）均保留，不納入本次 commit。
- Mapping SHA-256：`3e7954907508ee393d8541f0bcb9dbe1a79bea36fe9ccfe540666c0fa53af056`；前批：`3e7954907508ee393d8541f0bcb9dbe1a79bea36fe9ccfe540666c0fa53af056`。
- 相較前批，metadata source digest 改變 2 份；各檔完整 digest 見 audit-summary.json。
- 共用 mapping 全 16 sheets 核對；七線覆蓋 14 sheets，DRL UT／PL 另作唯讀診斷，未建立沒有 source 的 DRL candidate。

## 實際資料差異

相較前批 batch-02，Location／Bracket 多重集合差異 0 筆（刪除和新增分別列一筆，不代表相同數量的錯誤）；使用前批原始記錄快照，避免拆分、suffix 或移列影響。
[與上次審閱的 mapping 差異](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/mapping-diff-since-previous-review.csv>)
[location type 端點差異](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/location-diff-since-previous-review.csv>)

本次來源差異詳上述 CSV 與 source digests。候選依 Support 政策及外部人工授權更正清單重建；原始 metadata 未被流程寫回。
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
首末 Support 外的原始 non-support 依使用者已確認政策保留；本批5筆已明確接受並另存銜接證據，無須重複確認。只有明確授權且與來源值匹配的更正可參與推導，其原值與授權保留；其餘異常 Support 不自行更改單位或小數點。

本批人工授權更正 1 筆，清單 digest `857616e9f0bd82ba16fa480c78e64b7f80049e167264f7acd248f1635abaa7e8`。完整原值、有效值、授權與套用狀態見 audit-summary.json／候選 __review_corrections__。ISL / DT track type / row298：{'start': 99126.0, 'end': 99126.0} → {'start': 99.126, 'end': 99.126} km (applied)。

| Line／source sheet | 舊內側 non-support superseded | 新衍生段 | 外側待審 | 外側已接受 | Anchor 問題 |
|---|---:|---:|---:|---:|---:|
| ISL / UT track type | 323 | 323 | 0 | 1 | 0 |
| ISL / DT track type | 247 | 246 | 0 | 1 | 0 |
| KTL / UT track type | 214 | 214 | 0 | 2 | 0 |
| KTL / DT track type | 296 | 296 | 0 | 1 | 0 |

[每段雙側 Support 原始 row、端點及四位公里值](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/support-derived-intervals.csv>)
[來源列處置與原值](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/support-source-disposition.csv>)
[已接受外側範圍與 Support 銜接證據](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/accepted-outer-ranges.csv>)

## 人工操作表

| Workbook（完整路徑） | Sheet／Excel row | 欄位與原始值 | 問題／需要決策 |
|---|---|---|---|
| 無待確認列 | — | — | 已列問題全部解決或取得使用者接受；候選仍待整體核准 |

目前人工操作表共 0 筆，非重建範圍的 interval overlap 共 0 組。原始overlap仍保存在validator原始intervals證據；其中舊non-support端點不再列為修正待辦。候選有效interval另有effective_intervals檢查。
[完整人工操作表](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/manual-review-checklist.csv>)

## 實際驗證與候選

實際測試命令與數目見當日 request。Standardizer、validator結果與各候選parity／digest／provenance見JSON；source-to-candidate interval比對已納入Support推導政策，另核對anchor payload與衍生段數量。

| Line | Validator status | 新候選（全為 review-only） |
|---|---|---|
| ISL | pass | [ISL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/candidates/ISL metadata (wide candidate).xlsx>) |
| KTL | pass | [KTL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/candidates/KTL metadata (wide candidate).xlsx>) |
| LAR_AEL | pass | [LAR_AEL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/candidates/LAR_AEL metadata (wide candidate).xlsx>) |
| LAR_TCL | pass | [LAR_TCL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/candidates/LAR_TCL metadata (wide candidate).xlsx>) |
| TKL | pass | [TKL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/candidates/TKL metadata (wide candidate).xlsx>) |
| TKS | pass | [TKS metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/candidates/TKS metadata (wide candidate).xlsx>) |
| TWL | pass | [TWL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/candidates/TWL metadata (wide candidate).xlsx>) |

## 產物與 Linear

[規則集](<C:/Smart Maintanence/TOV1050_Analyzer/docs/tov1050-metadata-rules.md>)
[需求與實際執行命令](<C:/Smart Maintanence/TOV1050_Analyzer/docs/requests/2026-10-23-tov1050-support-intervals.md>)
[Validator JSON](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/validation-final/2026-10-23-tov1050-metadata-candidate-validation.json>)
[16 sheets 摘要](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/all-mapping-sheet-summary.csv>)
[Mapping 原始記錄快照](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/mapping-source-records.csv>)
[拆分及 termination 對照](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-04/mapping-components.csv>)

本工作階段 Linear MCP 實際掛載且成功讀取 DAV-19／DAV-10；實作前需求與設計已同步。結果與commit／push由當日request及Linear記錄。Next action：使用者審閱本批候選後明確決定是否核准；已接受外側範圍不再重複要求確認。尚未取得整份metadata核准，不promotion。
