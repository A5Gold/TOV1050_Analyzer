# Calculation／報表身份驗收

日期：2026-10-29。工作目錄：`C:\Smart Maintanence\TOV1050_Analyzer`。

## 最終針對性回歸

1. `venv/Scripts/python.exe -m pytest backend/tests/test_dual_system_report_context.py backend/tests/test_version_difference_api.py backend/tests/test_stagger_calculation_api.py -k 'not real_u3' -q --tb=short`
   - **50 passed, 1 deselected**，56.63 秒。
   - 包含 AEL／LMC／TKS／DRL context、空 TL 的 Summary 五欄、DT 下行、混合 line／branch／direction、Section 不相容、raw／median／version 衝突、同日來源／task 隔離、跨日不同 task 配對、新舊檔名及 unsupported Stagger 不開啟 ChartData XML。
2. `venv/Scripts/python.exe -m pytest backend/tests/test_calculation_api.py backend/tests/test_wear_records.py backend/tests/test_wear_calculator.py backend/tests/test_stagger_service.py backend/tests/test_stagger_selector.py backend/tests/test_stagger_formula.py backend/tests/test_stagger_keq.py -k 'not real and not streaming' -q --tb=short`
   - **130 passed, 8 deselected**，7.56 秒。
   - 完整輸出：`calculation-regression.log`。
   - 保留既有 EAL／TML Wear 與 Stagger 數值／公式、complete-cycle preview、temporary DB persistence 與 legacy wear channels。
3. 本次較早亦執行：`venv/Scripts/python.exe -m pytest backend/tests/test_dual_system_report_context.py backend/tests/test_stagger_calculation_api.py backend/tests/test_trend_analyzer.py backend/tests/test_excel_parser.py -q --tb=short`
   - **80 passed**，177.08 秒；包含原有真實 U3 Stagger fixture。
   - 其後新增預檢 ZIP 路徑及 composite TL／大小寫 Section 案例，由第 1 項最終命令覆蓋。
4. `git diff --check`：相關 tracked calculation/API 修改通過，僅 Git 的 LF／CRLF 提示。

最早完整 calculation／wear suite 曾有兩個失敗：legacy EAL 無 Track 路徑被錯誤阻擋，以及 mock parser 未接受新增 filename 參數。兩者已修正，並由第 2 項最終命令重新驗證通過；未把早期失敗列為未解決問題。

## 使用者真實報表

詳見 `calculation-fixture-validation.json`。只讀取原檔，未覆寫任何報表。

- AEL：`20260603_AEL_UT_MAINLINE_SHR_AWE_Exception_Report_MedianSample.xlsx`。
  - parent／branch／direction：AEL／Mainline／UP。
  - 來源 Track／Section／Task／Stn Start／Stn End：UT／Mainline／U3／SHR／AWE。
  - 演算法：`same_chainage_median_sample_v1`／`chainage_median`。
  - Stagger：422，`STAGGER_CONFIG_UNAVAILABLE`；detail.message、context 與 missing_configuration 包含實際身份及缺少的 support metadata／Keq 策略。
  - 直接 Python 呼叫耗時約 **0.08 秒**，不包括 Electron/UI 檔案上傳。預檢約 0.048 秒。
- TWL 20260907／20260630：皆 TWL／Mainline／UP、來源 UT／Mainline／U1／CEN／TSW、median sample v1；小型工作表預檢約 0.151／0.214 秒。

讀取套件的 read_only 模式仍會初始化 dimensionless ChartData；本版以記憶體中的 small-sheet ZIP 預檢副本避開該掃描。原 workbook 不變，未獲配置的 Stagger 不開啟 ChartData XML。具備已核准配置的 EAL／TML 才繼續完整量測解析。

## 可用性邊界

- 新線 Stagger／TOV1050 Wear 沒有已核准工程配置時，輸出明確配置診斷；沒有借用 EAL 或 TML 係數／metadata。
- Version Difference 本版對已知不同或多個 Section 拒絕比較，提示分開操作，避免僅靠 chainage 混算。
- Legacy 缺少演算法 provenance 保留相容，標示 `algorithm_status=unknown`；明確已知的模式／版本衝突拒絕比較。
- Trend 保留既有 10.2／0.2 判斷常數及回歸公式，沒有在本工作另訂新工程政策。
- 測試使用暫存資料庫；沒有修改正式 DB、raw／reference workbook 或 TOV640 repository。
