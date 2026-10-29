# 測試後續開發計畫

- 日期：2026-10-29；Linear：DAV-26（設計審閱），關聯DAV-25／DAV-21。
- 狀態：Draft；**本回合沒有開始功能實作**。
- 設計：`docs/superpowers/specs/2026-10-29-followup-stagger-metadata-chart-design.md`。
- 需求：`docs/requests/2026-10-29-followup-stagger-metadata-chart.md`。

## 1. 執行原則與依賴

先固定來源與重現證據，再完成可獨立驗收的Stagger診斷及圖表；metadata同時完成候選、邊界規則與缺口審閱。正式TL／Overlap填值依賴核准Contact區間，不要求等待全線資料齊備才做其他工作。

```text
P0 基線／版本／來源diff
 ├─ P1 Stagger診斷與真Electron重驗
 ├─ P2 圖表pointer命中、門檻矩陣、hover
 └─ P3 DRL候選＋TL邊界審閱
       └─ P4 核准Contact區間provider＋enrichment
P1/P2/P3/P4各自驗收 → P5 整合、文件與發布前證據
```

使用者已確認TL-BK未必完整、BWA/Fixed/Spring為邊界、C=Contact／M=Messenger、報表用C。不得把全表min/max或C/M同側兩點自動當兩端。

## 2. P0：基線、來源與重現

工作：

1. 記錄git HEAD/status、實際執行backend／Electron來源及build identity；核對是否舊portable或舊服務。
2. 對指定raw／AEL與TWL報表、runtime metadata、mapping建立SHA快照。七份config與release manifest逐格diff；不只因SHA不符就回退使用者修改。
3. 使用codebase-memory目前完整索引探索；較舊短名索引有落後，已refresh `C-Smart-Maintanence-TOV1050_Analyzer`。以磁碟核對實際修正位置。
4. 固定同一分析revision的canonical detection／median樣本基線。區分chart-only envelope與判定輸入；不在本需求中修改已存在的清洗／median政策。
5. 在測試／暫存DB操作；TOV640專案唯讀，兩項既有dirty保留。

產物：source snapshot、當前差異清單、問題重現矩陣（source route／HTTP／Electron分欄）。

完成條件：每個「未重現」列出實際版本與測試入口；前次emit測試不得標作真滑鼠驗證。

## 3. P1：Stagger錯誤分類與前端提示

預計範圍：`calculation.py`／`stagger_metadata.py`既有preflight gate、`useCalculationStore.ts`、`errorMessage.ts`及相關UI。必要才補diagnostics版本資訊。

工作：

1. Electron重上傳指定AEL `_MedianSample.xlsx`及無後綴版本，比較真正後端回應。
2. 正確顯示已辨識line／branch／direction與具體missing_configuration；翻譯繁中，保留可複製原始code及檔名。
3. 保持小表preflight→context→配置gate→ChartData順序；缺配置不掃大型ChartData，不把錯誤包成workbook格式損壞。
4. 只有重現出新parser缺陷才修parser；維持EAL/TML及EAL/LMC分支配置隔離。

驗收：真AEL得到`STAGGER_CONFIG_UNAVAILABLE`及可理解提示；metadata正確但改名、檔名與metadata衝突、未知線、壞workbook分別測試；EAL/TML既有公式結果相同。0.083s只是本次直接route觀察，不作HTTP／UI SLA。

## 4. P2：圖表可獨立交付

預計範圍：`ChartComponent.tsx`、門檻偏好state／型別、Vitest、Playwright真pointer測試。沿用既有MUI／Plotly與配色，不引入新圖表庫。

### P2a 真滑鼠點擊

先建立會真的move/click的重現案例，記錄Plotly送出的points與subplot。覆蓋hover出現前後、線與dot重合、dot邊緣、密集／重合例外、三panel。證實原因後才選擇trace調整或有限像素marker resolver；一般量測線不可選到遠處例外，重合候選需明確選單／列表。

驗收：實際點x後range=x±100m（domain邊緣裁切），三panel與側欄同步；pan後重點同dot仍聚焦；A→B競速、reset／double click、取消／retry與過期response不污染結果。

### P2b 門檻矩陣

三metric×三level選取，沿用實際segments；不存在級別停用。總開關不清細項偏好。完整overview決定availability；放大至無某級區間時不改選項；同session跨Graph/Table與remount保留，新session預設可用項全選。

驗收：只改對應metric/level shapes；多Class／Track及正負Stagger值均保持；無例外仍可顯示門檻；不重送分析、不改detector／匯出；raw overview保持原規則。

### P2c Hover

線及marker皆僅Chainage與實測值，保留m/mm與精度。DOM測試確認沒有來源列、SampleCount、有效樣本、ID或trace extra；payload與Excel provenance不減少。

## 5. P3：DRL標準化候選與Contact邊界推導

預計範圍：既有metadata candidate/review scripts、adapter分類及provenance；必要時新增小型Boundary candidate模組，不重寫整個manager。

### P3a DRL候選

- 三方source diff：runtime long、reference wide、目前TL-BK。
- 明確km/m；修正僅在新候選，保留原值與轉換policy。
- 去除空格式尾列；invalid／conflicting有值列保留audit。
- threshold8.9／9.1逐項審閱，預設不改runtime業務值。
- DRL Mainline DT缺資料、PL方向語意列阻塞，不複製UT資料。
- 產出TOV640相容欄組＋獨立Brackets／Boundary Review；新批次review-only。

### P3b TL候選推導

