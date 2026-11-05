# 測試後續設計：Stagger、metadata 邊界與圖表互動

- 日期：2026-10-29；狀態：已approve並完成程式實作／驗證，區間資料promotion另依scope批准。
- 追蹤：DAV-26；延續 DAV-25，metadata 依賴 DAV-21。
- 需求：`docs/requests/2026-10-29-followup-stagger-metadata-chart.md`。
- 計畫：`docs/plans/2026-10-29-followup-stagger-metadata-chart-plan.md`。
- 現況基線：master `15481bbe71c011153ac8fb1a57badc437348a4b3`。三名子代理完成 Stagger／metadata／圖表唯讀調查。

## 1. 本次確認的業務規則

**實作後補充（優先於下文早期審閱假設）**：使用者確認無C/M分型的BWA／Fixed／Spring全部可視作Contact邊界，明確M仍為Messenger；AEL計算配置先skip；64格runtime差異為有意調整，保留現值。Contact審閱v2及最終batch-04依此產生31組候選。角色確認不等於所有連通／scope／coverage均已批准；正式provider契約及交付結果見 `docs/metadata-approved-intervals.md` 和本次request。

使用者在本次對話依序更正及確認：

1. TL-BK 表**未必完整**；先前回覆「完整」已由使用者更正，不得沿用。
2. BWA／Fixed／Spring **一定是邊界**；不再把這類位置當成僅有觀察證據的普通 Bracket。
3. `_C`=Contact wire、`_M`=Messenger wire；Exception Report 使用 **Contact wire** 邊界。
4. 先討論如何由 Bracket 推導邊界；沒有批准把全部 TL 的 Bracket min/max 當正式有效區間。
5. 前次已決定其他線 Stagger 尚無核准配置，先給明確缺配置提示；本回合沒有變更該決策。

「終端位置確定」不代表「兩端已齊全」或「任何兩個終端可配成同一條 Contact wire」。來源缺端點時應保留已知邊界與缺項，不能用一般 Bracket 補出另一端。

## 2. 調查結果與證據

### 2.1 Stagger

目前 `upload_stagger` 已先讀小工作表、解析 ReportContext、檢查 line/branch 配置，再讀大型 ChartData。指定 AEL 報表實測識別 AEL/Mainline/UP，來源 UT、Task U3、SHR→AWE；直接 Python route 約0.083s，回422 `STAGGER_CONFIG_UNAVAILABLE`，缺核准支撐 metadata 與 Keq strategy/coefficients。

舊的空白 `Unsupported stagger line:` 本次未重現。舊 backend／portable 是待驗證假設，尚未核對使用者當時程序，不可宣稱已證實。現有前端能顯示英文 message，但未專門整理巢狀 context／missing_configuration。

程式：`backend/app/api/endpoints/calculation.py:592`、`backend/app/core/report_context.py`、`backend/app/core/calculation/stagger_metadata.py`、`frontend/src/store/useCalculationStore.ts`、`frontend/src/api/errorMessage.ts`、`config/line_catalog.json`。

### 2.2 三個 enrichment 欄

指定 TWL 報表 Summary 有160筆，Overlap／Tension Length／Landmark 三欄**存在而全部空白**；分頁63 Low Height、2 High Height、1 Wear、94 Stagger Right也相同。hidden capabilities記錄1176個 bracket points，但TL／Overlap／Landmark intervals均unavailable、overlap_state=unknown；不是Excel漏掉欄位。

ISL UT A:C有697筆（rows2–698），E:G有678筆（rows699–1376）；manager讀出677 physical bracket＋1 landmark。現有 `_point_frame` 掃描全頁，不會在A:C結束時停止。CR289有31點，99731–99991m。缺的是從點資料建立可用區間的業務政策及provider，而非再修一次尾段讀取。

程式：`backend/app/core/tov1050_capabilities.py`、`backend/app/core/tov1050_metadata.py`、`frontend/src/components/ExceptionTable.tsx`。現有 capability 對三種interval固定unavailable；已有核准區間sweep純函式但未接runtime。

