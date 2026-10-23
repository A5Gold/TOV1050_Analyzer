# TOV1050 與 TOV640 metadata 格式及語意相容方案

- 日期：2026-10-23
- 追蹤：DAV-21（Todo），關聯 DAV-20，parent DAV-10
- 狀態：設計提案；尚未實作新的 TL/Overlap 區間產生器或修改已啟用 config
- 目的：讓兩個產品透過相同 canonical interval/report 契約工作，同時完整保留 TOV1050 Bracket 點資料。

## 實際差異與已核對影響

| 資料 | TOV640 | TOV1050 batch-04 | 轉接方式 |
|---|---|---|---|
| threshold | Class／Track Type／Exc Type／L1–L3 | 已標準化為 wide | 既有 adapter 已處理 |
| location class | Exception Boundarys 與 UP/DN FromM/ToM | 同名表，line 為 ISL/LAR_AEL/TKS 等 | UT→UP、DT→DN；line/session alias；皆為公尺 |
| track type | Track Type FromM／ToM | 同欄位，另含 Support/non-support | 既有 adapter 讀 interval；保留原分類，不自動轉 Tangent/Curve |
| TL／Overlap | Overlap FromM／ToM、Overlap、Tension Length | Bracket FromM／Tension Length／Bracket | 保留點；另建立有依據的 TL 區間，再形成 overlap interval |
| Landmark | Landmark FromM／ToM／Landmark | 無明確區間，部分 mapping label 是 landmark 點 | 分離點與範圍；範圍缺失保留 unknown，不推定站台長度 |

程式核對：`ExceptionDetector._get_vectorized_threshold` 依 Exc Type、Class、Track Type 取得閾值；`_detect_scalar`、`_detect_stagger` 沒有以 Overlap／Landmark 作閾值條件。`_group_consecutive` 將群組中第一個非空 Overlap／TL／Landmark 放入 report，並不保證是 peak 位置或整段所有值。

因此「缺少 overlap 一定改變現行 threshold」不符合實作；但 report 標註會缺失，且不能宣稱 metadata 全功能等效。`MetadataManager.get_tension_length_lookup`、`get_tension_length_source_rows` 等 calculation／wear scope 路徑需要明確區間，現在的 TOV1050 點資料未提供這個契約。另須檢查 TOV640 既有 `_aggregate_tension_lengths` 的多 TL 平均切段行為；不能用這種切段代表兩條 TL 真正共同存在的範圍。

## 實際資料盤點

已按 batch-04 `mapping-components.csv` 的已確認 normal／termination／landmark 分類，與七份 runtime workbook 的 14 張方向表逐表核對點數：

- 14,143 個 mapping 點 rows，其中 physical 14,088、landmark 55；沒有把所有帶 Tension Length 欄位的 row 都當 physical TL。
- 373 個「sheet + physical TL」組合；14 張表皆無明確 Overlap／Landmark 區間欄位。
- ISL UT 的 CR289 有31個 physical bracket 點，觀察位置為 **99,731–99,991 m**；使用者列出的前四筆只到99,750m，不是完整 TL 的證據。
- ISL UT TL254 只有112,865m一點；ISL DT TL255只有112,772m一點。單點不能推定有效覆蓋長度。

盤點：`outputs/metadata-activation-2026-10-23/batch-01/metadata-capability-inventory.csv`。
實際觀察範圍：同目錄 `bracket-observed-envelopes.csv`，全部標 `observed_envelope_only_not_approved_physical_extent`。這份 CSV 是審閱證據，不是可直接啟用的 interval metadata。

## 建議的資料模型與 workbook 外觀

內部分開維護四張邏輯表，避免同一欄在不同資料列承擔不同意思：

| 邏輯表 | 最少欄位 | 語意 |
|---|---|---|
| BracketPoint | line/session/track、chainage_m、tension_length、bracket、classification、source row | 已知實體點；同位多 identity 全保留 |
| TensionLengthInterval | line/session/track、from_m、to_m、TL、boundary policy、status、provenance | 已核對的 TL 覆蓋範圍；允許多 TL 同時存在 |
| OverlapInterval | from_m、to_m、active_tension_lengths、overlap state、provenance | 由已核准 TL 區間的有效集合導出 |
| LandmarkPoint / LandmarkInterval | 點位置或 from_m/to_m、label、kind、status、provenance | SI/isolator點與 Platform等範圍分開 |

native TOV1050 workbook 保留目前 Track Type + Bracket 欄位。若要提供與 TOV640 相同版面的整合 workbook，另產生新批次相容輸出：

1. `<identity> UT/DT` 使用 TOV640 欄組：`Landmark FromM / Landmark ToM / Landmark`、`Overlap FromM / Overlap ToM / Overlap / Tension Length`、`Track Type / Track Type FromM / Track Type ToM`。
2. `<identity> UT/DT Brackets` 獨立保存 `Bracket FromM / Tension Length / Bracket` 及來源欄位；不可因輸出 TOV640 版面而丟失點資料。
3. capabilities/review/provenance 另頁記錄來源版本、已核准範圍、未知能力、產生政策與 digest。

