# TOV1050 契約與能力驗收紀錄（2026-10-23）

追蹤 DAV-20／DAV-21；本次可獨立交付的程式及審閱產物完成，跨線現場驗收與核准 TL geometry 尚未完成。沒有發布 portable，也沒有啟用新候選。

## 固定基線與比較方式

TOV640 固定 commit：`cbca528f090152ec2c776ee04a4c30f0d371810f`。執行前驗證 HEAD 與實際載入的 analyzers、metadata、data_ingestion、exporter 四個 core 檔案等於固定版本（容許 CRLF 差異）；其他並行工作修改保留，本次沒有寫入 TOV640。

結束前另比對 EAL metadata workbook 與固定 git blob 完全相同；四個 core／workbook 及 canonical metadata SHA 證據位於 `batch-02/reference-final-audit.json`。

最終收尾偵測到 TOV640 並行 annual-wear 工作提交後，HEAD 已推進至 `33e77ab3c7afc72d0dd531d2b660baf08cf8fd63`；沒有回退或修改它。本次實際比較的四個core及EAL metadata SHA仍與保存的固定基線完全相同，已記錄final_reference_head與逐檔證據。比較結果仍針對原固定輸入，未驗收新的annual-wear功能。主比較CLI嚴格要求HEAD固定，日後重跑須提供獨立固定ref checkout，不可直接回退此共用TOV640工作目錄。

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

batch-05 最終三組全部通過：API／report／raw export 均 HTTP200，AEL／KTL／TKL 分別276／830,606／501,211筆 ChartData逐列值、raw共有數值欄及0／160／69筆Summary核對通過。`real-results.json` 保存來源及匯出SHA／bytes、筆數與capability snapshot；`real-fixture-coverage.csv` 為最終矩陣：18組context有3組已驗證，15組缺已指派真fixture，另DRL來源檔context未確認而unassigned。

TKL raw reader有 DtypeWarning（第10欄）；已核對來源為 `Last Pole Code [---]`，同時含數字及 `554-38` 等文字杆號，來源112,030列非純數字。這是reader型別推斷警告，沒有轉換杆號或推導TL；診斷見 `reader-diagnostics.json`。raw驗收範圍為全部共有數值欄，未宣稱全部object欄位的CSV roundtrip。

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

最終真CSV批次的實際啟動命令（PowerShell、repo根目錄）：

```powershell
python -c "import sys,json; from pathlib import Path; sys.path.insert(0,'scripts'); from verify_tov1050_contracts import run_real_csv; p=Path('outputs/contract-regression-2026-10-23/batch-05'); p.mkdir(); r=run_real_csv(p); (p/'real-results.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8'); print([(x['context']['line'],x['raw_rows'],x['exception_counts']) for x in r['real_runs']])"
```

batch-02 是舊 writer 基線；大檔後續新增後，batch-03 的 KTL 匯出超過十分鐘、觀察到該測試程序 private memory 超過8GB，停止該測試程序。此觀察沒有正式 RSS benchmark 或 SLA 意義。batch-04 確認 BytesIO 逐行交付引發大量 thread-pool handoff，再停止該測試程序並保留中途產物。TOV1050 report/raw 改64KiB分塊、測試位元組一致後，以 batch-05 重跑真資料。沒有停止使用者的 TOV640 uvicorn 程序。CLI 重跑需使用新的 output 目錄，避免覆寫歷史證據。

## 未完成與下一個 action

1. DRL CSV 已由使用者確認 PL/UT；reference DRL UT row11 已隔離驗證（見下）。下一步為 DRL 來源標準化候選與 session/sheet、Bracket單位、DN邊界審閱，再決定正式啟用範圍。
2. 補足其餘 line/session/direction 真 fixture 與 TML 真 datac，不能以 synthetic 測例替代。
3. 審閱373組 TL 的 termination、缺列／中斷／單點與真正物理邊界；填入 approved boundaries、approval、scope 及閉合政策後，開發端才接入已測試的 interval sweep／wear lookup。
4. DAV-20／DAV-21 維持 In Progress；不宣稱全線契約、TL/wear parity 或 portable 已完成。

## DRL 確認與覆蓋檢查增量（2026-10-23）

以上 batch-05 的15缺fixture／DRL未指派描述為歷史快照。使用者現已確認 `20260817_022959_olpar.csv` = DRL/PL/UT，加入含SHA的 `config/tov1050-regression-fixture-contexts.json`。