### 2.3 DRL

| 來源 | 已核實問題 |
|---|---|
| runtime `config/DRL metadata.xlsx` | 舊long；UT10段41000–45500m、PL7段42000–44000m、Tunnel40000–46000m；大量格式空列；缺DT頁、Bracket及provenance |
| reference `00 Reference Document/config/DRL metadata.xlsx` | wide A:C為m，但E:G Bracket FromM仍含41.485這類km值；DN boundary46000→40000；不能直接複製啟用 |
| threshold來源差異 | reference Tunnel/Curve Wear L1=9.1，runtime=8.9；必須個別審閱，格式清理不得改門檻 |
| 現行共用TL-BK | DRL UT214筆、PL80筆；Location為km。UT／PL是分支標記，不足以證明對應UT／DT方向 |
| 版本／digest | ISL現檔SHA與2026-10-23 release批准SHA不同；須做逐格語意diff，不把byte drift直接判成資料錯誤，也不能沿用舊批准digest |

DRL UT仍有487-001／002（mapping rows198／199）；不得沿用歷史audit推定它們已刪除。reference缺現行487-004–007／BWA，候選必須依目前來源逐列重建。

### 2.4 圖表

`ChartComponent.tsx` 已有±100m、domain裁切、再次聚焦與session/revision防護。marker／量測線皆scattergl，handler只接受exception-marker。截圖hover命中height1量測線；是否阻擋點擊尚未證實，需查實際事件及trace命中。

前次 `frontend/tests/dual-system.spec.ts:76–79` 是 `gd.emit('plotly_click',...)`，未實際滑鼠命中；只能證明handler串接，不能證明hover／hit-test正常。

目前門檻只有一個布林總開關。後端實際提供Height L1/L2、Stagger L1/L2/L3、Wear L1/L2；不得為畫面九格自行創造Height/Wear L3。

## 3. Bracket推導邊界的方案比較

| 方案 | 優點 | 限制／決定 |
|---|---|---|
| 同TL所有Bracket取min/max | 容易涵蓋已有點、可快速產生觀察範圍 | 表未必完整，首末點不一定是邊界；只作observed envelope，不能直接啟用 |
| **終端邊界＋線材角色配對（建議）** | 使用本次已確認業務證據；保留C/M及來源；缺端點可清楚列出 | 完整、無歧義的Contact配對才形成區間候選；單端／無端／多端留缺口 |
| 全部人工提供FromM/ToM | 可處理缺失與複雜分支 | 維護成本高；只用於前方案無法唯一解析的TL或例外，不要求重填所有已知點 |

建議把自動化集中在分類、單位、排序、候選配對、矛盾檢查與Overlap sweep；人工只補缺端點、歧義配對及來源門檻差異。不得以nearest bracket、相鄰TL中點、固定延長距離填空。

### 3.1 真實案例

以下為本次mapping唯讀盤點，位置已換成m；不是已批准的完整interval：

| Context／TL | 證據 | 候選處理 |
|---|---|---|
| ISL UT／CR289 | 31點99731–99991，無termination | 保存觀察範圍；兩端待補。下一個CR291首點99997，6m間隔保持未知，不自行在99994切段 |
| TKL UT／579 | BWA63302（row145）、64561（row58）；70點都在中間 | 最適合提出雙端候選63302–64561；無分型終端的Contact適用性列明配對依據供審閱 |
| DRL UT／487 | 普通首點44871，BWA45026（row215） | 45026是已知邊界；44871僅是觀察首點，不能充作另一端 |
| TKL UT／541 | BWA_C56012、BWA_M56014；普通Bracket延至54956 | C/M不是兩端，不能產生56012–56014的假TL；報表保留C邊界，M另存；另一端待補 |
| TKL UT／581 | BWA_C64501、BWA_M64504、未分型BWA65633 | Contact候選優先C，M不混入；未分型另一端需核對適用線材，不靜默配對 |

