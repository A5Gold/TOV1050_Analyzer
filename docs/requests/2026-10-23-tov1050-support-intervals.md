# 依 Support 重建 non-support 候選區間

- 日期：2026-10-23
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-19／DAV-10
- 負責人：Codex
- 狀態：In Review

## 需求與目的

### 使用者與流程

使用者更新來源並要求重生候選：non-support 常未按位置遞增，改以 Support 的 startKM／endKM 為基準，推導相鄰 Support 之間的 non-support，公里保留四位小數。既有原始 Excel、舊候選及未提交修改全部保留。

### 商業規則與限制

採位置排序，並非 Excel row 順序。相鄰 Support A／B 之間推導 `[A.endKM + 0.0001, B.startKM - 0.0001]`，計算以十進位 0.0001 km（0.1 m）格點進行。Support 本身、Curve／Tangent、location type 不套用 non-support 重建規則。候選仍 canonical m、review-only；不改 runtime。

## 現況盤點

- master HEAD／origin/master：483b8e7a3883391f62e02ab19e501c852ca39713。
- 既有四份 dirty Excel：共用 mapping、ISL、KTL source、2026-09-23 舊 ISL candidate，不 stage。
- 已實際確認 graph／Linear MCP 掛載並讀取 DAV-19／DAV-10。
- mapping SHA-256 更新為 3e7954907508ee393d8541f0bcb9dbe1a79bea36fe9ccfe540666c0fa53af056；七份 metadata source digest 與 batch-01 相同。
- mapping 未分類格式唯讀掃描目前為 0；先前 3 列已由來源修正，詳細差異待新 audit 列出。
- Support／non-support 只出現在 ISL、KTL 的 UT／DT；其他線保持既有 interval。
- 發現 ISL DT row 298 的 Support startKM=endKM=99126，超出 location type 整體涵蓋範圍（97–113.5 km）；已詢問是否正確為99.126 km，未取得答案前不自行換單位或補小數。

## 設計

### 範圍

新增共享 Support interval policy，產生器與 validator 同時使用。原始 non-support 列改記 superseded，候選重建列另在 __interval_derivation__ 記錄雙側 Support 來源 row／原始值、四位公里數值／canonical m、規則版本與穩定 key。每筆 Support 及保留外側列的 provenance 保存實際輸出 payload，validator 核對其內容；generated interval 必須一對一符合 anchor 推導與 candidate parity，不能以一般 min/max 比對掩蓋反向候選。

### 不在範圍

原始 Excel 寫回、runtime promotion、location type overlap 自動處理、假設所有 Support 值必然正確。

### 資料流與錯誤處理

Support 按實體位置排序；重複／重疊／非有限值／不在四位小數格點或超出 location type 整體範圍（包含 ORCR）者列出 anchor 問題，不靜默推導極大區間。間距不足兩側各0.0001 km則不輸出反向段。來源外側 non-support 暫保留並列 review（已詢問使用者外側邊界政策）；缺少 Support 不改原有 non-support並列review。

新批次：outputs/metadata-review-2026-10-23/batch-02/。source digest、mapping digest、舊批次 diff、原始與有效 interval diagnostics 分開保存；新 audit 不把已取代的 non-support 端點再列為人工修正待辦。

### 驗收標準

範例產生 98.6431→98.6509、98.6511→98.6609、98.6611→98.6709 km。無論來源順序／舊 non-support 端點是否錯誤，內側輸出都由 Support 推導。非零長度 Support 使用前者 end／後者 start。外側、無 Support、重複、重疊、間距不足、浮點／精度、衍生 provenance 竄改與候選漏列／反向需回歸測試。新候選來源與衍生 provenance 完整，原始值保留，未解 anchor 問題明列，不得視為核准。

## 執行紀錄

### 實作

新增 `scripts/tov1050_support_intervals.py` 共享政策；standardizer 產生 Support 推導的候選及 `__interval_derivation__`。舊內側 non-support provenance 改為 superseded，保留原始端點及實際輸出 payload；外側仍 emitted 並另列 review。Validator 核對政策 parity、anchor payload、衍生 cardinality、原始來源處置與候選端點方向。Audit 改讀前批原始 mapping 快照，支援 slash 拆分後批次，並列新的衍生對照與剩餘操作表。規則集已補入政策版本。

### 測試與 debug

