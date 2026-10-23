# 上傳 context 與四位小數

- 日期：2026-10-23
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-20、DAV-21
- 負責人：Codex
- 狀態：In Review

## 需求與目的

### 使用者與流程

使用者上傳 CSV 或 datac，手動選擇 Line、Track、session；原始 CSV 的 ORANGE LINE/GREEN LINE 不代表可用的邏輯 context。表單是分析及 Exception Report 的權威來源。使用者已更新根 config 的 Exception Boundarys，並要求四位小數取代九位小數。

### 商業規則與限制

保留來源檔及所有使用者修改，不提交使用者 workbook；不推斷 TCL fixture 方向、不核准 TL/Overlap。detector 核心及 TOV640 唯讀參考不改。圖表抽樣不影響 raw/export。

## 現況盤點

- API 已收 Line/Track，TOV1050 僅覆寫 Track；CSV Line 仍可能保留原值。loader 依 line 選擇，未支援 TOV1050 line 搭 datac。
- UI 已有選單，但檔案 dialog 未列 datac。
- 根 ISL、LAR_AEL、LAR_TCL workbook 已有使用者修改。TCL 第3、4列 ToM 改33199.9、33445.9（雙方向）。
- 既有 adapter metadata rounding=9；CSV Decimal*1000 僅一次，保留實際量測。

## 設計

### 範圍

1. 依副檔名選擇已存在 CSV/datac parser；metadata 仍依表單 context 選擇。所有 Line/Track 大小寫欄位使用表單值，另保留 source_line/source_track。
2. UI 保留選單，明示表單優先，dialog 納入 datac；export 使用成功分析時 snapshot。
3. wide metadata 區間端點讀入四捨五入至4位公尺。Excel report 數值欄顯示最多4位，保留儲存的完整量測值與 raw CSV 精度；不更動 detector/enrichment。
4. 唯讀比較使用者 workbook 與 HEAD，記錄 SHA、cell changes 及 TCL UT/DT 假設 coverage；未確認方向不做正式 fixture pass。

### 不在範圍

不寫回 metadata、不更新 release manifest 假裝新版本已promotion、不發布 portable、不改 DB。

### 資料流與錯誤處理

已存在 metadata coverage guard 保留。副檔名只決定資料 dialect，line/session/track 決定 metadata。分析結果及原始完整 frame 保存於 client session，匯出使用該 snapshot。

### 驗收標準

不同原始 Line/Track 的 CSV/datac 仍以使用者選擇值分析與輸出；選擇值出現在 Summary、分類頁、ChartData、raw 與檔名。四位 metadata 端點及四位 Excel 格式有測試，實際 raw 數值不截短。新 metadata 真CSV coverage 重算並附 SHA，TCL 方向仍未確認。

## 執行紀錄

### 實作

已完成表單 context、CSV/datac dialog/parser 路由、來源標籤保留、metadata4位端點及TOV1050 Excel4位顯示；未改detector或來源workbook。

### 測試與 debug

```text
python -m pytest backend/tests/test_tov1050_capabilities.py backend/tests/test_tov1050_report_export.py backend/tests/test_tov1050_adapter.py backend/tests/test_tov1050_metadata_candidates.py backend/tests/test_api_analysis.py backend/tests/test_calculation.py backend/tests/test_metadata_manager.py backend/tests/test_analyzers.py backend/tests/test_analyzers_task_run_data.py backend/tests/test_exporter_field_injection.py backend/tests/test_export_raw_generate.py backend/tests/test_ingestion.py -q
145 passed in 37.60s

# frontend，程序內 NODE_USE_SYSTEM_CA=1
npm exec tsc -- --noEmit
exit 0

python scripts/verify_tov1050_contracts.py --real-only --context TKL TKS DT --output outputs/contract-regression-2026-10-23/batch-15
pass；130825 retained、1 Stagger Right；API/report/raw 200；ChartData完整130825筆、Summary1筆與raw共有數值欄逐值相符。
```

新API測試使用synthetic CSV/datac改成互相衝突的source Line/Track，實際parser/detector及GET/POST report/raw全部核對。這是程式契約測試，不能代替現場datac/line組合驗收。前端首次新增測試誤用Analyze按鈕名稱（實際為Start Analysis），已修正測試。

### 驗收結果

batch-16唯讀比對根ISL/AEL/TCL與HEAD，只發現Exception Boundarys端點變動（2/8/8 cells），保存原始double值與SHA。TCL真CSV 601804→598044筆；UT/DT假設均class/track uncovered0。該CSV方向未指定，故不執行detector，不列正式fixture pass。batch-15 TKS DT以新context/precision/full export完成回歸。所有使用者原始workbook、候選及未追蹤資料保留，不納入提交。七份根config目前有三份使用者修改，不能沿用舊release digest宣稱無漂移。

四位政策僅metadata interval讀入及Excel顯示；不round原始量測、不改raw CSV精度。detector、TOV640及enrichment未改；EAL/TML reporter預設格式保留。TOV1050 line＋datac使用既有trim20/20與高度+5300，CSV使用trim100/100與Km*1000。沒有發布新版portable。

## Linear 同步

- 2026-10-23 實際 get_issue 成功；DAV-20/21 已留言補同步 d4eece1、140 tests、TML/TKS 證據與本次承接。
- Issue 狀態：In Progress；DAV-19 Done。
- Next action：實作並驗證 context、精度及新 metadata 覆蓋，附 commit/push 結果。
- 阻塞：TCL 正式 fixture 方向及 TL 物理區間仍待業務確認，不影響手動表單功能。

## 相關檔案

- backend/app/api/endpoints/analysis.py
- backend/app/core/tov1050_metadata.py
- backend/app/core/tov1050_report_export.py
- frontend/src/views/ExceptionGeneratorView.tsx
- electron/main.js


### 最終驗收補充

- 前端 `NODE_USE_SYSTEM_CA=1; npm exec vitest -- run src/views/__tests__/ExceptionGeneratorView.test.tsx`：5 passed in25.88s。既有MUI Tabs測試出現act warning，不影響通過；沒有把這些警告當產品錯誤。首次測試名稱錯誤已修正。
- batch-16 canonical-parity.json：固定TOV640 pin cbca528f090152ec2c776ee04a4c30f0d371810f，現HEAD33e77ab3的四個核心normalized內容仍相同。三組獨立程序detector及report所有欄/值相符（atol1e-9/rtol0，ID/欄序exact）。這是synthetic契約驗證，不代替現場驗收；TOV640未修改或回退。
- codebase-memory已更新索引；git diff --check通過。
- Linear已補同步前輪及本輪進度、145tests、TKS完整匯出及TCL新coverage，DAV-20/21維持In Progress。後續可執行action：使用者在上傳時指定TCL實際方向，即可用新metadata分析；要納入固定fixture矩陣仍需該檔方向確認。TL物理interval/scope仍是獨立業務待決。
- 本次不提交三份使用者根config，因此乾淨checkout仍是舊workbook；新metadata coverage證據僅對audit記錄的SHA成立。日後portable/release前需另處理使用者workbook版本提交/啟用紀錄。
