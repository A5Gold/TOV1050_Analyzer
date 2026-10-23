# Metadata 能力與點／區間契約 v1

追蹤：DAV-21。已批准設計：`docs/plans/2026-10-23-tov1050-metadata-compatibility.md`。

`TOV1050MetadataManager.get_capabilities(line, session, direction)` 回傳 `tov1050-metadata-capabilities-v1`，附 workbook SHA-256、context、公尺單位、能力狀態與原因。`POST /api/analyze` 增加 `metadata_capabilities`；session-scoped report 的 hidden `_Metadata` 同時記錄能力及 `tov640-first-nonempty-v1`。GET latest report 亦記錄最近成功分析的能力。前端 wire type 定義於 `frontend/src/types/api.ts`。

## 點與區間

| 邏輯資料 | 本次入口／表示 | 限制 |
|---|---|---|
| BracketPoint | `get_bracket_points`：chainage_m、TL、Bracket、normal/termination、來源 lineage | 同位不同 identity 及所有 rows 保留；沒有半徑或覆蓋範圍 |
| LandmarkPoint | `get_landmark_points`：同點來源結構，classification=landmark | 不參與 TL observed envelope；不轉成站台範圍 |
| 未分類點 | `_point_frame` 完整保留，能力列 partial | 無 classification provenance 的點不升格為 physical TL |
| TensionLengthInterval | typed `TensionLengthInterval`：from_m/to_m/TL/approval/source | 需明確核准與來源；runtime 尚未供應此表 |
| OverlapInterval | `sweep_approved_intervals` 回傳 active TL 集合、state、closed、sources | 純函式、未接 runtime；只接受帶批准證據的 TL 區間 |
| LandmarkInterval | 現行 detector interval API 仍是 unavailable 空表，能力明確說明 | 需要權威範圍；本次不建立猜測範圍 |

點來源欄位包含 runtime workbook/sheet/Excel row，以及 mapping workbook/source sheet/source Excel row/source bracket/component index。LAR_AEL/LAR_TCL 的 mapping sheet 是 AEL/TCL，與 runtime identity 分開。分類使用核准 workbook 中的 component provenance，不擴大 regex 猜分類；無法對上時列 unclassified。

## 能力狀態

分別列 thresholds、class_intervals、track_intervals、bracket_points、tension_length_intervals、overlap_intervals、landmark_points、landmark_intervals。

- `available`：有可使用資料；**不表示全線每一公尺皆覆蓋或完成現場驗收**。
- `partial`：點存在，但部分缺 classification provenance；保留缺口，不猜分類。
- `unavailable`：無可用資料／無核准物理區間；附 count 與 reason。

目前七份 wide 的 TL/Overlap/Landmark interval 都 unavailable，overlap_state=unknown。沒有 landmark 點可讀與沒有任何 landmark 實體是不同陳述。DRL Mainline DT 沒有 `DT track type`，能力 unavailable，分析入口會在 detector 前停止。DRL PL 仍使用原 `PL track type`；此 schema 能讀不代表兩個方向的業務語意已確認。

分析入口對 thresholds/class/track unavailable 回 HTTP 400，避免 detector 的歷史 catch/fallback 掩蓋必要資料缺失。既有 optional enrichment 的空值欄位仍保留，API/report 能力用於揭露其 unknown 語意，不把空白轉成 N。

### 實際量測覆蓋 preflight

`get_measurement_coverage`／`require_measurement_coverage` 在 detector 前逐筆核對全部清洗保留 Chainage 的 Class 與 Track Type 區間，不使用圖表抽樣。即使 sheet 能力為 available，任一筆未覆蓋仍回 HTTP400，列 workbook/context、sheet、缺少筆數與前20個公尺位置；不執行 detector、不覆寫上次成功分析。端點沿用既有 closed-both 政策及 detector 的重疊解法，本次不變更判定核心或 EAL/TML 入口。

真 DRL/PL/UT sample 暴露根 config 舊 long PL sheet 到44000m的缺口（52筆全部在45388.2–45389.2m）。使用者後續指定 reference wide `DRL UT` row11 Curve44887–45500m，隔離回歸已覆蓋全部52筆且匯出通過；這是版本／sheet選擇差異，不是所有來源都缺區間。該reference仍有獨立DRL PL頁、Bracket疑似公里及反向DN邊界，未整份promotion。詳見 regression batch-07（runtime阻擋）與batch-09（isolated reference成功）。

