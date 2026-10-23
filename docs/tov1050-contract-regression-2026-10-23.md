# TOV1050 契約與能力驗收紀錄（2026-10-23）

追蹤 DAV-20／DAV-21；本次可獨立交付的程式及審閱產物完成，跨線現場驗收與核准 TL geometry 尚未完成。沒有發布 portable，也沒有啟用新候選。

## 固定基線與比較方式

TOV640 固定 commit：`cbca528f090152ec2c776ee04a4c30f0d371810f`。執行前驗證 HEAD 與實際載入的 analyzers、metadata、data_ingestion、exporter 四個 core 檔案等於固定版本（容許 CRLF 差異）；其他並行工作修改保留，本次沒有寫入 TOV640。

`tov1050_contract_worker.py` 分程序只載入一個 repo，以相同 canonical 量測、metadata workbook、context 執行 detector 及實際 Excel exporter。比較每個 exception type 的全部欄位、列順序／grouping、level、FromM／ToM、maxValue／peak、ID、boundaries 及全部 report sheets／ChartData。數值 `atol=1e-9, rtol=0`；字串、ID、欄序精確。證據以無損 `.json.gz` 保存。

| 測例 | 實際結果 | 證據限制 |
|---|---|---|
| canonical 升序／default ID | 五類例外皆非空，比較通過 | synthetic，非現場驗收 |
| canonical 降序／custom ID | 五類例外皆非空，比較通過 | synthetic，非現場驗收 |
| canonical isolated levels | 五類例外皆非空，涵蓋 L1/L2/L3，比較通過 | synthetic，非現場驗收 |
| EAL DN 真 datac | 54,057 rows、585 exceptions；detector／report 全欄值比較通過 | EAL 單一 fixture；沒有 TML 真 datac |

證據：`outputs/contract-regression-2026-10-23/batch-02/contract-results.json` 的 canonical／legacy 節點。該檔的早期 real matrix 已由 **batch-05** 取代，不得沿用其缺口數量。EAL fixture：`TOV640_Analyzer/docs/test data/EAL/Cycle 8/EAL_D1_260610.datac`。TML 盤點無真 datac，標記 blocked；既有 EAL/TML 程式路徑保留並經相關測試，不能據此宣稱 TML 現場 parity。

大型 TOV1050 report 改用 write-only ChartData writer，保留 legacy Summary／exception 的欄位和值，不改 enrichment。`streaming-parity/results.json` 的四組測例再次與固定 TOV640 證據全欄比較通過。50,001 rows 完整輸出及 EAL 大檔仍選 legacy writer 另有測試。

## 真實 CSV 與完整匯出

完整 detection goldens 位於 `outputs/contract-regression-2026-10-23/fixture-goldens/`。三份來源均重新讀取；class／track mapping uncovered rows 均為 0。NOT_PROVIDED 是 KTL/TKL 匯出測試的缺省站名標籤，沒有猜測站點物理範圍。

| context | 原始 rows | 清洗保留 rows | 真實 exceptions |
|---|---:|---:|---|
| AEL/Mainline/UT | 476 | 276 | 0；不能作 peak／level／ID 現場證據 |
| KTL/Mainline/UT | 863,661 | 830,606 | Low Height 99、High Height 5、Stagger Right 56（160） |
| TKL/Mainline/DT | 502,022 | 501,211 | Low Height 19、Wire Wear 1、Stagger Right 49（69） |

最終 API／report／raw export 結果：待 batch-05 完成後填寫。

檢查方式：送出僅一列 chart payload 但以 session raw frame 產生匯出，驗證未使用畫面 downsampling。ChartData 以 read-only reader 逐列／逐欄核對全部數值與字串，Summary 與 API 全部 exception records 逐值核對；raw CSV 全部共有數值欄與清洗 frame 核對，`atol=1e-9, rtol=0`。大型匯出完整驗證後只保存 byte count、SHA256、Summary、golden 與 checkpoint，不提交巨大產生檔或原始使用者 CSV。

## Metadata 能力與審閱

正式證據：`outputs/metadata-capabilities-2026-10-23/batch-02/`。

| 能力（18 contexts） | available | unavailable |
|---|---:|---:|
| thresholds | 18 | 0 |
| class_intervals | 18 | 0 |
| track_intervals | 17 | 1（DRL/Mainline/DT） |
| bracket_points | 14 | 4（DRL/PL為long schema） |
| landmark_points | 8 | 10 |
| tension_length_intervals | 0 | 18 |
| overlap_intervals | 0 | 18 |
| landmark_intervals | 0 | 18 |

