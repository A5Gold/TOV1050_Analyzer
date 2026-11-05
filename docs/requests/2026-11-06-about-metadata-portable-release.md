# About／演算法 metadata 說明及 portable dir 發布

- 日期：2026-11-06
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-29
- 負責人：Codex
- 狀態：In Progress

## 需求與目的

更新About及Algorithm Dialog說明metadata格式，回答設定來源目錄；依使用者授權commit/push目前dirty work，排除.csv、.datac及輸出Exception Report；重建最新portable dir。

### 使用者與流程

操作人員由About查詢wide工作表與區間規則、Algorithm確認raw偵測及median報表鏈，維護metadata時使用目前執行版本的config。

### 商業規則與限制

沿用已確認wide-v3：TL全部實體支架及Contact termination min/max；Overlap單TL=N、多TL=Y、無TL未知；Landmark單點±100m、實際範圍不再擴張、多名稱以 / 分隔；DRL只有UT與獨立PL、wear9.1。不改detector或wear授權範圍。原始資料與正式DB不改。

## 現況盤點

相關程式：About/aboutGuideContent.ts、OperatorGuide.tsx、DeveloperReference.tsx、ExceptionAlgorithmDialog.tsx、HistoryCompare/AlgorithmTutorialDialog.tsx、electron/main.js、backend/app/core/config.py、package.json、backend/backend_server.spec。

現有About與Exception Dialog部分仍描述median後偵測，與完整raw detector不符。package extraResources目前直接複製整份config，可能包含本機備份及測試seed。未提交檔包含約1.2GB產物及Electron user-data/cache，須區分審閱證據與暫存。

## 設計

採用共用靜態metadata說明，沿用現有表格／Typography；在About操作指南、開發者參考及Exception Algorithm顯示wide欄組及路徑；History Dialog補同一報表鏈。替代方案是只修開發者說明，維護簡單但操作人員難找；另一方案是新獨立說明頁，超過本次範圍，因此不採用。

標準wide欄：A:C Landmark FromM／ToM／Landmark，D:G Overlap FromM／ToM／Overlap／Tension Length，H:J Track Type／FromM／ToM，K Interval Closed控制D:E。欄組獨立，不按同行join；Chainage公尺。Brackets及來源頁保留供追溯。

開發版讀project/config；portable讀exe同層resources/config；CONFIG_PATH存在時backend優先採用，About診斷顯示實際路徑。

提交前列明可提交檔與排除項，保留本機raw／輸出報表。暫存DB、browser profile、安裝的診斷工具不作原始碼提交。保留必要候選workbook與audit證據。打包使用新輸出目錄，不覆寫舊portable或data；明確重建backend與frontend、排除本機config備份及測試資料，驗證打包SHA及啟動。

### 驗收標準

- About與相關演算法說明一致，涵蓋wide格式／單位／缺值及raw→median報表流程。
- frontend build及相關測試通過；dirty後端相關回歸通過。
- Git commit/push完成，提交無CSV／DATAC／輸出Exception Report及暫存DB/profile。
- 新portable dir可啟動，內附metadata等於正式8份SHA，含新說明及最新backend來源，不夾帶正式DB或備份。

## 執行紀錄

已讀brainstorming技能，依本次使用者明確更新／提交／打包授權繼續具體化；不增加重複批准閘門。子代理唯讀審核packaging與config路徑。

## Linear 同步

本工作階段Linear MCP實際可用。建立對應issue並於完成後同步測試、commit及portable證據。

## 相關檔案

以上程式、package config、本request、打包驗收紀錄及目前已授權dirty work；最終列表以commit diff及排除清單為準。


### 實作及驗證進度

共用MetadataFormatGuide供About兩種指南及Exception Dialog使用，History Dialog補同一median報表鏈；修正舊median判定敘述，沿用現有MUI。新增wide欄組、公尺、端點、DRL獨立PL、Landmark多名稱及config／DB路徑。版本提升2.0.1（package／backend health）。

打包排除config/backups、Excel鎖檔、DB及暫存，保留正式EAL/TML及內建seed。build:backend改專案venv Python -m PyInstaller，requirements-build.txt記錄6.18.0及hooks2026.9；spec BACKEND_DIR修正為實際backend目錄。新增verify_portable_release.py供8份SHA、release、backend樹及來源逐檔驗證。

已執行：frontend npm run build（TypeScript＋Vite）通過，4136 modules；既有assert外部化、xlsx混合import及chunk size warnings保留，非build失敗。後端focused首輪87 passed／4 fail，原因為正式wide啟用後舊測試假設；子代理只修測試並新增獨立legacy fixture，該檔10 passed；其餘7檔重新執行82 passed（72.80s），合計92項通過。前端單thread 42 passed／1 timeout（History工具列超過預設5秒）；該檔以30秒重驗中。About診斷assert改限制於診斷表，避免新路徑說明造成文字重複。

PyInstaller首次卡在Python3.12 platform._wmi_query（py-spy唯讀確認），已停止自建程序，僅建置程序以PYTHONPATH載入outputs/release-2026-11-06/build-tools/sitecustomize.py令WMI查詢走既有OSError fallback。沒有修改OS、全域Python或venv函式庫，也未將此工具作為runtime hook。建置現在已進入module analysis。一次輔助修補命令使用錯cwd未執行，隨後以正確根目錄完成；未改來源資料。

提交範圍約558檔／377MiB（含歷次候選、inspect及audit），selection清單位於outputs/release-2026-11-06/commit-selection.json。忽略CSV／DATAC／Exception及Repeated輸出、DevelopmentValidation報表、user-data、diagnostic-tools與暫存DB；2個原已tracked的排除檔仍保持本機dirty。必要變更及使用者修訂TL-BK workbook納入。秘密樣式掃描未命中；暫存stage無raw／report／profile／DB。未刪除本機排除檔。

History工具列檔以 --testTimeout=30000 重驗8 passed（47.01s），原超時案例4.058秒完成，前端本批5檔共43項通過；無功能修正。


### GitHub與最終建置

已提交並推送master：d6fd3a7d3512443ff2d37acc08cac64675e12c22，559檔。git ls-remote讀回origin/master完全相同。包含原本本機4e50d90設計commit一併推送；沒有force push。剩餘tracked dirty只有使用者排除的AEL CSV及既有TWL Exception Report。

提交後frontend以bundled Node執行vite build通過（4m1s，assets/index-a108f626.js）；只含既有bundle warnings。首次backend完成後檢查PYZ發現build-only sitecustomize被自動收錄，因此spec明確excludes sitecustomize並重新建置，verify腳本亦斷言PYZ不含此模組且必須有wide provider與history reader。新增raw CDP portable smoke腳本，直接啟動封裝EXE、實際health／diagnostics及About／兩個Logic Dialog，不使用API攔截；避開新版Playwright與Electron25的context指令相容性問題。

Next action：完成最終backend、electron-builder dir及實機封裝啟動驗收，將測試DB移至本輪驗收目錄，交付乾淨portable資料夾與SHA紀錄。

子代理說明覆核發現Class來源敘述需精確化：Class實際由Exception Boundarys頁讀取，方向頁是三組enrichment／Track Type區間，已修正文案並補K支援left/right端點。因此再做最終frontend build（frontend-build-final.log），確保交付包含更正。其餘wide欄組、DRL及History metadata沿用規則覆核一致。
