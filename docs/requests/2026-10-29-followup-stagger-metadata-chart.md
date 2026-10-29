# 測試後續：Stagger 診斷、metadata 標準化與圖表互動設計

- 日期：2026-10-29
- Linear project：TOV1050_Analyzer
- Linear issue：[DAV-26](https://linear.app/david-chu/issue/DAV-26)；延續 DAV-25，metadata 依賴 DAV-21
- 負責人：Codex 主代理，metadata／Stagger／圖表三個子代理唯讀調查
- 狀態：Draft；本次只交付設計與開發計畫，未授權功能實作

## 需求與目的

### 使用者與流程

使用者完成前次雙系統修改後，再次提出 AEL Stagger 上傳錯誤、DRL metadata 清理、Exception Generator 的 Overlap／Tension Length／Landmark 顯示，以及 marker 點擊、分級門檻線與 hover 精簡需求。先讀取指定兩個對話，核對現有來源與實際檔案，再提出可審閱的設計及分階段開發計畫。

### 商業規則與限制

- 本次不修改功能程式、原始 CSV／DATAC、runtime metadata、使用者 DB；不產生或啟用新 workbook。
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

### 實作

已新增需求、設計與開發計畫三份 Markdown；功能尚未實作，未產生候選 workbook，未修改 runtime config、raw 或 DB。

### 測試與 debug

已執行唯讀來源與 workbook 結構調查；不把前次測試結果宣稱為本次重跑。

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

調查用 manager smoke 與 openpyxl 盤點由三名子代理／主代理於本回合實跑；非完整 pytest／validator。此次沒有重跑前端 build、真 pointer、Electron或原生Excel，均列後續驗收。

### 驗收結果

已完成指定對話、檔案與目前程式調查，完成根因／假設區分、方案比較、使用者更正後的邊界規則、分階段工作與驗收矩陣。Stagger舊空白line錯誤本次source未重現；實際使用者程序版本仍待核對。設計待使用者審閱，不宣稱功能問題已修復。

## Linear 同步

- 最後同步時間：2026-10-29，本次已實際建立 DAV-26；收尾更新設計、使用者確認、測試結果與 next action。
- Issue 狀態：設計待審；DAV-26 收尾轉 In Review，DAV-25 保留 In Review、DAV-21 保留 In Progress。
- Next action：使用者審閱設計／計畫；批准後執行 P0 基線與版本重現，再推進可獨立驗收的 Stagger／圖表／metadata 候選。
- 阻塞／需要決策：無／單端 TL、未分型 terminal 的 Contact 適用性、連通配對、DRL方向及8.9／9.1門檻差異仍需來源／審閱；已確認termination是邊界與C/M角色不重問。

## 相關檔案

- `docs/requests/2026-10-29-followup-stagger-metadata-chart.md`
- `docs/superpowers/specs/2026-10-29-followup-stagger-metadata-chart-design.md`
- `docs/plans/2026-10-29-followup-stagger-metadata-chart-plan.md`
- 開始時原有兩項 dirty 完整保留，新增檔案以 git status 收尾核對。