- batch-06：舊入口對root long metadata未覆蓋的52筆仍回HTTP200／0 exceptions，僅保留為發現問題的診斷證據，不作detector驗收。
- batch-07：加入實際量測coverage guard後，同一root config回HTTP400，report/raw未執行；52筆來源CSV row102–153的缺口及舊PL sheet逐列列出。
- 使用者指定的新版來源已核實：`00 Reference Document/config/DRL metadata.xlsx` SHA `a386100bb6f47ab9d2a61e7e80c40ad5e87a91cc614e1659584ea41a0161ecff`，`DRL UT` Excel row11 Curve44887–45500m。先前缺口僅指root舊PL sheet，不再要求提供已存在的區間。
- 正式增量證據 batch-09：隔離reference目錄，252→52筆、45388.2–45389.2m，全部Tunnel／Curve；Class/Track uncovered均0。API/report/raw均HTTP200，52筆完整ChartData與raw共有21個數值欄逐值通過，Summary0筆。零異常不能作現場peak/level/ID證據。batch-08是同一隔離流程的初次診斷，不採用為正式矩陣。
- 最新 `batch-09/combined-fixture-coverage.csv`：18 contexts = 3組既有正式runtime完整匯出證據＋1組 `pass_isolated_reference_only`＋14組缺fixture。這1組**沒有成為runtime pass**，根DRL config仍由guard阻擋；3組歷史完整匯出來源及metadata SHA重查相同，沒有宣稱本輪重跑其大型匯出。
- 新來源仍有獨立`DRL PL`頁到44000m；DRL UT的218點及DRL PL的86點Bracket FromM原值約41–45，與Track Type公尺欄混用單位；DN Class邊界為46000→40000。僅本sample採用使用者指定DRL UT，不擴大為全PL方向映射、point分類、核准TL或整份DRL啟用。來源審閱：`batch-09/source-review.json`。
- 133項相關backend tests通過（38.42s）。三份真資料重新執行完整清洗/API/detector：AEL276／0、KTL830606／160、TKL501211／69；`coverage-preflight-goldens/comparison.json`核對清洗、來源SHA、mapping、全部exceptions/peak/level/ID、capabilities、chart resolution均與原golden完全一致，三份JSON的SHA也完全相同。未改detector或report enrichment。
- 七份正式config SHA再核對release全部相同，見`batch-09/approved-runtime-digest-check.json`；沒有重建或覆寫workbook。TOV640 HEAD仍為33e77ab3c7afc72d0dd531d2b660baf08cf8fd63，未修改其repo；本輪未重跑跨程序TOV640比較，固定基線證據沿用先前已提交批次。

本輪實際命令（使用新的output避免覆寫）：

```powershell
python scripts/verify_tov1050_contracts.py --real-only --context DRL PL UT --metadata-dir '00 Reference Document/config' --output outputs/contract-regression-2026-10-23/batch-09
python scripts/review_tov1050_confirmed_fixture.py --fixture '00 Reference Document/Raw data/DRL/20260817_022959_olpar.csv' --output outputs/contract-regression-2026-10-23/batch-09 --previous outputs/contract-regression-2026-10-23/batch-05 --metadata-dir '00 Reference Document/config'
python scripts/audit_tov1050_real_fixtures.py --output outputs/contract-regression-2026-10-23/coverage-preflight-goldens
```

測試命令與上節相同11個test files。新CLI的`--real-only`明確不執行TOV640 parity；替代metadata必須指定單context，程序退出後還原CONFIG_DIR。隔離成功在CSV及JSON均使用獨立status，不得列為runtime正式驗收。


## 新增 TML/TCL/TKS 原始資料（2026-10-23）

使用者更新 Raw data 後盤點三個來源。摘要與SHA見 outputs/contract-regression-2026-10-23/batch-13/updated-source-rollup.json。

