# Issue 1：Exception Generator 大檔匯出與圖表折返

- 日期：2026-10-26
- Linear project：TOV1050_Analyzer
- Linear issue：未建立／未同步（本工作階段未掛載 Linear MCP）
- 負責人：Codex
- 狀態：In Progress：診斷與設計，尚未修改產品程式

## 需求與目的

TWL 完整 CSV 約 117 MB、84 萬列可顯示圖表與例外，但 Excel（含完整 ChartData）等待超過五分鐘失敗；約五萬列可在約 30 秒匯出。要求優化分析與匯出、顯示真實進度百分比、評估 timeout，以及釐清圖表同 channel 同 chainage 多值／zigzag。

### 使用者與流程

選取 TWL CSV → 確認 UT/Mainline/20260907/CEN–TSW → 分析 → Graph/Table → Report Excel。

### 商業規則與限制

完整 raw data 用於 detector、peak/threshold、報告與 ChartData；抽樣只限圖表 payload。Chainage 為 m。保留既有 metadata、來源檔、前端未提交修改、多分頁隔離與顯示四位小數。不得以平均或任意去重靜默丟棄重複量測。

## 現況盤點

- 文件：PRODUCT.md、DESIGN.md、docs/architecture.md、2026-09-02 metadata/performance spec、2026-10-23 regression 與 request。
- 匯出：analysis.generate_report_from_data → export_analysis_report → 大於 50,000 列走 openpyxl write_only ChartData；同步執行在 async handler 內，完整 DataFrame deep copy。
- 現有 Vite proxy timeout/proxyTimeout 均為 300000 ms；Axios instance 未設 timeout。
- 圖表：build_chart_payload 依原始位置保留 min/max/first/last；ChartComponent 按收到順序連線。尚待資料檢查判定 zigzag 原因。
- 現有測試：backend/tests/test_tov1050_report_export.py、chart_sampling 與 analysis session 相關 tests。
- 工作區原有 frontend view/tests、workbooks 與 outputs 未提交變更，均保留。

## 設計

### 範圍

先量測完整／部分 TWL 清洗、分析、chart sampling、Excel 寫入與傳輸瓶頸；驗證重複里程與方向折返；提出具體方案與驗收條件供確認。

### 不在範圍

不修改 metadata workbook、不更改 detector 商業語意、不封裝／發布 portable、不影響其他分析模組。

### 資料流與錯誤處理

待診斷後補齊；保留 cache 與多分頁 identity，不允許 cache 失效時靜默將 sampled chart data 當完整報告。

### 驗收標準

- 完整與部分來源皆可匯出全部清洗後 ChartData，Summary/例外與基準一致；數值與來源不丟失。
- 紀錄階段耗時、列數、輸出大小與可取得的記憶體資訊。
- 百分比以真實 processed/total 計算，壓縮等未知比例階段明確標示。
- 大檔工作不阻塞狀態查詢；逾時／失敗顯示具體原因並可重試。
- 圖表明確區分重複樣本、連線折返與 envelope；保留噪音極值及例外 peak，detail 可追溯。

## 執行紀錄

### 實作

尚未修改產品程式；依 brainstorming 技能先完成診斷與設計確認。

### 測試與 debug

待填入實際診斷結果。

### 驗收結果

尚未驗收修正。

## Linear 同步

- 最後同步時間：無。
- Issue 狀態：Linear sync blocked。
- 偵測工具狀態：目前工具清單有 Codebase Memory MCP，沒有 Linear tools；未嘗試或宣稱建立／更新 issue。
- 影響：需求、診斷、設計與測試證據僅暫存 repo，尚未同步 Linear。
- Next action：重新連接／啟用 Linear MCP，重開 Codex 或建立新 local task；驗證 tools 實際掛載後先同步累積 request/spec 與測試證據，再繼續開發。

## 相關檔案

- docs/requests/2026-10-26-exception-generator-large-export-and-chart.md
- outputs/exception-performance-2026-10-26/（診斷產物）
