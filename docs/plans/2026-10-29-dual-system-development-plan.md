# 雙系統與測試回饋：已批准開發計劃

- 日期：2026-10-29（Asia/Hong_Kong）
- 狀態：已批准並完成實作及針對性自動驗證；人工驗收待辦。
- Linear：[DAV-25](https://linear.app/david-chu/issue/DAV-25)
- [設計草案](../superpowers/specs/2026-10-29-dual-system-support-design.md)／[需求紀錄](../requests/2026-10-29-dual-system-test-feedback.md)

## 目前交付狀態（取代下文歷史待辦語句）

P0–P6已完成本次實作；P7已完成針對性自動測試、真DATAC／兩份TWL量測、獨立Excel輸出與Chromium測試，Electron與原生Excel人工驗收尚待完成。[最終驗收紀錄](../verification/2026-10-29-dual-system-validation.md)列出實際命令、結果及未覆蓋項；下文保留已批准的開發規劃作歷史紀錄，不表示仍等待使用者批准。

落地調整：共用packaged JSON給Python與TypeScript，另有catalog API；DB沿用schema，保留canonical身份但不持久保存source別名；History／Version已知多／跨Section明確拒絕。TWL真實enrichment值依DAV-21，其他線Stagger缺配置依決策提示。三名子代理已交付，最終DB 135 passed、前端DB27 passed、Chromium2 passed；詳驗收log，不加總重疊suite。

## 原批准工作順序與依賴


採用「共用路線／報表契約＋逐模組修正」。順序為 P0 → P1；P2／P3／P4 可在 P1 契約穩定後按不同檔案分工；P5 消費相同契約；P6 文件以最終行為更新；P7 整合驗收。

本計劃不把缺 metadata 或工程配置的功能假稱為全線可算。其他路線的 Stagger 缺配置提示，是使用者已確認的本次交付行為；真正各線 Stagger 計算屬核准配置到位後的後續開發。TWL 三欄的可見性／缺資料說明可以先完成，填入真實 TL／Overlap／Landmark 值依賴 DAV-21 的核准 interval。

## P0：固定現況與回歸證據

1. 記錄 HEAD、git status、執行中的 Electron／frontend／backend 版本及來源路徑，避免比較舊 build 與現有 working tree。
2. 保留現有未提交修改；建立本次新增檔案清單，不自動 reset、stage、commit、push 或封裝。必要隔離 checkout 須明確攜帶現有 median 變更，不能從 HEAD 漏掉它們。
3. 只讀記錄指定三份 raw、三份 xlsx、runtime metadata 的 SHA-256、schema、context、algorithm 及 row-count 定義。既有 TWL metadata 記錄來源／代表筆數：838,859／83,963，830,792／83,244；這是舊產物證據，完整重新分析需 P7 才驗收。
4. 以臨時 runtime／SQLite 與獨立輸出目錄重現 AEL Stagger、Trend 身份／五欄、History 選項、negative zoom range；記錄 HTTP response body，不只 console status。

完成條件：每個問題有「重現／靜態已確認／尚未重現」分類；現有原檔與正式 DB 不變；缺 fixture 的路線／方向／session 明列。

## P1：共用路線與報表身份契約

### 預計修改位置

- `backend/app/core/tov1050_contract.py`、`config/app_settings.json`、metadata resolver。
- 新增共用 line registry／ReportContext／ReportReader 模組，名稱依現有 package 慣例決定。
- `backend/app/core/calculation/excel_parser.py` 及相關 model。
- `frontend/src/config/tov1050.ts`、API types/client、共用 selector hook。
- 涉及 line/session 欄位的 DB schema／filter adapters；先盤點再決定是否需要 migration，不能為加選單而先改 schema。

### 工作

1. 建立九個主 Line 的 catalog：EAL、TML、AEL、TCL、KTL、ISL、TWL、TKL、DRL。branch 依 Line 定義，分開 source system、metadata group/session、legacy storage identity、可用模組與缺項。前端改用後端 catalog；載入失敗給明確錯誤，不回退為 EAL。
2. 依使用者澄清：EAL={Mainline,LMC}、TKL={Mainline,TKS}、DRL={UT,PL}；DRL branch UT 已確認對應 legacy session Mainline。UI採Line→Branch→Direction；報表使用parent line＋branch，不將LMC/TKS列為獨立Line。現有EAL/LMC class、TKL/TKS session、DRL/Mainline經adapter相容；舊檔line=LMC/TKS或複合碼須有明確來源alias及provenance，不能只改字串而遺失分支。
3. 統一 UT/UP、DT/DN/DOWN 等方向對照，保留來源 track；未知不預設 up。DRL branch UT 與 track UT 分開，alias限定DRL分支欄位，不影響方向解析。清楚區分 branch、legacy session、Section、Class、Track Type；合法branch/direction組合依metadata驗證。
4. 共同 ReportReader 分層讀 `_Metadata`／Summary／ChartData；先讀小型 context 做 preflight，再按需要讀大型 ChartData。缺新欄位的舊報表保持相容；已存在的衝突值不得被 filename／UI 靜默覆蓋。
5. 集中欄位 aliases，streaming／一般 parser 共用。保留空值語義，不能把 unknown overlap 轉為 N；候選記錄保留自身 run/context，而非只靠 TL 補身份。
6. 核對 background、legacy export、report reader 的 schema/version 與 algorithm provenance；`raw_row_count` 現有語義不靜默改成另一種筆數，新增／文件化明確 source_points、representative_points，舊欄保留相容。

TOV640只讀核對已完成：主UI／metadata／wear DB用EAL＋LMC分支/class；annual parser `wear_annual_repository.parse_analysis_workbook`會保留來源sheet為`line=LMC`；legacy DB migration亦有LMC→EAL group＋LMC class規則。P1/P5須沿來源adapter轉換，不能全域重寫所有line欄位。對custom檔名缺分支的舊報表不得猜LMC；LOW/RAC等既有Section保留原語義。`branch`、legacy分支欄`session`、分析分頁`client_session_id`分開。

驗收：九個主線及已定義分支的context round-trip；EAL Mainline/LMC、TKL Mainline/TKS、DRL UT/PL互相隔離；LMC/TKS legacy line alias有證據才映回parent line＋branch；DRL legacy Mainline映到branch UT且track不變；UT/DT、缺值／衝突／多context／未知線；蛇形與顯示欄名aliases；同日不同任務不混用。新舊 `_MedianSample` 檔名皆可讀，來源內容不因解析被修改。

## P2：Stagger、Trend 與身份正確性

### Stagger

修改 `calculation.py` 的 `_infer_stagger_line`／`upload_stagger`、`stagger_metadata.py`、`stagger_selector.py`、`stagger_service.py` 及前端錯誤呈現。

- 先完成報表格式／身份驗證，再查明確路線策略表。取消非 EAL 無條件進 TML 的 Keq 分支。
- AEL 及其他缺配置路線回可操作的 `STAGGER_CONFIG_UNAVAILABLE` 類型診斷，內容包括實際parent line／branch／direction、缺少參數／support metadata。與 `INVALID_REPORT_CONTEXT`／未知線分開；EAL Mainline配置不能自動套用LMC。
- 未通過配置閘門不載入整份大型 ChartData、不計算結果。UI 不把它顯示成「檔案解析失敗」或長時間等待後的空白 unsupported line。
- EAL/TML 已有配置保持原公式與數值結果；DT 正確走 down lookup。

### Trend

修改 `useTrendStore.ts`、`calculation.py` 的 trend route、`trend_analyzer.py`、excel models/reader；對讀 `TrendResultTable.tsx` 與 export。

- 移除 filename 判斷後 fallback EAL 及 API 預設 EAL；結果使用經驗證 workbook context。
- 五欄已存在，修正中途遺失的 context：候選由 Summary 保留自身身份，同份報表的 ChartData context join 使用 source/run/date＋parent line＋branch＋direction＋section＋TL/位置。跨日期量測配對則不以 date/task 相等作條件，使用相容 scope、section、TL／物理span，日期是回歸的時間軸。TL 空白不應令已有 task／station context 全部消失，也不能讓所有空TL候選互相配對。
- 替代現有僅 TL、第一筆優先及僅日期分桶的 metadata lookup；測試同名 TL、同日多任務、空 TL 及不同上傳順序。
- 本版每次 Trend／History comparison／Version Difference 操作僅接受一個parent line＋branch＋direction scope，混合scope明確拒絕並提示分開執行；同scope各section分組，不以chainage直接混算。表格、API、Excel五欄與branch一致。

驗收：指定 AEL 報表可識別，Stagger 正確提示缺配置；Trend `line=AEL`，五欄依序為 UT／Mainline／U3／SHR／AWE，不得顯示 EAL；無 candidate 時正確顯示無結果而非捏造一列。EAL/TML 原 fixture 數值不變。

## P3：History、Database、Check 1 Year 與全線儲存

修改 `SaveToDBDialog.tsx`、`HistoryCompareView.tsx`、`Check1YearDialog.tsx`、`LineTabPanel.tsx`、`database.py`、`database_records.py` 與對應 stores/types。

- 所有選單／section options 使用 registry，不再限制兩線或另一組七線；預填 workbook 已解析 context，選項改動不能覆蓋成另一條路線。
- 後端對所有 registry 路線做一致驗證；未知線不能因不在 LINE_SESSIONS 便繞過嚴格驗證。
- line tabs以九個parent line為入口，branch為子篩選；line counts涵蓋全部分支且每筆只計一次。LMC/TKS不新增獨立line tab，PL/TKS/LMC不共用其他分支的badge key，DRL UT與legacy Mainline為同一分支不重複計數。
- 維持 preview/save digest、optimistic version、atomic transaction、冪等與跨線隔離。
- 若舊 DB schema 需要新 identity 欄位／索引，提供版本化、可回復 migration 及 legacy adapter；只在複製 DB 演練，不猜測未知舊紀錄。

驗收：九個主線及已定義分支在暫存SQLite完成compare→preview→save→重開→filter/count→export；重複保存不增殖；衝突／過期版本不部分寫入；EAL/LMC、TKL/TKS、DRL/UT/PL舊資料分支不丟失。任何舊line alias只經明確adapter解析，不全庫改寫；parent count與各branch count可核對且不重計。

## P4：Exception Generator UI、命名與圖表

### UI 與報表

修改 `ExceptionGeneratorView.tsx`、`ExceptionTable.tsx`、analysis export job 及共用 filename builder。

- Quick Select run 移到 Line 正上方。
- 標題左置，右側 action group 為原始資料概覽及橙色 Start Analysis；保留 loading/disabled/cancel、短窗／窄窗可見性與鍵盤順序。
- 三個 enrichment 欄保持可見，缺 interval 顯示原因。分清「未有核准資料」與「已確認沒有 overlap」，不把空值填成 0／N。已核准資料到位後，UI／Excel 必須實際有一致值。
- 移除 `_MedianSample` 命名附加；background／legacy／Content-Disposition 名稱一致，保留 metadata 與樣本值。以新輸出目錄驗收，不覆寫使用者原 Excel。

### 圖表正確性

修改 `ChartComponent.tsx`、API types、`analysis.py` chart endpoint、threshold payload builder。

- 共用 focus 行為：marker／右側清單／再次點同一 dot 全部用 dot x 或 maxLocation ±100m；顯示 range 與 detail 參數一致，三 panel 同步，邊界取交集。
- 依事件內 marker trace/id 尋找真正例外，不只讀第一個點；同座標多例外有穩定身份。
- 沿用既有 Thresholds toggle，預設顯示並解除 selectedException 限制。threshold_segments 重用 detector resolver及同 revision/metadata digest，含無例外區段、Class/Track Type 切換及 stagger 正負門檻，selection 只控制高亮。保留 Class 未定義才 fallback both、明確 NaN 不 fallback、Wire Wear L2 未配置便不畫的語義；圖線值須與 detector 實際門檻逐段一致。
- 前後端 range normalization、domain 交集、finite 驗證及空視窗狀態一致。以使用者 negative from_m 案例加入 API regression，避免 viewport padding 422。
- 保留 debounce/cancellation/generation guard。正常取消不顯示錯誤；stale response 不覆蓋；double-click reset 立即還原 overview。
- 增加「重試此範圍」；FastAPI detail 陣列轉可讀驗證訊息，過期分析與 timeout 各有可操作提示。

### 圖表效能

修改 `chart_sampling.py`、snapshot payload 路徑及必要的 background job/cache。

- 每 revision 一次準備 numeric arrays／位置索引，先切 window 再取樣。非單調採集順序用排序搜尋索引取位置後保留原採集次序，不能為快而把 pass/segment 連錯。
- 加有界 window cache／請求去重，key 含完整 session/revision/mode/window/max_points；最新請求優先，避免已過期 backend 工作塞住單 limiter。
- raw overview 進入時驗來源並準備有限資料；wheel 不反覆全檔讀取及雙 SHA。每次 detail/cache hit 檢查 identity/size/mtime，改動後重驗 SHA；來源變更／刪除即失效並回409要求重匯入。TTL後冷載入驗讀取前後digest。離開／TTL／取消釋放，維持 raw 不常駐規則。
- 在完整兩份 TWL 量測冷／熱 detail 的 P50/P95、排隊、sampling、JSON、render、peak RSS/heap；明列 timeout 真正成本，不能只延長 timeout。

驗收：縮放／平移／負 padding／重點同 dot／門檻切換／reset／兩分頁／新 revision／失敗重試全通過。對有效 median 熱 detail 暫定目標 P95≤2s，冷路徑獨立報告；這是待實測目標，不是目前已達成。若未達需完成瓶頸修正或列出實測限制，不能宣稱效能驗收通過。

## P5：Wear、Version Difference 與 enrichment 能力

- Wear：移除非 TML 一律 EAL 的路徑，拆開報表讀取與 raw cycle／工程設定；核對 wear_cycle_types、wear_cycle_metadata、source aliases、EXPECTED_SEGMENTS、UI 及保存鍵。缺批准 TL interval／公式顯示明確 blocking reason；不把新線套既有 EAL/TML scope。
- Version Difference／其他報表模組：接共同reader，增加parent line/branch/direction／單位／mode provenance檢查，混合scope拒絕，避免只憑日期／Chainage對齊。raw與median／不同algorithm version不直接做數值差，要求以相同模式產生報表；舊檔無provenance保留legacy comparison相容行為並標示algorithm unknown。保留現有檔案／列數／記憶體限制。
- Enrichment：接續 DAV-21 審閱，取得帶 source workbook/sheet/rows、approved_from/to、核准人及端點政策的 interval 候選；驗證後才接 resolver。Landmark 點與區間分開，缺範圍不推算。原始 metadata 不靜默覆寫。

完成條件：各模組有逐路線「可用／缺 metadata／缺工程配置／待真 fixture 驗收」矩陣。合成的已核准區間 fixture 能產生正確三欄，實際 TWL 的缺資料原因仍如實呈現。真正 TWL 三欄有效數值的完成另需 interval 資料核准，不假稱只改程式就完成。

## P6：About、Algorithm Explain 及操作文件

更新 About 的 `aboutGuideContent.ts`、OperatorGuide、DeveloperReference、GuideVisuals、各模組 Algorithm Explain 與相關 docs。

必須包含格式專屬清洗差異：

| 項目 | DATAC | TOV1050 CSV |
|---|---|---|
| 常見 header | LINE/TRACK/KM/LOCATION/WHGT1c/STG1c/RWH1mm | Line/Km/HeightWire1 [mm]/StaggerWire1 [mm]/WearWire1 [mm] |
| 檔案／chunk | 分號 legacy loader | 分隔符偵測／UTF-8 BOM／50,000 row chunks |
| 前後修剪 | 現有規則：大於40行時首尾各20 | 現有規則：首尾各最多100 |
| 公尺換算 | KM 與 LOCATION 組成 Chainage | Decimal Km×1000，一次 |
| 高度 | 既有 +5300 校正 | 不加 +5300 |
| invalid | wear 6.56 等 legacy 規則 | 精確 1.#IO、無有效 Km／全量測無值等規則 |
| context | 保留來源與選定 run；來源日期／檔名可能不同 | 原始 Line 可為 RED LINE，不能作邏輯路線權威 |

再說明 canonical model→metadata→median→detector→chart/Excel、各 channel 中位來源可不同列、raw overview 限制、job/revision/digest、DB 交易、threshold/±100m 與能力矩陣。更新舊圖及 alt，不再聲稱現行 detector 使用所有原十點資料。文件描述以最終程式核對，不能把本設計當已完成實作。

## P7：整合驗收與交付

| 驗收項目 | 必測案例／證據 |
|---|---|
| 雙系統輸入 | 指定 TML DATAC、兩份 TWL CSV；清洗／單位／context 正確；其他線有真 fixture 才列現場通過 |
| median 不回歸 | 代表值與來源 row/channel oracle、奇偶規則／gap/pass／非相鄰重訪；同 revision detector／ChartData／Excel 一致 |
| 檔名 | 兩份 TWL 新輸出無後綴；舊有後綴仍能讀；algorithm、digest、數值及來源點／代表點定義不變 |
| AEL Stagger | 讀出 AEL/UT/Mainline/U3/SHR/AWE，快速列缺配置，沒有空路線或計算結果；EAL/TML 數值 golden 不變 |
| Trend | AEL 不變 EAL；五欄 API/table/export 一致；空TL／同名TL／同日多context／上傳次序／無候選 |
| 全線及分支保存 | 九個parent line及各已定義branch的save/read/filter/count/export；EAL Mainline/LMC、TKL Mainline/TKS、DRL UT/PL互不污染；DRL branch UT不誤當track UT；legacy alias不重計；annual來源line=LMC保留且canonical映EAL＋LMC；custom檔缺分支不猜測；暫存SQLite atomic/version／重複保存 |
| enrichment | 欄位可見；unknown/non-overlap 分開；核准 interval 邊界／多TL／landmark點／缺資料原因 |
| 圖表 | 每 dot±100m、同 dot 重點、邊界裁切、概覽threshold與detector一致、明確NaN不補線、負padding、快速wheel／reset／雙分頁／取消／超時／重試；raw模式開啟期間改檔／刪檔／TTL重載 |
| 下游 | Wear／Version／Check1Year 身份隔離、capability、輸入限制及現有流程不回歸 |
| 真實 UI／Excel | Electron 寬／窄／短窗；表格橫向捲動與橙色按鈕；新檔實際開啟不 repair、格式／欄位／metadata正確 |
| 資料保護 | raw/metadata/參考xlsx SHA不變；正式DB未作測試寫入；輸出到獨立驗收資料夾 |

### 測試執行原則

先跑有意義的 parser／identity／DB／chart 針對性測試，再做兩份真 CSV 與 DATAC 整合；純位置改動以視覺 QA，不新增只複製 JSX 結構的測試。重用現有 `test_excel_parser.py`、`test_calculation.py`、`test_chart_sampling.py`、`test_tov1050_report_export.py` 及 frontend ChartComponent／ExceptionGeneratorView tests，再新增缺少的契約、DB identity、錯誤與競態 cases。

原計劃測試命令（歷史規劃；實際執行項目及結果以驗收紀錄為準）：

```powershell
# 在 repo；使用已驗證 Python runtime，測試 DB/輸出均為暫存位置
python -m pytest -q backend/tests/test_excel_parser.py backend/tests/test_calculation.py
python -m pytest -q backend/tests/test_chart_sampling.py backend/tests/test_tov1050_report_export.py

# 每次新 shell 的第一個 npm/npx 前設定，只作用當前程序
$env:NODE_USE_SYSTEM_CA='1'
npm --prefix frontend run test -- --run
npm --prefix frontend run build
```

正式執行前核對 package scripts；先按改動選取 suites，之後才整合。全量 suite 若有既有失敗，分開列明；不重用 2026-10-26 的 pass 數當成本輪結果。不改 strict-ssl、不改 registry 或持久環境變數。

## 子代理協作與審閱

設計階段由三名子代理只讀調查；批准後已沿相同邊界完成實作及交叉審閱。整合者負責契約一致性及最後文件核對。實作獲批准後可沿相同邊界分工；共用 registry／parser／analysis.py 等共用檔由指定單一負責人編輯，其他代理提出需求，避免同檔競寫。每階段完成後整合者審查 diff、測試與風險，再進下一階段。

## 依賴、風險與下一步

1. 新路線 Stagger 係數／support 配置未有：本次以明確提示為完成條件，不是開發阻塞。
2. TWL/AEL enrichment 缺 approved physical intervals：先完成缺資料呈現及 adapter 測試；真實值依 DAV-21 核准後補。
3. LMC/TKS歷史identity及DRL UT/Mainline alias：須對比舊DB及報表golden，不能直接全庫改line。TOV640的LMC hardcoding已只讀核實，證據見設計草案；有來源line=LMC與migration相容碼，但未查正式DB，不宣稱實際歷史列分布。本次不修改TOV640專案。
4. 現有多項未提交 median／background／chart 修改：P0 固定 working tree，不漏掉或覆蓋。
5. 首次 marker 完全未放大的單一原因與 timeout 頻率仍待真 UI 重現；已確認 range／selection／計算成本問題，不保證靜態推測就是唯一根因。
6. 所有路線／session／direction 缺少真 fixture 的組合列待驗證，synthetic contract 通過不能替代現場樣本。

目前下一個動作：使用者以當前source啟動Electron並進行人工驗收，包括指定檔案上傳／圖表、測試DB與新Excel開啟。未封裝、未發布；正式metadata／資料庫未改動。詳細限制與後續資料依賴見驗收紀錄，無需重啟設計批准。
