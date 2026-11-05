# 其他 TOV1050 路線統一 DRL wide 候選欄組

- 日期：2026-11-03
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-21
- 負責人：Codex；子代理唯讀資料審查
- 狀態：In Progress

## 需求、設計與範圍

使用者要求其他 TOV1050 路線重新生成與 DRL wide 候選相同的欄組，方便查找 Overlap／Tension Length／Landmark。本輪延續已批准的候選生成→人工修訂流程，產生七份 workbook：ISL、KTL、LAR_AEL、LAR_TCL、TKL、TKS、TWL；每份 UT／DT 共14張方向表。EAL／TML不處理；DRL已有新候選，不重寫。

方向頁固定 A:K：Landmark FromM、Landmark ToM、Landmark、Overlap FromM、Overlap ToM、Overlap、Tension Length、Track Type、Track Type FromM、Track Type ToM、Interval Closed。既有支架移至獨立 Brackets 頁，不刪減；threshold、Exception Boundarys、原有audit／provenance及現有人工更正保留。單位沿當前canonical m，不再乘1000。

TL以同路線／方向／TL的實體支架最小／最大里程生成候選；Landmark不參與TL界定，明確Messenger／ambiguous termination不作Contact範圍依據，但在點表原樣保留。其他線的min/max是本次要求生成的review候選，不能冒稱Contact幾何已經逐組核准。單點TL保留且列入review。依TL閉區間sweep建立active TL集合與精確closure，單點atoms closed=both、span=neither。Y為有多TL；N只描述現有點表TL集合，不承諾工程來源完全；域外及空集合維持未知。

Landmark有核實區間時沿原區間；本批來源只有Landmark點，採FromM=ToM保留精確位置，不猜範圍，另保留Landmark Points及來源。主頁A:C、D:G、H:J為獨立清單，列號不代表三者有業務對應。

## 不在範圍

不覆寫正式config、歷史候選、來源mapping或DB；不改detector／threshold／raw-median資料鏈，不生成runtime sidecar，不宣稱新欄組已接正式loader。metadata promotion／runtime enrichment接入另追蹤DAV-21。

## 開發與驗收計畫

1. 記錄七來源SHA及格式，檢查14方向點表分類、原生feature／公式；先讀現有rules與provider，不從label猜分類。
2. 建立可重跑資料提取器，沿用現有分類及provenance；產生TL／Overlap／Landmark候選與新增來源追溯資料。
3. bundled artifact-tool匯入正式來源到新目錄，保留未改工作表與native格式；改寫方向頁，新增分離點表／邊界／說明頁；不動來源檔。
4. 驗證所有未改sheet逐格value／formula parity、14方向Track Type／point multiset parity、TL min/max及每個atomactive集合、Landmark點精確性與來源SHA。
5. 各方向／新增頁render檢視；輸出7份候選、manifest與validation報告，更新Linear及精確手修說明。

## 現況盤點

七份正式來源皆為wide threshold及舊7欄方向頁；有已存在__standardization__、review corrections／acceptances／provenance與interval derivation，須全部保留。現有TOV1050MetadataManager._point_frame已支援獨立Brackets頁並用原provenance分類。

## 執行紀錄

已完成七份候選及14方向頁，輸出 `outputs/metadata-review-2026-11-03/other-lines-wide-v1/candidates/`。使用 bundled artifact-tool 匯入來源並輸出；Python只讀提取／驗證。新增三支腳本：`scripts/prepare_other_lines_wide.py`、`scripts/build_other_lines_wide.mjs`、`scripts/validate_other_lines_wide.py`。

執行prepare、build七檔，再因來源domain警告單檔重建TKL與ISL；最終執行bundled Python的 `scripts/validate_other_lines_wide.py` 全數passed：7 workbooks、294965未改來源cells、14143 points、55 landmarks、373 TL，source_files_unchanged=true、production_activation=false。manifest確認7個不同identity，ISL有1筆、TKL有2筆source_warnings。子代理完成其他metadata唯讀審查；主代理另檢視ISL／TKL Data Review預覽，資料可讀。

需人工核對：ISL UT!E1362=113948（251-027，候選ISL UT Brackets!A665）；TKL UT!E377=126（555-040，候選TKL UT Brackets!A341）；TKL DT!E234=-108（570-017，候選TKL DT Brackets!A207）。三筆超出同方向Class整體domain，保留原值並標示Data Review；TKL兩筆令TL555=126–60357、TL570=-108–62476，受影響範圍尚不能啟用。ISL的域外支架可能有效，不能直接認定錯誤。ISL UT TL254／DT TL255保留單點。

完整手修及語義說明見output目錄README.md。Brackets更正後須重新生成衍生區間。Landmark來源僅有點，無法提供未核實的涵蓋範圍。

本輪變更範圍限上述3腳本、本request及新output目錄。repo已有大量前輪程式、config及資料修改，均保留，不reset、不提交。

最終語法檢查：bundled Python `-m py_compile` 兩支Python腳本及bundled Node `--check scripts/build_other_lines_wide.mjs` 均通過；`git diff --check` 通過，僅既有檔案LF／CRLF提示。已同步Linear comment `bb27ce7d-0fcc-48e2-adb8-a0bac678a340`，記錄生成、驗證、限制及下一步。

## Linear 同步

已驗證本工作階段Linear MCP實際掛載並讀回DAV-21。七線候選生成／驗證完成；Next action：使用者核對3筆來源里程與候選TL範圍，後續完成loader接入／promotion驗收。DAV-21維持In Progress，因正式接入尚未完成。