不同TL同位置是點上多TL證據，並不自行確立整段overlap；沒有精確同位點也不代表沒有區間overlap。

### 3.2 邊界推導規則草案

1. 按line＋branch＋direction＋TL隔離；原始mapping sheet／track標籤另保留，不跨方向補資料。
2. slash拆分每個component，保留所有同位多identity；km乘1000一次。canonical m及精度沿現有契約。
3. BWA／Fixed／Spring及既有已確認`_` subtype是邊界證據；保留raw label，跨位置同名termination使用既有位置suffix，不能合併成一筆。
4. 線材role：C→contact、M→messenger、無分型→unspecified；既有其他subtype不得猜role。未確認格式不擴大regex。
5. 明確Contact兩端＋同一scope、方向、線材連通關係，可形成`termination_bounded_candidate`。必須核對普通點是否在兩端內、是否另有termination／branch／chainage reset。未分型端點不能單憑名稱當C；列人工role／配對欄。
6. 單端、無端、多端／中間Fixed、單點TL分別列review原因；多端可拆成多個連通segment，不能直接取最外兩端跨過中斷。固定最大gap也不作自動切分規則。
7. 審閱表明列known_from/to boundary、observed_from/to、候選pair、wire_role、缺口、全部source rows、approved_from/to/by、配對／邊界政策版本。已確認的termination不再要求逐個重新證明「是否邊界」，只審閱尚未確認的role／連通／另一端。
8. 只有核准配對／scope及閉合政策後，區間provider才供runtime使用。提出沿用closed-both輸入及獨立endpoint atoms，需由本設計批准及契約測試固定，不任意加減0.1m。
9. 已核准TL intervals以active TL集合掃描Overlap。多TL為overlap、單TL為known_non_overlap；若該範圍仍有未解析TL可能進入，完整性未確認，Overlap仍標unknown／partial，不能只憑目前唯一已知TL就輸出N。
10. 僅端點相接保留point overlap，不延伸成非零長度共段；Landmark point與interval獨立，不由TL終端推測站台範圍。

## 4. 共用資料結構與相容性

延伸現有typed adapter，不另建繞過TOV640驗證的旁路。

| 資料 | 必要欄位／責任 |
|---|---|
| Context | canonical line、branch/session、direction；保留source labels，DRL branch UT=Mainline與direction UT分開 |
| BracketPoint | chainage_m、TL、Bracket、classification、wire_role、原始source及component lineage；已存在結構增量擴充 |
| TLBoundary | termination位置、kind、wire_role、rule確認狀態、source；可獨立於完整interval存在 |
| TLInterval | TL、segment_id、from/to_m、wire_role=contact、scope、端點source、pairing policy、approval／digest |
| OverlapInterval | active_tls、state、closed、完整性／scope、source intervals；保留endpoint atoms及open spans |
| Landmark | 點與區間分開；每類能力、來源、匹配狀態獨立 |

候選workbook延續TOV640相容欄組，另外用Brackets／Boundary Review保存原生點及候選；不把unknown文字或候選觀察範圍寫成正式numeric interval。TOV640既有reader仍讀原欄組；TOV1050 adapter消費typed欄位。

provider將目前固定unavailable改為實際可用／partial／unavailable；另外保留每位置狀態`matched / no_approved_interval / outside_coverage / unresolved_pairing / ambiguous`，不能用全sheet available掩蓋局部缺口。

UI保留正式Overlap／Tension Length／Landmark三欄，顯示已匹配值或具體缺口；提供可展開的Bracket／已知邊界／觀察範圍證據。正式TL不能混入「候選TL」。API與Excel記錄相同enrichment版本、context及metadata digest；diagnostics可獨立工作表，不刪來源。

