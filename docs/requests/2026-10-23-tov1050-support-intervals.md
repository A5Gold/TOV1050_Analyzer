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


## Batch-03：使用者回覆後的候選更正（實作前）

- 開始 HEAD／origin/master：e8361bb850036b46d7fb1d28ecdc1ab451f25f3e；仍只有原有四份 dirty Excel。
- 重新計算 mapping／ISL／KTL SHA-256，均與 batch-02 相同，沒有新的來源內容變更。
- 使用者確認：首末 Support 外保留原有 non-support 範圍並另列審閱，只重建兩個 Support 之間。
- 使用者確認 ISL metadata.xlsx / DT track type / Excel row298 的 startKM=endKM=99126，正確為99.126 km；授權候選更正並記錄原值，原始檔不寫回。
- 設計：新增外部 reviewed-corrections JSON，包含 line／sheet／row／預期標籤及原端點／有效端點／授權原文。值不符則停止；來源已符合更正時記為 already_applied。僅按指定範圍套用，禁止一般化推斷單位。產生器、validator、audit 皆需明確輸入同一清單；candidate 另存清單摘要及逐列更正 provenance，anchor 同時保留原值與有效值。
- 驗收：row298 輸出99126m，不再輸出99126000m；兩側衍生段採99.126km；stale／誤套、更正 provenance 或衍生 anchor 竄改必須被拒絕。重新驗證七線於新 batch-03，舊批及原始Excel保留。
- Linear MCP 本回合實際掛載且 DAV-19／DAV-10 讀取成功；next action：同步本節後實作、測試及產生新批次。


### Batch-03 追加確認（實作前）

使用者確認 ISL／KTL 共5筆外側 non-support 及銜接的 Support 可接受，因範圍可以連續連接。設計：新增明確的外側接受清單，逐筆約束 line／sheet／row／原標籤／端點／授權；核對與首末有效Support相差0.0001km，原值或銜接不符則停止。候選保存接受紀錄與digest，validator另按外部清單核對。將這5筆改為已接受證據，不再列待人工決策，AEL／TCL location overlap仍未核准。
Next action：同步DAV-19／DAV-10後加入接受紀錄驗證及測試，再重跑尚未交付的batch-03。


### Batch-03 LAR 來源更新

使用者通知已更新 LAR_AEL／LAR_TCL 的 location type，清除8.9m overlap。重新讀取來源、重算SHA與原始／候選overlap；不得沿用先前兩筆待辦。新增兩份使用者dirty Excel也不stage。Next action：依實際新來源重生兩線及完整七線驗證，只有實測為0才將兩筆記為已解決。


### 最終輸出改用 batch-04

重生batch-03時KTL候選發生PermissionError（無法寫入，可能正在Excel開啟）。不關閉Excel、不覆寫或刪除該候選；保留batch-03中途產物，不作最終交付或stage。所有最新來源、個別更正及5筆接受紀錄改在全新的outputs/metadata-review-2026-10-23/batch-04生成與驗證，以batch-02作前次完整審閱基準。


## Batch-04 最終實作、測試及驗收（取代前述未回答／待辦狀態）

### 實作摘要

- 新增 tov1050_review_corrections.py：讀取外部人工授權更正與外側接受清單，驗證line/sheet/row/標籤/原值，記錄原值與有效值；已符合有效值則already_applied，不符合則停止。
- 原始DataFrame儲存格不改；Support policy只在計算與候選輸出使用有效值。來源provenance及雙側anchor都包含更正授權；5筆外側接受另記範圍與相鄰Support，驗證0.0001km銜接，來源或Support銜接改變即停止。
- standardizer／validator／audit皆明確輸入兩份清單；候選新增__review_corrections__、__review_acceptances__與清單digest。驗證不信任候選自述，獨立從外部清單核對原值、輸出、provenance與digest。
- 正式規則集已更新外側保留、5筆個別接受及row298授權更正。audit新增location端點差異、接受範圍與Support銜接證據。

