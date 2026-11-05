# Wide metadata補值規則確認及手修後整合設計

- 日期：2026-11-05
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-21
- 負責人：Codex
- 狀態：8份正式metadata已啟用，16 routes及npm dev啟用檢查通過；其餘長期事項見最新段落

## 需求與目的

承接三欄空白根因調查，使用者已確認：其他線TL採候選支架min/max或termination（BWA／Spring／Fixed）；Overlap僅一個有效TL便N，多個Y；Landmark使用實際範圍，單點X自動擴成[X-100,X+100]公尺。使用者更新TKL／ISL候選及TL-BK來源。本次先核對修改及完成整合設計，不覆寫來源／config。

## 唯讀核對結果

與2026-11-03生成layout逐格比較：TKL候選只有兩格修改，TKL UT Brackets!A341由126改60316、TKL DT Brackets!A207由-108改62208；ISL候選只有ISL UT Brackets!A665由113948改112948。TL-BK原表TKL UT第341列=60.316km、TKL DT第207列=62.208km、ISL UT第659列=112.948km，三筆與候選公尺值一致。

其他新增頁及主方向頁未修改，代表TL Boundaries／D:G／Data Review仍為舊快照，必須重新生成，不能只啟用手修檔。使用者不需再手改衍生列。原始mapping單位仍公里，轉換一次成canonical公尺。

## 設計方案

推薦以wide Excel為唯一人工維護入口，由Excel adapter建立統一區間模型，沿用版本／SHA檢查。替代是自動編譯sidecar，缺點是Excel更改後多一份產物必須同步。不得要求使用者手寫JSON。

1. 保存更新檔SHA與差異；重新核對mapping provenance，不能沿用舊source SHA／舊source位置分類而不驗證。
2. 以修訂後支架重新生成TL／Overlap、更新Data Review及來源provenance，輸出新版本候選，保留手修檔。全部實體支架及Contact termination一起取min/max。
3. Landmark原始點位及來源保留；FromM<ToM用原範圍，FromM=ToM才擴±100m。擴張後記錄point_buffer_100m，避免再次擴張。域外部分不猜裁切；不同Landmark同時命中須列明名稱或ambiguous，不能任選。無來源維持空白。
4. wide adapter分別讀A:C／D:G／H:J，K只控制D:E closure，G解析多TL；N=一個active TL，Y=多個，無TL未知。補值沿用當前例外maxLocation查詢，不改detector／ID／peak／median。
5. 修正DRL UT／獨立PL的sheet/context對應，不借用UT或DT；DRL wear9.1及已確認min/max保留。
6. 隔離config驗證：750m多TL、單TL N、端點／開區間、Landmark點±100m端點及雙重擴張、多地標、域外／單點TL、PL獨立。最後新報表驗證三欄、raw例外數與median列數，History輸入同一新報表鏈。

## 2026-11-05 最終規則確認

使用者明確選擇：全部實體支架及Contact termination一起取最小／最大里程，不以termination優先覆蓋支架首末。此規則適用本批其他線；排除明確Messenger與Landmark。三筆修訂後：TKL UT TL555=59442–60357m、TKL DT TL570=61902–62476m、ISL UT TL251=112180–113139m。使用者本回合已確認所提規則，依wide adapter方案繼續實作及隔離驗證。

## 不在本次範圍

不更改raw偵測／threshold商業規則、不靜默覆寫正式metadata、不將Landmark缺來源猜成最近地標，不改wear計算授權範圍。

## Linear同步與下一步

已驗證Linear MCP實際可用並讀回DAV-21 In Progress。2026-11-05已同步最終規則及實作進度（comment b0515236-750f-45cd-973c-98497f35e684）。Next action：完成新候選逐格讀回與兩份TWL報表／History隔離驗收，再提出具體正式替換版本。

## 實作摘要

- 新增 WideExcelEnrichmentProvider：自動辨識完整11欄，獨立讀取A:C／D:G／H:J、保留D:E混合開閉端點、同一workbook SHA驗證；舊7欄維持sidecar。
- DRL PL獨立選表及Class／Track Type，不借用UT資料。
- Brackets當列明確分類及來源優先於舊provenance，避免三筆手修里程被錯誤降為unclassified。
- 新候選輸出至outputs/metadata-review-2026-11-05/wide-v3/candidates，保留原Brackets、Landmark Points與歷史audit，新增規則及來源SHA。正式config未替換。
- 本批TWL／AEL／TCL／DRL無Landmark區間；有TL不代表一定有Landmark。使用者最後確認多地標命中須列出全部不同名稱，以「 / 」分隔。

## 已執行檢查

子代理：wide＋approved intervals 26 passed；capabilities＋TL 27 passed；最後來源別名回歸wide 14 passed。指定backend檔案diff whitespace檢查及主代理Python compile通過。候選逐格／SHA與實際報表驗收結果待下段記錄。

## 候選驗收

