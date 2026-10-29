# Exception Generator 真實 Plotly 瀏覽器驗收

執行時間：2026-10-26。目標：`http://127.0.0.1:5179`。

命令（frontend 目錄）：

```powershell
$env:NODE_USE_SYSTEM_CA='1'
node tests/exception-chart-browser-qa.mjs
```

使用 Chromium、實際 React／Plotly／WebGL。API 回應為獨立 fixture，沒有驗證真實 CSV 分析或 XLSX 下載；這兩項須由後端整合測試驗收。

| 視窗 | 結果 | 說明 |
| --- | --- | --- |
| 1280×720 | 通過功能驗收 | mean markers、同組 min/max、raw points／acquisition lines、raw exception peak=5800、共用合法 x 軸、滑鼠縮放 detail、過期 detail 隔離均通過 |
| 1033×640 | 通過功能驗收，有可讀性限制 | 同上；完整報表／Raw／精簡報表／Graph／Table 的中心點 hit test 均可操作 |
| 390×844 | 未通過圖表操作 | 固定 320px 例外側欄擠壓並遮擋 chart controls；Chart data combobox 點擊逾時。匯出 toolbar 已換行，但不能宣稱手機圖表可用 |

兩個桌面尺寸均沒有 pageerror 或非法座標軸警告。截圖顯示，1033px 視窗的圖區垂直空間偏少，三個直向 y-axis 標題重疊；1280px 亦有些重疊。此為待改善的可讀性限制，未影響本輪數值／座標與工具列 hit test 結果。

`report.json` 保存測量與完整警告、請求、資料快照；`mean-*`、`minmax-*`、`selected-*` 為截圖。腳本最後 exit code 1，忠實反映 390px 的操作失敗，未將桌面通過視為手機通過。

沒有修改 production code。此次新增的腳本為 `frontend/tests/exception-chart-browser-qa.mjs`。