採分頁可避免 `Tension Length` 同時代表 overlap interval 的多 TL 集合與 bracket point 所屬 TL；Excel 的並排欄組也不以同一 row number 當作彼此位置配對。UT/DT sheet alias 留在 adapter，不需將整個產品改成 EAL/TML 或全域改名 UP/DN。

## TL／Overlap 可如何產生

### 第一層：已知點與觀察範圍

依 line/session/track/physical TL 分組，列 min/max Bracket FromM、點數、termination、原始 rows、重覆位置與缺口，形成 observed envelope。landmark／未分類不得混入；重名 termination 的位置 suffix 只區分 bracket identity，不改 TL 歸屬。

這一步已完成唯讀盤點。min/max 是目前記錄的觀察邊界，不能證明 TL 的真實起終點，也不能證明兩點之間的 mapping 完整且連續。禁止 nearest bracket、向下一 TL 延伸、平均切割或由編號跳號猜缺失位置。

### 第二層：核對有效 TL 邊界

優先使用工程確認的起終點／termination pairing。若使用者確認每條 TL 的 mapping 完整、連續，且首末 bracket 可作有效邊界，才可將對應 observed envelope 轉為核准 TL interval。確認可按已滿足條件的批次政策處理，不必無目的逐列重審。

須明確記錄：mapping 完整性、首末點與真實 termination 的關係、TL中斷是否須拆段、只有一點的處理，以及範圍閉合方式／解析度。既有 Support-derived non-support 的0.1m格點政策不自動套用到所有 TL 邊界。

### 第三層：生成 TOV640 Overlap interval

對已核准 TL intervals 使用端點掃描，按每一小段的 active TL 集合輸出：

- 同時有兩個以上不同 TL：`Overlap=Y`，Tension Length 保存所有 TL，例如 `303, 307`。
- 一個 TL：已知非 overlap；輸出符合既有 TOV640 blank flag 的格式，另在 canonical state 記 `known_non_overlap`。
- 未覆蓋或來源能力缺失：`unknown`，不能當已知非 overlap，也不能把 TL 空白解讀成無 TL。
- 同位置多個 bracket 可屬同 TL，並不一定是多 TL overlap；不同 TL 同點可形成接點 overlap，仍不能只靠那一個點推定非零長度區間。

端點接觸需獨立處理：數學上的共同一點與有長度的 overlap 分開保留。內部可採半開區間加 terminal point，但現有 detector 使用 closed-both IntervalIndex；正式轉出前必須定義可表示格點及邊界映射並測試。不能未經政策便任意減0.1m消除接點或製造間隙。

## Landmark 缺失的處理

已有 SI／isolator／POA 等明確 label 和位置時，先保存為 LandmarkPoint。若業務只要精確該點匹配，可在明訂公尺精度與匹配政策後，提供零長度 `[x,x]` 相容表示；這不代表量測落在附近就屬於該設備。

站台等 LandmarkInterval 需要權威 FromM/ToM 或人工提供範圍。沒有資料時保持 unavailable；不從站名、相鄰 bracket 或點之間中點推定區間，也不把 location class 的 Tunnel/Open 當成 landmark。

## 能力與相容性驗收

這部分尚未實作，必須在下一階段接入 API/readiness/report：

- 分別回報 thresholds、track intervals、bracket points、TL intervals、overlap intervals、landmark points／intervals 的 available／partial／unavailable，不用一個籠統 metadata valid 取代。
- 使用 Class／Track Type 的現有 exception detection 可在必要資料驗證後使用；缺 TL／Landmark 的欄位須明確標缺資料，不宣稱已具備完整 TOV640 enrichment。
- 依賴完整 TL 範圍的 wear calculation／scope 操作，在缺少核准區間時回報具體缺口；不能靜默回空、預設唯一 TL 或把未知當非 overlap。
- report enrichment 若要從「第一個非空值」改成 peak 或整段全集合，須另定版本及回歸，不能在格式轉換中偷改現有 TOV640 行為。
- 測試同點多 bracket、同 TL 多點、兩 TL 共段／只接一點、三 TL 共段、單點 TL、空白／未分類／landmark點、slash拆分、termination suffix、UT/DT與TKS隔離，以及 source/digest drift。
- 相同已核准區間與 canonical 量測分別交給 TOV640／TOV1050，比對 detection、ID、report 與 TL scope；保留 EAL/TML 原始回歸。

## 下一步

DAV-21 先實作點／區間分離與 capabilities，再將 observed envelope 補為可操作的 TL 邊界審閱表（含 termination 及來源 row）。確認有效邊界政策後才產生新的 review candidate 及 sweep-derived overlap，通過 validator/parity 再正式啟用。DAV-20 可先並行建立 detection canonical 基線；涉及 TL/wear 的完整驗收依賴 DAV-21，不將缺失資料當已相容。
