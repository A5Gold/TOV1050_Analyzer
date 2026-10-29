# 使用者測試回饋：雙系統與全模組支援

- 日期：2026-10-29
- Linear project：TOV1050_Analyzer
- Linear issue：[DAV-25](https://linear.app/david-chu/issue/DAV-25)
- 負責人：Codex；使用者審閱設計
- 狀態：實作及針對性自動驗證完成；Electron／原生 Excel 人工驗收待辦

## 需求與目的

使用者要求先設計、擬定開發計劃，並使用子代理。修正 Stagger AEL 解析錯誤、Exception Generator 配置／enrichment／命名／圖表互動、History 全線保存、Trend identity／context、About 說明及全模組 EAL/TML hardcoding。

目標主Line共九個：TOV640 EAL/TML；TOV1050 AEL/TCL/KTL/ISL/TWL/TKL/DRL。依使用者後續澄清：EAL分支{Mainline,LMC}、TKL分支{Mainline,TKS}、DRL分支{UT,PL}；DRL的UT已確認對應現有Mainline。LMC/TKS不列獨立Line，Branch與Track方向分開。DATAC與CSV格式轉接分開，下游共用parent line＋branch＋direction報表契約。此澄清取代前版「十一線」設計。

已確認：其他路線尚無核准 Stagger 配置，先加明確提示，不借用 EAL/TML 公式。中位實測樣本邏輯維持正確現況，只去掉檔名 `_MedianSample`。

## 參考資料

以下均在 repo，已交子代理只讀檢閱，不覆寫：

- `00 Reference Document/Raw data/TML/TML_D1_260410.datac`
- `00 Reference Document/Raw data/TWL/20260907_TWL_UT.csv`
- `00 Reference Document/Raw data/TWL/20260630_TWL_UT.csv`
- `02 Output Document/TWL/20260907_TWL_UT_MAINLINE_CEN_TSW_Exception_Report_MedianSample.xlsx`
- `02 Output Document/TWL/20260630_TWL_UT_MAINLINE_CEN_TSW_Exception_Report_MedianSample.xlsx`
- `02 Output Document/AEL/20260603_AEL_UT_MAINLINE_SHR_AWE_Exception_Report_MedianSample.xlsx`
- `01 Screenshot/Exception Generator graph.png`

## 現況盤點、設計與驗收

完整證據、替代方案、資料流、UI、錯誤處理與範圍：[設計草案](../superpowers/specs/2026-10-29-dual-system-support-design.md)。

分階段實作、測試與驗收：[開發計劃](../plans/2026-10-29-dual-system-development-plan.md)。

關鍵限制：既有工作目錄有大量未提交修改；知識圖譜部分 snippet／行號落後，已以定位後的實際檔案核對。TWL 三個 enrichment 欄已存在，但來源缺核准物理區間，不能以補 UI 欄位當成解決。其他線 Stagger 工程配置缺失為使用者確認的外部依賴。

## 執行紀錄與結果

使用者已明確 approve，三名子代理由調查轉入實作，完成資料契約／計算、前端圖表／UI、backend chart／匯出；主代理整合 registry、History／DB、共用型別及文件，並完成交叉審閱。

- 共用九主線 catalog、branch／direction adapter 與 ReportContext 已接入；LMC／TKS legacy alias 限來源 adapter，DRL UT 相容 Mainline。未知身份及衝突不再靜默套 EAL／UP。
- AEL Stagger 快速辨識後提示缺核准配置；真檔直接 Python 呼叫約 0.08s，不開大型 ChartData XML。既有 EAL／TML 公式回歸通過。
- Trend 保留 AEL 身份與 Track／Section／Task No／Stn Start／Stn End；History／DB 九線保存、分支隔離、branch counts 與地理 Section 分開。
- Quick Select、橙色 Start Analysis、三欄缺資料原因、無 `_MedianSample` 檔名、marker ±100m、概覽門檻切換、負範圍裁切及取消／重試完成。
- Wear／Version 的身份、缺配置、演算法／Section 相容閘門，以及 About 雙系統清洗／架構說明完成。

完整命令、測試 log、真 fixture、性能定義、修改清單與限制：[驗收紀錄](../verification/2026-10-29-dual-system-validation.md)。主要結果包括 DB 135 passed／28 skipped、export／registry 113 passed／12 skipped、計算契約 50 passed／1 deselected、Wear／Stagger 130 passed／8 deselected、前端整合39 passed、最後DB前端27 passed及Chromium整合2 passed；這些套件有重疊，不能加總為unique數量。最終production build見驗收log。

兩份真 TWL median 熱視窗 route＋JSON P95 約170／172ms；raw TTL後冷讀仍約37–45s，已提供等待提示、取消及同窗重試。性能不含 Electron／傳輸／render。

16個來源／參考報表／runtime metadata SHA全部不變；正式DB未作測試寫入，TOV640專案只讀。保留原有dirty／untracked檔案，未reset／stage／commit／push／package。

## 設計調整與未完成的驗收

中央catalog以同一packaged JSON供Python／TypeScript消費，另保留唯讀API，前端不在啟動時fetch。既有DB schema保留canonical身份，沒有持久保存source_line/source_track原始別名；新報表及ReportContext仍保留來源provenance。已知多／跨Section的History／Version本版明確拒絕比較，避免chainage混算。

其他線Stagger尚無核准配置，依使用者決策明確提示即為本次交付；不借EAL／TML公式。TWL三欄的真實有效值仍依DAV-21核准interval。未有真fixture的組合不能宣稱現場驗收完成。Electron全流程與原生Excel開啟／格式尚待人工驗收，目前未封裝版本。

## Linear 同步與下一步

2026-10-29已驗證Linear MCP掛載並同步DAV-25；本次最終交付狀態為In Review，下一動作為使用者以當前source啟動Electron，重測指定AEL／TWL上傳、圖表互動、測試DB保存及新Excel開啟。DAV-20／21／24未標為完成。工程配置及enrichment資料依核准後再接續，不需要重新批准已完成的本次實作。

## 相關檔案

主要production／測試／新增檔及原有dirty基線詳見驗收紀錄與 `outputs/dual-system-2026-10-29/source-baseline.json`。需求／設計／計劃／驗收均為本機未提交文件，不宣稱GitHub blob已存在。


## 2026-10-29 GitHub 保存補記

使用者後續授權保存全部工作狀態，並排除原始 CSV／DATAC。主提交與後續 metadata 快照已推送至 GitHub master：`74f49ee`、`0c26a71`。需求／設計／計劃／驗收文件現已存在 GitHub；上文「未提交／未推送」描述保留作原驗收當刻紀錄。完整範圍、檢查差異、HTTP 408 重試與剩餘 raw 修改見 [提交需求紀錄](2026-10-29-commit-dirty-work-state.md)。本次未重跑功能驗收，也未封裝版本。
