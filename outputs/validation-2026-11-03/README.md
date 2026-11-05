# 2026-11-03 核准計畫實作驗收

本資料夾包含驗收產物；正式 raw、metadata workbook、指定參考報表及使用者資料庫未覆寫。原工作樹已有大量修改，final-dirty-status.txt 是整個工作樹狀態，不代表全部由本次新增。

- targeted-pytest.log：13個相關backend套件218 passed。
- targeted-vitest.log：4個相關frontend套件52 passed，serial worker。
- final-preflight-pytest.log：最後preflight/raw/chart回歸39 passed。
- final-enrichment-pytest.log：核准metadata enrichment回歸23 passed。
- final-gap-pytest.log：最後缺值圖表回歸8 passed；final-history-vitest.log：404／410過期工作回歸8 passed。
- final-tsc.log：TypeScript檢查成功、無輸出；production build亦完成。以上pytest集合重疊，不相加，未宣稱全套backend通過。
- stagger-policy/：固定median前後語意差異；TWL Left 0→116/109、Right 94/111不變。TML最後annotated raw為20/46。最後已用完整segment重跑三檔，TWL raw數量與raw-integration完全一致，TML所有類型與median一致；stagger-final-run.log與semantic-diff保存來源列／峰值／區間差異。
- raw-integration/validation.json：最終兩TWL完整raw分析／ChartData讀回；本處才是完整raw最終數量依據。
- history-http/validation.json：原有median報表的direct/proxy背景比較；不能代表新raw性能。proxy submit2.21秒，超過≤2秒目標；status P95約0.084秒。
- electron-history/：source Electron、實際backend／Vite proxy、隔離DB及九線保存驗收。
- final-source-sha256.json：原始資料、指定報表及正式metadata的來源指紋。

Metadata P3候選另見 outputs/metadata-review-2026-11-03/batch-01。維持review-only；DRL方向／DT、Contact端點配對與coverage、Landmark範圍待資料負責人批准。三欄契約與核准fixture測試通過不等於正式coverage已批准。

軟體未封裝／發布，沒有建立commit。需求、設計及開發計畫見docs下2026-11-03文件；Linear DAV-27追蹤整合，DAV-21追蹤資料批准。

完整raw報表結果：九月838859列／289例外（Left118／Right103），分析59.39秒；六月830792列／330例外（Left112／Right123），分析63.17秒。含完整xlsx匯出及逐列讀回分別1158.13／1193.18秒；不能把這個總耗時當分析耗時。source-final-recheck.json：14來源指紋全部一致。

最終Stagger診斷：`python -u scripts/validate_stagger_policy_20261103.py` 成功；三檔來源均未改，兩TWL固定median除新增Left外其餘canonical完全一致，raw差異有來源列證據；TML全類型在三模式皆一致。

Electron最終passed：15筆重複例外；九線Save、chart overview/detail、比較xlsx、隔離DB保存與read-only重開均通過。含上傳完成895.158秒、提交12.977秒（未達≤2秒）、status P95 0.474秒。詳細見electron-history/validation.json及postchecks/validation.json。

最終production build：final-build.log，3m27s成功；Linear DAV-27 In Review。
