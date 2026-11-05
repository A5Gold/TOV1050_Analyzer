# 三個metadata欄位空白：根因、方案與人工決策

日期：2026-11-03。唯讀診斷；未改程式、config、候選或DB。

## 已證實的直接根因

1. npm-dev報表使用 `config/TWL metadata.xlsx`；新wide檔在 `outputs/metadata-review-2026-11-03/other-lines-wide-v1/candidates/`，未作runtime替換。正式方向表仍是Track Type A:C與Bracket E:G點表。
2. **只換檔案也不會解決。** `tov1050_metadata.py:178–182` 的 `get_overlap_intervals`／`get_landmark_intervals`固定回傳空DataFrame；並沒有解析新wide的A:G。基底TOV640 Manager有相應Excel讀取，但TOV1050 override刻意停用。
3. TOV1050補值目前走另一個入口：`ApprovedIntervalProvider`只讀 `<workbook>.approved-intervals.json`；`__init__`發現sidecar不存在即返回空context，`lookup`返回三欄None。正式config沒有這些sidecar，新候選旁也沒有。
4. `analysis.py:670`用這個provider填chart；`:687–691`再按每個例外的`maxLocation`查provider並寫入三欄。故Summary實際資料在匯出前已是None。匯出器只是保留None為空格，並非Excel樣式、欄名或median遺失。

已用當前正式檔與候選檔各自建立manager；154.2m與750m都返回三欄null，且兩個interval getters都為0列。正式及候選SHA未變，結果在diagnosis.json。

候選 `TWL UT` 的TL1實體範圍為10–758m、TL11為747–1477m：154.2m可推TL1，750m可推TL1+TL11與Overlap=Y，但當前loader均讀不到。N的使用仍取決於完整性政策，不能由此次重現自行批准。

因此先前「候選尚未接入」描述不夠完整：runtime已有sidecar區間provider，但**wide Excel→該provider的橋接沒有完成**。這是軟體整合缺口，不應要求使用者靠改Excel欄名解決。

## 三欄各自的資料限制

| 欄位 | 有資料後的預期 | 目前其他限制 |
| --- | --- | --- |
| Tension Length | 對命中位置列出全部有效TL | DRL已確認min/max；其他七檔仍標review候選；ISL有兩個單點TL，TKL有兩筆可疑里程 |
| Overlap | 兩個以上TL同時有效可回Y | 現行provider只有完整coverage確認後，單TL才回N；wide候選的N只表示已列TL集合無重疊，兩者定義不同 |
| Landmark | 根據明確點／區間及例外匹配政策顯示 | TWL／AEL／TCL來源均零Landmark；其他檔55個全為點，不是涵蓋區間。只在峰值精確命中點的政策下，多數例外仍會空白 |

「三欄全空」不應當作三種資料都已經齊備；TWL的Landmark是真正缺來源，即使修好loader也不能自動補名字。

## 格式相容問題：由程式負責

- A:C（Landmark）、D:G（Overlap/TL）、H:J（Track Type）是獨立清單；不能將同列三組資料視為同一實體。
- K `Interval Closed`適用D:E；both代表包含兩端、neither代表不包含兩端。現行通用wide parser硬編both，sidecar v1輸入也只接受both，不能直接把拆好的open spans貼進v1 JSON或當全部閉區間。可用原始TL Boundaries的閉區間重建sweep，或新增可精確讀K的Excel adapter。
- G有多TL（如`1,11`），應解成集合，不能當單一TL名稱。輸出可用`1 / 11`，需一致且排序穩定。
- 空白未知區段應保留未知，不能補N；不應因Landmark／Overlap沒有來源而阻斷有效threshold分析。
- **DRL PL讀錯sheet**：`_wide_context`只回workbook identity與UT/DT，`get_track_type_intervals`把sheet組成`DRL UT`，忽略session=PL。以DRL wide v2實測，Mainline與PL均讀10列UT Track Type；真正DRL PL有7列且範圍42000–44000m，UT是41000–45500m。應讓PL獨立對應DRL PL與其Brackets/context，不要讓使用者重命名PL為UT/DT。
- 報表目前按峰值maxLocation填值；不是整段FromM–ToM內任一命中，也不是最近地標。保留或改變此語義須明示。能力資訊仍標first-nonempty，應一併校正為實際查詢政策。

