# 重新審閱更新後的 TOV1050 TL-BK mapping

- 日期：2026-09-23
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-19（DAV-10 子 issue）
- 負責人：Codex
- 狀態：In Review

## 需求與目的

使用者更新了 `00 Reference Document/TOV1050 TL-BK No.xlsx`，要求依更新後的 Location/Bracket mapping 重新檢查 metadata candidate 與 audit。使用者補充：一般 physical bracket identity 常見格式如 `123-01`、`CR283-15`；`SI`、`Mid Point`、`POA`、站名與設備代碼是 landmark，不應當作一般 bracket identity。

### 使用者與流程

使用者會人工檢查 Excel。Codex 比對 mapping 變更、更新唯讀 validator 的診斷語意，並把新 candidate 與 audit 寫到新的獨立輸出目錄供人工審閱。

### 商業規則與限制

- `Location` 是 Km；metadata adapter 轉換為公尺（`Location * 1000 -> Bracket FromM`）。
- landmark 不納入 physical bracket 的 exact duplicate、同位置多 bracket 或同 bracket 多位置 identity 判定，但保留在 landmark 診斷中。
- 同位置多個一般 bracket 可能是合法 tension changeover/overlap，只列為 review；不得自動刪除。
- 同一一般 bracket 出現在多個位置應列為錯誤候選；本次更新後須重新計算。
- 不覆蓋原始 mapping workbook、既有 candidate、runtime metadata 或既有 audit。
- candidate 維持 review-only；無人工核准前不得 promotion。

## 現況盤點

- 相關程式碼：`scripts/standardize_tov1050_metadata.py`、`scripts/validate_tov1050_metadata_candidates.py`
- 相關 API／資料流程：validator 讀取 metadata source、TL-BK mapping、wide candidate 與 provenance；不寫 runtime metadata。
- 現有測試：`backend/tests/test_tov1050_metadata_candidates.py`
- 已知風險或阻塞：目前 same-location 診斷把 landmark 與一般 bracket 一起計數；更新 workbook 後必須在新目錄產生 candidate，以確保 mapping digest 與 provenance 一致。

## 設計

### 範圍

- 以 Git HEAD 與目前 dirty workbook 比較 Location/Bracket 兩欄，另外記錄 ISL DT 中被移除的非 mapping 輔助欄位。
- 讓 same-location multi-bracket 診斷只比較一般 bracket identity，landmark 繼續列入 landmark rows。
- 加入 `123-01`、`CR283-15`、`SI`、`Mid Point`、`POA` 與 marker/bracket 同位置的回歸測試。
- 在 `outputs/metadata-review-2026-09-23/` 產生新的 review candidates、provenance manifest 與 validator JSON/Markdown。

### 不在範圍

- 修改或覆蓋原始 metadata workbook、TL-BK mapping workbook、runtime `config/`、既有 candidate 或既有 audit。
- 自動決定 overlap/marker 業務意義、修正人工 source rows 或核准 candidate。
- 對未 mapping 的額外工作表欄位作回填或復原。

### 資料流與錯誤處理

`TOV1050 TL-BK No.xlsx` 的 `Location`/`Bracket` → 標準化 candidate（Location 乘 1000，canonical 公尺）→ provenance（保留來源列與 digest）→ validator（檢查 parity、invalid rows、mapping identity 與 digest）。任何錯誤或未核准 review finding 都保留在 audit，不直接寫入 runtime。

### 驗收標準

- validator 把 `123-01` 與 `CR283-15` 辨識為一般 bracket；把使用者列舉的 landmarks 排除於 physical bracket identity conflicts。
- landmark 與一般 bracket 共用同一位置時，不再誤報為同位置多 bracket；landmark 本身仍可追溯。
- mapping workbook 每個有效 Location 僅按 Km 乘 1000 轉換為 m，不誤將 `98150.2` 當作 Km。
- 更新後 candidates 的 mapping digest 與目前 workbook 相符，且候選輸出與原始/runtime workbook 分離。
- targeted metadata tests 通過；audit 清楚列出仍需人工決策的問題。

## 執行紀錄

### 實作

更新 validator 的 landmark 篩選，避免 landmark 參與 physical same-location Bracket 衝突；加入 `POA804-01` landmark prefix 保護；ambiguous overlap audit 增加可追溯的 source row examples；validator audit 檔名改用實際產生日，避免寫入 2026-09-02 固定檔名。candidate/provenance/audit 產生在 `outputs/metadata-review-2026-09-23/`，未更動原始 workbook 或 runtime metadata。

### 測試與 debug

```text
python -m pytest backend/tests/test_tov1050_metadata_candidates.py -q
12 passed

python scripts/validate_tov1050_metadata_candidates.py --candidate-dir outputs/metadata-review-2026-09-23/candidates --output-dir outputs/metadata-review-2026-09-23/validation-final --lines ISL KTL LAR_AEL LAR_TCL TKL TKS TWL
exit 0; all seven lines review_required; no error findings
```

### 驗收結果

一般 bracket/landmark 分類測試通過；mapping digest 與 source digest 均匹配，provenance mismatch 為 0。同 Bracket 多位置與 exact duplicate identity 均為 0。candidate 仍 review-only。等候使用者確認 workbook row deletions、ISL DT removed helper columns、reversed intervals 與 TWL DT row 46 後才可再產生候選／評估 promotion。

## Linear 同步

- 最後同步時間：2026-09-23
- Issue 狀態：In Progress
- Next action：使用者確認 audit 第「目前最需要人工確認的項目」所列 workbook 變更後，再重生／驗證 candidate。
- 阻塞／需要決策：AEL DT、DRL UT/PL、KTL DT、ISL UT/DT 刪除列；ISL DT 輔助欄位移除；ISL/KTL DT 反向 interval；TWL DT row 46 空 Location。

## 相關檔案

- `00 Reference Document/TOV1050 TL-BK No.xlsx`
- `scripts/validate_tov1050_metadata_candidates.py`
- `scripts/standardize_tov1050_metadata.py`
- `backend/tests/test_tov1050_metadata_candidates.py`
- `docs/audits/2026-09-23-tov1050-metadata-review-update.md`
- `outputs/metadata-review-2026-09-23/`
