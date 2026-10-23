# TOV1050 補充分類規則與重新產生候選

- 日期：2026-10-23
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-19／DAV-10
- 負責人：Codex
- 狀態：In Review

## 需求與目的

### 使用者與流程

使用者更新共用 mapping 及 ISL／KTL metadata，要求依補充 normal、termination、slash、isolator／SI 命名與一般同位 overlap 規則重新產生七線 review-only candidates，並要求正式規則文件。

### 商業規則與限制

以 `docs/tov1050-metadata-rules.md` 2026-10-23 版為準。保留原始 Excel、舊候選及使用者修改，不 promotion。不同 Bracket 同位合法；normal 同名多位置仍 error；termination 可同名跨位置，候選以位置後綴識別。

## 現況盤點

- master HEAD／origin/master：4c12e8d4e004c004c07b21394028beac88ebf75d。
- 原有四份 dirty Excel：共用 mapping、ISL source、KTL source、2026-09-23 舊 ISL candidate；不 stage。
- Graph MCP 已 index，實際 search_graph／get_code_snippet 已讀 standardizer。Linear MCP 已掛載且成功讀 DAV-19／DAV-10。
- 新 mapping digest b3e415f599c19b546cd1ae46085c92e6482fb2ab39354bfd9dac4314f7ecc3b2；ISL／KTL digest 與昨日 batch-03 相同。
- 程式：standardize_tov1050_metadata.py、validate_tov1050_metadata_candidates.py；既有 targeted tests 14 項。

## 設計

### 範圍

共享純函式分類／mapping transform policy；slash 拆分同位列；重名 termination 以位置 suffix 區分；一筆來源 provenance 保存 JSON component array 並由 validator 核對內容與 cardinality；獨立輸出 parity 防止漏列。將所有不同 physical identity 同位列為 accepted overlap。新規則不涵蓋的格式保留 unclassified。

### 不在範圍

runtime、圖表、原始 Excel 修改、歷史產物覆寫、metadata 核准。

### 資料流與錯誤處理

source／mapping 唯讀 → components／classification／termination suffix → 七線 candidate 與 provenance → validator parity／digest／identity → 16 sheets audit 與人工操作表。無效 slash 空元件不靜默略過；candidate suffix 碰撞 fail closed。輸出 `outputs/metadata-review-2026-10-23/batch-01/`。

### 驗收標準

已確認格式均正確分類；slash component 多位置／重複不能漏檢；termination suffix 可追溯且穩定；缺失／竄改 component provenance 會 fail。七線 tests／validator 通過，無原始 workbook 由流程修改；未解格式及 interval 具完整路徑、sheet、row、值與決策。

## 執行紀錄

### 實作

實作前已完成唯讀 Git、文件、來源 digest 與 mapping 掃描；本文件與規則集先於程式修改建立。

### 測試與 debug

```text
python -m pytest backend/tests/test_tov1050_metadata_candidates.py -q
18 passed (2.28s), exit 0

python scripts/standardize_tov1050_metadata.py --root "00 Reference Document/config" --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir outputs/metadata-review-2026-10-23/batch-01/candidates --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
exit 0; seven candidates + manifest

python scripts/validate_tov1050_metadata_candidates.py --source-root "00 Reference Document/config" --candidate-dir outputs/metadata-review-2026-10-23/batch-01/candidates --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir outputs/metadata-review-2026-10-23/batch-01/validation-final --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
exit 0; no error findings; TWL pass, other six review_required

python scripts/audit_tov1050_metadata_review.py --batch-dir outputs/metadata-review-2026-10-23/batch-01 --previous-batch-dir outputs/metadata-review-2026-10-22/batch-03
exit 0; all 16 mapping sheets inspected; source digest stability asserted
```

初次回歸測試的兩項失敗為舊規則預期（一般同位未確認、slash 不拆／termination 未分類）；已依使用者新規則更新，加入拆分後跨位置衝突、空／重複 component、termination 穩定 suffix／碰撞、candidate 漏列與 provenance 竄改測試。稽核初版比較出 Excel 浮點尾數噪音，改按 canonical m 六位精度比對後，與上批的實際多重集合差異為 85 筆，而非 871 筆。

### 驗收結果

- 新增共享規則模組與正式規則集；standardizer／validator／audit 引用 2026-10-23 規則。來源完全保留，runtime 未改動。
- 七線 threshold／location／track interval／Bracket parity 與 source／mapping digest 全部吻合；provenance missing／unexpected／duplicate／status／target／component mismatch 均 0。
- 共用 16 sheets：normal 多位置、physical exact duplicate、invalid mapping 皆 0；reversed intervals 0。343 組不同 physical identity 同位接受，不再列未確認。
- 40 個 slash 來源列拆分，增加 44 個候選 rows。25 個重名 termination 候選 rows 加穩定位置 suffix；保留原值與完整 component JSON provenance。
- 三列待格式決定：TKL UT rows 578／579 的 545-BWA-M／545-BWA-C（55.958／55.956 km），及 TKS UT row 2 的 595-BMA_C（66.604 km）。未自動修正或接受。
- 146 組 interval overlap：ISL DT 12、KTL DT 132、LAR_AEL location type 1、LAR_TCL location type 1。優先 ISL DT rows 80／84（0.8 m）、KTL DT rows 50／306（5.8 m）；Bracket 同位規則不直接核准 interval 範圍／解析優先。
- Mapping 自昨日更新：7 sheets 共 85 筆多重集合差異（刪與增各列一筆）；DRL 無變更。七份 metadata source digest 皆與昨日 batch-03 相同。
- AEL DT 350-001～042 各保留一次；TWL DT row 46 0.4 km／2-045；KTL DT CR186-06／08 各只在 98.368／98.382 km；ISL DT C:N 非空 0，row 387 99.5361→99.5369 km。
- Validator TWL 為 pass，但七份 candidate 的 __standardization__.candidate_status 皆 review_required；技術 pass 不代表業務核准，全部維持 review-only。
- 產物含七份 xlsx、manifest、validator JSON／Markdown、完整 audit、149 筆人工操作表（3 命名 + 146 interval pairs）、全16 sheets 原始記錄與component快照及歷史差異 CSV。

## Linear 同步

- 最後同步時間：2026-10-23；實作前需求／設計已成功同步 DAV-19／DAV-10，最終結果於提交前同步。
- Issue 狀態：In Progress
- Next action：使用者確認三列未分類命名，以及兩組等長 interval／其餘 interval overlap 政策；按新決策再產生候選。尚未取得 metadata 核准。
- 阻塞／需要決策：上述業務審閱；程式驗證與候選產生已完成。

## 相關檔案

- docs/tov1050-metadata-rules.md
- outputs/metadata-review-2026-10-23/batch-01/
