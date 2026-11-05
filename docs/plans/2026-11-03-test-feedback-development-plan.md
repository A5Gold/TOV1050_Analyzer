# 測試回饋分階段開發計畫

- 日期：2026-11-03
- 狀態：使用者已 approve；P1–P4 已實作／重驗，P5 整合驗收進行中
- Linear：DAV-27；metadata依賴DAV-21，既有交付DAV-25／DAV-26
- 設計：`docs/superpowers/specs/2026-11-03-test-feedback-design.md`

> 後續 median 報表鏈需求以 `docs/plans/2026-11-03-median-report-history-plan.md`（DAV-28）為準，取代本文件「TOV1050 報表 ChartData 完整 raw」部分。detector、peak、Summary、獨立 raw CSV 與 TOV640 完整 raw 契約不變。

## 工作順序與交付物

P0 → P1；P2、P3可分開交付，P4沿用P0基線；P5整合驗收。資料缺口不阻擋History或Stagger開發；正式metadata promotion另需具體scope批准。

### P0：固定版本、來源與重現條件

1. 保存現有dirty清單及SHA；不reset、不把本次修改混入前次成果。優先graph定位並核對磁碟，實作前更新索引及inbound impact。
2. 記錄Electron／renderer URL／frontend build／backend PID與來源、metadata digest、report algorithm；確認九線catalog是否為實際載入版本。
3. 只讀盤點三份指定raw、指定xlsx、reference screenshot及DRL／ISL／TWL／TML config。全部產物寫獨立outputs批次，DB只用隔離複本／暫存SQLite。
4. 受控重現History直連API及Vite proxy兩路，記錄階段耗時、記憶體、response bytes、server exit／traceback；設定資源上限，不反覆盲跑五分鐘。
5. 建立目前median與完整cleaned raw的獨立基線，標記raw rows／cleaned rows／representatives／chart points不同定義。

完成條件：每項問題分為已重現／靜態已確認／未重現，證據可回溯，來源不變。

### P1：全線Stagger共用magnitude契約

位置：`backend/app/core/metadata.py` threshold adapter、`backend/app/core/analyzers.py` `_detect_stagger`、TOV1050 adapter／capabilities、`analysis.py` threshold payload、相關API types／chart consumer、配置候選與測試。

1. 盤點所有runtime workbook每個Class／Track／Level的Left/Right與單位，生成一致／單側／雙缺／衝突diff。採用2026-11-03使用者全線對稱決策。
2. 在共用adapter將legacy單側轉為canonical magnitude，雙側一致合併、衝突明確阻擋；正式wide候選可逐步改單一Stagger欄組，不為本次強制重排全部來源。
3. detector分別判正最大與負最小的abs，避免全列abs max丟掉另一側；保留原符號與SL/SR分類。圖表同一門檻生成±線。
4. 提供缺配置／衝突diagnostic與版本provenance；不影響Stagger Calculator缺Keq的既有gate。

測試：`backend/tests/test_detection_logic.py`及現有threshold／capabilities／chart套件（實作時依graph核實名稱）；覆蓋±t、門檻上下、L1/L2/L3、空level、四channel雙側、Class／Track切換、單側legacy、衝突。兩份TWL＋TML真檔固定輸入回歸；UI／API／Excel類型／數量一致。

完成條件：舊median固定基線下只出現可解釋的對稱修正差異；兩側同時超限均保留，所有線不再因僅缺Left重複配置而跳過。

### P2：完整raw判定契約與版本隔離

位置：`analysis.py` `_analyze_sync`／job快照、chainage reduction、chart provider、report export／ReportContext、History scope驗證及相關回歸。

1. 依本次AGENTS把detector／threshold crossing／overshoot／peak／export接完整cleaned逐筆raw；median與envelope限定明確標記的圖表視圖。
2. 先固定P1門檻，比較raw與舊median數量／type／level／峰值／FromM／ToM／ID差異，列出每項來源rows，不把改變當無關回歸。
3. 新algorithm版本與報表provenance隔離；舊報表不重寫。History對不相容版本給可操作拒絕，不靜默混比。
4. 驗證raw cache／TTL與大型工作資源，不能以overview envelope作raw fallback。

完成條件：圖表抽樣完全不參與例外與匯出；實檔raw crossing保留、所有差異可追溯。此階段獨立提交／審閱，避免掩蓋P1修正效果。

### P3：Metadata標準化與核准區間啟用準備

位置：`tov1050_metadata.py`、`tov1050_capabilities.py`、既有`tov1050_approved_intervals.py`／`tov1050_boundary_review.py`、review scripts、metadata文件；不重建已有provider。