執行 `venv/Scripts/python.exe scripts/validate_refreshed_wide_20261105.py --existing`；執行過程8檔均已完成匯出並通過，正式validation.json記錄8 workbooks、16 routes、production_activation=false。逐格比對所有未修改頁（含公式／visibility）、更新欄組、來源SHA、TL atoms查詢、Landmark不重複buffer、DRL Mainline10條及PL7條Track Type獨立讀取均通過。另以唯讀程式斷言TL555／TL570／TL251三筆新邊界吻合使用者修訂。ISL、TKL、DRL方向頁及TL Boundaries預覽已抽查。

執行的生成命令：bundled Python `scripts/refresh_wide_metadata_20261105.py`、bundled Node `scripts/build_refreshed_wide_20261105.mjs`。Excel使用artifact-tool產生；來源與手修候選未覆寫。

## 本輪變更檔案

Backend：`tov1050_wide_enrichment.py`（新）、`tov1050_metadata.py`、`tov1050_capabilities.py`、`api/endpoints/analysis.py`（三處版本標記）；測試：`test_tov1050_wide_enrichment.py`（新）、既有capabilities測試及`test_median_analysis_snapshot.py`。Scripts：`refresh_wide_metadata_20261105.py`、`build_refreshed_wide_20261105.mjs`、`validate_refreshed_wide_20261105.py`、`validate_wide_reports_20261105.py`、`export_wide_history_20261105.py`、`repair_wide_report_version_20261105.py`。文件：本request及`docs/metadata-approved-intervals.md`新版規則段。產物：wide-v3及隔離報表目錄。Repo原已有大量未提交變更，本輪未reset、提交或清理其他修改。

## 報表耗時診斷

本機第一份報表等待較久；以僅安裝在outputs/…/wide-v3/diagnostic-tools的py-spy唯讀取樣，定位在openpyxl ChartData XML串流寫入，83963列中已進行至82131列，並非metadata lookup或History Compare停滯。診斷輸出export-stack.txt。未修改系統Python／venv依賴，也未因效能測試縮減raw偵測資料。

第一份20260907報表完成並驗收：raw838859、median83963、Summary289；TL與Overlap各289筆有值，Landmark0（TWL無來源）；所有非enrichment欄與11/3基準逐格一致。分析186.443秒，分析＋寫檔＋讀回驗證994.646秒；後者不可當作History Compare耗時。

第二份20260630報表完成並驗收：raw830792、median83244、Summary330；TL與Overlap各329筆有值，Landmark0；所有非enrichment欄與11/3基準逐格一致。分析240.283秒，整體923.844秒。僅餘SL97峰值2853.8m無TL，原因是TL17末端2853.5m與TL19起點2854m有0.5m空隙。新候選TWL UT!D21:G21、K21=neither，TL Boundaries第6／7列及Brackets第335–338／339–377列可追查。依使用者min/max規則維持未知，不能擅自跨gap延長；不是格式錯誤或讀取失效。

確認venv openpyxl.LXML=False，bundled runtime則True。為完成剩餘驗證，停止本次自建驗證程序的第二檔工作，保留第一份完成結果，透過venv Python程序內`sys.path.append(bundled …/python/Lib/site-packages)`臨時使用附帶lxml，並以`--resume`續跑。沒有修改venv／系統依賴；resume會先驗證已完成報表與來源SHA。此為測試環境處理，不代表一般npm run dev的匯出效能問題已解決。

Landmark覆核另輸出`LANDMARK-REVIEW.md`及JSON：TKL／TKS擴張後有16組不同名稱範圍交集（包含同一區間三個名稱的成對紀錄）。這不是格式錯誤；目前沿用多名稱ambiguous、值留空，已提供使用者「列出全部名稱／保留ambiguous」選擇，未有新決策前不自行選名。

## 補充覆核：匯出版本標記

子代理發現analysis.py三個匯出入口仍寫死`enrichment_version=tov640-first-nonempty-v1`，會與新版capabilities／MetadataEvidence矛盾。已改從對應snapshot／capabilities取得版本，缺值才沿用舊fallback。`venv/Scripts/python.exe -m pytest tests/test_median_analysis_snapshot.py -q`（backend工作目錄）10 passed（17.16s），涵蓋三個入口使用相同median snapshot、版本傳遞及舊fallback。

兩份大型測試報表的程序在修正前已載入舊入口；完成原流程驗證後，使用限定本輪outputs的`repair_wide_report_version_20261105.py`更正單一_Metadata版本標記，嚴格斷言其餘所有XLSX ZIP parts（包括Summary／ChartData／逐筆證據）位元組不變，記錄前後SHA。這是測試產物的版本標記修復，不重新計算例外或覆寫任何參考檔；新執行的程式匯出入口直接產生正確版本。

## 最終驗收及後續決策

History直接讀取上述兩份新median Exception Report：83963／83244列，220.78秒（約3.7分鐘），15筆重複例外（Low Height4／Left6／Right5），algorithm_provenance=verified，overview1376點。參考CSV、正式config及既有參考報表SHA維持不變。新版Repeated報表匯出15列，全部15列有TL與Overlap，Previous 1在Summary第二列表頭；檔案與結果見history-export-validation.json。

