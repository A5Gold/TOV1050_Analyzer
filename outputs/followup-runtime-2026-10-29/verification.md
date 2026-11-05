# 測試後續實作驗證

日期：2026-10-29。使用者已approve設計並補充：無C/M分型終端全部為Contact；AEL配置先skip；64格runtime改動有意保留。

## 交付與範圍

- 三子代理完成Stagger診斷、圖表及metadata候選；主代理完成approved interval provider、API／UI／Excel evidence及整合。
- 最終 metadata 審閱：`outputs/metadata-review-2026-10-29/batch-04`。382組中31組Contact雙端候選；candidate FromM／ToM明列，批准欄空白。Known Boundaries記錄角色規則provenance。DRL候選保留runtime threshold，不複製UT造DT。
- 64格差異（46 threshold、18 Exception Boundarys）保留。無runtime sidecar／config promotion，沒有改原始CSV／DATAC或使用者DB。
- 本機程式修改尚未commit／push；起點HEAD `4e50d90f175c607cf5a6937c4137f6933dc911dc`。`implementation-files.json`保存本次修改檔案SHA，以免把基底HEAD當已提交實作版本。

## 自動驗證

```powershell
venv/Scripts/python.exe -m pytest -q backend/tests/test_tov1050_approved_intervals.py backend/tests/test_tov1050_capabilities.py backend/tests/test_tov1050_adapter.py backend/tests/test_median_analysis_snapshot.py backend/tests/test_tov1050_report_export.py
# 74 passed，61.97s；含Contact、scope、端點atoms、coverage、source drift、無效JSON、來源消失、median/ID/first-nonempty、Excel長JSON拆表。

venv/Scripts/python.exe -m pytest -q backend/tests/test_api_analysis.py backend/tests/test_analysis_chart_data.py backend/tests/test_chart_viewport_contract.py
# 31 passed，51.21s

venv/Scripts/python.exe -m pytest -q backend/tests/test_tov1050_boundary_review.py backend/tests/test_followup_metadata_review.py
# 最後更新候選欄／guide後：21 passed，8.18s

venv/Scripts/python.exe -m pytest -q backend/tests/test_dual_system_report_context.py -k stagger backend/tests/test_stagger_calculation_api.py
# 子代理：16 passed、26 deselected，含真EAL U3 HTTP200
```

前端均先設程序 `NODE_USE_SYSTEM_CA=1`，未降低SSL驗證：

- ChartComponent／chartMarkerHitTest Vitest：18 passed；Playwright真滑鼠3 passed。涵蓋line/dot重合、hover後click、三panel、同點重點、重合選單、隱藏trace、普通線不誤選、延遲response、門檻偏好、三種viewport及模擬DPR。
- Stagger前端四檔：16 passed；ExceptionTable：2 passed，候選不填正式欄、位置缺口及來源證據可開啟。
- `npm run build`：exit0，4150 modules，10m27s；既有assert externalization／大chunk／xlsx動靜態匯入警告未在本需求重構。最後`npx tsc --noEmit`：exit0。
- `git diff --check -- backend frontend docs scripts`：通過（只有Git CRLF提示）。

## 真實輸入與匯出

```powershell
venv/Scripts/python.exe scripts/validate_followup_runtime.py --output outputs/followup-runtime-2026-10-29/batch-01
```

| 檔案 | raw→median | 例外 |
|---|---:|---:|
| 20260907_TWL_UT.csv | 838859→83963 | 160：Low63／High2／Wear1／StaggerRight94 |
| 20260630_TWL_UT.csv | 830792→83244 | 199：Low66／High7／Wear15／StaggerRight111 |
| TML_D1_260410.datac | 41138→41138 | 152：Wear86／StaggerLeft20／StaggerRight46 |

三份來源SHA前後不變，canonical detection digest保存在batch-01/validation.json。這是direct `_analyze_sync`，不宣稱三份都是Electron圖表驗收。兩份TWL新開發驗證報表保留完整median ChartData，讀回Summary三欄／證據頁及隱藏capabilities JSON成功。TL等正式欄仍無核准區間，不以候選填值。

實檔程序在使用者無分型規則補充前啟動，batch-01報表的review evidence屬v1；v2只更新角色分類／候選，沒有改detector或已匯出正式空值。最後資料審閱以batch-04 v2為準。分析與匯出耗時694.0s／369.3s／12.3s，受同時測試及資源影響，不作效能SLA。

## 真 Electron

`node scripts/validate_followup_electron.mjs`：**passed**，source Electron renderer + 本機backend HTTP multipart，沒有攔截API。指定AEL報表回422／STAGGER_CONFIG_UNAVAILABLE，繁中身份／缺配置／可展開JSON正確。`outputs/followup-electron-2026-10-29/validation.json`核對DB在該outputs內，截圖`stagger-real-electron.png`已查看，實際Windows renderer deviceScaleFactor=1.5。這是診斷驗收，依使用者指示不計算AEL。

前三次QA錯在選到DevTools Page及Electron Playwright request context；保留attempt-01/02/03，改選應用URL及renderer fetch後成功，未修改產品繞過。測試程式已關閉Electron及其backend；專用Vite 5192完成後停止。

## 候選 workbook

```powershell
venv/Scripts/python.exe scripts/review_followup_metadata.py --output outputs/metadata-review-2026-10-29/batch-04
# bundled Node執行 scripts/build_followup_metadata_workbooks.mjs .../batch-04
venv/Scripts/python.exe scripts/validate_followup_metadata_workbooks.py --output outputs/metadata-review-2026-10-29/batch-04
```

來源25份最終SHA保持；DRL 4532格、Contact 7152格parity通過。兩份workbook所有sheet均render並做error scan；Review Guide及明細PNG已檢視。沒有用openpyxl author候選；read-only驗證使用openpyxl。

## 剩餘與下一步

正式TL資料仍需31組候選的配對連通／scope／完整性審閱、其他TL補端、DRL方向確認；Landmark沒有核准實體range仍空。具體批准後才可做sidecar發布、來源備份及manifest更新。AEL配置先skip；64格現值保留。

原生Excel、使用者舊portable、各Windows DPI的真資料圖表全面人工驗收未執行；未建立新portable。圖表真pointer證據為fixture Chromium，勿與真Electron診斷混稱。起始兩項dirty（AEL原始CSV modified、Excel lock deleted）保留。
