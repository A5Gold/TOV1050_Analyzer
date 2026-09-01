# TOV1050 Data Contract 與說明文件設計

- 日期：2026-08-29
- Linear project：[TOV1050_Analyzer](https://linear.app/david-chu/project/tov1050-analyzer-d897dfced2f1)
- Linear issue：[DAV-6](https://linear.app/david-chu/issue/DAV-6/設計盤點-tov1050-使用者流程與狀態模型)
- 主控 issue：[DAV-5](https://linear.app/david-chu/issue/DAV-5/tov1050-analyzer建立專案-triage-與交付路線圖)
- 狀態：Implemented and verified

## 目標

修正三個已確認問題：TOV1050 metadata workbook 格式未標準化、Exception Generator 錯誤把任意 CSV basename 當成嚴格業務檔名、About／操作指南／開發者參考未完整反映目前契約。設計維持既有 FastAPI、React/MUI、SQLite 與 Electron 邊界。

## 現況與根因

TOV1050 config 多為 long threshold table（`Location Type, Track Type, Exc Type, min, max, remark`），TOV640 EAL/TML 為 detector 寬表（`Class, Track Type, Exc Type` 與各項 L1-L3），而 `LAR_AEL metadata.xlsx` 混有兩種欄位。後端已局部 normalize，但讀取與寫回仍允許混合欄位；前端也會依動態欄位推導 grid，round-trip 契約不穩定。

`/api/analyze` 在讀取 UI context 前無條件呼叫 `parse_input_filename`。該 parser 只接受 `YYYYMMDD_LINE_TRACK_STATION_START_STATION_END.csv`，因此 `20260817_022959_olpar.csv` 即使 UI 已提供參數仍回傳 400。

## 採用方案

### Metadata canonical adapter

1. 讀取 workbook 時先 trim 欄名、套用大小寫／alias normalization，並辨識 long、wide、mixed 三種輸入。
2. 長表與 TOV640 寬表轉為單一 detector canonical threshold model：`Class`、`Track Type`、`Exc Type`、各異常的 L1-L3；保留來源欄位、檔名與列號 provenance。
3. mixed、缺欄、無法轉換、非數值、threshold 順序錯誤與位置區間 overlap 一律 fail closed，錯誤包含 sheet、列號與可修正建議。
4. 寫回只接受 canonical payload，先備份，再輸出乾淨的 canonical sheet，避免舊欄位殘留。TOV640 adapter 僅作 legacy input compatibility。
5. 前端 Metadata Editor 固定 canonical columns；不再以原始欄位集合決定主要 grid schema。

### Exception Generator context

1. UI 表格的 date、line、track、session、station start/end 是 authoritative context。
2. filename parser 僅作 fallback；解析失敗不阻擋合法 `.csv`，也不從非業務 token 推測日期或路線。
3. 分析與匯出前明確驗證必要 context，缺少時回傳 4xx/422 與欄位級錯誤，不讓 `ValueError` 變成 500。
4. 輸出使用既有 canonical output contract，並保留 raw filename 作 lineage metadata。

### 說明文件

更新 Operator Guide、Developer Reference 與 About content，說明 canonical metadata、輸入 context 優先級、輸出命名、preview/save、錯誤診斷與 TOV640 legacy 邊界。維持現有 MUI/Plotly、鍵盤操作、對比度與狀態標示。

## 實作順序與 Linear 對應

1. DAV-7：metadata adapter／workbook migration、Exception Generator validation 與 output naming。
2. DAV-8：backend/frontend regression、round-trip、malformed filename、missing context、lint/build 測試。
3. DAV-9：About、操作指南、開發者參考內容與驗收。

## 驗收標準

- 每個 TOV1050 workbook 可讀取為 canonical model；long、wide、mixed 行為有明確測試。
- `20260817_022959_olpar.csv` 在完整 UI context 下可分析；缺必要 context 時收到可理解的 4xx/422。
- Exception Report 輸出名稱符合 canonical contract，原始 basename 可追溯。
- Metadata Editor round-trip 不產生混合欄位；錯誤含 sheet／列號。
- About 三個文件面向與實際產品行為一致。
- Linear issue 狀態、next action、測試結果與阻塞於每階段同步。

## 未納入本次範圍

- 不重寫 TOV640 detector 演算法。
- 不改變既有 threshold 判定方向或資料庫 schema，除非測試證明契約不一致。
- 不進行與三個問題無關的 UI 重構或檔案清理。

## 實作與驗收紀錄

- 已完成：`backend/app/api/endpoints/analysis.py` 對非 canonical CSV basename 採 best-effort fallback；export filename validation 以 HTTP 422 回傳。
- 已完成：`frontend/src/views/ExceptionGeneratorView.tsx` 將 Station Start／End 作為明確 TOV1050 context。
- 已完成：About／Operator Guide／Developer Reference 補充輸入優先級、canonical metadata 與輸出命名。
- 測試：`pytest -q backend/tests/test_api_analysis.py backend/tests/test_tov1050_adapter.py`，14 passed。
- 測試：`pytest -q backend/tests/test_metadata_service.py backend/tests/test_metadata_threshold_levels.py backend/tests/test_tov1050_adapter.py`，16 passed。
- 測試：`npm --prefix frontend test -- --run src/views/__tests__/ExceptionGeneratorView.test.tsx`，4 passed。
- 建置：`npm --prefix frontend run build` 成功；保留既有 xlsx dynamic import 與 bundle size warnings。
- 已完成：canonical workbook write-back migration、long/wide/mixed round-trip coverage 與 malformed basename integration regression。

### 追加實作

- `backend/app/core/metadata.py`：threshold 數值清理現在移除千分位逗號後再轉 numeric。
- `backend/app/core/tov1050_metadata.py`：加入欄名 alias、canonical required columns、有效 wide 欄位判定，以及 long+wide mixed schema fail-closed。
- `backend/tests/test_tov1050_adapter.py`：加入 mixed schema rejection 與 case/numeric normalization 測試。
- `backend/tests/test_api_analysis.py`：加入 parser 失敗但表格 context 完整時分析成功的 regression test。
- 追加驗證：`pytest -q backend/tests/test_api_analysis.py::test_tov1050_analysis_ignores_noncanonical_input_basename backend/tests/test_tov1050_adapter.py`，10 passed。
- `backend/app/core/metadata_service.py`：TOV1050 threshold save 會將長表 payload 轉為 canonical wide schema，移除舊欄位殘留；混合 long/wide payload 會拒絕。
- `backend/tests/test_metadata_service.py`：新增 canonical write-back round-trip 測試。
- 追加驗證：metadata、API metadata、adapter、analysis 測試共 31 passed。
