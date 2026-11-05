# TOV1050 median 報表與 History Compare 設計

- 日期：2026-11-03
- 需求：docs/requests/2026-11-03-drl-median-history-report.md
- Linear：DAV-28；DRL 資料決策 DAV-21
- 決策來源：使用者指定 TOV1050 以 median 報表作 History 輸入；先前已批准的 raw 偵測契約繼續適用。

## 方案比較

| 方案 | 優點 | 缺點 |
|---|---|---|
| A：History 收到完整 raw 報表後重新 median | 不改報表 | 仍需產生／上傳／解析 83 萬列，無法消除主要耗時，且有重算版本風險 |
| B：在 TOV1050 報表入口使用分析時已產生的 median frame（採用） | 縮短 Excel、上傳與 History 掃描；維持同一報表資料鏈；少改既有比較器 | History detail 只具 median 曲線，raw peak 仍需由 Summary／例外表顯示 |
| C：同一報表保留 raw 與 median 兩個大型資料頁 | 可選精度 | 檔案仍大，History scope／cache 與版本規則較複雜，超出需求 |

## 資料契約

分析仍先清洗、映射完整資料，以完整 cleaned raw 執行 detector，並在 session 保存既有 chainage median frame。TOV1050 Exception Generator 報表 Summary／五類分型表只取 detector 的 raw-derived results；ChartData 取 session median frame。獨立 raw CSV 及 raw detail 仍以 source SHA 驗證後重載完整 cleaned raw。TOV640 EAL、TML 的報表 ChartData 繼續走 _export_frame；不要按 analysis_mode 一刀切。

三個報表入口共用 line-aware 選擇函數：背景 report job、GET /export/report、POST /export/report/generate。對有 session 的 TOV1050 median 分析，若 frame 缺失則回明確錯誤；不得用 frontend overview envelope，亦不得靜默重載 raw 到報表。legacy 無 session 的 POST 繼續既有相容處理，但不得宣稱它具備可信 median provenance。

報表 _Metadata 分別寫出偵測算法／資料模式與 ChartData 模式、原始列數、代表列數。既有 detection_algorithm=cleaned_raw_signed_stagger_v1 與 detection_data_mode=cleaned_raw 不變；新 TOV1050 報表的 export_data_mode 明確為 chainage_median。History 的演算法相容性仍比對偵測算法，不把圖表來源模式當偵測算法。舊完整 raw 報表繼續可讀；使用者要取得新效能須由來源重新生成報表。

## 邊界與驗證

- ChartData median 是已完成分析的代表資料，不是前端有界 envelope；報表可以約 8 萬列，而畫面 overview 可以更少。
- History 仍從同一 xlsx 的 _Metadata、例外表與 ChartData 作 scope 驗證、比較及圖表 cache；不新增 raw CSV 輸入或 DB 直接路徑。
- 如 raw 偵測 peak 不恰好落在 median row，例外表中的原始 maxLocation／maxValue 為權威值；圖表呈現須核對 peak 標記語義，不可用最近 median 值覆蓋。
- 測試需覆蓋三個報表入口、raw CSV、TOV640、無 session fallback、source digest，以及兩份 TWL 真檔及 History 性能。
- DRL 正式檔由使用者手修；review-only 候選與 audit 只作參考，未核准區間仍輸出未知。