1. 全部點保留source lineage；termination保留位置及kind，C/M/unspecified分開。
2. 已知Contact端點及同一連通scope唯一配對時產生候選；未分型適用C的問題顯式列review。
3. 普通首末Bracket只作observed envelope。無端／單端不補猜；多端或外側仍有同TL點時列矛盾／分段審閱。
4. 先用CR289、579、487、541、581五案例驗證，再全mapping展開；不得把兩個同側C/M配成假區間。
5. 審閱表含每端點／所有row證據、observed、known boundary、candidate pair、wire_role、scope、完整性、人工缺口、批准欄及規則版本。

產物：候選workbooks、provenance、validation/audit JSON/Markdown、Contact TL邊界審閱表、DRL context能力矩陣、threshold difference decision表。

完成條件：來源→component→候選逐筆可追溯，沒有靜默drop、猜單位、跨方向補點或直接promotion；使用者能只處理具體缺項。

## 6. P4：核准區間接runtime與三欄填值

依賴：部分可用scope的Contact TL配對／閉合政策核准；不要求全線一次完成。

1. 接approved interval provider，保留TLBoundary與未解決候選；capabilities依實際資料及coverage回available／partial／unavailable。
2. 核准TL與Overlap sweep保留point atoms／open spans，端點接觸不擴成有長度overlap；可能有未解析TL時不輸出known non-overlap。
3. Legacy mapper不能直接接open-span atom；加明確containment adapter、端點測試及version。既有first-nonempty群組enrichment保留，不借機更改群組規則。
4. Exception Table／API／Excel一致顯示值、版本及缺口；Bracket／邊界參考獨立可展開，不冒充正式TL值。Landmark沒有核准range仍清楚說明，不推成站台區間。
5. 針對核准scope產生新版報表與before/after；變動限預期enrichment。比較detection type／level／FromM／ToM／peak／ID保持基線，禁止把候選或chart envelope送入detector。
6. runtime promotion另記明批准scope、source/candidate/destination SHA、備份及manifest；單純validator通過不等於核准。

完成條件：核准範圍內三欄有正確值／明確狀態，範圍外不猜；TOV640原有報表與公式通過回歸。未取得的Landmark／TL資料保留獨立缺口，不能宣稱全線完成。

## 7. P5：整合驗收矩陣

| 項目 | 必須覆蓋 |
|---|---|
| ISL sparse資料 | E:G在A:C之後仍678點；CR289=31；physical677＋landmark1；不混入Track intervals |
| mapping | slash、同位多TL、同identity多位置、termination suffix、C/M同側、多端／單端／無端、來源變更與digest drift |
| interval | 單點、只接端點、三TL共段、未解析TL存在時unknown、方向／分支隔離、局部coverage |
| DRL | km只乘一次、wide m不二次換算、反向DN、threshold差異、Mainline DT拒絕、PL scope明示 |
| 圖表 | 真pointer、hover後點擊、三panel、同點重點、trace重合、±100m裁切、九格／缺級別、reset／競速 |
| API／Excel | 同revision／digest、三欄與status一致、provenance完整、舊檔相容、enrichment版本與舊first-nonempty parity |
| 真輸入 | 指定兩份TWL CSV、TML DATAC、AEL Stagger及TWL輸出；資料／門檻前置條件不足明確標阻塞 |
| 環境 | Electron實際上傳／下載及原生Excel；1280×720、1033×640、390×844與Windows DPI；不以fixture Chromium代替 |

實作後預定命令（**本回合尚未執行以下整套**）：

```powershell
venv/Scripts/python.exe -m pytest -q backend/tests/test_dual_system_report_context.py -k stagger
venv/Scripts/python.exe -m pytest -q backend/tests/test_tov1050_capabilities.py backend/tests/test_tov1050_adapter.py
# 新增邊界／provider／enrichment regression加入對應套件後執行
Set-Location frontend
$env:NODE_USE_SYSTEM_CA='1'
npm test -- --run src/components/__tests__/ChartComponent.test.tsx
npm run test:e2e -- tests/dual-system.spec.ts
npm run build
```

Python採專案venv做程式測試；workbook產物依spreadsheet skill使用bundled工具，原始workbook不覆蓋。npm保留HTTPS／strict-ssl，只設程序CA。

## 8. 本回合已做的調查驗證

- 兩個指定對話已read_thread；產品／設計／metadata規則／能力／前次驗收已讀。
- codebase graph refresh成功；舊短名索引落後不作當前行為權威。
- 真AEL小表preflight約0.078s、直接route約0.083s，422 `STAGGER_CONFIG_UNAVAILABLE`。
- 子代理實跑`venv/Scripts/python.exe -m pytest -q backend/tests/test_dual_system_report_context.py -k 'stagger'`：9 passed、26 deselected（12.31s）。
- openpyxl read_only核對指定TWL160筆三欄空白，未讀取ChartData；ISL／DRL／mapping唯讀盤點與manager smoke。
- 本次沒有全套pytest、前端build、真pointer／Electron／Excel人工驗收；上述為後續計畫。

## 9. 下一步與完成定義

使用者先審閱本設計及計畫，批准後執行P0→P1/P2/P3，再按核准資料推進P4。這次批准設計不等同所有TL配對、DRL方向或threshold來源已批准。

DAV-26交付設計後進In Review，Next action為使用者審閱；DAV-21維持metadata實作與資料依賴，DAV-25既有In Review不因新計畫而標Done。每階段實作、測試及阻塞同步Linear。