### 實際命令與結果

```text
python -m pytest backend/tests/test_tov1050_metadata_candidates.py -q
27 passed in 13.66s, exit0

python scripts/standardize_tov1050_metadata.py --root "00 Reference Document/config" --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir outputs/metadata-review-2026-10-23/batch-04/candidates --review-corrections outputs/metadata-review-2026-10-23/batch-04/reviewed-corrections.json --accepted-outer-ranges outputs/metadata-review-2026-10-23/batch-04/accepted-outer-ranges.json --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
exit0，七線候選及manifest

python scripts/validate_tov1050_metadata_candidates.py --source-root "00 Reference Document/config" --candidate-dir outputs/metadata-review-2026-10-23/batch-04/candidates --mapping "00 Reference Document/TOV1050 TL-BK No.xlsx" --output-dir outputs/metadata-review-2026-10-23/batch-04/validation-final --review-corrections outputs/metadata-review-2026-10-23/batch-04/reviewed-corrections.json --accepted-outer-ranges outputs/metadata-review-2026-10-23/batch-04/accepted-outer-ranges.json --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
exit0，七線全部pass，findings總數0

python scripts/audit_tov1050_metadata_review.py --batch-dir outputs/metadata-review-2026-10-23/batch-04 --previous-batch-dir outputs/metadata-review-2026-10-23/batch-02 --review-corrections outputs/metadata-review-2026-10-23/batch-04/reviewed-corrections.json --accepted-outer-ranges outputs/metadata-review-2026-10-23/batch-04/accepted-outer-ranges.json
```

曾有測試新增位置誤放於既有測試中段，修正後既有竄改檢查與新更正測試皆通過。batch-03重生遭KTL候選鎖定，因此不再覆寫該批，最終交付改batch-04。

### 驗收結果

- 七線validator技術pass；error/review findings=0。source/mapping digest、threshold/location/track/Bracket parity、衍生cardinality/anchor payload、更正及接受紀錄全部吻合；所有provenance mismatch=0。
- ISL DT row298：來源仍99126/99126，候選99126m/99126m（有效99.126km）。雙側Support來源row296=99.116、row300=99.137；衍生99.1161–99.1259及99.1261–99.1369km。保留原始異常與授權，未寫回原始檔。
- 內側superseded1080列；新推導1079段：ISL UT323、DT246、KTL UT214、DT296（比batch-02增加1段）。candidate各track同類別overlap=0，無異常Support。
- 5筆外側範圍均符合0.0001km銜接且由使用者接受，已改為證據而非待決策。
- LAR_AEL與LAR_TCL各自location type row2 endKM：28.3099→28.3009；row3 startKM=28.301，原8.9m overlap已消除。兩份source digest實際更新，其餘五線及mapping與batch-02相同。
- 待人工逐列處理項目已清空；尚待整份candidate明確核准，沒有runtime promotion。
- 六份使用者dirty Excel保留且不stage：共用mapping、ISL、KTL、LAR_AEL、LAR_TCL source與2026-09-23舊ISL candidate。batch-03中途產物保留且不stage；只提交程式、tests、request/rules及batch-04新產物。

### Linear 與下一步

DAV-19／DAV-10本工作階段實際掛載並已同步需求、兩項補充確認與來源更新；最終結果及commit/push於完成後同步。Issue維持In Progress：等使用者審閱batch-04並明確核准metadata。沒有未解資料列或環境阻塞需要使用者先處理；batch-03檔案鎖定已用新批次解決。


Batch-04 audit實際exit0：全16 sheets診斷完成，manual-review-checklist為0列；location overlap=0、未分類=0、normal多位置/physical exact duplicate/invalid mapping=0，343組合法同位保留。來源digest穩定斷言通過；7份候選內candidate_status仍為review_required（review-only），不把validator pass當成業務核准。
