# Metadata三欄空白根因與修正方案

- 日期：2026-11-03
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-21
- 負責人：Codex
- 狀態：Done（診斷及方案交付；實作待業務決策）

## 需求與目的

使用者要求解釋Overlap／Tension Length／Landmark空白的根因、潛在解法，並列出需要其確認或手修的格式／資料。先完成唯讀流程追查及具體方案；不修改程式、正式config或啟用候選。

## 現況盤點

已讀PRODUCT.md／DESIGN.md（前輪）、docs/metadata-approved-intervals.md、wide候選request及npm-dev重測readback。正式報表289／330筆三欄全空。Linear MCP可用，已讀回DAV-21，沿用既有業務決策（DRL UT／獨立PL、wear9.1、DRL支架min/max），不重問已確認事項。

## 設計與驗收

以graph探索metadata provider／analysis enrichment／exporter，必要時讀當前未索引程式。唯讀比較正式與wide候選sheet、sidecar、context及里程；用最小資料重現匹配，不重跑兩個大CSV。列明直接根因、次級格式相容問題、程式端責任、資料端決策及精確儲存格。

## 執行紀錄

完成唯讀重現：正式TWL與新wide候選在154.2／750m均三欄None；兩個interval getters均0列；兩側sidecar均不存在；兩workbook SHA前後不變。結果：outputs/validation-2026-11-03/metadata-enrichment-root-cause/diagnosis.json。

已核實analysis.py在670填chart、687–691按maxLocation覆寫例外三欄；不是exporter或median抹掉資料。wide Excel→provider橋接未做，僅換檔無效。TWL／AEL／TCL來源零Landmark，其他55筆全是點。55筆人工儲存格清單輸出landmark-review.csv；data-review.json記錄3筆來源警告與2個單點TL。

新發現DRL PL Track Type誤用UT：候選有DRL UT（10列）與DRL PL（7列），manager對Mainline及PL都回UT10列，根因_wide_context／sheet拼接忽略PL。無需使用者改PL命名或改為DT。

詳細根因、程式定位、兩種方案、3項業務決策及精確手修位置見同output目錄ROOT-CAUSE.md。未改產品程式、正式config、候選或DB。診斷沿用先前報表讀回證據，不重跑大型CSV。graph舊索引行號失準，已用當前檔案核實。

## Linear 同步

DAV-21維持In Progress。Next action：使用者確認其他線min/max、Overlap=N與Landmark匹配政策／修訂來源；開發端完成wide adapter或Excel→sidecar編譯、修PL context，在隔離config驗收後才promotion。

已同步comment c6e12eef-673f-469d-9c40-d69421dfa606。診斷產物只新增本request與outputs/validation-2026-11-03/metadata-enrichment-root-cause目錄；現有dirty程式與config保持不動。
