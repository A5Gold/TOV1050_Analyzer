# Exception Generator 真實圖表 QA

執行：2026-10-26，`node tests/exception-chart-browser-qa.mjs`，exit 0。

本輪使用 API fixture 與真實 React／Plotly／WebGL。它驗證前端互動與布局，不能代替原始 TWL CSV 分析及 XLSX 數值驗收。

1280×720、1033×640、390×844 全部通過。逐尺寸紀錄、工具列 hit-test、Plotly traces 與軸資訊見 `report.json`；`mean-*`、`minmax-*`、`selected-*` 是各步驟截圖。

- 預設為 mean markers，例外 marker 保留原始峰值5800。
- min/max 為每組獨立垂直線段，原始資料可切換 points／acquisition lines。
- 共用合法 x 軸，三組 y 軸標題無重疊，繪圖高度454–470px。
- 三種尺寸工具列、模式選擇、min/max、例外列表選取與 Graph／Table 切換可操作。
- 桌面尺寸另驗真實滑鼠拖曳縮放、detail API 與快速切換窗口時忽略舊回應。
- 390px 未驗滑鼠拖曳縮放／回應競速；窄畫面以圖表在上、列表在下並捲動操作。
- 三種尺寸無 pageerror、無非法軸警告，已建立 WebGL canvases；紀錄中的頁面寬度等於視窗寬度。

本輪布局採圖表最低高度與結果區垂直捲動，較小高度需往下捲動以查看 Wear 圖區；Table 保留原有受限高度布局。
