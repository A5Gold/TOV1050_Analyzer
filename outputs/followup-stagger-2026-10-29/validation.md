# P1 Stagger 結構化診斷驗證

日期：2026-10-29（Asia/Hong_Kong）。本輪未變更 Stagger 公式、line catalog 或 backend 計算流程。

## 實作

- `apiErrorDiagnostic` 讀取 nested `context`／`missing_configuration`，翻譯 `STAGGER_CONFIG_UNAVAILABLE` 缺項。
- Calculation cycle 保存結構化診斷，換檔、移除檔案、重試或 reset 時清除；不同 cycle 隔離。
- `StaggerDiagnosticAlert` 顯示繁中原因、scope、檔名、代碼及下一步。詳細資料可展開、選取及複製，clipboard 失敗保留手動複製方式。
- 詳細資料僅包含白名單欄位，不複製 Axios headers/config。

## 已執行

```powershell
# frontend
$env:NODE_USE_SYSTEM_CA='1'
npx tsc --noEmit
# exit 0
npx vitest run src/api/__tests__/errorMessage.test.ts src/components/Calculation/__tests__/StaggerDiagnosticAlert.test.tsx src/store/__tests__/useCalculationStore.test.ts src/views/__tests__/CalculationView.test.tsx
# 4 test files, 16 passed, 156.81s；見 frontend-diagnostics.log

# repo root
venv/Scripts/python.exe -m pytest -q backend/tests/test_dual_system_report_context.py -k 'stagger' backend/tests/test_stagger_calculation_api.py
# 16 passed, 26 deselected in 272.74s
```

後端測試包含 AEL early capability gate、不開 ChartData XML、LMC 不繼承 Mainline、EAL/TML API／公式相容與真 EAL U3 report HTTP 200。沒有將 deselected 計為通過。

首次前端套件有一項 assertion 用法錯誤：toHaveValue 不接受 stringContaining matcher；改讀取 textarea.value 後重跑。此錯誤不涉及產品邏輯。

指定真 AEL workbook 另以直接 route 及 TestClient multipart API 重驗，兩者均 422／STAGGER_CONFIG_UNAVAILABLE，正確辨識 AEL/Mainline/UP 及原始 UT/U3/SHR/AWE。route 約 0.0695s、TestClient API 約 0.1531s；preflight 約 0.6552s（同時有其他測試，不作效能門檻證據）。見 real-ael-validation.json；來源檔案 SHA256 前後一致。

## 限制

- TestClient API 不含真 Electron、HTTP 網路傳輸、原生 clipboard 或實際 Excel 開啟；尚未執行 Electron 人工驗收。
- 其他線尚缺核准支撐點資料／Keq 規則，繼續停止 Stagger 計算，未借用 EAL/TML。
- 沒有新增 runtime/build identity；真檔 JSON 已記錄本次 source HEAD，避免把 source 測試當成已核對使用者舊程序版本。