```text
python -m pytest backend/tests/test_tov1050_metadata_candidates.py -q
24 passed (3.56s), exit 0

python scripts/standardize_tov1050_metadata.py --root "00 Reference Document/config" --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir outputs/metadata-review-2026-10-23/batch-02/candidates --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
exit 0; seven candidates + manifest

python scripts/validate_tov1050_metadata_candidates.py --source-root "00 Reference Document/config" --candidate-dir outputs/metadata-review-2026-10-23/batch-02/candidates --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir outputs/metadata-review-2026-10-23/batch-02/validation-final --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
exit 0; no error findings; ISL/KTL/LAR_AEL/LAR_TCL review_required; TKL/TKS/TWL pass

python scripts/audit_tov1050_metadata_review.py --batch-dir outputs/metadata-review-2026-10-23/batch-02 --previous-batch-dir outputs/metadata-review-2026-10-23/batch-01
exit 0; 16 sheets, source digest stability asserted
```

實際來源檢查發現：ORCR 的 Support/non-support 為97–100.241 km（ISL）或97–99.942 km（KTL），Curve/Tangent自其後主線開始。因此初版用Curve/Tangent包絡檢查會誤排正常Support；在交付前改以location type整體範圍（含ORCR），加入回歸測試並重新產生本批候選。location type涵蓋ISL97–113.5、KTL97–116 km，row298的99126仍為唯一異常Support。

### 驗收結果

- ISL UT：323列舊內側non-support superseded，衍生323段；ISL DT：247列superseded，衍生245段；KTL UT：214列superseded，衍生214段；KTL DT：296列superseded，衍生296段。合計1080列superseded、1078個新衍生段，雙側anchor與四位公里值全部可追溯。ISL DT兩列淨減包含舊冗餘non-support及異常Support未參與推導的影響，不能只看列數判定資料遺失。
- 候選所有track type同類別interval overlap為0；原始144組ISL/KTL DT overlap只保留作來源證據，不再要求逐筆修正其non-support端點。其餘2組location overlap未被Support政策涵蓋。
- 全部threshold／location／policy-adjusted track interval／Bracket parity、source／mapping digest吻合；provenance missing／unexpected／duplicate／status／target／component／interval payload mismatch皆0；衍生段provenance parity吻合。技術驗證成功不核准原始Support或外側邊界。
- 未解：ISL DT row298 Support=99126 km。原值仍出現在review-only候選（99126000 m）並標記anchor問題；未自動改為99.126，亦未衍生連接99126的巨大區間。該異常未處理前不得promotion。
- 外側non-support共5列暫保留：ISL UT row2（97→97.2619）、ISL DT row2（97→97.7809）、KTL UT row2（97→98.0519）及row432（99.8771→99.942）、KTL DT row2（97→97.4099）。等待邊界政策，沒有依Curve/Tangent下限刪除ORCR。
- LAR_AEL、LAR_TCL location type rows2/3各8.9m overlap仍列業務review，不屬本次non-support推導範圍。
- Mapping自batch-01的3個label修正：TKL UT rows578/579改為545-BWA_M/C；TKS UT row2改為595-BWA_C；多重集合刪／增差異共6筆。未分類0，343組同位已接受，normal多位置／physical exact duplicate／invalid mapping皆0。
- 七份candidate全部review-only，__standardization__.candidate_status皆review_required。原始Excel、舊候選、runtime均未覆寫。只stage本次程式、tests、規則／request及新batch-02。
- 新audit、原始值／衍生anchor對照、8筆人工操作表（1異常Support、5外側non-support、2 location overlap）完整產出。

## Linear 同步

- 最後同步時間：2026-10-23
- Issue 狀態：In Progress
- Next action：使用者確認ISL DT row298的正確Support值及5筆外側non-support邊界政策；另處理AEL/TCL location overlap。按新答案再重生。尚未取得metadata核准。
- 阻塞／需要決策：上述業務確認；本批產生／程式驗證已完成。兩項非同步問題尚未收到答覆，保守保留來源值，不以經過時間視為核准。

## 相關檔案

- docs/tov1050-metadata-rules.md
- scripts/standardize_tov1050_metadata.py
- scripts/validate_tov1050_metadata_candidates.py
- scripts/audit_tov1050_metadata_review.py
- backend/tests/test_tov1050_metadata_candidates.py
