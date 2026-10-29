# Exception Generator：同 Km 中位實測樣本設計／測試提案

- 日期：2026-10-26
- Linear project：TOV1050_Analyzer
- Linear issue：[DAV-24](https://linear.app/david-chu/issue/DAV-24)
- 負責人：Codex；使用者審閱設計
- 狀態：Approved / Implementation complete — 使用者已批准；targeted 驗證完成，待使用者以 Electron 進行工作區驗收

## 需求與目的

### 使用者與流程

CSV 同 Km 約十筆來自來源系統截掉下一位小數。正常匯入後，每 channel 選一個同 Km 中位實測樣本，例外偵測、連線圖表、Excel及ChartData共用這份精簡資料。分析後不常駐原十點cache，原始磁碟檔保留。

另設「原始資料 overview」入口，跳過中位精簡，只畫來源量測概覽；不做例外分析，禁止例外Excel匯出。合併 raw points／raw lines 選項。

### 商業規則與限制

- 使用者後續明確接受中位精簡造成單點例外及例外數量減少；長區段仍須依代表資料正確計算 FromM／ToM，不因分組或品質 gap 錯誤合併。
- 使用者最終明確取消共識容許差、高通、Hampel及所有單點／區段／分片噪訊處理。沒有noise參數需要決策。
- 此需求取代先前raw detector／mean圖表及未實作極值方案，也是AGENTS raw-only偵測規範的明確需求例外。新增algorithm/version/digest，不冒充舊raw報表。
- 中位精簡會改變threshold crossing、peak及例外範圍；不能把消失峰值一律稱為噪訊。
- 公尺為canonical unit，CSV Km×1000。不得虛構來源被截掉的小數位，不取近似里程分桶。
- 不覆寫CSV、DATAC、metadata或既有Excel，不提交／封裝／發布。

## 現況盤點

- `tov1050_data_ingestion.py`保留source_row_number及counter；既有格式清理沿用。
- `chainage_aggregation.py`是mean，且可合併非相鄰同坐標，不能冒充新中位契約。
- `analyzers.py`沿用metadata threshold，連續分組只看布林mask；新流程須明確處理segment邊界。
- `analysis.py`快照／report job及legacy globals依賴raw_df，釋放記憶體須處理全部引用。
- raw reset局部線段、hover缺欄及正常取消誤記error的根因沿用前版提案，尚未修正。

## 設計

### 算法與資料流

1. 按採集順序，以精確同Chainage、同context／metadata、同pass的相鄰run分組。來源列中斷亦斷開，counter下降開新pass；不固定每十列，不合併非相鄰重訪。
2. 每channel只取finite值。奇數取中間值；偶數從排序中間兩個實測值中，選原採集次序較早出現的樣本；重複值同樣取最早來源。不使用兩值平均的標準median()，不內插。
3. 1／4／9／11／20／30筆依實際有效數選取；單點原值直通，因此DATAC不因沒有重複Km遭刪除。all-null／Inf channel留空，不補零。沒有五點支持要求。
4. 每channel保留value、來源列／counter、有效數；群保留來源界限及context/pass/segment。不同channel可能源自不同列，標示為「各通道中位代表值」，不聲稱同時採集的raw row。
5. 跨品質gap／context／pass，圖表及例外連續性明確斷開；不drop後橋接。不缺失的其他channel仍可依既有row min/max觸發例外。保留所有中位樣本，不另作噪訊剔除。
6. 建立獨立reduction模組，不就地修改來源。逐chunk只攜帶未完run，跨chunk結果須與整體計算相同；metadata/context在分組前須可辨識。
7. detector以代表資料重算channel min/max，沿用同一workbook的Class／Track Type／threshold／level規則及High Height；新增segment邊界不變更數值門檻。

### 快取、匯出與進度

- session只保留immutable代表資料、例外、provenance、source/metadata digest及參數。釋放raw frame、舊session、legacy globals、job及前端引用；不把代表frame命名raw_df。
- 圖表、markers、Excel各例外頁及ChartData使用同一revision代表資料，不能混用舊mean／raw。不輸出不再需要的十點mean/min/max統計表。
- 報表標記`same_chainage_median_sample_v1`、偶數平手規則、source/metadata SHA-256、有效列數／代表列數／context；例外peak附channel及真實來源列，供重讀audit。
- 沿用背景job的真實階段／完成數／總數、取消、重試及revision guard；未知總數不偽造百分比。加長timeout不是主要解法。

### 圖表與原始overview

- 主圖為中位代表資料連線；例外marker定位真正代表peak。約84k點是否全部傳送，由full Electron heap/render實測決定；圖表取樣不影響偵測／報表。
- raw overview按需重讀來源並核對digest，跳過精簡及例外分析。既有格式清理仍明示，不稱為逐byte原始檔。
- raw overview可用明確標示的min/max圖表取樣保留尖峰，不稱為完整每點，也不承諾84萬×12channels全載流暢；保持採集順序連線。
- raw模式前端停用例外Excel，後端依snapshot.mode拒絕直接API呼叫。退出釋放資源，來源變動要求重匯入。
- 每revision/mode保留overview，雙擊reset立即恢復並取消detail；generation guard防止舊回應覆蓋。
- hover無資料用文字／省略欄位，不用null供template讀取。正常Axios ERR_CANCELED不記error；真正timeout／HTTP／網路失敗保留並可重試。

### Excel 數字顯示修正（新增需求）

- 使用者提供 `02 Output Document/20261026_TWL_UT_MAINLINE_CEN_TSW_Exception_Report.xlsx`，Summary 的 ToM／Threshold Value 整數顯示為 `9142.`／`200.`；預期為 `9142`／`200`，小數例如 `9390.4` 維持原精度。
- 現行匯出共用 `REPORT_NUMERIC_FORMAT = "0.####"`；修正數字格式選擇，整數用 `0`，非整數沿用既有小數顯示精度。只更動顯示格式，不把數字轉成字串、不改 underlying value，也不以截尾或四捨五入寫回儲存格。
- Summary、各例外頁及相關 ChartData 的數值格式一致處理；來源測試 workbook 不覆寫。
- 新增驗收：整數／零／負整數沒有尾點，小數仍顯示；保存重開後 cell type 為 numeric、value 不變，並檢查實際 Excel 顯示。既有只斷言 `0.####` 的測試須改為檢查此使用者行為。
- 已唯讀核對使用者檔：Summary!J3=9142、U2/U3=200，型別均為 `n`，number_format均為 `0.####`；J2=9390.4亦同格式。來源檔SHA-256前後一致。尚未實作格式修正或執行實際 Excel 顯示驗收。

### 替代方案

| 方法 | 評估 |
|---|---|
| 中位實測樣本 | 使用者最終指定；每值可追溯，約九成減量 |
| mean／兩中值平均 | 可能產生原始檔不存在的值，不採用 |
| 共識／Hampel／高通 | 需工程參數及真假標註，使用者已取消 |

## 測試與驗收提案

1. **算法**：奇偶數、平手、1/4/9/10/11/20/30筆、NaN/Inf／全空；每channel value及source identity完全對應來源，不誤標同一raw row。
2. **分組**：精確小數公尺、正反方向、非相鄰重訪、counter reset／alias／無counter、metadata/context/source gap；同Km跨chunk與整體計算相同。
3. **例外**：以代表資料建立獨立threshold oracle，核對Class／Track Type、L1/L2/L3、Stagger正負、Low/High Height、Wear；gap不橋接、peak來源準確。raw結果差異是語意變更，不能只比較筆數。
4. **資料流**：CSV／DATAC、來源變動、取消／過期／revision亂序；raw overview前後端拒絕匯出；新舊快照不混用。
5. **Excel**：partial/full真正完成背景job，逐列比對ChartData、例外、provenance、algorithm/digest與同revision代表資料；開檔無repair，來源檔hash不變。
6. **圖表**：真API+Plotly hover無warning；median/raw zoom→真正doubleclick在pending／timeout／race均立即恢復全段；正常取消無error，真正錯誤可重試。
7. **效能**：量測import/reduction/metadata/detector/Excel/傳輸/render及peak RSS/heap；完成後無原十點cache。目標full分析≤舊94.11秒、Excel較舊compact367.51秒改善；未達須說明瓶頸，未實測前不保證。

## 執行紀錄

### 已執行只讀研究

重用現有loader／metadata／detector，auto_save=False，沒有正式Excel或DB寫入。raw與median均使用TWL Mainline UT、20260907、CEN–TSW及相同metadata。所有populated channel/run以獨立逐群排序核對代表值與來源。

| 資料 | 有效raw列 | 代表群 | 減量 | 精簡＋全群來源核對 | 代表detector |
|---|---:|---:|---:|---:|---:|
| partial | 50,904 | 5,086 | 90.0086% | 0.445秒 | 0.218秒 |
| full | 838,859 | 83,963 | 89.9908% | 4.644秒 | 1.402秒 |

時間是core隔離研究，不含完整UI、匯出及cache生命週期。full有83,756個十筆群，另有短群及20／30筆群；不應固定十列切片。與舊mean的82,144群差異來自相鄰run／source gap，而非算法漏資料。

| full例外 | raw | 只做中位精簡 |
|---|---:|---:|
| Low Height | 57 | 55 |
| High Height | 2 | 2 |
| Wire Wear | 1 | 1 |
| Stagger Left | 0 | 0 |
| Stagger Right | 95 | 87 |

partial Stagger Right仍2段，但peak／範圍改變。full Low Height及Stagger Right各有1個raw段沒有重疊候選段；其餘數量差含合併／分裂，不能將57→55稱為去除兩個噪訊。研究沿用現有detector，context/pass舊連續性限制仍存在；正式segment修正須另驗收。

### 測試與debug

```text
Runtime: C:/Users/chusiukd/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe
python outputs/consensus-filter-study-2026-10-26/median_study.py
Result: completed_read_only_median_and_noise_sensitivity_study
partial/full全群代表值及來源oracle通過。
兩份CSV與TWL metadata SHA-256前後一致。
```

研究曾誤用0.11m為noise鄰域gap，而實檔常見步長為0.2m，造成所有點斷開；已修正為觀測步長、加入可評估鄰域斷言並重跑完成。只影響已放棄的noise研究，不影響median分組。

先前共識`study.py`在需求改變時停止，未完成full比較；noise候選後來跑完但被使用者取消。全部只作歷史探索，不能用來宣稱正式filter通過；現行方案只引用median結果。

### 驗收結果

本輪 production 修改已完成，未覆寫來源檔，並完成 targeted backend／frontend 驗證。無人工標註，不宣稱被median抑制者全屬噪訊。

#### 實作摘要

- `chainage_reduction.py` 以相鄰同 Chainage／context／pass run 每 channel 選取真實中位樣本；偶數取中央兩筆中來源較早者，保留 source row／counter／valid count provenance。
- median snapshot 只保存代表資料；例外 detector、threshold、chart payload、Excel ChartData 共用同一 revision。`raw_overview` 重新讀取並核對 SHA-256，只供概覽且後端／前端拒絕例外報表匯出。
- 圖表以代表點連線，保留 segment／pass／exception group，detail request 有取消與 generation guard；reset 立即恢復 overview；hover 不再引用缺失 customdata；正常 Axios cancel 不再誤報。
- Excel Summary／例外頁／ChartData 的整數數值使用 `0` 格式，小數維持 `0.####`；新增來源 provenance 與 metadata sheet。
- loading state 顯示目前階段百分比；full CSV 代表資料約 83,963 群，從 838,859 有效列減少約 90%。

#### Electron／Excel 追加核對（2026-10-26）

- 已在 `npm run dev` Electron 工作階段完成 full CSV 分析：介面顯示「同 Km 中位實測樣本」、overview 約 1,087 / 838,859 點、例外清單 160 items，並曾顯示 `550,000 / 843,623 rows（本階段 65.2%）` 的階段進度。
- 已確認輸出 workbook 可由 openpyxl 讀取，包含 `Summary`、各例外頁、`ChartData` 及隱藏 `_Metadata`；使用者提供的 `20261026...xlsx` 是舊／partial 產物（`chart_data_mode=raw`、`raw_row_count=50904`），其整數儲存格仍為 `0.####`，因此不可作為新格式修正的驗收證據，也沒有覆寫該檔。
- 目前程式的 `report_number_format` 與 targeted test 已驗證：整數保持 numeric value 並套用 `0`，非整數套用 `0.####`；另以小型 TWL export oracle 讀回確認 `ToM=9142`、`Threshold Value=200` 的格式為 `0`，`FromM=9141.4` 保持 `0.####`。
- 使用者提供的 `20261020_TWL_UT_MAINLINE_CEN_TSW_Exception_Report_MedianSample.xlsx` 亦已唯讀核對：`Summary!J3=9142`、`U2/U3=200` 為 numeric 且套用 `0`，小數 `J2=9390.2` 維持 `0.####`；其 `ChartData`、`ExceptionProvenance`、`_Metadata` 工作表均存在。
- Electron 同名檔的最後內容與 full／median session 不一致，故 full Electron workbook 的 row count／format 仍標示為待使用者重新匯出確認；這是驗收證據限制，不是回寫或資料處理錯誤。

#### 實際驗證

```text
backend targeted regression: 22 passed
backend core/export/background suites: 98 passed
frontend API/component suites: 15 passed
frontend ExceptionGeneratorView: 10 passed
frontend TypeScript/build: passed (Vite existing chunk-size/assert warnings only)
```

已完成 partial/full 的 reduction 與逐群來源 oracle；partial 50,904→5,086、full 838,859→83,963，來源 CSV／metadata SHA-256 維持不變。Electron 真實操作、DATAC 實檔及完整 full report download 仍是使用者驗收 action；測試 fixture 已涵蓋 DATAC request context 與 raw overview guard。

## Linear同步

- 2026-10-26已實際更新DAV-24需求、研究結果及next action；狀態In Progress。
- 已同步 DAV-24：median-only、raw overview guard、chart reset／hover／cancel、Excel 整數格式與 targeted 測試結果；issue 維持 In Progress。
- Next action：使用者在 `npm run dev` Electron 工作區重新匯出一次 full／partial workbook，確認同名檔的 `_Metadata` row count 與 `chart_data_mode=median`，並驗收圖表切換、raw overview 禁止匯出、Excel Summary 格式與長時間 job；若驗收通過即可將 DAV-24 設為 Done。
- 目前無需新增 noise 容許差；使用者已明確取消高通／Hampel／共識濾波。

### 收尾驗證（2026-10-26）

- 修正 legacy `GET /export/raw`：保留 raw overview guard；非空 `LAST_RAW_DF` 優先，否則回退分析快照，避免舊快照影響 raw CSV。
- Backend targeted regression：77 passed（chart sampling、chainage reduction、analysis chart data、background jobs）。
- Frontend Exception Generator targeted：25 passed（ChartComponent、TaskLoadingState、analysis jobs、client cancellation、ExceptionGeneratorView）。
- `npm --prefix frontend run build`：passed；Vite 僅有既有 assert externalized 與 chunk-size warnings。
- 全量 frontend suite 曾發現多個與 Exception Generator 無關的既有測試失敗，未將全量 suite 宣稱通過；本次需求相關 targeted suite 全數通過。

## 相關檔案與未提交修改

- 本文件；前兩版extrema／consensus提案已標Superseded。
- `outputs/consensus-filter-study-2026-10-26/median_study.py`、`median-study.json`、`partial/full-median-audit.csv`、`partial/full-median-vs-raw.csv`及median例外CSV。
- 工作區大量既有未提交修改不還原。本輪未提交、未封裝、未發布；保留測試產物與歷史研究輸出供審核。