2026-11-05使用者最後確認：多地標同時命中列出全部不同名稱，以「 / 」分隔。新版wide provider已改為matched並保留名稱集合／來源列；舊sidecar多重命中政策不變。wide＋snapshot routes focused tests最後24 passed（15.50s）；實際55筆Landmark區間的邊界／中點／交集另以validate_wide_landmarks_20261105.py驗證，結果記錄於wide-v3/landmark-validation.json。TWL無地標來源，此最後調整不影響已完成TWL報表或History數據，無需重跑完整raw分析。

版本修復腳本初版重用ZipInfo導致來源reader offset被改動，驗證即中止，正式來源及原測試檔未被替換；改為copy(info)後通過，只有_Metadata所在ZIP part變更。Repeated驗證初版依舊docstring假設有Previous頁，按現行程式確認已併入Summary，修正讀回檢查後通過。兩者均屬輔助驗證腳本修正。

本輪成果：程式與8份新候選可供審閱；未替換正式config，沒有git commit。Next action：確認此8檔為啟用版本後備份並替換正式config，再做一般npm dev啟用確認。TWL 0.5m gap依已確認min/max規則維持未知；若需補滿，須提供工程涵蓋區間。一般環境Excel寫檔效能仍偏慢，本輪未修改依賴或宣稱已解決；History Compare已實測約3.7分鐘。

最終Linear同步：DAV-21 comment `926584c6-ed29-4137-8d88-c79ca50e6f0a`，已讀回狀態In Progress。實際Landmark8方向驗證全部通過；新版Repeated檔已讀回17列（2列表頭＋15筆）、Previous 1欄及15筆TL／Overlap均正確。來源／產物位置、驗收與下一步已同步；正式啟用與一般環境匯出效能列為剩餘事項。

## 使用者批准正式啟用

2026-11-05使用者明確回覆「approve and proceed」，授權啟用上述8份候選。執行計畫：核對候選validation SHA及Landmark測試；先備份目前正式config（含SHA及回復方法），再以已驗證候選逐檔替換；驗證正式讀取、版本、DRL獨立PL與多Landmark名稱，最後啟動一般npm run dev確認使用正式config。不得修改原始資料、DB或其他未提交變更。原本「待批准」敘述保留為歷史紀錄，本段為最新授權及狀態。


## 正式啟用完成（2026-11-05）

使用者批准後執行 `venv/Scripts/python.exe scripts/activate_wide_metadata_20261105.py`，8份候選（ISL、KTL、LAR_AEL、LAR_TCL、TKL、TKS、TWL、DRL）已替換正式config。16 routes preflight通過。新release為 `config/tov1050-metadata-release.json`，狀態activated；啟用結果見 `outputs/metadata-activation-2026-11-05/wide-v3/activation.json`。原8檔及舊release完整備份在 `config/backups/2026-11-05-wide-v3-activation-01/`，含SHA manifest與回復方法。候選內容沒有再修改；候選內review-only文字屬歷史，新release記錄正式授權。

子代理獨立唯讀覆核：正式8檔SHA等於核准候選及validation SHA，備份等於previous SHA，舊release備份及activation紀錄一致。原始CSV、TL-BK來源與正式DB未修改，未git commit；既有未提交修改保留。本次新增啟用腳本、正式8檔／release及備份與啟用證據。

一般 `npm run dev` 使用程序限定NODE_USE_SYSTEM_CA=1及獨立DB啟動成功，Vite／Electron／FastAPI健康正常。Playwright 1.58.2連Electron25 CDP遇Browser.setDownloadBehavior不支援，改用headless browser操作同一真實Vite UI及FastAPI；僅file picker回傳真實fixture路徑，沒有API interception。8檔sheets API成功；UI完成Browse、選TWL、填station、Start Analysis及背景job ready。從真實20260907 CSV擷取740–760m共1010列，清洗後raw810／median81／0例外，只作啟用測試，不作peak驗收證據。結果使用正式TWL SHA、wide_excel provider及wide-excel-enrichment-2026-11-05-v1，匯出按鈕可見，最後8檔SHA仍一致。

證據：啟用目錄的 `smoke.json`、`smoke.log`、`dev.log`、`activation-ui.png`；工具限制見 `cdp-attempt.log`。本次自建npm dev程序樹已核實指令後關閉，避免獨立DB測試環境與日常操作混淆。

驗收結論：本次8檔正式promotion完成，不再等待啟用批准。DAV-21維持In Progress處理長期事項；下一個可執行action為調查一般環境Excel寫檔效能及補跨線真fixture驗收；wear計算scope仍沿用既有授權限制。TWL 0.5m gap保留未知、無Landmark來源保留空白，均不需為本次啟用再修Excel。

正式啟用收尾檢查：Python compile、相關git diff --check及8份正式／備份SHA複核均通過。Linear DAV-21 description已置頂最新啟用狀態，完成留言315ca296-10da-431f-a0f6-da26e92ab13f；維持In Progress並列出上述後續action。
