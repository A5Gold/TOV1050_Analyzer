# P2 圖表實作與驗證

- 日期：2026-10-29（Asia/Hong_Kong）；對應 DAV-26，主需求／設計／計畫位於 docs 的 followup-stagger-metadata-chart 文件。
- 範圍：圖表 pointer 命中、metric×level 門檻偏好、hover；不修改 detector、匯出、API、metadata workbook、raw、正式 DB 或 TOV640。
- 本目錄的瀏覽器驗證採 API fixture＋真正 React/Plotly/Chromium/WebGL；沒有讀取現場 raw。不得將結果稱為真實 TWL raw／Electron 人工驗收。

## 重現及原因

新增 `frontend/tests/chart-pointer.spec.ts`，以 `page.mouse.move/click` 點擊與量測線同位置的 marker。修正前 pointer-before-confirm.log：測試失敗，x range 未聚焦，實際 `plotly_click.points` 只有 height1 的 1000m／4000mm，customdata 是量測 provenance，event target 為 rect。這證實該 fixture 的 scattergl 線／點命中競爭，hover 仍有傳遞點擊；不擴大推論全部現場問題。

修正保留 Plotly，使用 `chartMarkerHitTest.ts` 按目前 fullLayout、可見 marker trace、subplot、實際 CSS pixel 點擊位置做有限命中。8px 圓點只允許半徑 4px 加 2px 容差；沒有全域 nearest chainage fallback。略過 legendonly、隱藏及畫面外點、一般量測 trace；同位置多例外要求選單明確選擇。既有 ±100m、domain clipping、session/revision 請求隔離、reset／cancel／retry 保留。

## 最終行為

- 門檻總開關旁增加設定 Popover：Height／Stagger／Wire Wear × L1／L2／L3；缺級別停用及顯示未配置。
- availability 採完整 overview；detail 裁切不會把已配置級別誤判缺失。各格只過濾原有 segments，保留多 Class／Track Type／正負 stagger 的區段與值。
- 偏好按 session 存在既有 Zustand store；Graph/Table remount、縮放、清選取保留，關閉／重設 session 釋放，新 session 全選可用級別；總開關不覆寫細項。
- raw overview 的門檻控制停用，不新增未分析的 threshold。
- 線與 marker hover 統一只有 Chainage（m）／實測值（mm），保留 4 位小數；customdata provenance 留存。
- 舊 dual-system.spec.ts 的 emit 案例名稱改為明示 emitted event handler；真 pointer 證據使用新測試。

## 命令與結果

所有 npm/npx 指令只對當次 PowerShell 程序設定 `$env:NODE_USE_SYSTEM_CA='1'`，未變更 npm SSL、registry 或永久環境。

```powershell
# frontend；本任務專用 Vite server
$env:NODE_USE_SYSTEM_CA='1'
npm run dev -- --host 127.0.0.1 --port 5191 --strictPort
$env:TOV1050_E2E_URL='http://127.0.0.1:5191'

# 修正前實際滑鼠重現：failed，見 pointer-before-confirm.log
npx playwright test tests/chart-pointer.spec.ts --reporter=line --output=../outputs/followup-chart-2026-10-29/pointer-before-confirm

# TypeScript：exit 0，見 tsc-final.log
npx tsc --noEmit

# 完整命令及各次結果保存在同目錄 logs；不將重複重跑相加成 unique tests
npx vitest run src/components/__tests__/ChartComponent.test.tsx src/components/__tests__/chartMarkerHitTest.test.ts
npx playwright test tests/chart-pointer.spec.ts --reporter=line
```

前次實作中驗證：pointer-after.log 三 panel 真滑鼠為 1 passed；pointer-final.log 擴充第一案例（邊緣、pan 後同點、普通線不選、hover DOM、門檻與 Graph/Table 偏好）passed，第二案例因測試點在 legend text 而被透明 legendtoggle rect 攔截失敗。已修正測試改實際鼠點圖例 toggle 的位置，pointer-choices-final.log 為 1 passed；沒有為此修改產品行為。

第一輪 Vitest 的門檻 remount 整合案例超過預設 5 秒，改該複合案例的 timeout 為 30 秒；其後 17 passed。新增 A→B 延遲 detail 回歸後，預設 forks 啟動兩個 worker 逾時，沒有執行測試（vitest-final.log），不當成產品測試失敗或通過。降低當次測試並行，改以下命令，最終 **2 files／18 passed**，204.68 秒，見 vitest-final-single-worker.log：

```powershell
npx vitest run src/components/__tests__/ChartComponent.test.tsx src/components/__tests__/chartMarkerHitTest.test.ts --pool=threads --maxWorkers=1 --no-file-parallelism
```

門檻面板以 1280×720、1033×640、390×844 及模擬 deviceScaleFactor=1.25 驗證 bounds／九格／缺級別；panel-responsive-final.log 為 1 passed。截圖已等待 Popover 進場 opacity=1 並停用動畫，避免把過渡影像誤判為半透明；三張 thresholds-*.png 已查看，窄窗內顯示完整，文字與表格沒有裁切。這不是實際 Windows DPI 或 Electron 證據。

最終完整瀏覽器命令重跑同一測試檔（選 TWL line 的 API fixture），**3 passed，3.5 分鐘**，見 browser-final.log／browser-final/。三個案例涵蓋實際 hover→click、三 panel、line/dot 同位與邊緣、pan 後同點、普通線不誤選、hover DOM、門檻總開關／細項、Graph/Table remount、多例外選單、圖例隱藏 trace，以及三種 viewport／模擬 DPR。沒有 `gd.emit` 當作真 pointer 證據。

## 人工驗收與限制

- 需主代理／使用者進一步以當前 source 在 Electron 讀取指定兩份 TWL CSV／TML DATAC，驗 marker、側欄、detail HTTP、raw 冷讀、不同 Windows DPI。
- 本次 fixture browser 的 deviceScaleFactor=1.25 是模擬 CSS／device pixels 比例，不能稱為真 Windows DPI 現場驗證。
- 沒有封裝、發布、commit 或 push；本任務專用 5191 server 已於驗證完成後停止。停止前核對 PID 3736 為本 repo 的 `vite --host 127.0.0.1 --port 5191 --strictPort`，停止後確認 5191 無 listener；未停止使用者其他服務。