- TML TML_D1_260410.datac：SHA da226284648bbec7c9e16c2d5d709aa6a39fb96fc6059c0ae88e9d85a54f48e0；源資料TRACK=DN、41,138 rows。TOV640 Mainline metadata SHA與四個比較core都經核對等於固定pin cbca528f090152ec2c776ee04a4c30f0d371810f；目前TOV640 HEAD雖為33e77ab3c7afc72d0dd531d2b660baf08cf8fd63，沒有變更的核心檔仍與pin相同。TOV640/TOV1050各在獨立程序讀同一datac與metadata，detector及完整Excel report逐欄／逐值一致；比較容差數值atol1e-9、rtol0，字串/ID/欄序精確。例外共149（Wear86、Stagger Left20、Stagger Right43），Summary149列。TOV640專案未修改，見batch-10/tml-readonly-parity.json。
- TKS 20260902_TKS_DT.csv SHA 9263b95b8fdf705a805fc7d196943b83c61f7e58d4b31881509c8e0cdfae7d11；既有產品契約指定line TKL/session TKS，檔名指定DT。精確十進位Km轉換及端點容差修正後以batch-13重跑：131,222→130,825 rows（trim100/100、invalid chainage0、無有效量測197），Stagger Right 1；API/report/raw全200，ChartData130,825逐列、raw共有21數值欄及Summary逐值驗證通過。Class/Track coverage均0缺口。TKS Excel row5起點原存64522.00000000001m，按1e-9m容差只消除7.28e-12m表達噪音；原始workbook未改。初次batch-10 pass是CSV乘法與Excel端點的浮點表示剛好相等、掩蓋精度問題；batch-11阻擋才揭露端點儲存噪音；兩者均由batch-13最終驗收取代。詳細見batch-13/tks-interval-tolerance-review.json及batch-13/real-results.json。
- TCL 20260618_032025_olpar.csv SHA 13efae7caa2e22b066d33f72c3b0bf1ad94a8436820ce3b182d52fa4157d51bc；601,804 raw、598,044 rows保留、3,560無有效量測。folder及ORANGE LINE指向TCL，但檔名及資料不能確認direction。UT/DT只作診斷：十進位轉換後兩者track均全覆蓋（先前32431m pseudo-gap已消失）；兩者class都缺100 rows，metadata來源為Excel row4到row5間約1.1m缺口，逐列審閱見batch-13/tcl-class-gap-row-review.json。因此不執行detector/API，不標pass；尚待確認方向且需審閱Class缺口。
- 最新18組矩陣：4組正式完整匯出通過（原3組＋TKS）、1組DRL isolated-reference通過、13組缺fixture；TCL未指派方向不新增為pass。見batch-13/combined-fixture-coverage.csv。DRL仍未promotion；TML不是TOV1050 line/session matrix項目，另以TOV640相容比較保存。
- 精度修正測試：decimal 32.431km→32431.0m；wide端點在1e-9m內正規化、超過容差保留。相關adapter/capability測試40 passed；完整相關suite 140 passed in32.27s。更早precision-only整體suite 139 passed，現以140項最終結果為準。 batch-14對三份舊golden重跑：detector例外欄位、ID、level、grouping、清洗、mapping及能力結構/文字完全相同；最大數值表示差2.91e-11（atol1e-9/rtol0）。KTL/TKL圖表envelope只因Chainage精確表示變更，returned chart points分別-1/+1；完整raw detector/export未抽樣。比較見batch-14/comparison.json。
- TOV640唯讀比較固定pin已驗證四檔內容一致，雖HEAD不同；僅有frontend/index.html及docs/TOV1050_Migration未提交，均保留。

## DRL 標準化審閱候選

只讀取reference 00 Reference Document/config/DRL metadata.xlsx（SHA a386100bb6f47ab9d2a61e7e80c40ad5e87a91cc614e1659584ea41a0161ecff），在 outputs/metadata-review-2026-10-23/batch-05-drl-source/ 建立具來源workbook/sheet/Excel row provenance的間隔候選19列、threshold讀回20列及Bracket單位審閱304點。row11 DRL UT 44887–45500m只標為該確認sample使用依據；不認定全PL sheet路由。Bracket候選Chainage_m保持空白，因原值約41–45但header為FromM，單位未確認；沒有生成TL/Overlap/Landmark interval。DRL PL獨立頁、DN Class反向端點原樣保存。只有CSV/JSON review-only產物，沒有覆寫原workbook或runtime七份config。

## Linear 同步狀態

本輪Linear MCP工具曾回覆Authentication required，需求記錄已標Linear sync blocked。依repo流程執行OAuth後CLI回報登入成功，但目前Codex session需重新開啟或新建local task，現session不得宣稱已同步本輪進度。下一次MCP恢復後先將batch-10至batch-14證據、140 tests、TML/TKS/TCL與DRL candidate結果同步DAV-20/21；DAV-20/21維持In Progress。
