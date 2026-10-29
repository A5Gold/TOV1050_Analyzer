# Exception Generator 開始分析操作可見性

- 日期：2026-10-23
- Linear project：TOV1050_Analyzer
- Linear issue：[DAV-22](https://linear.app/david-chu/issue/DAV-22)
- 負責人：Codex
- 狀態：Done（工作區修正；尚未封裝發布）

## 需求與目的

### 使用者與流程

使用者上傳 raw data、確認 run/context 後，截圖中找不到開始分析按鈕。必須能清楚找到並啟動既有分析。

### 商業規則與限制

保留既有 /analyze、context、必填檢查、loading 與多分頁隔離；不修改 detector、metadata、raw data 或匯出行為。保留工作區既有 workbook 與 outputs 修改。

## 現況盤點

- 相關程式碼：ExceptionGeneratorView.tsx、pageLayout.ts、MainLayout.tsx。
- Start Analysis 已存在於 CardContent 最後；fillDataRegionSx 固定高度且 overflow:hidden，config height:100% 加置中與內層捲動、card 預設可收縮，長表單有裁切風險。
- 既有測試：ExceptionGeneratorView.test.tsx（5 cases，含手動 context API payload）。
- Linear MCP 本工作階段實際可用；已建立 DAV-22。

## 設計

### 範圍

採用標題旁的單一 Start Analysis 操作，sticky 在配置區上方；保留既有 bounded region，配置區由頂部開始並可垂直捲動。Card 使用內容自然高度且禁止收縮，窄視窗欄位堆疊。錯誤放在操作區供點擊後立即看到。

已比較：只縮小間距仍可能在縮放後遮住按鈕；只修表單捲動可達但可發現性較差；採用頂部操作加不收縮表單可同時解決兩者。保留配置內層捲動，使 sticky 不受 MainLayout overflow 祖先影響，也避免更動全域版面。

### 不在範圍

不重設共用結果圖表高度、不發布 portable、不改分析商業規則。

### 資料流與錯誤處理

沿用 handleAnalyze；缺檔時禁用，缺站點顯示既有錯誤，執行中禁用且顯示 Analyzing。結果頁沿用 bounded data region。

### 驗收標準

- 桌面、短視窗與窄視窗初次配置可看到唯一 Start Analysis。
- 選檔後可點擊並送出正確 context；缺站點仍阻止 API；loading 禁止重複啟動。
- 捲動至 Station End 時分析操作可見，欄位與按鈕無裁切／水平溢出。

## 執行紀錄

### 實作

已移動唯一分析操作至配置標題旁，sticky 操作區含錯誤訊息。移除 config 垂直置中，Card flexShrink=0；解除 400px 最小寬度，兩／三欄輸入在 xs 堆疊；分頁工具列允許換行。handleAnalyze、backend、metadata、結果區及既有缺檔禁用保留。

### 測試與 debug

```text
# frontend，以下 npm 程序均設 NODE_USE_SYSTEM_CA=1
npm exec vitest -- run src/views/__tests__/ExceptionGeneratorView.test.tsx --pool=threads --maxWorkers=1
6 passed (11.65s)

npm exec tsc -- --noEmit
exit 0

# 另啟測試用 Vite：npm run dev -- --host 127.0.0.1 --port 5186 --strictPort
# TOV1050_E2E_URL=http://127.0.0.1:5186
npm exec playwright -- test tests/exception-generator.spec.ts --reporter=list
3 passed (28.1s)：1280x720、1033x640、390x844

git diff --check
exit 0
```

首次 Vitest 預設 forks worker 60 秒啟動逾時，改單一 threads 後完成。既有 MUI Tabs act warning 仍存在。新測試初版誤用導覽顯示文字、對 readonly 路徑直接 fill、只取唯一 alert；均已改為實際 accessibility name、模擬 Electron Browse 與指定錯誤 alert，最終通過。

### 驗收結果

三種尺寸驗證初始操作完整可見、缺檔禁用、Browse 後缺站點阻止分析、填至 Station End 時 sticky 操作仍可 hit-test 點擊、/analyze payload 正確、錯誤後可重試與無頁面水平溢出。單元測試另驗證 pending 禁用與失敗恢復，既有多分頁/context 測試通過。已檢視 1033px 截圖。瀏覽器使用 mock API 與 Electron openFile；未重新執行 raw detector，亦未封裝／替換目前正在使用的 portable。

## Linear 同步

- 最後同步時間：2026-10-23
- Issue 狀態：Done；已同步設計、實作、測試與驗收限制。
- Next action：使用目前 source/dev 重開配置畫面驗收；若使用 portable，需後續重新封裝後才包含修正。
- 阻塞／需要決策：無。

## 相關檔案

- frontend/src/views/ExceptionGeneratorView.tsx
- frontend/src/views/__tests__/ExceptionGeneratorView.test.tsx
- frontend/tests/exception-generator.spec.ts

上述三個程式／測試檔與本 request 為本次未提交修改。frontend/output/exception-generator-{1280,1033,390}.png 是測試截圖（含 mock error），frontend/test-results 是可再生測試產物；既有 workbook、raw fixture 與 outputs 修改全部保留，未納入本次工作。
