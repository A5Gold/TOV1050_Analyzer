# npm run dev 真實報表鏈重測

- 日期：2026-11-03
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-27
- 負責人：Codex
- 狀態：Done（報表鏈測試完成；metadata補值另追蹤DAV-21）

## 需求與目的

使用者要求啟動npm run dev，生成新一組Exception Report與History Comparison。沿用指定TWL 20260907／20260630 CSV，輸出到新的隔離目錄，不覆寫既有報表。使用正式config現值；前輪wide候選尚未promotion，不能把候選生成視為runtime已接入。

## 現況盤點

已讀PRODUCT.md、DESIGN.md、package.json、dev-latest.mjs及前輪median／Electron驗證紀錄。dev會啟動Vite、Electron及真實FastAPI；API port固定8000，先檢查佔用。前輪median預期ChartData為83963／83244，Summary為289／330，History重複15筆，作為本輪對照而非替代真實結果。

## 設計與驗收

1. 設定程序NODE_USE_SYSTEM_CA=1，執行npm run dev，保存啟動log與runtime diagnostics。
2. 在真實dev服務以UI操作兩次Exception Generator，完整raw偵測、median ChartData匯出；新輸出保存在本輪目錄。
3. History以剛生成的兩份報表輸入，執行比較及匯出；記錄提交／完成時間、例外數、console／network失敗。
4. 讀回xlsx核對Summary／ChartData／provenance；檢查來源及正式config SHA未變。

不修改正式商業規則、不啟用未核准metadata、不寫入正式DB。測試專用腳本／檔案及隔離DB放於outputs/validation-2026-11-03/npm-dev-retest/。

## 執行紀錄

已完成UI報表生成、History匯出及Excel讀回驗證。

已用程序NODE_USE_SYSTEM_CA=1啟動npm run dev，確認Vite／Electron／FastAPI及隔離DB。Electron25不支援Playwright CDP的Browser.setDownloadBehavior，因此完整UI自動化改由瀏覽器連接同一5174 dev服務；僅以file-picker adapter提供真實路徑，不攔截API。

測試腳本初輪未指定日期而沿用今天；產出保留於initial-default-date，不作正式交付。已改用MUI Date的Year／Month／Day輸入，並assert實際analysis POST的date_str等於CSV日期。另修正測試selector：初始Start New Analysis與結果頁New Analysis不同。以上是測試腳本修訂，未修改產品程式。

另發現既有啟動限制：dev-latest可選其他port，但dev:local仍硬編wait-on tcp:5174；使用5196時Electron未被啟動。本輪回到預設5174完成測試，已於DAV-27記錄後續action。

實際命令：程序設定NODE_USE_SYSTEM_CA=1、TOV1050_DEV_PORT=5174、DB_PATH指向本輪isolated.db；npm run dev，隨後node outputs/validation-2026-11-03/npm-dev-retest/run.mjs。測試專用NODE_OPTIONS preload只提供CDP／隔離Electron userData／檔案對話框路徑；未改產品程式。CDP失敗後，瀏覽器使用同一dev服務完成真實HTTP流程。

UI結果：20260907 raw838859／median83963／Summary289，分析連匯出166.49秒；20260630 raw830792／median83244／Summary330，172.89秒。Stagger Left／Right為118／103及112／123。History提交202（1.09秒）、UI完成78.57秒、worker76.14秒，重複15（Low Height4／Left6／Right5），比較Excel已下載。failed API requests=[]；只有兩次Exception頁非必要截圖5秒逾時；History截圖完成。

正式資料補值未完成：初輪報表讀回顯示Overlap／Tension Length／Landmark欄全空，已即時同步DAV-21 comment 2838f25a-6a2d-4212-9026-0de65b29082a。wide候選未promotion，本輪不將其冒稱為runtime已接入。完整結果與檔案連結見output README.md。

最終命令：bundled Python執行outputs/validation-2026-11-03/npm-dev-retest/readback.py，exit0。兩份ChartData精確83963／83244、Summary289／330，export_data_mode=chainage_median、detection_data_mode=cleaned_raw；comparison的15個exception IDs全部存在匯出Excel。兩份Summary的Overlap／Tension Length／Landmark分別289／330筆全空，確認是未完成功能。CSV與全部正式metadata workbook SHA前後不變。Python py_compile及Node --check通過。

驗收：報表生成、median檔案鏈、History15筆及匯出內容通過；metadata三欄補值未通過。History截圖人工檢視可讀、顯示15 Matches及正確量測日期。兩次Exception頁截圖逾時屬工具warning，無renderer exception／failed API request。本輪新增本request及隔離output目錄；沒有產品程式修改、提交或正式DB寫入。

## Linear 同步

本工作階段Linear MCP已掛載並成功查到DAV-27／DAV-28。DAV-27維持In Review；本輪測試結果已同步。Next action：DAV-21接入wide metadata補值並重測；DAV-27另處理dev port等待不一致。兩者不影響本輪新三份報表的交付。

最終同步comment：DAV-27 cf0f3ad5-a4b8-421c-8986-aec38446232c。測試完成後停止本輪npm dev程序樹，避免測試專用file-picker hook影響日後人工操作；環境變數只作用於該程序，未永久設定。
