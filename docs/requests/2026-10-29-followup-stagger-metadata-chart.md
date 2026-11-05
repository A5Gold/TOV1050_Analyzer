# 測試後續：Stagger 診斷、metadata 標準化與圖表互動設計

- 日期：2026-10-29
- Linear project：TOV1050_Analyzer
- Linear issue：[DAV-26](https://linear.app/david-chu/issue/DAV-26)；延續 DAV-25，metadata 依賴 DAV-21
- 負責人：Codex 主代理，metadata／Stagger／圖表三個子代理協作
- 狀態：實作與驗證完成，待資料區間及人工環境審閱；使用者於2026-10-29明確approve設計／開發計畫

## 需求與目的

### 使用者與流程

使用者完成前次雙系統修改後，再次提出 AEL Stagger 上傳錯誤、DRL metadata 清理、Exception Generator 的 Overlap／Tension Length／Landmark 顯示，以及 marker 點擊、分級門檻線與 hover 精簡需求。先讀取指定兩個對話，核對現有來源與實際檔案，再提出可審閱的設計及分階段開發計畫。

### 商業規則與限制

- 設計階段僅文件；使用者approve後授權必要功能實作、測試與review-only候選。原始CSV／DATAC、runtime metadata及使用者DB保持不覆寫；候選不自動啟用。
- 延續九主 Line＋Branch＋Direction；DRL branch UT 對應 Mainline，與方向 UT 分開。
- 前次已確認其他路線 Stagger 未有核准配置；不得套用 EAL／TML 的公式或係數。
- Chainage canonical unit 是 m；點位不能直接當成有效區間，unknown overlap 不等於 N。
- metadata 標準化須先候選、provenance、audit 與批准範圍，不能靜默覆蓋原檔。
- 本次使用者更正：TL-BK 表未必完整，但 BWA／Fixed／Spring 一定是邊界；C=Contact、M=Messenger，報表使用 Contact wire 邊界。先前「完整」回覆已被取代。
- chart downsampling 僅供顯示；不改本次需求外的清洗、median 實測樣本、detector、threshold、peak、ID 或匯出契約。既有文件對 raw／median 基線有歷史差異，實作前須明確核對；不得把 chart envelope 傳入判定。

## 現況盤點

- Git HEAD：15481bbe71c011153ac8fb1a57badc437348a4b3（master）。
- 開始時既有未提交：`00 Reference Document/Raw data/AEL/20260822_AEL_UT_SHO_AWE.csv` modified；`00 Reference Document/~$TOV1050 TL-BK No.xlsx` deleted。全部保留。
- 已讀取兩個指定對話、PRODUCT.md、DESIGN.md、架構、metadata 規則／能力契約、前次計畫與驗收文件。
- codebase-memory MCP 已掛載且已有索引；短名索引發現落後，已以 index_repository(mode=fast) 更新較完整的 `C-Smart-Maintanence-TOV1050_Analyzer`，並核對實際磁碟程式。
- Linear MCP 已實際掛載並成功讀取 DAV-21／DAV-25；不沿用舊工作階段可用性假設。
- ISL E:G 位於 A:C 區塊之後，已有點資料讀取路徑；區間能力不足需獨立處理。
- AEL Stagger 已有 preflight／缺配置錯誤處理；須區分舊程序／舊報表診斷與目前真檔結果。
- ChartComponent 已有 marker ±100m 與 detail 載入；本次須調查實際 hit-test／hover／重點同點操作，並加入 metric×level 個別選取。

## 設計

### 範圍

調查及交付 Stagger、DRL 候選標準化、點／區間 enrichment 與圖表互動的整體設計、實作順序、測試矩陣、資料缺口與下一步。

### 不在範圍

本回合不實作、不啟用 config、不修改 TOV640 專案、不改公式、不封裝發版、不提交原始輸入。

### 資料流與錯誤處理

詳見設計及分階段計畫。建議「終端邊界＋線材角色配對」；普通 Bracket 首末只作觀察範圍。完整無歧義的 Contact 端點配成候選，單端／無端／多端與未分型端點列缺口。只有核准 scope／配對及閉合政策後接 runtime，並從已核准 TL intervals 推導 Overlap；存在未解析 TL 的範圍不可把單一已知 TL 誤當已知非重疊。

DRL 先做 runtime long／reference wide／現行 mapping 三方 diff、單位與方向盤點，特別列明 Wear L1 8.9／9.1 差異；新候選、provenance、audit 不自動 promotion。Stagger 改善結構化繁中診斷；圖表補真滑鼠命中測試、metric×level 門檻選取與兩項 hover。

### 驗收標準

1. 每項回報有現況證據、已確認事實／待驗證假設之區別及可執行修正方案。
2. 明確解釋 TOV1050 點資料如何保存／展示、何時可供 legacy interval 消費。
3. DRL 計畫列明單位、方向／分支、反向區間、coverage、mapping 與 promotion 條件。
4. 圖表計畫涵蓋真 Plotly 點擊、±100m、各 metric 的 L1/L2/L3、hover 與既有非同步防護。
5. 文件完整、Linear 實際同步，功能程式與來源檔維持本回合開始狀態。

## 執行紀錄

### 2026-10-29 設計批准後承接

- 使用者明確回覆approve；不再等待設計批准。Linear MCP已實際掛載，DAV-26轉In Progress並同步承接。
- 本次實作起點4e50d90f175c607cf5a6937c4137f6933dc911dc；既有兩項dirty與前回合相同。
- 依P0–P5推進；三子代理分工圖表／Stagger／metadata候選，主代理整合approved interval provider、API／UI證據與驗證。
- 未分型terminal配對、DRL方向及threshold差異仍依具體資料，不把本次approve視為任意資料promotion。

### 實作

- Stagger：繁中結構化診斷、巢狀 context／missing_configuration、檔名及代碼、可展開及複製 JSON，換檔／cycle／重試隔離。
- 圖表：真 pointer 僅在可見 marker 圓內選取；同位多例外提供明確選單。Height／Stagger／Wear × L1／L2／L3 門檻矩陣，缺級停用、session 偏好保存；hover 僅 Chainage／實測值。
- Metadata：獨立 Contact 邊界審閱 v2、approved interval sidecar provider、SHA／批准／context gate、端點 atoms 與 open spans、partial coverage 不推 N。可選 enrichment 在 median reduction 後填入，保留 detector／ID／first-nonempty。
- API／UI／Excel：例外「依據」視窗顯示峰值位置狀態、已知邊界與來源列；MetadataEvidence／MetadataBoundaryReview 保存證據，不把大型 review JSON 塞進 Excel 單格。Summary 欄序不變；Wear gate 維持。
- 最終候選：`outputs/metadata-review-2026-10-29/batch-04`，兩份 workbook、完整 provenance、audit、來源 SHA、64格 release diff；新 guide、candidate_from_m／candidate_to_m 與 wire_role_basis 明確列出。前批次保留為歷史，不啟用任何候選。
- 契約：`docs/metadata-approved-intervals.md`。沒有 runtime sidecar、promotion、原始資料／正式 config／使用者 DB 寫回；開始時兩項 dirty 保留。

### 使用者補充決策（實作中已納入）

1. 無 `_C`／`_M` 分型的 BWA／Fixed／Spring **全部視作 Contact 邊界**；明確 `_M` 仍為 Messenger。v2 保存 `user_confirmed_untyped_contact_2026-10-29` 角色依據；候選由1增至31組。
2. 沒有核准 AEL 配置，**先 skip 計算**；缺配置診斷及相容性驗證仍交付，不借 EAL/TML。
3. 七份 runtime 相對 release 的64格差異為使用者有意調整，**保留現值**，本次不還原或代改 release manifest。

### 測試與 debug

以下先保留設計調查證據，再列批准後實際驗證；不將舊結果當本次重跑。

```text
# 子代理執行
venv/Scripts/python.exe -m pytest -q backend/tests/test_dual_system_report_context.py -k 'stagger'
9 passed, 26 deselected (12.31s)

# 真 AEL 報表，直接 Python preflight／route
preflight ~0.078s；route ~0.083s
正確 AEL/Mainline/UP（來源UT），422 STAGGER_CONFIG_UNAVAILABLE
缺 approved branch support metadata、approved Keq strategy/coefficients

# 唯讀 openpyxl／manager smoke
ISL UT E:G 678點（physical677＋landmark1），CR289=31點
指定TWL Summary 160筆，三個enrichment欄皆存在而全空
Low Height63／High Height2／Wire Wear1／Stagger Right94
未讀取ChartData；沒有寫入workbook

# codebase-memory
index_repository(C-Smart-Maintanence-TOV1050_Analyzer, fast): indexed
```

批准後實際驗證：

| 驗證 | 結果 |
|---|---|
| provider／capabilities／adapter／median snapshot／report export pytest | 74 passed（61.97s） |
| API analysis／chart data／viewport contract pytest | 31 passed（51.21s） |
| Contact v2／真 mapping／DRL source review pytest | 21 passed；最後 schema／guide 更新後再跑記於整合紀錄 |
| Stagger context＋API pytest | 16 passed、26 deselected，含真 EAL U3 HTTP200 |
| Chart／marker Vitest | 18 passed，真 pointer Playwright 3 passed |
| Stagger 前端四檔 | 16 passed |
| ExceptionTable 證據視窗 | 2 passed |
| TypeScript／production build | exit0；Vite build 4150 modules、成功，既有 assert externalization／大 chunk 警告 |
| DRL／Contact候選 | artifact-tool author/render/error scan；最終逐格 parity 與圖片檢查見 batch-04 |
| 真 Electron AEL 上傳 | 真本機 HTTP multipart，422 STAGGER_CONFIG_UNAVAILABLE；UI 顯示繁中身份／缺項／可複製 JSON，DB 確認隔離 |

實檔 direct `_analyze_sync` 及 TWL 報表讀回：

| 檔案 | raw→median | 例外 |
|---|---:|---:|
| 20260907_TWL_UT.csv | 838859→83963 | 160：Low63／High2／Wear1／StaggerRight94 |
| 20260630_TWL_UT.csv | 830792→83244 | 199：Low66／High7／Wear15／StaggerRight111 |
| TML_D1_260410.datac | 41138→41138 | 152：Wear86／StaggerLeft20／StaggerRight46 |

來源 SHA 前後不變；兩份開發驗證報表位於 `outputs/followup-runtime-2026-10-29/batch-01`，Summary 三欄、證據工作表及隱藏 metadata JSON 讀回成功。這批實檔程序在使用者無分型規則補充前啟動，Review 證據為 v1；detector／門檻／正式空值不因 v2 角色分類改變。最終資料審閱以 batch-04 v2 為準。耗時含分析及大型匯出，不作效能 SLA。

Debug：修正 optional TL 於 reducer 前導致 segment 改變的風險；修正 sidecar 非物件 JSON／來源消失的可理解錯誤；大型審閱拆表避免 Excel 32767字元截斷；既有測試 doubles 對 filename keyword、結構化 wear error、manager 新方法已更新。測試 worker 曾因資源啟動逾時，降為 threads／單 worker 後通過；Electron QA 前三次是誤選 DevTools Page／QA request context 問題，改選 renderer URL及實際 renderer fetch 後成功，未為此改產品。

### 驗收結果

完成已批准的程式實作、三子代理驗證、metadata 候選及實檔／Electron 診斷。最新382組 TL 中31組可列雙端候選、332組無 Contact 終端、15組單端、2組普通點超出配對、2組多端，另9組 DRL direction scope 未明（缺口可重疊）。TL-BK 未必完整，正式 TL／Overlap／Landmark 仍只接核准區間，沒有用候選冒充正式值。原生 Excel、使用者舊 portable、真實圖表於各 Windows DPI 的完整人工驗收未執行；不把 fixture Chromium 當真 Electron 圖表資料驗收。

## Linear 同步

- Linear MCP 實際可用，已同步 DAV-26／DAV-21；收尾同步最新使用者決策、batch-04、實作／測試與限制。
- Issue 狀態：DAV-26 交付後 In Review；DAV-25 不變、DAV-21 維持 In Progress。
- Next action：資料負責人審閱 batch-04 的31組 Contact 配對／連通 scope／完整性及缺端表；DRL方向另確認。取得具體 scope 核准後，開發端才做備份、sidecar／manifest 發布與新版正式報表。現行64格有意調整保留，AEL配置先skip。

## 相關檔案

- `docs/requests/2026-10-29-followup-stagger-metadata-chart.md`
- `docs/superpowers/specs/2026-10-29-followup-stagger-metadata-chart-design.md`
- `docs/plans/2026-10-29-followup-stagger-metadata-chart-plan.md`
- 開始時原有兩項 dirty 完整保留，新增檔案以 git status 收尾核對。