1. 重驗10/29 batch-04與當前runtime/reference/TL-BK SHA；沿用有效成果，有漂移另產新batch。
2. DRL產review-only TOV640相容wide／點表候選、逐來源provenance／audit／三方diff；修正單位與反向表示但保存來源，保留8.9及有意調整值。
3. 明列DRL branch/direction缺口、Contact配對／coverage、Landmark範圍，交資料負責人審閱。CR289普通點不得推定終端。
4. 在隔離fixture核實現有provider／API／UI／Excel三欄及證據一致、SHA失效阻擋與unknown語義。
5. 只有另有具體資料批准，才備份、生成scope sidecar／manifest、隔離驗證後promotion與rollback演練；若無批准交付候選及缺口表即可，不假稱正式三欄完成。

測試：`test_tov1050_approved_intervals.py`、`test_tov1050_boundary_review.py`、`test_followup_metadata_review.py`及metadata adapter／report契約；ISL678點／CR28931點、重疊端點、partial coverage、來源SHA漂移、Landmark多命中。候選workbook按spreadsheets技能讀回／render確認。

### P4：History背景比較、例外表識別與全線保存驗證

位置：`backend/app/api/endpoints/analysis.py` compare／export、`backend/app/core/repeated_finder.py`、report reader／exporter、可重用`background_jobs.py`；`frontend/src/views/HistoryCompareView.tsx`、`frontend/src/components/HistoryCompare/SaveToDBDialog.tsx`、API client/types／store、`frontend/vite.config.ts`；SQLite／catalog僅按證據補缺。

1. 抽出ReportReader明確例外sheet registry與legacy adapter，排除ChartData／MetadataEvidence／MetadataBoundaryReview等輔助表，防Summary重複；小型context先驗證。
2. 將同步大量I/O／pandas移至受控worker，避免async event loop阻塞；有界worker／queue、按job/session/revision隔離、cancel／TTL／failure／restart expired及上次成功結果保留。
3. 新增建立／狀態／結果／chart viewport／export契約；沿用既有job路由風格，具體URL由現有路由盤點決定，禁止破壞其他analysis job。前端改短請求輪詢、真實phase與恢復查詢。
4. ChartData若需全scope驗證則一次串流，不重複預掃；summary與chart分離，overview有界、選例外才detail，匯出保完整資料。
5. 保存request/job id、phase耗時、row counts、RSS、payload bytes；辨識backend離線／proxy／job失敗。只延長timeout不算完成。
6. 驗證現有九線Save流程；有真缺漏才改選單或後端，不能重做已存在catalog。分支／方向、地理Section、來源system及algorithm相容性保留。
7. 取代LAST_COMPARE全域結果；必要時按profile加入matcher區間候選索引，以現算法oracle確保雙峰值交集、latest值、首匹配去重與Previous鏈順序完全一致。兩session交錯compare/export納入回歸。

測試：`test_history_scope_contract.py`、`test_auto_persistence.py`、既有DB／report-reader／history export套件；新增job生命週期與輔助sheet污染回歸。frontend針對loading／cancel／retry／stale result／九線選單測試；暫存DB round-trip、冪等及衝突。大型兩TWL報表真比較需測direct/proxy、cold/warm，目標job建立／status P95≤2秒、overview每cycle≤5000點，記錄完整耗時與峰值RSS而不捏造總時間SLA。

### P5：整合與交付

1. 用新演算法版本從兩份TWL raw產新報表於獨立目錄，再History compare→chart/detail→export→暫存DB save/reopen；TML DATAC作雙系統回歸。
2. 真Electron確認載入版本、九線選單、job進度與取消重試；Excel讀回Summary／ChartData／provenance，必要時原生Excel視覺驗收。
3. 跑相關pytest／frontend Vitest、TypeScript及production build；首次npm/npx前在該程序設定NODE_USE_SYSTEM_CA=1，維持HTTPS／strict-ssl。
4. 記錄實際命令／結果／未覆蓋fixture／SHA，檢查git diff --check及dirty差異，只提交本次經授權內容；不自動封裝或發布。
5. 同步DAV-27與DAV-21／25／26相關成果／阻塞。metadata資料責任人補批准，開發端負責軟體及隔離測試；未核准scope保留unknown。

## 本次規劃交付驗證

規劃交付時三名子代理完成唯讀調查。使用者其後 approve，已進入實作；目前進度、測試及資料批准缺口以 `docs/requests/2026-11-03-test-feedback-development-plan.md` 的執行紀錄為準。全線對稱規則、點／區間、raw／median 差異及 metadata promotion 的具體 scope 批准界線維持本設計。

## 核准後驗收進度

P1全線共用絕對值門檻、P2完整raw判定／匯出、P4背景History與session隔離已實作。P3依原計畫交付review-only候選，25來源SHA一致，尚無具體scope promotion批准。P5兩TWL完整raw報表與來源指紋通過，真Electron背景比較及保存／匯出驗收全部通過；大檔提交／總時間的效能限制如request所載。實際測試、性能數值及資料依賴統一記錄於對應request與outputs/validation-2026-11-03/README.md；套件有重疊，不相加，完整backend suite未完成。
