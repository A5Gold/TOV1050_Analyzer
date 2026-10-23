# TOV1050 Metadata 規則集

規則版本：2026-10-23。業務依據：使用者於 2026-10-22／23 的人工確認；追蹤 DAV-19／DAV-10。本文件記錄已確認規則，取代舊 audit 中尚待確認的對應分類結論；歷史 audit 保留作時間點證據。規則確認不等於整份 metadata 核准。

## 單位與來源

- 原始 `Location`、`startKM`、`endKM` 單位為公里；候選 canonical Chainage 為公尺，僅轉換一次：`km * 1000`。`98150.2 m` 不得再視為公里。
- `TOV1050 TL-BK No.xlsx` 是多線共用 mapping，含 16 張工作表；不是 `KTL metadata.xlsx`。
- identity 以同一 line／track 為範圍；UT／DT 的 Chainage 仍代表實體位置。

## 分類（依序判定）

| 類型 | 已確認規則 | 範例 | 候選處理 |
|---|---|---|---|
| 複合 mapping | `/` 分隔多個 TL-Bracket，忽略分隔符兩旁空白 | `148-026/152-002`、`148-032 / 152-008 / 154-001`、`148-BWA_UP / 152-011 / 154-004` | 拆成同位置多列；逐個 component 分類，保留原值與順序；空 component 列為 invalid，不靜默丟棄 |
| Isolator landmark | 三個英文字母加三個數字 | `HAH885`、`TIS901`、`TKO803`、`YVB983`、`QUB807` | 保留，不參與 physical identity 衝突 |
| Section Insulator landmark | `SI-` 加三英文字母三數字、三數字或 CR 三數字 | `SI-NOP801`、`SI-CR186`、`SI-211` | 同上 |
| 既有 landmark | `SI`、`Mid Point`、`POA`、已知站名／設備碼；既有純文字標記 | `SI`、`Mid Point`、`POA804-01`、`AFW` | 同上；不以「不符合 Bracket regex」作為 landmark 的證據 |
| Normal physical Bracket | 兩組由 `-` 分隔的英數字；各組必須含數字，可有前／後字母；允許尾接 `(T)` | `123-001`、`211-1`、`123A-001A`、`481-A01`、`481A-A02`、`CR272-001`、`CR001A-002`、`211-3B`、`549-007(T)` | 按完整 label 檢查 identity；不得任意去零、移除字母或 `(T)` |
| Termination physical Bracket | 第一組英數字且含數字；第二組為 `BWA`、`Fixed`、`Spring`，可接 `_` subtype | `487-BWA`、`148-BWA_UP`、`581-BWA_M`、`547-Fixed_C`、`549-Spring` | TL 起終點可合法同名跨位置；候選按下述位置後綴區分 |
| 未分類 | 其餘格式 | `595-BMA_C`、`545-BWA-M` | 保留原值並列出 workbook／sheet／row，等待具體格式決策；不自動視為 landmark 或 termination |

英文字母比對不分大小寫，但候選保留來源大小寫；identity 暫保留來源完整字串，不自動合併大小寫或不同 padding。這些等價規則尚未經使用者確認。`BWA-M` 這類連字號 subtype 尚未等同已確認的 `BWA_M`。

## Identity 與 overlap

- 不同 physical Bracket 同一 Chainage 為合法 overlap，所有列保留，無須逐組重新確認。例如 AEL UT `24.54 km` rows 14／19：`303-013`、`307-001`。包括字母變體、termination 及拆分後 component。
- 同一 normal physical Bracket 在同 line／track 的多個位置應列 error；slash 內的 component 同樣參與檢查，不能被整串 label 隱藏。
- 同一 physical identity 同位置重複，包含 slash 內重複 component，仍列 exact duplicate review，不能因 overlap 規則自動刪除。
- Termination 同名跨位置是已確認例外。僅當同一來源 termination label 出現不同位置時，各候選 label 加 `@<公尺位置>m`，例如 `579-BWA@65000m`。位置取 canonical 公尺小數至六位、去尾零，避免因來源列順序變化而改號。相同位置重複不以 suffix 隱藏；原值、位置、來源 row、component index 與結果都記入 provenance。保留 suffix 字元 `@`，若與原始 label 碰撞則停止產生候選。
- Landmark 不參與 physical identity 衝突；未分類 label 的同名多位置、同位關係仍另外列 review。

## Interval、provenance 與核准

- 反向 interval 以 `min(start,end)`／`max(start,end)` 轉換為 canonical interval，保留原始端點及方向處理記錄。排序本身不能證明端點正確；使用者已手動整理 ISL／KTL，仍需每批重算。
- 同位置 Bracket overlap 的規則不直接核准 track／location interval overlap；interval 的端點、範圍、優先次序仍需獨立審閱。
- 每個來源列保留一筆 provenance；mapping provenance 另含完整原值及 JSON component 陣列，記錄每個輸出 identity、分類與公尺位置，允許一來源對多輸出。Validator 必須核對陣列、count 及輸出 parity。
- 每批記錄 source／mapping SHA-256、規則版本與 candidate digest。新 candidate／audit 使用新日期／批次目錄；保留原始 workbook、歷史產物和人工修改。
- 候選始終 review-only；validator 成功不等於 metadata 已核准，不得自行 promotion 至 runtime。
- Chart downsampling 僅作用於 chart payload；detector、threshold crossing、overshoot、peak 與 export 使用完整 raw data。

## 已確認的歷史資料整理

使用者確認移除的是重複 tension length（保留一份）與錯位 mapping；ISL DT C:N 輔助欄位可棄用。TWL DT row 46 的 `2-045` 已補 Location。這些為歷史決策，每批仍須重查現值與 identity，不能只依刪除列數推論整段消失。

## 維護方式

新格式或規則由使用者確認後更新本文件、需求紀錄、Linear、產生器／validator 與回歸測試；audit 必須標記所採用版本。尚未確認格式不得以擴大 regex 靜默接受。
