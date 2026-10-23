# TOV1050 metadata 審閱：2026-10-23 batch-01

本批以目前實際來源重新產生七線候選，規則版本 2026-10-23。候選全部維持 review-only，沒有 runtime promotion；技術 pass 不代表 metadata 核准。

## Git 與實際來源

- 開始時 master；HEAD／origin/master 均為 4c12e8d4e004c004c07b21394028beac88ebf75d。
- 使用者原有四份 dirty Excel（mapping、ISL、KTL、2026-09-23 舊 ISL candidate）均保留，不納入本次 commit。
- Mapping SHA-256：`b3e415f599c19b546cd1ae46085c92e6482fb2ab39354bfd9dac4314f7ecc3b2`；前次 batch-03：`d1651946e0dc96459323b089459f7c940883164d497fa65a04f8f37af41bea46`。
- 七份 metadata source digest 全部與昨日 batch-03 相同；ISL／KTL 自該次審閱後沒有新內容變更，與 Git HEAD 的差異仍存在。
- 共用 mapping 全 16 sheets 核對；七線覆蓋 14 sheets，DRL UT／PL 另作唯讀診斷，未建立沒有 source 的 DRL candidate。

## 實際資料差異

相較昨日 batch-03 的 14 sheets，Location／Bracket 多重集合差異 85 筆（刪除和新增分別列一筆，不能當作相同數量的錯誤）。以前次 candidate 配對 provenance 重建來源 row，按 canonical 精度排除 Excel 浮點尾數噪音；非單純比較移列後的 row。DRL 依前次已核實的歷史 mapping 比較，變更 0 筆。
[與上次審閱的完整差異](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/mapping-diff-since-previous-review.csv>)

本次變更包括 SI 補編號、BWA／Fixed subtype、TKS isolator 格式、TKL DT／TKS DT 刪除或整理列；已重新核對剩餘 identity，不以刪列數推論整段 tension length 消失。
較早的刪除決策另以 9742a50 比較；2026-09-23 審閱檔以 dbce953 比較，完整 CSV 保留各歷史基準，不能把今日 HEAD 當作 9 月更新前版本。

## 已解決與已接受規則

- 不同 physical Bracket 同位置：共 343 組已依使用者規則接受，不再要求逐組確認；資料全保留。
- Slash 複合 mapping：40 個來源列拆分，增加 44 個輸出列；provenance 保留原串、各 component、位置及分類。
- 合法同名 termination：25 列候選加位置 suffix；未改來源。
- 全 16 sheets 的 normal 同名多位置、physical exact duplicate 與 invalid mapping 皆為 0。
- 所有 source reversed interval 共 0 列；ISL DT row 387 仍為 99.5361 → 99.5369 km。
- AEL DT 350-001～350-042 各保留一次；KTL DT CR186-06／08 分別只在 98.368／98.382 km；TWL DT row 46 為 0.4 km／2-045；ISL DT C:N 輔助欄無非空值。

## 優先人工操作表

| Workbook（完整路徑） | Sheet／Excel row | 欄位與原始值 | 問題／需要決策 |
|---|---|---|---|
| [TOV1050 TL-BK No.xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/00 Reference Document/TOV1050 TL-BK No.xlsx>) | TKL UT / 578 | A:Location / B:Bracket：55.958 km / 545-BWA-M | 未確認命名格式；確認連字號 subtype -M/-C 是否等同 _M/_C；或提供正確類別／值 |
| [TOV1050 TL-BK No.xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/00 Reference Document/TOV1050 TL-BK No.xlsx>) | TKL UT / 579 | A:Location / B:Bracket：55.956 km / 545-BWA-C | 未確認命名格式；確認連字號 subtype -M/-C 是否等同 _M/_C；或提供正確類別／值 |
| [TOV1050 TL-BK No.xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/00 Reference Document/TOV1050 TL-BK No.xlsx>) | TKS UT / 2 | A:Location / B:Bracket：66.604 km / 595-BMA_C | 未確認命名格式；確認 BMA_C 是獨立類型或 BWA_C 的輸入錯誤；提供分類或正確值 |
| [ISL metadata.xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/00 Reference Document/config/ISL metadata.xlsx>) | DT track type / 80;84 | startKM / endKM：98.1181 → 98.1199 / 98.11710000000001 → 98.1189 km | interval overlap 0.8 m（等長，解析優先次序不明）；確認兩列端點是否正確；若保留 overlap，確認 interval 範圍／解析優先政策 |
| [KTL metadata.xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/00 Reference Document/config/KTL metadata.xlsx>) | DT track type / 50;306 | startKM / endKM：98.6371 → 98.6459 / 98.6341 → 98.6429 km | interval overlap 5.8 m（等長，解析優先次序不明）；確認兩列端點是否正確；若保留 overlap，確認 interval 範圍／解析優先政策 |

另有 146 組 interval overlaps（包含上述兩組等長 overlap），完整操作表保留每組 workbook／sheet／row／端點與決策。Bracket 同位合法規則不直接核准 interval 的範圍／解析優先政策。
[完整人工操作表](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/manual-review-checklist.csv>)

## 實際驗證與候選

18 targeted metadata tests passed；standardizer exit 0；validator exit 0，沒有 error finding。各候選 threshold／location／interval／Bracket parity、source／mapping digest、provenance source-row 及 component payload 核對全部吻合。

| Line | Validator status | 新候選（全為 review-only） |
|---|---|---|
| ISL | review_required | [ISL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/candidates/ISL metadata (wide candidate).xlsx>) |
| KTL | review_required | [KTL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/candidates/KTL metadata (wide candidate).xlsx>) |
| LAR_AEL | review_required | [LAR_AEL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/candidates/LAR_AEL metadata (wide candidate).xlsx>) |
| LAR_TCL | review_required | [LAR_TCL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/candidates/LAR_TCL metadata (wide candidate).xlsx>) |
| TKL | review_required | [TKL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/candidates/TKL metadata (wide candidate).xlsx>) |
| TKS | review_required | [TKS metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/candidates/TKS metadata (wide candidate).xlsx>) |
| TWL | pass | [TWL metadata (wide candidate).xlsx](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/candidates/TWL metadata (wide candidate).xlsx>) |

## 產物與 Linear

[規則集](<C:/Smart Maintanence/TOV1050_Analyzer/docs/tov1050-metadata-rules.md>)
[需求與實際執行命令](<C:/Smart Maintanence/TOV1050_Analyzer/docs/requests/2026-10-23-tov1050-metadata-review.md>)
[Validator JSON](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/validation-final/2026-10-23-tov1050-metadata-candidate-validation.json>)
[16 sheets 摘要](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/all-mapping-sheet-summary.csv>)
[Mapping 原始記錄快照](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/mapping-source-records.csv>)
[拆分及 termination 對照](<C:/Smart Maintanence/TOV1050_Analyzer/outputs/metadata-review-2026-10-23/batch-01/mapping-components.csv>)

本工作階段 Linear MCP 實際掛載且成功讀取 DAV-19／DAV-10；實作前需求與設計已同步。結果與 commit／push 狀態由當日 request 及 Linear 最終進度記錄。Next action：使用者確認三列未分類命名與 interval 端點／政策，之後依決策重新產生；未取得明確核准不得 promotion。