## 核准區間 sweep 的邊界

輸入為 closed-both TL interval。輸出將每個端點獨立為 `[x,x]` atom，相鄰端點間則為 open `(x,y)` atom；不設定尚未核准的 0.1m 或其他格點。每個 atom 保存所有 active TL：多 TL=`overlap`，單 TL=`known_non_overlap`，範圍內無 active TL=`unknown`。輸入範圍外仍未知；同一 TL 多筆不重複計數，但來源證據保留。

兩 TL 只接於一點時，只有該端點 atom 是 overlap，絕不延伸為非零長度共段。單點 TL 只出現在端點；三 TL 共段保留三個 identity。這些 atoms **不得直接轉入 legacy closed-both mapper**；正式 runtime 導入仍需業務核准解析度／閉合政策及 adapter 回歸。本次沒有把 observed min/max 送入 sweep。

## Wear 消費者

TOV1050 `get_tension_length_lookup`／`get_tension_length_source_rows` 現在明確拋 `MetadataCapabilityError`，列 workbook、line/session/direction、所需核准 FromM/ToM 與 scope policy。`/calculation/wear` legacy branch 及 `/calculation/upload` 遇到 TOV1050 context 回 HTTP 422；不再落入 TML workbook 或無 lookup 的推測路徑。TOV640 EAL/TML manager、scope classifier、complete-cycle branch 保留。

完整 TL/wear parity 尚未通過，原因是沒有已核准 TOV1050 interval/scope，而不是測試替它假設唯一 TL。原 detector/report enrichment 繼續使用群組第一個非空值，本次未改成 peak 或全集合。

## 大型報表的資料契約

`export_analysis_report` 僅對 TOV1050 line 且超過 50,000 rows 的 ChartData 使用 `tov1050_report_export.py` write-only writer。Summary／exception 先由既有 exporter 產生，保留欄序、值與 `tov640-first-nonempty-v1` enrichment；ChartData 逐列寫入完整 raw frame，沒有 downsampling。EAL/TML 及較小資料保留 legacy writer。hidden `_Metadata` 記錄同一能力 snapshot。

新 writer 已對三組 canonical 及真 EAL 54,057 rows 的固定 TOV640 分程序證據，逐欄／逐值比較全部 report sheets 通過；另外測試 50,001 rows 完整輸出與 EAL 大檔仍選 legacy 路徑。這是大型 TOV1050 report 的記憶體使用修正，沒有修改 detector、物理邊界或 enrichment；不代表 portable 或效能 SLA 驗收。

TOV1050 report/raw 下載以64KiB分塊，避免 `BytesIO` 預設逐行迭代造成每行一次 thread-pool handoff；binary／CSV 全部位元組保持一致。EAL/TML下載路徑保留。驗證亦包含分塊前後位元組一致與多chunk完整性。

## 審閱產物與重跑方式

`scripts/review_tov1050_capabilities.py --output <新批次>` 唯讀核對 release/config/candidate SHA、來源漂移，產生能力矩陣、TL 邊界審閱 CSV、DRL/PL inventory 及相容 layout JSON。`build_tov1050_review_workbooks.mjs` 使用 bundled artifact-tool 產生七份新 workbook；`validate_tov1050_review_workbooks.py` 逐格核對全部欄位／點列。

相容候選保留 threshold/boundaries，方向頁使用 TOV640 欄組，另以 `<identity> UT/DT Brackets` 保存全部原生點及 lineage。未核准 TL/Overlap/Landmark 欄組留空，Capabilities 首頁明確標記 unknown/unavailable、review-only。它們只有版面／資料保留用途，**不能當已完成 TL 功能的 runtime 替代品，也沒有 promotion**。

TL 審閱 CSV 每組列觀察首末位置、首末 Bracket、所有來源 Excel rows、termination 原值／位置／來源、runtime rows，並留下獨立空白 approved_from_m/approved_to_m/approved_by。需確認 mapping 完整連續、真正 termination 邊界、中斷拆段、單點政策及閉合精度後，才能生成核准區間。