本批無 partial context；partial 狀態仍有程式支援。unavailable point records 不表示現場沒有該實體，available intervals 也不表示全線覆蓋已驗收。

- `metadata-capability-matrix.csv`：18 contexts × 8 能力，區分 available／partial／unavailable。已確認無 overlap 與未知 overlap 不能混為一談；目前 overlap_state=unknown。
- `tl-boundary-review.csv`：373 physical TL groups，保存來源 workbook／sheet／Excel row、termination 與 observed boundaries，另留空白 approved boundaries／approval。2 個單點群組：ISL UT TL254 112865m（mapping row656）、ISL DT TL255 112772m（row806）。
- 324 組沒有 termination、11 組有1個、28 組有2個、8 組有3個、2 組有4個（共99點），不構成整批 observed envelope 已獲核准的證據。
- 七份相容候選與獨立 Brackets 頁逐格讀回通過，保存14,143點。原 config／已批准候選未覆寫；來源漂移0。TL／Overlap／Landmark interval 欄組維持空白，Capabilities 首頁標 review-only；不得直接啟用。
- 七份批准 batch-04 候選重新 validator：全部 pass、findings0；本次證據在 `batch-01/validation/`，此處 batch-01 僅採用 validation，不採用其草稿 workbook。
- DRL／PL 獨立盤點：不在七份批准 batch-04；現存4 sheets，缺 Mainline DT track type，PL方向語意未確認。真 DRL CSV `20260817_022959_olpar.csv` 的 Line=PINK LINE 不足以推定 Mainline/PL、UT/DT，列 unassigned。

## 已執行驗證命令

```text
python -m pytest backend/tests/test_tov1050_capabilities.py backend/tests/test_tov1050_report_export.py backend/tests/test_tov1050_adapter.py backend/tests/test_tov1050_metadata_candidates.py backend/tests/test_api_analysis.py backend/tests/test_calculation.py backend/tests/test_metadata_manager.py backend/tests/test_analyzers.py backend/tests/test_analyzers_task_run_data.py backend/tests/test_exporter_field_injection.py backend/tests/test_export_raw_generate.py -q
```

結果：最終131 passed（45.55s）；下載入口修正後亦重跑相關24項全pass。前端在 frontend 執行 `$env:NODE_USE_SYSTEM_CA='1'; npm exec tsc -- --noEmit`，exit0，未放寬 TLS。

```text
python scripts/verify_tov1050_contracts.py --output outputs/contract-regression-2026-10-23/batch-02
python scripts/verify_tov1050_streaming.py --baseline outputs/contract-regression-2026-10-23/batch-02 --output outputs/contract-regression-2026-10-23/streaming-parity
python scripts/audit_tov1050_real_fixtures.py --output outputs/contract-regression-2026-10-23/fixture-goldens
python scripts/review_tov1050_capabilities.py --output outputs/metadata-capabilities-2026-10-23/batch-02
python scripts/validate_tov1050_review_workbooks.py outputs/metadata-capabilities-2026-10-23/batch-02
git diff --check
```

batch-02 是舊 writer 基線；大檔後續新增後，batch-03 的 KTL 匯出超過十分鐘、觀察到該測試程序 private memory 超過8GB，停止該測試程序。此觀察沒有正式 RSS benchmark 或 SLA 意義。batch-04 確認 BytesIO 逐行交付引發大量 thread-pool handoff，再停止該測試程序並保留中途產物。TOV1050 report/raw 改64KiB分塊、測試位元組一致後，以 batch-05 重跑真資料。沒有停止使用者的 TOV640 uvicorn 程序。CLI 重跑需使用新的 output 目錄，避免覆寫歷史證據。

## 未完成與下一個 action

1. 業務資料負責人確認 DRL CSV 的 Mainline/PL、UT/DT 及 PL scope，並補必要 track sheet；開發端將確認值納入明確 fixture context，再跑回歸。
2. 補足其餘 line/session/direction 真 fixture 與 TML 真 datac，不能以 synthetic 測例替代。
3. 審閱373組 TL 的 termination、缺列／中斷／單點與真正物理邊界；填入 approved boundaries、approval、scope 及閉合政策後，開發端才接入已測試的 interval sweep／wear lookup。
4. DAV-20／DAV-21 維持 In Progress；不宣稱全線契約、TL/wear parity 或 portable 已完成。