## 可選修正方案

### 建議：wide Excel是使用者維護入口，程式做標準化轉接

保留現在11欄wide格式及獨立Brackets。開發Excel adapter逐組讀A:C／D:G／H:J，尊重K、公尺單位及line/session/route；轉為同一個型別明確的區間模型再匹配。可沿用既有provider的lookup／sweep／digest，也可由程式自動產生版本化cache；不要要求使用者維護第二份JSON。

先使用隔離config測試，不直接改正式config。經資料確認後才依scope啟用；候選未確認區段保持可追溯unknown。原始偵測、median取樣、例外ID／peak／level不改。測試需涵蓋TL內部、重疊內部、精確端點、域外、單點、多Landmark與DRL UT/PL。

### 替代：由程式把已確認TL Boundaries／Landmark編譯成現有sidecar

改動較少：使用原始TL閉區間重建atoms，附來源SHA與核准紀錄，沿用現有lookup。但仍須處理coverage=N政策、PL context及Excel手修後重編譯；不能只複製候選workbook或手改JSON。若從拆好的D:G反推TL，必須驗證不丟失closure／coverage語義。

## 需要使用者決定的業務規則

1. **其他七檔TL邊界**：是否如DRL，全部採同方向／TL的實體支架min/max（排除明確Messenger及Landmark）？DRL已確認，不需重問；兩個ISL單點TL保留或補支架需另核對。
2. **Overlap=N定義**：採「已提供metadata中當前只有一個TL」；或維持較嚴格的「完整TL集合已確認才可標N」？Y=多個同時有效、資料域外空白可固定。
3. **Landmark顯示**：維持點位精確命中、由使用者填真正涵蓋FromM/ToM、或改為附近最近地標（另需距離上限）？目前程式是峰值查詢，沒有最近地標算法。沒有來源的路線可以保留空白，不能推測。

## 可自行手修的精確位置

候選根目錄：`C:\Smart Maintanence\TOV1050_Analyzer\outputs\metadata-review-2026-11-03\other-lines-wide-v1\candidates`。

| 檔案 | 候選儲存格 | 原正式config儲存格 | 現值m／需核對內容 |
| --- | --- | --- | --- |
| ISL metadata.xlsx | ISL UT Brackets!A665 | ISL UT!E1362 | 113948；超出Class整體域97000–113500，可能是有效域外支架，不直接判錯 |
| TKL metadata.xlsx | TKL UT Brackets!A341 | TKL UT!E377 | 126；TL555會延伸至126–60357 |
| TKL metadata.xlsx | TKL DT Brackets!A207 | TKL DT!E234 | -108；TL570會延伸至-108–62476 |
| ISL metadata.xlsx | TL Boundaries!C18:D18 | 來源ISL UT物理點1359 | TL254只有112865這一個位置，決定保留單點或補來源點 |
| ISL metadata.xlsx | TL Boundaries!C39:D39 | 來源ISL DT物理點1358 | TL255只有112772這一個位置，決定保留單點或補來源點 |

若要將Landmark改成實際範圍，修改各方向頁A=FromM、B=ToM、C=名稱。55筆精確檔案／sheet／儲存格列於landmark-review.csv；例：ISL UT!A2:B2目前100512／100512、C2=SI-211。不要修改同列D:G來配合Landmark，因兩組清單獨立。TWL沒有既有Landmark rows，可在TWL UT／DT A:C輸入實際來源資料；不要求補不存在的資料。

支架更正後需要由程式重新生成TL Boundaries及D:G；這些是快照，不是隨A665變動自動重算的Excel公式。使用者不需手改所有衍生列。資料警告與單點TL不是本次TWL三欄全空的直接根因；TWL也會在目前loader被回傳None。

## 驗收要求

相同有效metadata在Excel與內部區間模型命中一致；TWL154.2m與750m能回對應TL及重疊；精確端點不重複／不擴張；未知、confirmed N、missing Landmark有區別；PL不借UT；例外偵測及median列數不漂移；新報表三欄與API證據一致。Landmark缺來源時允許空白，但需顯示原因。