維持`first-nonempty`的既有群組enrichment契約；不得在本次格式轉換中偷偷改成peak或整段TL全集合。如果物理候選跨度造成新值，需以新metadata版本驗證預期diff，detection／ID／peak須維持既定基線。

## 5. DRL標準化設計

採新日期批次 `outputs/metadata-review-2026-10-29/<新批次>/`，產出候選workbook、provenance、source逐列diff、audit、能力／coverage矩陣及TL邊界審閱表。

先做三方比較：runtime long、reference wide、最新共用mapping。清除尾端格式空列與一致化欄組只作用候選；有數值／標籤的invalid row不可刪除。明確記錄column unit，reference的混用Bracket FromM須以mapping來源重建，不能用數值大小猜轉換。

DRL UT分支→Mainline映射已知，但Mainline DT缺資料、PL方向是否可共用仍未確認。候選按實際可支持context列能力，不能複製UT造DT。threshold8.9／9.1差異列業務decision，預設保留runtime規則，不因schema換版改值。

先稽核七份runtime metadata與release manifest差異，建立當前快照及逐格diff，勿直接還原舊檔。promotion需明確批准workbook、context、threshold版本、區間範圍與digest，備份及可回復manifest；本次設計回合不啟用。

## 6. 圖表互動設計

### Marker

先用真正pointer move→hover→click取證（curve/customdata、像素、hoverlayer pointer-events、range、detail request），不能以emit替代。若證實trace搶命中，再調marker trace／hit radius；必要時限同subplot、可見marker、有限像素距離解析，多個候選以明確列表選取。禁止全域nearest chainage誤選。

點擊實際marker x，三panel同步到x±100m並按domain裁切；側欄同步；平移後重點同一marker仍聚焦。保留快速A→B取消、session/revision guard、reset、retry、raw detail timeout與resident overview。不把hover精簡當作已解決hit-test的證據。

### 門檻面板

工具列「門檻線」保留總顯示開關，旁有可展開Popover；三列Height／Stagger／Wire Wear，各有L1/L2/L3 checkbox。缺配置停用並註「未配置」；目前Height/Wear L3停用。總開關暫時遮蔽，不抹掉細項偏好。

狀態為metric×level矩陣；只filter後端同revision的threshold_segments，不重算值、不鏡射Stagger、不改detector或Excel。完整overview決定availability；detail窗無某級別不代表未配置。每analysis session保留偏好；縮放、選例外、reset不清除，新session預設全部實際可用級別開啟。raw overview維持未分析時不顯示threshold。

### Hover

量測線與marker統一只有兩項：`Chainage: … m`、`實測值: … mm`，保留目前小數精度；`<extra></extra>`隱藏trace name／ID。來源列、SampleCount、有效樣本仍保留payload／provenance／export／診斷，僅移出hover。

## 7. Stagger診斷設計

先核對實際啟動的backend來源／build identity與目前HEAD，利用既有diagnostics能力，確有不足才補必要版本資訊。真Electron上傳重驗舊錯誤；source正常部分不重寫parser。

`STAGGER_CONFIG_UNAVAILABLE`前端改繁中：「已識別AEL／Mainline／UT；缺核准支撐資料及Keq係數，暫停計算」，保留檔名與可複製詳細診斷。身份衝突、未知線、缺公式與workbook損壞各自分類。其他線沒有核准公式時不啟用計算，也不把DRL／TL資料整理當作Keq已具備。

## 8. 驗收及決策邊界

- 本回合交付設計／計畫；待使用者審閱後再實作。
- 已確認規則直接納入，不再對「termination是邊界」「C/M角色」「Stagger缺配置」重複索取許可。
- 單端／無端TL、未分型terminal角色／配對、DRL方向與門檻差異仍需具體資料；先完成候選／缺口與不依賴它們的圖表／診斷工作。
- 來源當前SHA及後續promotion分開；任何來源變更重算diff，不套用舊approval。
- 不改原始raw、TOV640專案或正式DB；不封裝、不發版、不把先前測試當本次重跑。
