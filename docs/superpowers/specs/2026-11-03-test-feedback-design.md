# Metadata、Stagger 與 History Comparison 設計草案

- 日期：2026-11-03
- 狀態：使用者已 approve；依開發計畫實作及整合驗收中
- Linear：[DAV-27](https://linear.app/david-chu/issue/DAV-27)，延續 DAV-21／DAV-25／DAV-26
- 需求：`docs/requests/2026-11-03-test-feedback-development-plan.md`
- 計畫：`docs/plans/2026-11-03-test-feedback-development-plan.md`

> 後續使用者已指定 TOV1050 median 報表鏈，詳細設計以 `docs/superpowers/specs/2026-11-03-median-report-history-design.md`（DAV-28）為準。僅報表 ChartData 改用 median，完整 raw detector／peak／Summary／raw CSV 與 TOV640 流程維持。

## 1. 目標與已確認決策

修正使用者無法取得例外 metadata、正值 Stagger Left 未出現、History 全線保存與大型比較斷線的流程。先核對現有已完成及未提交成果，再補缺口，避免重建已有的九線 catalog 或 approved interval provider。

使用者本次明確確認：**所有路線的 Stagger Left 與 Stagger Right 使用相同門檻絕對值；正值代表 Left、負值代表 Right。** 此決策取代「TWL Left 門檻需另提供」的初期假設。同一路線／Class／Track Type／Level 左右共用 magnitude；不同路線或情境仍使用各自設定，不把某線數值套給其他線。這是 Exception Generator 的偏移超限規則，不是 Stagger Calculator 的 Keq／支撐計算配置批准。

## 2. 本次調查證據與確定程度

| 問題 | 本次唯讀核實 | 結論／限制 |
|---|---|---|
| DRL 格式不同 | runtime 為 long threshold、startKM/endKM；git 檔案歷史只有初始提交 fb3cf7c；10/23 release 七份未含 DRL | 是遷移未完成，非應有不同業務格式 |
| DRL reference 能否直接取代 | reference DRL UT E2=41.485，但 B2=41000，E 標頭仍為 Bracket FromM；Exception Boundarys F2:G2=46000,40000 | 混合單位與反向來源需 provenance，不可直接覆蓋 |
| ISL E:G 是否漏讀 | ISL UT A2:C698=697筆；E699:G1376=678點；CR289 E699:G729=31普通點、99731–99991m；_point_frame 掃全頁 | 已讀到點資料，不能把普通點首末當實體TL終端 |
| 三個報表欄位 | provider 已在 dirty tree，config 無 approved-intervals sidecar；指定報表欄位已存在 | 正式有效區間缺失，非單純 UI 欄位遺漏 |
| 正值 Stagger | TWL threshold 僅10筆 Right、無 Left；_detect_stagger 查分側threshold，Left gate為NaN | 缺單側配置導致漏執行；應按最新全線對稱規則正規化 |
| Save to Database | 現行共用 catalog 九線，SaveToDBDialog 已用 PARENT_LINES | 先核對測試版本／啟動來源，不能再把現況當兩線hardcoding |
| 約五分鐘斷線 | Vite timeout/proxyTimeout=300000；compare仍在單請求掃描／讀大型ChartData、同步pandas及全量JSON | 高可信效能／proxy線索；無當時backend日誌，尚不能排除程序終止或記憶體不足 |

Stagger 子代理本次直接讀取原始檔的統計（非清洗後列數、非例外數）：

| 檔案 | 原始列數 | 正最大／負最小 mm |
|---|---:|---:|
| 20260907_TWL_UT.csv | 843623 | +270.779／−478.727 |
| 20260630_TWL_UT.csv | 837132 | +500.721／−446.219 |
| TML_D1_260410.datac | 41178 | +621.99／−616.99 |

兩份TWL分別有15895／14597個raw rows至少一通道≥+200；六月檔有25列≥+300。這不等於依Class／Track／分組後的Left數量。指定九月報表Summary本次讀回160筆：Low63、High2、Wear1、Right94、Left0。截圖與此相符，不能只看overview曲線推定各位置的適用門檻。

10/29 batch-04 既有審閱成果記錄382組TL／31組Contact雙端候選，其餘有缺端、多端或scope問題；本次沒有重新生成該批，也沒有把其歷史驗證當本次重跑。

## 3. 可選方案與推薦

| 方案 | 優點 | 代價／風險 |
|---|---|---|
| A 最小修補：複製左右threshold、改選單、加長timeout | 修改少 | 無法處理schema漂移、大型ChartData、單側再缺漏；現行選單已修正 |
| **B 延續typed adapter與現有provider；Stagger共用magnitude；History背景工作與按需圖表（推薦）** | 解決成因、延用現有架構、可分批驗收 | 需版本化契約與工作生命週期測試 |
| C 全面重建metadata管理與History資料平台 | 長期彈性高 | 超出本次範圍，牽涉廣泛DB／UI遷移 |

## 4. Metadata：來源表格、邏輯模型與啟用分離

外部候選workbook參照TOV640的區間欄組；內部沿用typed canonical adapter，不要求所有來源物理排版完全相同。建議候選有Track／Class區間、Brackets點表、Contact TL區間、Landmark點／區間及Review／Provenance。TOV640相容視圖維持 `Overlap FromM/ToM + Overlap + Tension Length` 與 `Landmark FromM/ToM + Landmark`；既有wide來源由adapter讀取，不強迫立即重排全部runtime檔。

| 邏輯實體 | 主要欄位／語義 |
|---|---|
| Context | line、branch/session、direction；DRL branch UT 與 direction UT 分開 |
| BracketPoint | chainage_m、TL、Bracket、classification、wire_role、來源sheet/row/component |
| TLBoundary | Contact／Messenger、BWA／Fixed／Spring、實體位置與角色依據 |
| TLInterval | from_m/to_m、TL、segment、closure、Contact配對／連通依據、approval、source SHA |
| Coverage | 範圍、complete_tl_set、批准scope；完整性與已知TL數量分開 |
| Overlap | 由同位置active核准Contact TL集合導出，保留全部TL |
| Landmark | Point與Interval分開；點不自動延伸為站台範圍 |

沿用現有provider及契約：同點兩條已核准TL可為Y；單TL須完整coverage才可為N；其餘unknown。端點相接只在該點重疊，partial coverage不可擴大。無分型終端為Contact、明確M為Messenger；角色分類不能代替連通配對批准。

DRL延續10/29 review-only候選，先重新核對runtime／reference／TL-BK三方及SHA。只按來源schema轉一次km→m，不以數值大小猜單位。保留runtime Wear L1=8.9與使用者有意調整值；reference9.1差異另列，不藉格式標準化改門檻。DRL Mainline DT缺track sheet、PL方向scope仍需資料依據。核准具體scope後另行備份／promotion／manifest及rollback；本次規劃不自動啟用。

UI／API／Excel保留三個欄位與證據，區分matched、no_approved_interval、outside_coverage、unresolved_pairing、ambiguous；不能把unknown填N或用nearest interval。報表正式值與峰值位置證據的既有語義差異需保留並說明。

## 5. Stagger：共用絕對門檻與方向分類

建立每個context／Class／Track Type／Level的共用非負magnitude threshold。來源可先保留legacy Left／Right表，由adapter正規化：

1. 只有一側：依本次使用者全線規則，將其絕對值作共同門檻，記錄來源側與決策版本。
2. 左右皆有且絕對值一致：合併為單一canonical threshold。
3. 左右衝突、非有限、無法解析：preflight給出workbook／row／情境／level與衝突值，不任選一側；兩側均缺時回缺配置。部分level空白沿用合法缺級政策，不虛構級別。

每列先保留四通道的正側最大與負側最小，以同一magnitude gate獨立判兩側：Left檢查正峰值、Right檢查負峰值絕對值。**不能只選全列abs最大的一個值**，否則同一位置正負同時超限會再漏一側。peak仍保存原始正負號；Left/Right type、SL/SR ID、分組與嚴重級別契約保留。等於門檻的包含政策及L1/L2/L3分類沿用detector契約，由邊界測試固定，不隨正規化修改。

此規則應同時供detector與圖表正負門檻線使用，避免圖表與報表讀不同設定；舊報表不重寫，新分析記錄threshold／algorithm版本。全線盤點先生成語意diff，配置衝突不能被對稱規則掩蓋。

### 判定輸入既有契約差異

目前median模式在reduce_chainage後呼叫detector；DAV-24歷史設計允許此行為。本次提供的AGENTS要求detector、crossing、overshoot、peak與匯出使用完整raw，優先於歷史文件。實作須將**完整清洗後逐筆量測**作本次目標契約，median可留作明確標記的圖表視圖，chart envelope絕不可送入判定。先做獨立raw／median差異報告及演算法版本隔離，不把左右門檻修正與raw政策變更混成同一比較：固定舊輸入測對稱修正，再固定新門檻比較raw政策。History拒絕不同algorithm版本混比；舊報表保留，不靜默重算。此項可能改變例外數量與ID，必須在驗收中獨立呈現。

## 6. History：版本核對、受控工作與分層讀取

先核對Electron／frontend／backend實際啟動來源與build，確認Save選單是否舊版。延用九線catalog與branch/direction adapter，並在暫存DB驗證compare→preview→save→reopen，保留digest、版本衝突、atomic／冪等及分支隔離，不為選單直接改DBschema。

比較採與現有大型分析／匯出一致的背景工作模式，重用可用基礎設施但隔離History工作狀態：建立工作快速回job id；狀態查詢回queued／validating／reading／comparing／ready／failed／cancelled；結果與匯出按job及client session／revision綁定。進度使用可量測file／row／phase，不編造百分比。工作資源有上限、排隊有界、TTL清理、取消、重啟後明確expired、失敗可重試；取消或失敗不覆寫上一成功結果。

讀取順序為小型_Metadata／context與相容性檢查→明確例外表→比較→按需chart。禁止只依黑名單拼接所有sheet：目前新增MetadataEvidence／MetadataBoundaryReview可能混入，應用五類例外表schema registry與明確legacy adapter；未知表略過並留diagnostic，不當例外資料。Summary與分型表不可重複計入。

ChartData避免重複全掃與pandas整表常駐；需要驗證全部scope時在worker串流一次，僅持有必要欄位／索引。比較結果先回Summary／exceptions；圖表overview回有界min/max envelope並保留first/last、extrema、exception chainage及FromM/ToM，選擇例外再取detail window。比較與匯出仍使用完整符合契約資料，不用圖表抽樣。

request id／job id串起階段耗時、rows、RSS、response bytes與例外日誌；前端區分proxy斷線、backend離線、失敗與expired，支援恢復查詢。300秒不再由單次compare連線承擔；只延長proxy timeout不列完成方案。先用日誌辨別實際故障，不將ERR_EMPTY_RESPONSE直接宣稱OOM。

現有LAST_COMPARE_RESULTS／FILES／PARAMS為全域，須由job/session/revision快照取代，否則多分頁匯出仍可能交叉覆寫。RepeatedExceptionFinder以同類型merge產生候選；先profile才決定是否加區間索引，並以現算法作oracle，保留雙峰值均在交集、latest值、首匹配去重及Previous鏈順序，不把效能改寫變成商業判定改變。圖表失敗可獨立重試，不撤銷已完成的比較表。

## 7. 驗收與交付界線

- Stagger全線左右正規化、衝突阻擋、四通道雙側超限、各level邊界；TWL真檔Left可追溯且兩側數值符號正確；TML相容性回歸。
- Metadata點／區間、同點多TL、混合closure、partial coverage、Landmark歧義、來源漂移與promotion rollback；無資料時保留真實缺口。
- History九線分支／方向round-trip、暫存DB冪等／衝突、輔助表排除、跨algorithm/context拒絕、同時工作隔離／取消／過期。
- 大型兩TWL報表比較記錄cold/warm耗時與峰值RSS／bytes；job建立與狀態查詢工程目標各P95≤2秒（本機測試條件固定，非總比較SLA），overview每cycle預設≤5000點。完整比較須成功或給可操作失敗，不能僅spinner等五分鐘。
- Electron真HTTP／舊新版本核對、UI／Excel讀回與raw數值一致；來源與正式DB前後SHA不變。

本回合只交付設計及計畫。三名子代理完成唯讀調查；功能測試、大型compare重現、封裝與資料啟用均未執行。待使用者審閱後才開始開發。
