# TOV1050 程式解說圖集
- 日期：2026-09-10
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-10
- 負責人：Codex
- 狀態：Done（圖集交付；2026-09-23 已同步 DAV-10）

## 需求與目的
依使用者列出的 13 個主題，以 A6API gpt-image-2.5-sunburst 產生繁體中文解說圖片。
### 使用者與流程
供接觸網維護工程人員了解匯入、分析、歷史比對、metadata 審閱及資料管理。
### 商業規則與限制
以現行原始碼為準；區分 TOV640 遺留規則、TOV1050 現況與未來規劃。不修改程式或 workbook。
## 現況盤點
HEAD a174ef2。原有未提交變更：兩份 workbook 與 docs/audits/visuals/，保留。
graph 原索引與文件有舊脈絡，已重新索引為 C-Smart-Maintanence-TOV1050_Analyzer。
現行 loader 仍 trim 首尾各 100 rows，與 2026-09-07 文件聲稱不同，圖集列為缺口。
Stagger 預設 EAL/TML workbook；Trend 仍有 10.2/0.2 常數。
線耗 r 為剩餘厚度；分母是名義截面 120 mm²，不是 πR²；r=0 回傳0為現行特殊行為。
### 相關 API／資料流程
CSV → adapter → detector；chart-only sampling；source-scoped raw export；SQLite transactions。
### 現有測試
本次為圖像／文件交付，使用圖片解碼、尺寸、文字與事實視覺檢查，不重跑未變更程式測試。
## 設計
### 範圍
13 張獨立橫向 PNG；藍白工程解說風格；UI 為概念流程示意。附 prompts、來源、總覽與封裝。
比較三種方案：單張總圖內容過密；少數合併圖難獨立引用；採每題一張便於簡報與訓練。
使用 brainstorming 整理分鏡；Impeccable 主導操作流程；Taste 僅適用字級、留白、層級，不套行銷布局。
DESIGN_VARIANCE=3，MOTION_INTENSITY=1，VISUAL_DENSITY=5；沿用 DESIGN.md 配色。
### 不在範圍
不修正已發現產品缺口；不重新驗證使用者修改的 workbook；不更改 frontend。
### 資料流與錯誤處理
A6API 官方 helper，每張獨立 prompt，僅從核准的兩個 Codex credential files 讀取憑證且不輸出。
### 驗收標準
13 個主題皆有圖片；逐張解碼與視覺檢查；實際尺寸和 provider/model 記錄可查；限制明確。
## 執行紀錄
### 實作
已核對 PRODUCT、DESIGN、migration、architecture、request 及 graph snippets；建立 prompts。
### 測試與 debug
執行 python outputs/2026-09-10-program-explain/generate_series.py 產生初稿與修訂；修正 Windows cp950 輸出錯誤後繼續。最後兩張以 A6API edits 修正多餘文字與風格。
逐張檢查標籤、公式與箭頭；執行 finalize.py 驗證 13 張 PNG 解碼、SHA-256、圖集連結與 ZIP 完整性。git diff --check 通過。未修改產品程式，未重跑產品測試。
### 驗收結果
13 個主題均已產出，最終選取版本見 manifest.json。實際皆為 1672 × 941 PNG，供應商未遵從請求的 1920 × 1080。圖集與 README 附現況／舊模組／未來規劃限制。
2026-09-11 使用者要求停止生成；所有已啟動請求當時均已完成，不再送出新生成請求。只整理既有產物。
既有 workbook 與 docs/audits/visuals/ 未修改。本次新增 request 文件與 outputs 圖集、提示詞、生成記錄、驗證報告及 ZIP，未提交。
## Linear 同步
- 最後同步時間：2026-09-23
- Issue 狀態：DAV-10 In Progress（圖集子工作已完成）
- 工具狀態：最初產生圖集時未掛載；2026-09-23 本工作階段已確認 Linear MCP 實際掛載。
- 同步結果：已在 DAV-10 記錄 13 張圖、prompts、manifest、verification、gallery 與 ZIP 路徑。
- Next action：使用者檢視圖集並提供修訂意見。
## 相關檔案
- outputs/2026-09-10-program-explain/
- docs/requests/2026-09-10-program-explanation-images.md
