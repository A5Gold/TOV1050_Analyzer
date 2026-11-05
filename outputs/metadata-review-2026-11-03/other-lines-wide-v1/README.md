# 其他 TOV1050 線路 wide metadata 候選

日期：2026-11-03。七份候選位於 `candidates/`，供人工檢查及修訂；尚未啟用到正式程式。原始 config、mapping、DB 及既有候選均未被本輪覆寫。

## 檔案與內容

| 檔案 | UT／DT TL 組數 | UT／DT Landmark 點數 |
| --- | --- | --- |
| [ISL metadata.xlsx](candidates/ISL%20metadata.xlsx) | 19／28 | 1／2 |
| [KTL metadata.xlsx](candidates/KTL%20metadata.xlsx) | 27／30 | 4／1 |
| [LAR_AEL metadata.xlsx](candidates/LAR_AEL%20metadata.xlsx) | 47／49 | 0／0 |
| [LAR_TCL metadata.xlsx](candidates/LAR_TCL%20metadata.xlsx) | 41／42 | 0／0 |
| [TKL metadata.xlsx](candidates/TKL%20metadata.xlsx) | 19／19 | 22／19 |
| [TKS metadata.xlsx](candidates/TKS%20metadata.xlsx) | 4／4 | 1／5 |
| [TWL metadata.xlsx](candidates/TWL%20metadata.xlsx) | 22／22 | 0／0 |

EAL／TML屬TOV640，本輪不處理；DRL沿用先前wide候選。TKS是TKL session；AEL／TCL保留LAR檔名。

## 主頁欄位與使用方式

每張方向頁採用相同11欄：

| 欄 | 內容 |
| --- | --- |
| A:C | Landmark FromM、Landmark ToM、Landmark |
| D:G | Overlap FromM、Overlap ToM、Overlap、Tension Length |
| H:J | Track Type、Track Type FromM、Track Type ToM |
| K | Interval Closed，描述D:E區間端點 |

三組是獨立清單，同一列不代表Landmark、TL與Track Type互相對應。所有里程單位為公尺。

支架資料完整移到各方向的 `... Brackets` 頁。`TL Boundaries` 記錄同方向／TL的實體支架最小／最大里程；明確Messenger／ambiguous termination及Landmark點不參與Contact TL邊界。其他線的min/max本輪仍是review候選。原有threshold、Exception Boundarys、provenance及人工修訂資料均保留。

D:G按active TL集合切分；多TL為Overlap=Y，單TL為N，空集合維持未知。N僅表示現有TL集合沒有重疊，不代表工程資料完整核准。單點區間採both，兩端之間的開區間採neither，避免同一端點重複歸屬。

55個Landmark來源全為點位，FromM=ToM；不猜測涵蓋範圍。同名不同位置保留為不同點。沒有Landmark來源的方向留空，不以支架名稱補造。

## 請人工核對的3筆來源值

以下來源均在 `C:\Smart Maintanence\TOV1050_Analyzer\config`；請先核對候選，再決定正式來源修正。原值保留，workbook的 `Data Review` 頁及受影響D:G區間已標示。

| 來源檔／工作表／儲存格 | 支架 | 現值 m | 候選修訂位置 | 影響 |
| --- | --- | --- | --- | --- |
| ISL metadata.xlsx／ISL UT／E1362 | 251-027 | 113948 | ISL UT Brackets!A665 | 超出Class整體範圍97000–113500；核對是否為邊界外實體支架及TL251範圍 |
| TKL metadata.xlsx／TKL UT／E377 | 555-040 | 126 | TKL UT Brackets!A341 | TL555候選變成126–60357，超出Class整體範圍54500–66000 |
| TKL metadata.xlsx／TKL DT／E234 | 570-017 | -108 | TKL DT Brackets!A207 | TL570候選變成-108–62476，超出Class整體範圍54500–66000 |

候選中的衍生區間是生成時快照；更正Brackets後須重新生成TL Boundaries及D:G，不能只改一個點就視為已完成所有修訂。ISL UT TL254、ISL DT TL255各只有一個實體位置，保留單點，不自行擴張。

## 驗證與下一步

七份檔案、14張方向頁全部通過驗證：294,965個未改來源儲存格逐值／公式比對；14,143個點、55個Landmark、373組TL完整保留；Track Type、來源row、TL min/max、active TL集合及端點closure一致。來源SHA未變，manifest維持七份。方向頁及新增工作表已render檢視；ISL／TKL的Data Review可讀。

下一步：人工核對以上3筆、單點TL及候選區間；修訂後重新生成並驗證。正式採用另須完成loader對Interval Closed、TL與Landmark語義的接入及enrichment驗收。目前新增欄位不代表Exception Report已自動採用。
