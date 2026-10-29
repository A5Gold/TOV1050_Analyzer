# 雙系統與全模組修正：實作驗收紀錄

- 日期：2026-10-29（Asia/Hong_Kong）。
- 狀態：已依使用者 approve 完成實作及針對性自動驗證；Electron／原生 Excel 人工驗收待辦。
- 工作目錄：`C:/Smart Maintanence/TOV1050_Analyzer`；基線 HEAD `2f6f173`，包含原有未提交修改。
- Linear：[DAV-25](https://linear.app/david-chu/issue/DAV-25)。
- [需求](../requests/2026-10-29-dual-system-test-feedback.md)／[已批准設計](../superpowers/specs/2026-10-29-dual-system-support-design.md)／[開發計劃](../plans/2026-10-29-dual-system-development-plan.md)。

## 實作結果

| 範圍 | 最終行為與證據 |
|---|---|
| 共用身份 | 九個主 Line：TOV640 EAL、TML；TOV1050 AEL、TCL、KTL、ISL、TWL、TKL、DRL。EAL Mainline/LMC、TKL Mainline/TKS、DRL UT/PL 分開；DRL 分支 UT 相容 legacy Mainline，不與 Track UT 混用。未知身份不預設 EAL/UP，衝突明確拒絕 |
| Stagger | 小型工作表 preflight 辨識 AEL context，不開大型 ChartData XML；缺配置回 `STAGGER_CONFIG_UNAVAILABLE`，列實際身份及缺項。沒有借用 EAL/TML 係數；既有公式回歸通過 |
| Trend | 移除 AEL→EAL fallback；保留 Track、Section、Task No、Stn Start、Stn End。隔離同日不同來源／任務，跨期配對仍允許不同日期與 task；不造無候選結果 |
| History／Database | 九主線保存、查詢、篩選、計數；保存前驗完整 batch，拒絕覆蓋已知身份。方向與 legacy 別名相容；recurrence 先隔離分支再配 Section。branch_counts 與地理 Section counts 分開，不將 PL/TKS/LMC 合併至 Mainline |
| Exception 配置 | Quick Select 位於 Line 上方；右側橙色 Start Analysis 與原始資料概覽相鄰；窄／短窗配置已作瀏覽器測試 |
| 報表與 enrichment | 檔名移除 `_MedianSample`，保留原 median 實測樣本演算法及 provenance，新舊檔均可讀。Overlap／Tension Length／Landmark 保持可見；缺核准區間時顯示原因，不虛構值 |
| 圖表 | marker 真實里程 ±100m、同點可再次聚焦、三 panel 同步；threshold 預設顯示且可獨立切換。前後端裁切 domain，負 padding 不再因 ge=0 被拒絕；取消／舊請求／reset／同範圍重試有處理 |
| 圖表效能 | median 先切視窗再取樣；有界視窗快取。raw 使用暫存 mmap、120 秒 idle TTL、離開／shutdown 釋放及來源 drift 驗證；raw 冷載入顯示提示，允許取消／重試 |
| Wear／Version | 移除未知線套 EAL；Wear 缺核准 scope／公式即提示。比較驗身份及演算法；History／Version 對已知多個或不同 Section 明確要求分開，避免 chainage 混算。舊檔缺 provenance 標 unknown |
| About | 更新雙系統架構、DATAC/CSV 清洗差異、median 樣本、資料契約、threshold、快取／revision／digest 與工程能力限制 |

## 設計落地選擇與限制

中央來源為 `config/line_catalog.json`。Python registry 與 TypeScript adapter 消費同一份隨程式封裝的 JSON；另提供唯讀 `/api/line-catalog`。前端啟動不依賴 fetch catalog，這是對原設計「前端向後端取 catalog」的實作調整，可避免選單初始化受 API 啟動時序影響。

共同 ReportContext 與新報表保留來源身份／provenance；本版 repeated-record DB 沿用現有 schema，保存 canonical parent／session／Section，沒有持久保存 `source_line/source_track`。因此 DB 重匯出不能完整還原原始別名拼寫；分支與方向不會因此合併。未為來源別名稽核新增 schema migration。

其他線 Stagger 尚無核准配置，EAL Mainline 配置亦不代表 LMC 可用。TOV1050 Wear 缺核准工程 scope 時同樣停止；「全線身份支援」不表示全部工程計算已核准。TWL 三欄真正有效值仍依 [DAV-21](https://linear.app/david-chu/issue/DAV-21) 核准物理區間。沒有真 fixture 的路線／分支／方向組合僅有合成契約證據，不宣稱現場通過。

## 自動測試與建置

本輪結果分開列出，套件存在重疊，**不可相加當成不重複測試總數**。完整 log 在 `outputs/dual-system-2026-10-29/`。

| 驗證 | 結果 | 記錄 |
|---|---|---|
| 最終 DB／History／分支計數回歸 | 135 passed、28 skipped，18.10s | `database-regression-final.log` |
| 匯出／registry 回歸 | 113 passed、12 skipped，28.36s | `export-registry-final.log` |
| ReportContext／Version／Stagger 最終針對性測試 | 50 passed、1 deselected，56.63s | `calculation-validation.md` 含完整命令 |
| Wear／Stagger 既有計算回歸 | 130 passed、8 deselected，7.56s | `calculation-regression.log` |
| 較早 parser／Trend／Stagger（含真 U3） | 80 passed，177.08s | `calculation-validation.md` |
| 最終前端整合六個測試檔 | 39 passed | `frontend-integration-final.log` |
| 最後 branch navigation／DB store | 27 passed | `frontend-database-final.log` |
| 前端錯誤呈現／store | 29 passed | `frontend-diagnostics.log` |
| 真 Plotly 與九線／DRL 選單（Chromium） | 2 passed，39.2s | `browser-dual-system-final.log`、`browser-drl.png`、`browser-marker.png` |
| 配置視窗 1280×720、1033×640、390×844 | 三個尺寸案例通過 | `browser-qa-final.log`；當時另一 threshold 案例的測試 label 錯誤已修，以上一列重跑通過為準 |
| 最終 production build | exit 0；Vite 1m50s，含前置 TypeScript 檢查 | `frontend-build-final.log`；`tsc && vite build` |
| whitespace／來源保護 | `git diff --check` exit 0；16 檔 unchanged | `diff-check.log`、`source-baseline.json`、`verify_sources.py` |

skip／deselect 不列為通過；沒有宣稱執行全 repo 測試。Calculation 最終命令與歷次失敗修正見 [分項驗收](../../outputs/dual-system-2026-10-29/calculation-validation.md)。前端 diagnostics 與整合結果重疊；較早前端 70 passed 不重複列入最終數量。

最終收尾實際命令（PowerShell）：

```powershell
# frontend 目錄；只為當次 shell 設定 CA
$env:NODE_USE_SYSTEM_CA='1'
npm run build
npx vitest run src/components/DatabaseRecord/__tests__/LineTabPanel.test.tsx src/views/__tests__/DatabaseRecordView.test.tsx src/store/__tests__/useDatabaseStore.test.ts

# repo 根目錄
git diff --check
venv/Scripts/python.exe outputs/dual-system-2026-10-29/verify_sources.py --verify
```

最後建置曾發現新增分支篩選的兩個 TypeScript 型別遺漏：`DatabaseFilters.session` 仍限制為舊 TOV1050 列舉，`SavedRepeatedRecord` 未宣告 session。已補齊共用字串契約與可選欄位，重跑上列 DB 前端測試及 production build；最終結果以表列 log 為準。

最終重跑前端 DB：3 檔、27 passed（99.13s）。建置仍有既有大 bundle、`assert` browser externalization 及 xlsx 同時靜態／動態 import 警告；未阻擋產物生成。本任務啟動的5189驗收server已停止，未停止其他使用者程序。四份文件的相對連結已檢查，無失效連結。

## 真資料、輸出與效能

指定 AEL、兩份 TWL 舊報表只讀驗證：AEL/Mainline/UP、來源 UT/Mainline/U3/SHR/AWE；TWL/Mainline/UP、來源 UT/Mainline/U1/CEN/TSW，演算法皆 median sample v1。AEL Stagger 直接 Python 呼叫約 **0.08 秒**回缺配置，preflight 約 0.048 秒；不含 UI 上傳時間。詳 `calculation-fixture-validation.json`。

獨立輸出 `outputs/chart-validation-2026-10-29/`：

- `20260410_TML_DN_Mainline_Exception_Report.xlsx`：41,138 來源有效／代表列；分析約 31.8s、匯出約 138.3s，已以 openpyxl 完整讀回。DATAC 來源 Date=11.04.2026 與檔名／選定日期 20260410 不同，保留明確表單日期並記錄差異。
- `20260907_TWL_UT_MAINLINE_CEN_TSW_Exception_Report.xlsx`：838,859→83,963 代表點、160 exceptions；獨立分析約 103.2s、匯出約 192.9s。並行測試資源影響耗時，不與下表分析時間混為同次實驗。
- 20260630 TWL 已完整分析及 detail 量測；本輪沒有另外交付其新 Excel 實檔。命名規則另由匯出回歸覆蓋。

兩份 TWL 分別量測（順序 20260907／20260630），**範圍只含 Python route＋JSON，不含 Electron、HTTP 傳輸或 Plotly render**：

| 項目 | 20260907 | 20260630 |
|---|---:|---:|
| median 分析 | 65.54s | 60.37s |
| median cold detail | 218ms | 233ms |
| median 12 個不同熱視窗 P95 | 170ms | 172ms |
| raw 分析 | 53.39s | 49.37s |
| raw TTL 後冷重載 | 36.75s | 45.34s |
| raw 熱視窗 P95 | 358ms | 591ms |

`measurements.json`、`measure_chart.py`、`external-memory.json` 保存定義與原始量測；初版 RSS 探針無效已排除，另有外部程序量測，沒有宣稱低記憶體峰值。median route 熱視窗達到原暫定 P95≤2s 目標；完整 Electron 體驗仍待人工驗收。raw 冷讀仍需約 37–45s，120s timeout 與 loading 提示並未消除該成本。

真 Excel 產物產生於最後 branch／source 欄位白名單修改前；新增可選 provenance 欄由最新匯出測試覆蓋，沒有宣稱真產物已重驗該欄。原生 Excel 開啟是否 repair、視覺格式及 Electron 真實上傳／下載全流程尚未人工驗收。

## 修改與資料保護

基線保存於 `source-baseline.json`，含最初完整 git status；原有 raw／metadata 改動早已存在，不能把全部 `git diff HEAD` 歸為本次。此次在既有 median／background／chart 修改上整合，沒有 reset／stage／commit／push／package。

主要新增：`config/line_catalog.json`、`backend/app/core/line_registry.py`、`report_context.py`、`backend/app/api/endpoints/line_catalog.py`、`frontend/src/config/lineCatalog.ts`、`frontend/src/api/errorMessage.ts`，以及身份／圖表／DB／瀏覽器測試與本次文件。

主要整合位置：backend `analysis.py`、`calculation.py`、`database_records.py`、`version_difference.py`、`database.py`、report parser／Trend／Stagger／Wear、chart sampling／cache／export；frontend ExceptionGenerator／ChartComponent、History／DB selectors／stores、Trend／Calculation／Wear／Version stores、About／footer。既有 untracked chart／median 檔亦見基線，並非全部由本次新增。

最終 SHA 驗證：三份 raw、三份參考報表及十份 runtime metadata 共 **16 檔不變**。未向正式 DB 作測試寫入；測試使用暫存 SQLite，輸出至獨立驗收目錄。TOV640 專案僅只讀盤點，沒有修改。

三名既有子代理已完成資料契約／計算、前端圖表／UI、backend 原始流程／匯出工作，主代理整合 registry／DB／文件並審查跨模組契約。

## 下一步與完成條件

使用者以當前 source 啟動 Electron，重測指定 AEL/TWL 上傳、marker／wheel／門檻線、九線 History 保存至測試 DB，以及新 Excel 實際開啟與表格欄位。尚未封裝，既有安裝版不會自動包含本次修改。

DAV-25 進入 In Review，保留上述人工驗收；DAV-20／21／24 不因本次自動測試而標為完成。工程配置及 enrichment 實際值依核准資料另行接續；缺真 fixture 組合須取得現場樣本後再宣稱已驗。
