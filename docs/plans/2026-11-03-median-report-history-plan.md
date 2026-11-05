# TOV1050 median 報表與 History 比較開發計畫

- 日期：2026-11-03
- 狀態：P0–P3 完成；DRL 人工資料決策另追蹤 DAV-21
- Linear：DAV-28；相關 DAV-27／DAV-21
- 設計：docs/superpowers/specs/2026-11-03-median-report-history-design.md

## P0：確認基線與資料安全

1. 記錄 dirty 工作樹、兩份 TWL 來源與正式 DRL 的 SHA；保留指定參考報表及 DB。
2. 核對三個報表入口、TOV1050 median snapshot、raw CSV 及 History reader 現況；用 codebase-memory graph 定位後讀局部程式。
3. 將 DRL 格式、方向、單位、門檻及核准配對缺口列入 request；僅提供手修清單。

完成條件：文件與 DAV-28 有可追溯 next action；不修改任何正式 metadata。

## P1：統一報表 ChartData 選擇

1. 在 backend/app/api/endpoints/analysis.py 增加窄範圍的 line-aware report frame helper：TOV1050 median 用分析 snapshot 的 analysis_df，EAL／TML 用原 _export_frame。
2. 背景 report job、GET /export/report、POST /export/report/generate 共用 helper；保持 Summary／分型表取 snapshot results。
3. 獨立 raw CSV、raw detail、detector 路徑不改。缺 session median frame 時明確失敗，不回退 raw／前端抽樣。
4. _Metadata 記錄 raw_row_count、chart_row_count、export_data_mode=chainage_median 與原有 raw detection provenance；TOV640 不變。

完成條件：三入口同樣選源，TOV1050 不因產報表重載 83 萬列，TOV640 保留既有行為。

## P2：契約與回歸測試

1. 修改原先將 TOV1050 報表 ChartData 視為完整 raw 的測試；新增同一 session 的 report median／raw CSV 完整 raw 對照。
2. 測背景 job、同步路徑、無 frame／來源失效、TOV640 EAL／TML raw，確認結果表／ID／peak 不變。
3. History 以含 median ChartData 的報表 fixture 讀取並核對 chart_rows、例外 scope／算法相容、overview／detail；舊完整 raw 報表保留可讀。

完成條件：相關 pytest 全通過；不因輸出模式變更更改偵測結果或比較判定。

## P3：真檔效能與整合驗收

1. 在隔離 outputs 目錄由兩份指定 TWL CSV 產生新報表；Excel 讀回 ChartData 約 83963／83244 列、Summary raw 例外 289／330、_Metadata 模式及來源 SHA。
2. History Compare 使用這兩份新報表，驗證結果、圖表 peak／detail、comparison Excel；量測提交、worker、總時間、檔案大小與 cache。與前輪完整 raw 報表約 895 秒比較，目標是明顯縮短並避開五分鐘斷線，不虛報固定 SLA。
3. 用 TOV640 EAL／TML 做報表完整 raw 回歸；核對來源／正式 metadata／指定參考報表 SHA 未變。
4. 運行 TypeScript／frontend 相關測試（如有修改）及 git diff --check；記錄實際命令、結果、未覆蓋風險至 request 與 DAV-28，按驗收結果調整 issue 狀態。

完成條件：報表 file chain 可直接供 History 成功比較、性能數字有真實記錄、DRL 手修依賴清楚交接；不自動封裝／發布。

## 最終驗收

- 兩 TWL 報表 ChartData 83,963／83,244 列，Summary 289／330；直接比較 187.539 秒、HTTP 192.911 秒。
- 真 Electron／Vite proxy 首次比較 205.230 秒；重跑整合驗證 113.952 秒，15 筆結果，overview／detail／Excel／隔離 DB 保存及重新開啟通過。效能受 cache 與機器負載影響，不作固定 SLA。
- TML 真 DATAC raw／ChartData 皆 41,138 列，Summary 152；來源、metadata 與指定參考檔未改。
- 前端 38 tests、TypeScript、production build、相關 backend 回歸與 git diff --check 通過；首次平行 Vitest worker timeout 及 Electron screenshot timeout 已在 request 記錄重跑結果。
- 完整證據與未提交範圍見 `docs/requests/2026-11-03-drl-median-history-report.md`；正式 DRL 不覆寫，待資料負責人手修／核准。
