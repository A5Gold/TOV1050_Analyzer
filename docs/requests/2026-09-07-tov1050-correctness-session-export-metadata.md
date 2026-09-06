# TOV1050 correctness、session isolation 與 metadata 修正

- 日期：2026-09-07
- Linear project：TOV1050_Analyzer
- Linear issue：待建立並連結至 DAV-10
- 負責人：David Chu
- 狀態：In Progress

## 需求與目的

修正使用者確認的正確性與 UX 風險：CSV 邊界不應默認遺失、Report/Raw export 必須使用完整 raw data、backend latest cache 不得造成跨 tab/module 污染、metadata audit 應反映合法 overlap/landmark 與不合法 identity。

### 使用者與流程

鐵路接觸網維護分析人員從 Exception Generator 載入 CSV、執行 detector、檢視 Graph/Table、選取 detail、匯出報表，並在 History Compare／Database Record 間切換。

### 商業規則與限制

- Chainage canonical unit 為公尺：Km * 1000 -> Chainage_m。
- chart downsampling 只能作用於 chart payload。
- detector、threshold crossing、overshoot、exception peak 與 export 使用完整 raw data。
- 合法 tension-length overlap 可保留；landmark 為獨立語意。
- 同 Bracket 多位置不合法；reversed interval 不得靜默以 min/max 修正。
- 不覆蓋原始 metadata，任何 promotion 必須保留 provenance、digest 與 audit。

## 現況盤點

- 相關程式碼：backend/app/api/endpoints/analysis.py、backend/app/core/tov1050_data_ingestion.py、backend/app/core/tov1050_metadata.py、backend/app/core/chart_sampling.py、frontend/src/views/ExceptionGeneratorView.tsx、frontend/src/components/ChartComponent.tsx。
- 相關 API／資料流程：POST /analyze、GET /analyze/chart-data、POST /export/report/generate、POST /export/raw/generate。
- 現有測試：analysis chart-data、chart sampling、TOV1050 adapter、candidate validator、frontend Exception Generator/About/GuideVisuals。
- 已知風險：latest global cache、downsampled chart export、前後 100 rows trimming、metadata candidate fail/provenance mismatch。

## 設計

### 範圍

1. 保留完整有效 CSV rows，清楚記錄 boundary diagnostics。
2. 將完整 raw data 與 chart payload 分離，export 不再依賴 downsample payload。
3. 讓 detail 與 export 使用 session/request scoped source。
4. 修正 metadata validation 的 interval、landmark、identity 與 provenance 規則。
5. 增加 regression tests、benchmark/validation evidence。

### 不在範圍

不變更 TOV640 detector threshold 方向、SQLite schema 或無關 UI 重構；不把未經人工確認的 metadata candidate promotion 到 runtime。

### 資料流與錯誤處理

分析先載入完整 raw frame，再建立 detector 結果與 chart-only payload。每個 export request 必須帶明確 raw source 或完整 raw payload；缺少時回傳 4xx。detail request 以 session source identity 驗證，來源不存在或無法載入時回傳明確錯誤。

### 驗收標準

- full raw row count 與 detector/export row count 可驗證一致。
- chart payload 可 downsample 且保留 extrema/exception chainage。
- 多 tab／module 切換不會讀到其他 session 的 raw data。
- metadata validator 對合法 overlap/landmark 不誤報；同 Bracket 多位置、reversed interval、provenance mismatch 仍 fail-closed。
- targeted backend、frontend tests 與 production build 通過。

## 執行紀錄

### 實作

完成：session-scoped registry、完整 raw export、CSV 清洗邊界診斷、metadata validator 規則已實作；原始 workbook 未修改。

### 測試與 debug

```text
pytest -q backend/tests/test_tov1050_metadata_candidates.py backend/tests/test_tov1050_adapter.py backend/tests/test_analysis_chart_data.py backend/tests/test_chart_sampling.py backend/tests/test_api_analysis.py backend/tests/test_export_raw_generate.py backend/tests/test_exporter_field_injection.py
50 passed

npm --prefix frontend run build
成功；保留 xlsx dynamic/static import 與大型 bundle warnings

python scripts/validate_tov1050_metadata_candidates.py --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL --output-dir docs/audits/validation-20260907
exit 1；ISL review_required、KTL fail（physical bracket identity 多位置）、其餘 review_required；不是程式崩潰
```

### 驗收結果

已完成程式修正與 targeted 驗證；metadata candidates 仍 review-only，等待人工確認後才可 promotion。

## Linear 同步

- 最後同步時間：2026-09-07
- Issue 狀態：DAV-11 In Progress，完成後回寫 DAV-10
- Next action：commit/push、同步 Linear，等待人工 metadata decisions。
- 阻塞／需要決策：無；使用者已提供決策。

## 相關檔案

- docs/audits/2026-09-02-tov1050-metadata-review-summary.md
- docs/audits/2026-09-02-tov1050-metadata-candidate-validation.json
