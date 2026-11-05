# Wide metadata v3 — 2026-11-05

本版包含 ISL、KTL、LAR_AEL、LAR_TCL、TKL、TKS、TWL、DRL 共8份新候選，16個方向／路線。使用者於2026-11-05批准後，8份已正式啟用；release見 config/tov1050-metadata-release.json。

## 使用規則

- TL：全部實體支架及 Contact termination（BWA／Spring／Fixed）一起取最小／最大公尺里程；明確 Messenger 與 Landmark 排除。
- Overlap：單 TL=N，多 TL=Y，無 TL 未知。D:G 已按端點分段，K 控制 D:E 的 both／neither 開閉端點。
- Landmark：實際涵蓋範圍保留；單點 X 擴成 [X−100,X+100]m。程式不再擴張已具有範圍的資料。
- A:C、D:G、H:J 是獨立清單；同一列不表示資料互相對應。
- DRL 維持 UT 與獨立 PL，沒有 DT；既有 9.1 wear 門檻保留。

## 已納入的手修資料

| 原候選位置 | 修訂里程 m | 重算 TL 範圍 m |
|---|---:|---|
| TKL UT Brackets!A341 | 60316 | TL555：59442–60357 |
| TKL DT Brackets!A207 | 62208 | TL570：61902–62476 |
| ISL UT Brackets!A665 | 112948 | TL251：112180–113139 |

不需再手改衍生的 TL Boundaries、主頁 D:G 或 Data Review。原 Brackets 及 Landmark Points 保留，歷史 provenance／audit 保留為轉換紀錄；Rules 2026-11-05 列出本版輸入候選與最新 mapping 的 SHA256。

## 驗證與限制

8檔已完成未改頁逐格及公式比對、來源 SHA 不變、更新欄組讀回、16個 route provider 區間查詢、Landmark 不重複擴張及 DRL PL／UT 獨立區間驗證。結果見 validation.json。

本批TWL／AEL／TCL／DRL候選沒有Landmark區間，維持空白；其他線也只在有來源且命中涵蓋區間時補值。共55筆Landmark範圍；TKL／TKS有16組不同名稱交集，位置及候選儲存格列在LANDMARK-REVIEW.md。使用者已確認多地標同時命中時顯示全部不同名稱，以「 / 」分隔，不需修改這些重疊儲存格。Wear 計算授權限制不因本版 enrichment 解除。

實際 TWL 報表及 History Comparison 隔離驗收輸出位於 outputs/validation-2026-11-05/wide-enrichment；完整執行結果見需求紀錄 docs/requests/2026-11-05-wide-metadata-enrichment-rules.md。

20260907報表289筆全部有TL／Overlap；20260630報表330筆中329筆有值。剩下一筆`20260630_TWL_UT_Mainline_SL97`峰值2853.8m，位於TL17末端2853.5m與TL19起點2854m之間的0.5m空隙（TWL UT!D21:G21，K21=neither），因此按已確認規則維持未知。這不是loader失效，不自動把空隙延長成任一TL；如要補滿，需要先確認工程涵蓋區間。

正式啟用完成：一般 npm run dev 現使用本版8份config。原檔及舊release備份於 config/backups/2026-11-05-wide-v3-activation-01；啟用及真UI smoke證據位於 outputs/metadata-activation-2026-11-05/wide-v3。候選與validation保留原始審閱紀錄，未更動核准xlsx內容。
