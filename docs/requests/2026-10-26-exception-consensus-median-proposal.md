# Exception Generator：同里程共識中位樣本研究與設計／測試提案

- 日期：2026-10-26
- Linear project：TOV1050_Analyzer
- Linear issue：[DAV-24](https://linear.app/david-chu/issue/DAV-24)
- 負責人：Codex；工程容許差及例外語意由使用者審閱
- 狀態：Superseded — 使用者取消共識及所有噪訊處理。現行設計與研究結果見 `2026-10-26-exception-median-sample-proposal.md`；本文件不作實作依據。

## 需求與目的

### 使用者與流程

CSV 同 Km 的約十筆量測源於截掉一位小數。使用者希望正常匯入後，按每個 channel 的同里程值域共識選一個中位實測樣本，直接作例外偵測、報表及連線圖表；其餘原樣本不再常駐 cache。完整未篩選量測另設入口，顯示連線與例外標記，禁止例外 Excel 匯出。原始磁碟檔不修改。

### 商業規則與限制

- 此最新要求明確取代先前「偵測保留 raw、圖表／精簡匯出用 mean」及未實作極值方案；亦為 AGENTS raw-only 規則的明確需求例外。必須使用新算法版本、參數及 digest，不能冒充舊 raw 報表。
- 使用者沒有既定 Height／Stagger／Wear 相近容許差，已明確選擇「先比較候選容許差」。研究數字不是工程標準。
- 未有人工標註噪訊／真實異常；例外變少不代表正確。

## 現況盤點

- 相關程式碼：`tov1050_data_ingestion.py`、`chainage_aggregation.py`、`analyzers.py`、`analysis.py`、`ChartComponent.tsx`、`client.ts`。
- 現有 mean aggregation 合併同 context/pass 非相鄰同 Km，不能直接拿作本次相鄰鄰域。
- detector 只依 threshold mask 分組；刪除不確定點可能橋接例外。需保留品質邊界。
- 既有圖表 reset／hover／正常取消根因及測試缺口沿用前版文件；目前尚未修正。

## 設計

### 範圍

本輪先完成只讀資料研究、設計及驗收提案。隔離研究腳本及產物放 `outputs/consensus-filter-study-2026-10-26/`，不改 production，不生成正式 Excel、不覆寫來源。

研究比較三種解讀：每點半徑支持（可能雙群）、有界跨度最高支持群（推薦候選）、採集次序連續五點支持（真正時間連續）。主比較使用有界跨度，另量度固定五點與嚴格過半差異。

### 資料流與錯誤處理

- 以同 Km、同 metadata/context、同 pass 的相鄰 run 分組；不能固定每十列，也不能合併重訪。source row／counter 中斷需作邊界或明確品質紀錄。
- 相近定義為群內最大值減最小值 ≤ Δ（mm，總跨度，不是 ±Δ）。不得用相鄰值鏈接無限延伸。
- 主候選至少五個有效值且嚴格過半；最高支持分離群平手標 ambiguous，不任選；短群、缺值、DATAC singleton 另有品質政策。
- 中位代表必須是群內真實樣本；偶數中位兩者等距時以採集順序穩定選一。每 channel 附來源列，不能把不同來源 channel 拼成同時採集 raw row。
- 不確定 channel 為空並有原因，圖表斷線、detector 不跨品質 gap。不能將空值補零或當正常。
- 預設 cache 只保存代表點、品質及稽核來源（不保存十筆列表）；讀取時逐 chunk 保留未完 run，分析完成釋放所有 raw 引用及 legacy globals。
- raw 檢視按需重讀並驗證來源 digest；例外標記明確來自未篩選分析。前後端均拒絕該模式例外 Excel 匯出；退出後釋放 raw。若來源變動，要求重匯入。
- revision/mode overview 常駐，reset 立即恢復；取消 detail 並有 generation guard。hover 缺值用文字／省略欄位，正常 Axios 取消不記 error，timeout 保留。

### 驗收標準

1. 研究 partial/full 每 channel 保留率、無共識／歧義率、群大小與容許差敏感度，附來源 SHA-256 前後一致。
2. 正式例外比較使用同一 metadata／threshold／context，列出消失、新增、等級、範圍及 peak 變化；未標註資料不作真假判斷。
3. 合成案例覆蓋 8+2、6+4、5+5、4+3+3、交錯群、鏈式漂移、真短異常、偶數中位、NaN/Inf、1/4/5/9/10/11 點、metadata/pass/chunk/source gap。
4. DATAC 不因 singleton 遭全刪；同量測單位但不同格式不可混用錯誤鄰域。
5. 同 Km 代表值可由來源列重建；參數、algorithm version、source/metadata digest 在報表可核查。
6. 測試真正 API+Plotly hover／雙擊、pending/timeout/亂序/reset/revision，正常取消無 error，真正錯誤可重試。
7. partial/full 量測分析／匯出／傳輸／繪圖時間、payload bytes及 peak memory；先前效能數字不當成本輪通過。

## 執行紀錄

### 實作

無 production 修改。本輪候選研究待下方補入實際結果。

### 測試與 debug

研究前已確認 bundled Python 之 pandas 3.0.1、numpy、openpyxl 及 detector／metadata 模組可匯入。

### 驗收結果

正式變更尚未驗收；研究完成後提供具體參數候選及影響，待設計審閱。

## Linear 同步

- 最後同步：2026-10-26；已實際更新 DAV-24 標題、需求方向及 next action。
- Issue 狀態：In Progress。
- Next action：完成已授權研究，更新測試／設計提案，取得具體算法與參數決策後才正式實作。
- 需要決策：容許差及不確定群政策；無人工標註，不能保證刪除者全屬噪訊。

## 相關檔案

- 本文件；`2026-10-26-exception-graph-extrema-and-reset-proposal.md`（已取代）。
- `outputs/consensus-filter-study-2026-10-26/`（隔離研究產物）。
