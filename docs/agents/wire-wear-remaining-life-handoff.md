# Wire Wear Remaining Life 修正交接摘要

## Workspace 基線

- Repository: `C:\Smart Maintanence\TOV640_Analyzer`
- Canonical checkout: 是
- Branch: `main`
- Worktree: 原本已有大量 dirty changes；不得 reset、checkout、revert、刪除、覆蓋或廣泛 stage。
- 本次未 commit、未 stage。
- Codebase-memory project: `C-Smart-Maintanence-TOV640_Analyzer`

## 使用者已批准的需求

1. Remaining Life Cycle 與 Projection Tab 共用目前選取的 thickness threshold。
2. `Estimated Life` 顯示年／月及預計到達日期，例如 `4 年 7 個月（2031-03-18）`。
3. 新增 Wear Calculator 的 `Remaining Life Cycle` tab。
4. 表格欄位：Tension Length、Latest Remaining Thickness、Wear Rate (- mm/year)、Estimated Life。
5. 圖表顯示 remaining days 曲線；預設顯示 EAL 與 TML 各自最差的有效 TL，選取其他 TL 後加入該 TL 曲線。
6. insufficient data、non-positive rate 顯示 `N/A / Insufficient data`；already-at-threshold 必須可辨識。
7. Latest Summary 的 Metric 與 TL 欄位需緊湊固定寬度。
8. 30-Year Thickness Projection 的 `TL count reaching threshold` y 軸只顯示整數刻度。

## 已確認根因／技術發現

- 既有 regression 規則在 `backend/app/core/calculation/wear_cycle_analytics.py::fit_tl_trend()`：每個歷史日期先取平均，再對 elapsed years 做線性回歸。
- 少於兩個歷史日期回傳 `insufficient_data` 且 rate 為 `null`。
- 回歸斜率非正回傳 `non_positive_rate` 且 rate 為 `null`。
- Projection 已有 `already_at_threshold`、`insufficient_data`、`non_positive_rate`、`outside_horizon` status 分流。
- frontend 透過 `frontend/src/api/client.ts` 將 snake_case API contract 映射成 camelCase。
- `WearLatestSummaryTable` 由 `WearRecordsPanel` 使用，再由 `WearCalculatorView` 掛載，屬 HIGH/CRITICAL shared hotspot。
- Projection chart 位於 `frontend/src/components/Calculation/wearRecordCharts.tsx`。

## 本 chat 已完成的修改（尚未完整整合）

### Backend

- `backend/app/core/calculation/wear_cycle_analytics.py`
  - 新增 `build_remaining_life(records, threshold_mm, as_of)`。
  - 以既有 `_trend_row()` / `fit_tl_trend()` 計算每 TL 的 latest thickness、rate、crossing date、remaining days。
  - 對 eligible record 產生最多約 24 個等距 curve points，最後一點為 crossing date / 0 days。
  - status 不合格時不拋出整體 endpoint error。
- `backend/app/api/endpoints/wear_records.py`
  - 新增 `GET /calculation/wear-records/remaining-life?threshold_mm=...`。

### Frontend

- `frontend/src/types/api.ts`
  - 新增 `WearRemainingLifeRow`、`WireWearRemainingLifeResponse`。
- `frontend/src/api/client.ts`
  - 新增 `fetchWireWearRemainingLife()` 及 snake_case -> camelCase mapping。
- `frontend/src/store/useWearRecordsStore.ts`
  - 新增 remaining-life state、loading/error state 與 `loadRemainingLife()`。
- `frontend/src/components/Calculation/WearLatestSummaryTable.tsx`
  - Metric 固定約 148px、TL 固定約 82px，使用 fixed table layout。
- `frontend/src/components/Calculation/wearRecordCharts.tsx`
  - Projection y-axis 設為 `tickmode: 'linear'`, `dtick: 1`, `min: 0`。

## 驗證結果

- `python -m compileall backend/app/core/calculation/wear_cycle_analytics.py backend/app/api/endpoints/wear_records.py`：通過。
- `python -m pytest backend/tests/test_wear_cycle_analytics.py backend/tests/test_wear_records_api.py -q`：`39 passed`。
- 使用兩個日期的 reference-like records 直接呼叫 `build_remaining_life()`：成功產生 crossing date、remaining days 與單調下降 curve。
- 尚未完成：backend remaining-life focused tests、frontend tests、TypeScript、ESLint、production build、browser acceptance、10,000+ rows check、codebase-memory final re-index/impact verification。

## 尚待完成工作

1. 完成並審查 `Remaining Life Cycle` tab shell。
2. 將 Projection 的 active threshold 傳給 Remaining Life tab；切換 threshold 後兩者一致。
3. 完成 Remaining Life table：所有 TL 可見、selected TL 搜尋／清除、N/A/status 視覺化。
4. 完成 Remaining Life chart：預設 EAL/TML worst rows，selected TL 可加入，x 軸日期、y 軸 remaining days。
5. 補測試：empty、insufficient、non-positive、already-at-threshold、outside/finite crossing、API mapping、tab selection、N/A display、曲線非空。
6. 確認 `WireWearRemainingLifeResponse` 型別的 nullable 欄位與現有 API contract 完全一致。
7. 重新執行 codebase-memory `index_repository(mode="moderate", persistence=true)`，再對 changed symbols 做 impact verification。
8. 執行 `git diff --check`，只檢查不 stage。

## 下一個 Chat 可直接使用的 Prompt

```text
請在 canonical checkout C:\Smart Maintanence\TOV640_Analyzer 繼續實作 Wire Wear Remaining Life 修正。

先讀取 docs/agents/wire-wear-remaining-life-handoff.md，並先執行：
git rev-parse --show-toplevel
git branch --show-current
git status --short

不要建立 worktree，不要 reset、checkout、revert、刪除、覆蓋或廣泛 stage dirty changes，不要 commit。
使用 codebase-memory project C-Smart-Maintanence-TOV640_Analyzer；修改既有 symbol 前先做 impact analysis，修改後重新 index 並驗證 impact。
Frontend 修改遵守 $impeccable 與 $design-taste-frontend。

完成 handoff 中所有尚待完成工作，尤其是：
- Remaining Life Cycle tab
- threshold 與 Projection 共用
- all-TL table、搜尋/選擇/清除、selected curve
- EAL/TML worst default curve
- N/A / Insufficient data / non-positive / already-at-threshold status
- Latest Summary 緊湊欄寬與 Projection y-axis 整數刻度
- focused backend/frontend tests、TypeScript、focused ESLint、production build、browser desktop/narrow acceptance、git diff --check
- final codebase-memory re-index 與 impact verification

所有 npm/npx/npm exec process 必須設定 NODE_USE_SYSTEM_CA=1，維持 HTTPS registry 與 strict-ssl=true。
完成後以繁體中文回報修改檔案、根因、測試結果、效能比較、residual risks、是否可安全整合。
```

## Residual risks

- `build_remaining_life()` 目前尚未由 API test 覆蓋；需確認 empty/non-finite records 的 JSON serialization。
- Remaining Life chart 尚未接入 tab shell，store state 目前只是 contract 基礎。
- 既有 worktree 包含大量非本次變更；後續只能逐檔審查，不得以整體 checkout 還原。
