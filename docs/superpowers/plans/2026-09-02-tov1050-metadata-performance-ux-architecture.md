# TOV1050 metadata、Graph 效能與 Exception Generator 實作計畫

- 日期：2026-09-02
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-10
- 狀態：In Progress

## 目標

在不改變既有 exception detector 商業規則的前提下，完成 metadata audit、圖表 payload 分層解析度、Exception Generator 輸入 UX、共用 loading 狀態，以及 About/Algorithm Explain 視覺素材整合。

## 執行步驟

1. **Metadata audit（目前步驟）**
   - 掃描 DRL/ISL/KTL/LAR_AEL/LAR_TCL/TKL/TKS/TWL runtime workbook。
   - 對照 TOV640-style DRL reference、TOV640 EAL/TML 與 TOV1050 TL-BK mapping。
   - 報告 workbook/sheet/schema/units/interval overlap，保留 source row，不直接覆蓋 workbook。

2. **Backend chart payload optimization**
   - 保持 full-fidelity detector 與 raw exception finding。
   - 新增 chart envelope helper：每 bucket 保留 first/last/min/max、raw index/chainage；強制保留 peak、threshold crossing、interval boundary 與 selected window。
   - API 回傳 overview payload 與 zoom/detail payload；加入 parity tests。

3. **Exception Generator input UX**
   - 先讀取現有 view、API 與測試，再以 MUI 現有元件改造 input config。
   - Run List 快速選取、自動填入 line/Track/date/stations/task；保留 free-text override 與明確 override state。
   - `Direction` 改為 `Track`，只允許 UT/DT。

4. **Loading contract**
   - 建立共用 staged task model 與可取消、錯誤、reduced-motion 狀態。
   - 對六個分析模組接入 analysis/export loading；未知進度不得偽造百分比。

5. **About/Algorithm Explain visuals**
   - 使用 gpt-image-2 生成九張圖，程式內補充可驗證 caption/legend/alt text。
   - About 放 architecture/data-flow/operator workflow；各模組放對應演算法圖。

6. **Verification and Linear sync**
   - 執行 metadata、backend、frontend tests 與 production build。
   - 將每階段實作、測試、風險與 next action 留言同步 DAV-10。

## 驗收標準

- Detector 不因 chart downsampling 漏掉任何 raw exception。
- Overview graph 可快速顯示完整 FromM-ToM；zoom 後回傳更高解析度，足夠近時可看 raw points。
- Metadata audit 可重跑、輸出 machine-readable 與 human-readable 報告，不靜默修改來源 workbook。
- Track、run quick select、free-text override、loading/error/cancel/export workflow 均有測試覆蓋。
- About 與 Algorithm Explain 圖片有正確 caption、legend、alt text，且不以 AI 圖中文字作唯一規格。
