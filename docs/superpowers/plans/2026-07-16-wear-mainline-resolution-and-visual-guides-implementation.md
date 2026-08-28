# Wear Mainline Resolution and Visual Guides Implementation Plan

> **執行狀態：** 設計已由使用者核准，brainstorming 已完成。本計畫提交後直接開始 development，不再要求第二次設計核准。

**日期：** 2026-07-16

**設計依據：** `docs/superpowers/specs/2026-07-16-wear-mainline-resolution-and-visual-guides-design.md`

**Canonical workspace：** `C:\Smart Maintanence\TOV640_Analyzer`

**Branch / baseline：** `main` at `20f7d21`

**保護範圍：** 不還原、刪除、清理或 stage 現有已刪除 fixture、參考截圖、workbook、分析輸出與未追蹤 artifact；不得修改 `config/EAL metadata.xlsx` 或 `config/TML metadata.xlsx`。

## 1. 交付目標

分三個可獨立驗證的 phase 完成核准設計：

1. Phase A 建立中央、line-specific、table-driven TL scope classifier，讓結果、coverage、Expected TLs、Diagnostic Gaps、save 與 export 僅包含 MAINLINE；加入 strict Section gap 後才可啟動的 exact Section transition，並移除 Analysis 的 Siding dataset filter。
2. Phase B 以既有 Zustand staged change set 為唯一真相，補齊 add/edit/delete_cell/delete_row 的橙色語意、icon、繁中 label、keyboard/focus、legend 與 pending summary；將 `線耗計算邏輯` 提升為四個 feature tabs 共用入口，重整 dialog 為實際操作決策流程。
3. Phase C 將 About runtime 從 iframe/IPC 移至可維護 React components，預設 `操作指南`，另設 `開發者參考`，保留 legacy HTML artifact 並提供 diagnostics loading/success/failure、responsive、light/dark 與 accessible chart alternatives。

## 2. 不可破壞的既有合約

- Section-aware resolution、source row identity、ordered composite source signature、source priority 與 canonical split geometry 維持不變。
- `preview_digest`、`data_version`、conflict acceptance、atomic save、preview-level index、deterministic preview/save 與 tab-scoped async state維持不變。
- TL scope 只由 line-specific identity/series 判斷，不以 canonical `Track` 判斷。
- canonical `Track == "Siding"` 但具 UP/DN physical intervals 的合法 mainline TL 必須保留。
- `Neutral Section` 是 SIDING；任何其他未知非空 TL identity 是 UNKNOWN 並 fail closed。
- Section transition 只在 strict Section match 為真正 gap 時執行；不得轉換 chainage、擴大 interval、nearest match、general Mainline fallback 或改變 source bounds。
- Transition 必須同 Line、Track、原始 numeric Chainage、完整 ordered composite signature，且 source bounds 包含原始 Chainage；只容許唯一 source row 與唯一 primary TL。
- Approved siding 是預期排除，不產生 result、conflict、coverage、gap、save 或 export；UNKNOWN 維持 HTTP 422 且 diagnostic 必須可行動。
- Frontend staged save 失敗必須保留 pending state；feature tab 切換不得觸發分析 tab 或 staged navigation guard 的副作用。

## 3. Codebase-Memory 與風險門檻

已解析 persistent graph project：`C-Smart-Maintanence-TOV640_Analyzer`。每次 production symbol 編輯前必須：

1. `search_graph` 取得 exact qualified name。
2. `trace_path(direction="inbound", risk_labels=true)` 檢查 production callers，必要時加 outbound/data-flow trace。
3. 若風險為 HIGH 或 CRITICAL，先在 commentary 明確警告，再開始該 symbol 編輯。
4. 先讀對應 source 與 focused tests；graph snippet 不完整時才以直接 file read 補足。
5. 每次 commit 前重跑 affected-scope query、`git diff --check`、exact file list 與 status audit。

預期主要 production symbols：

- Backend：`load_line_metadata`、`build_measurement_resolution_index`、`resolve_measurement_tension_length`、`build_segment_coverage`、`build_cycle_preview`、`_parse_complete_cycle_source`、`_build_complete_cycle_preview`、wear export/save route helpers。
- Analysis：`WearAnalysisCharts`、physical-interval direction selector、`WearCalculatorView`。
- Staged records：`WearHistoryPivotTable`、`WearRecordsPanel`、相關 presentation helpers。
- Shared dialog：`WearCalculatorView`、`CycleTabBar`、`WearAlgorithmDialog` 或新增 feature toolbar boundary。
- About：`AboutView`、`loadDiagnostics`、Electron `resolveVisualGuidePath` 與 preload `loadVisualGuideHtml`（cleanup 前先證明無 caller）。

## 4. Phase A Required Subagent Protocol

Phase A 必須啟用至少一個 subagent，且與主 agent 不可同時改同一檔案。

**指定 ownership：**

- Subagent 僅建立新的 `backend/tests/test_wear_tl_scope_real_files.py`，負責 classifier collision matrix、UNKNOWN diagnostics 與 available real-file regression；同時閱讀 production classifier contract 並回報獨立 review findings。
- 主 agent 擁有全部 production code、既有 backend tests、frontend code 與 integration。
- Subagent 不得 stage、commit、restore、delete、clean 或修改 production files。
- 若預定 test filename 已存在或有衝突，subagent 必須先回報，由主 agent指定另一個全新 isolated test file。
- 主 agent 合併前重讀 subagent diff、核對 fixture availability，並執行該 test file。

## 5. Phase A Implementation

### A1. TL scope classifier 與 contract tests

**Production：**

- Add `backend/app/core/calculation/wear_tl_scope.py`。
- 必要時只在 `wear_cycle_metadata.py` 匯入並使用 classifier；classifier 本身不得依賴 workbook Track。

**Tests：**

- Add `backend/tests/test_wear_tl_scope.py`。
- Subagent add `backend/tests/test_wear_tl_scope_real_files.py`。

**Steps：**

- [ ] 定義 `TensionLengthScope` enum：`MAINLINE`、`SIDING`、`UNKNOWN`。
- [ ] 共用 `normalize_line_group()` 與 `normalize_tension_length()`，避免第二套 normalization。
- [ ] 以 anchored tables/rules 實作 TML/EAL identity families；explicit exception 必須在 general family 前判斷。
- [ ] TML mainline：M01-M33、D01-D60、U01-U55、slash-U variants、K01-K16、01-74。
- [ ] TML siding：MX、MD、MP24、EM1、PT、CT、KX、X、W1-1、27A、101-103、Neutral Section。
- [ ] EAL mainline：H、H23D/H26D、D01-D31、U、slash-U、K、1-76、69B/70A、L、T2/T3、X36/X37/X50/X53/X54。
- [ ] EAL siding：HX02、X01-X39 except X36/X37、LX positive integer、D32/D33、EM1、Neutral Section。
- [ ] 測試 padded/unpadded、family boundaries、TML 27/27A、EAL D31/D32/D33、special X/general X、D/MD、X/MX/KX、cross-line suffix、unknown text/number。
- [ ] UNKNOWN diagnostic contract 包含 Line、sheet/source row（可得時）、raw ordered signature 與 unknown identity。
- [ ] 驗證 canonical Track `Siding` 不影響 mainline classification。

### A2. Mainline-only metadata, aggregation, coverage and export

**Production candidates：**

- `backend/app/core/calculation/wear_cycle_metadata.py`
- `backend/app/core/calculation/wear_cycle_aggregation.py`
- `backend/app/core/calculation/wear_cycle_io.py`
- `backend/app/api/endpoints/calculation.py`
- `backend/app/api/endpoints/wire_wear.py`（只在 graph 證明 export/save 有獨立篩選責任時）

**Tests：**

- `backend/tests/test_wear_cycle_metadata.py`
- `backend/tests/test_wear_cycle_aggregation.py`
- `backend/tests/test_calculation_api.py`
- wear export/save focused tests discovered by graph/test inventory。

**Steps：**

- [ ] Metadata load/index 保留完整 records 供 exact resolution，但在 denominator/expected identity boundary 套 scope classifier。
- [ ] Measurement 先依 Section-aware/source-signature resolution 唯一選出 primary TL，再分類；不得先把 mixed composite source row 整列刪除。
- [ ] MAINLINE 進入 identity de-duplication、conflicts、aggregation 與 accepted-source coverage。
- [ ] SIDING 在 conflict generation 前排除，且不出現在 unresolved 或 diagnostics。
- [ ] UNKNOWN 加入 blocking unresolved diagnostic，preview/save route 回 HTTP 422。
- [ ] `build_segment_coverage()` 的 denominator、present set、Expected TLs 與 Diagnostic Gaps 都只使用 mainline identities。
- [ ] `coverage_percent = round(100 * present_mainline_tls / expected_mainline_tls, 2)`；missing segment、empty denominator、range intersection 與 advisory semantics 不變。
- [ ] Saved records 與 Excel rows 只接受 mainline records；避免另外實作與 preview 不同的 scope 規則。
- [ ] 用 supplied TML export 驗證 164 UP/DN result records，coverage/gaps 不再包含 siding TL。

### A3. Exact Section transition

**Production candidates：**

- `backend/app/core/calculation/wear_cycle_types.py`（若 index 需要 exact transition lookup field）
- `backend/app/core/calculation/wear_cycle_metadata.py`
- `backend/app/api/endpoints/calculation.py`

**Tests：**

- `backend/tests/test_wear_cycle_metadata.py`
- `backend/tests/test_calculation_api.py`
- isolated subagent real-file tests。

**Steps：**

- [ ] 在 `MeasurementResolutionIndex` 一次建立 strict Section index 與 transition lookup；禁止 measurement loop 重建 metadata grouping。
- [ ] Strict Section resolve 成功時完全跳過 transition。
- [ ] Strict gap 才以 same Line/Track/original Chainage/exact ordered signature/source bounds 查 candidates。
- [ ] 候選必須折疊為一個 unique source row，並由 source priority 得出一個 unique primary TL。
- [ ] 成功後仍經 scope classifier；MAINLINE 繼續、SIDING 排除、UNKNOWN 422。
- [ ] 無 exact signature、零 row、多 row、多 primary、true gap/ambiguity 均保留 422。
- [ ] Diagnostic 保留 filename、raw TL、report Section、Track、Chainage 與 transition failure reason。
- [ ] RAC `111301.0 / 23,25` regression 唯一選 primary `23`，不改座標、不改 interval。
- [ ] 對 Mainline、LOW S1、LMC 原有 HTTP 200 建 regression，防止 transition 擴大適用範圍。

### A4. Analysis direction behavior

**Production candidates：**

- `frontend/src/components/Calculation/WearAnalysisCharts.tsx`
- `frontend/src/utils/wearAnalysisPresentation.ts` 或 graph 找到的實際 selector module。
- `frontend/src/views/WearCalculatorView.tsx`（只在 props contract 需要調整時）。

**Tests：**

- `frontend/src/components/Calculation/__tests__/wearAnalysisPresentation.test.ts`
- `frontend/src/components/Calculation/__tests__/WearAnalysisCharts.test.tsx`（不存在時新增）。

**Steps：**

- [ ] 移除 visible `Siding` checkbox 與對應 dataset filter state。
- [ ] UP 依 record physical intervals 是否包含 UP；DN 同理。
- [ ] canonical Track `Siding` 的 mixed-direction mainline record 在任一適用方向選中時可見。
- [ ] 保留 chart metric、selection、tab-scoped state 與 empty state。
- [ ] 更新繁中 visible labels，維持 existing MUI control density、keyboard 與 light/dark theme。

### Phase A gate and commit sequence

1. `feat: classify wear tension length scope`
2. `fix: restrict wear cycles to mainline scope`
3. `fix: resolve exact wear section transitions`
4. `fix: filter wear analysis by physical direction`

每個 commit 只 stage 明列檔案；classifier commit 可包含 subagent isolated tests。Phase A 完成前執行 focused backend tests、available real-file tests、Analysis Vitest，並確認 RAC/Mainline/LOW/LMC/TML acceptance。

## 6. Phase B Implementation

### B1. Staged-record semantic presentation

**Production candidates：**

- `frontend/src/components/Calculation/WearHistoryPivotTable.tsx`
- `frontend/src/components/Calculation/WearRecordsPanel.tsx`
- Add `frontend/src/components/Calculation/wearPendingPresentation.ts`（只有當可明顯移除重複 token/label 邏輯時）。

**Tests：**

- `frontend/src/components/Calculation/__tests__/WearHistoryPivotTable.test.tsx`
- `frontend/src/components/Calculation/__tests__/WearRecordsPanel.test.tsx`
- presentation helper unit test（若新增 helper）。

**UX contract：**

- `add` label `待新增` + existing MUI Add icon。
- `edit` label `待更新` + existing MUI Edit icon。
- `delete_cell` label `待刪除` + existing MUI Delete icon，保留舊值並加 strikethrough。
- `delete_row` label `整列待刪除`，整列連續橙色語意，Cycle Date cell 顯示 label。
- Add new cycle row 時同時標示 Cycle Date cell 與新增 record cell。

**Steps：**

- [ ] 使用 `theme.palette.warning` 與 MUI `alpha()` 分別校準 light/dark background、border、text、hover、focus；不寫死 `warning.50`。
- [ ] icon + label + shape/strikethrough 確保不以顏色單獨傳達。
- [ ] 保留 double-click edit、Enter/Space、hover/focus delete、touch overflow、Save/Discard 與 failed-save retention。
- [ ] heading 旁加入 compact legend；不建 nested cards。
- [ ] bottom pending summary 改繁中，`role="status"` + `aria-live="polite"`，數量與 kinds 可掃讀。
- [ ] 測試 existing row add、new row add、cell edit、cell delete、row delete、keyboard、failed save、legend、summary、light/dark semantic tokens。

### B2. Shared algorithm entry and dialog

**Production candidates：**

- `frontend/src/views/WearCalculatorView.tsx`
- `frontend/src/components/Calculation/CycleTabBar.tsx`
- `frontend/src/components/Calculation/WearAlgorithmDialog.tsx`
- Add `frontend/src/components/Calculation/WearFeatureToolbar.tsx`（若 shared entry 無適當現有 boundary）。

**Tests：**

- `frontend/src/views/__tests__/WearCalculatorView.test.tsx`
- `frontend/src/components/Calculation/__tests__/WearAlgorithmDialog.test.tsx`
- new toolbar test（若新增 component）。

**Steps：**

- [ ] 將 analysis-only algorithm action 移至 feature-level toolbar，Analysis、線耗紀錄、Dashboard、Projection 均顯示 info icon + `線耗計算邏輯`。
- [ ] Entry 不修改 active analysis tab，不繞過 staged-record navigation guard。
- [ ] Dialog desktop 是 wide scroll surface + sticky title bar；mobile `fullScreen`；close button 有 accessible name。
- [ ] 內容依 `開始前先確認`、`系統如何判斷`、`結果如何保存` 三個操作問題組織。
- [ ] 使用 unframed flow bands、decision table、status examples、threshold table 與小型 diagram；禁止 nested card grid。
- [ ] 準確描述 file/segment、Section/Track、strict resolver、exact transition、MAINLINE/SIDING/UNKNOWN、identity de-dup、lower-value conflict selection、mainline coverage、save gates、atomic persistence、staged changes。
- [ ] Visible prose 全繁中；technical identifiers 保留 English；focus trap/Escape 由 MUI Dialog 提供。

### Phase B gate and commits

5. `feat: clarify staged wear record changes`
6. `feat: share wear calculation guidance`

Phase B gate：interaction tests、keyboard/focus、failed-save retention、四 tabs entry、dialog content、desktop/mobile、light/dark screenshots全部通過。

## 7. Phase C Implementation

### C1. React About guide architecture

**Production：**

- Rewrite `frontend/src/views/AboutView.tsx` as page shell/default tabs only。
- Add `frontend/src/components/About/AboutGuideTabs.tsx`。
- Add `frontend/src/components/About/OperatorGuide.tsx`。
- Add `frontend/src/components/About/DeveloperReference.tsx`。
- Add `frontend/src/components/About/GuideSectionNav.tsx`。
- Add `frontend/src/components/About/GuideVisuals.tsx` for reusable accessible flow/timeline/chart primitives。
- Add `frontend/src/components/About/DiagnosticsPanel.tsx`。
- Add `frontend/src/components/About/aboutGuideContent.ts` for structured verified copy/source references。

**Artifact：**

- Preserve `docs/tov640-analyzer-visual-guide.html` unchanged as legacy artifact。

**Tests：**

- Rewrite/extend `frontend/src/views/__tests__/AboutView.test.tsx`。
- Add focused component/content tests under `frontend/src/components/About/__tests__/`。

**Steps：**

- [ ] Default `操作指南` tab follows import → metadata align → six algorithm decisions → conflicts/coverage → save/export/diagnose。
- [ ] `開發者參考` covers architecture, API/state ownership, end-to-end flows, Section/source signatures/canonical geometry/indexes, digest/version/audit/atomic save/tab scope/staged set, error taxonomy, regression layers, DB/package diagnostics。
- [ ] Charts：threshold ranges、repeat timeline、one-year window、wear decision、mainline coverage numerator/denominator、staged states、stagger span；invented values label `範例`。
- [ ] 每個 chart 提供 textual/table equivalent 與 accessible summary。
- [ ] Desktop compact navigator + wide content；mobile one-column、scrollable tabs；stable headings and no text clipping。
- [ ] Diagnostics skeleton 符合 final panel geometry；failure 只影響 developer diagnostics section，不隱藏 guide。
- [ ] 沿用 MUI、Railway Blue、6px radius、existing typography；不新增 design-system dependency、marketing hero、gradient、glass、card wall 或 ornamental motion。
- [ ] Content self-audit：繁中自然、technical contract 與 production/tests一致、零裝飾式 em dash、無虛構 precision。

### C2. Obsolete iframe runtime cleanup

**Candidates：**

- `electron/main.js`
- `electron/preload.js`
- `frontend/src/types/electron.d.ts` 或 graph 找到的 bridge type。
- packaging config references discovered by literal/config search。

**Steps：**

- [ ] React About commit/build 通過後，重新 index graph。
- [ ] 對 `resolveVisualGuidePath`、IPC handler、`loadVisualGuideHtml` 做 search_graph + inbound trace。
- [ ] 只有在所有 runtime callers 已消失時刪除 IPC/bridge/package reference。
- [ ] 保留 legacy HTML file；cleanup commit 不包含 React guide files。
- [ ] Build/package path smoke test 證明 Electron 不再依賴 guide HTML runtime。

### Phase C gate and commits

7. `feat: replace about iframe with react guide`
8. `chore: remove obsolete visual guide bridge`（只有 impact analysis 證明可安全移除時）

## 8. Verification Matrix

### Backend focused

```powershell
Set-Location backend
python -m pytest tests/test_wear_tl_scope.py tests/test_wear_tl_scope_real_files.py -q
python -m pytest tests/test_wear_cycle_metadata.py tests/test_wear_cycle_aggregation.py tests/test_calculation_api.py -q
```

若任一歷史 fixture 已刪除，記錄 unavailable path 與被 synthetic test 覆蓋的 contract；不得還原 fixture。

### Backend full

```powershell
Set-Location backend
python -m pytest -q
```

### Frontend Vitest shards

每個 npm process 都必須在同一 PowerShell command 先設定 `$env:NODE_USE_SYSTEM_CA='1'`：

```powershell
$env:NODE_USE_SYSTEM_CA='1'; Set-Location frontend; npm test -- --run --shard=1/4
$env:NODE_USE_SYSTEM_CA='1'; Set-Location frontend; npm test -- --run --shard=2/4
$env:NODE_USE_SYSTEM_CA='1'; Set-Location frontend; npm test -- --run --shard=3/4
$env:NODE_USE_SYSTEM_CA='1'; Set-Location frontend; npm test -- --run --shard=4/4
```

### Lint/build

```powershell
$env:NODE_USE_SYSTEM_CA='1'; npm run lint
$env:NODE_USE_SYSTEM_CA='1'; npm run build
```

使用 root scripts，不直接呼叫 Vite/Electron/electron-builder。維持 `strict-ssl=true` 與 HTTPS registry。

### Canonical dev and Playwright

```powershell
$env:NODE_USE_SYSTEM_CA='1'; npm run dev
```

- [ ] 只從 canonical root 啟動，若 port 被占用先查明既有 server，不繞過 root script。
- [ ] Real EAL Mainline、RAC、LOW S1、LMC browser workflows。
- [ ] Real TML complete cycle，結果 164 UP/DN records，coverage/gaps 無 siding identity。
- [ ] Analysis 無 Siding filter，mixed-direction mainline 在 UP/DN 適用方向可見。
- [ ] Staged add/edit/delete_cell/delete_row 與 failed save retention。
- [ ] Algorithm dialog 由四 feature tabs 開啟且不改 active analysis/tab navigation state。
- [ ] About operator/developer tabs、diagnostics loading/success/failure。
- [ ] Desktop/mobile、light/dark screenshots；檢查 overlap、clipping、blank chart、focus visibility 與 contrast。

## 9. Commit Safety Procedure

每個 commit 依固定順序執行：

1. Graph affected-scope/trace audit；HIGH/CRITICAL 先警告。
2. Focused tests。
3. `git diff --check`。
4. `git diff --name-only` 與 `git status --short`，辨別 feature files 與 user artifacts。
5. 使用 explicit `git add -- <exact files>`；禁止 `git add .`、`git add -A`。
6. `git diff --cached --name-only` 與 cached diff review。
7. Narrow commit；記錄 hash。
8. Production commit 後重新 index codebase-memory，再做下一個 phase 的 graph impact lookup。

## 10. Final Acceptance

- [ ] Phase A、B、C production 與 tests 均完成，沒有 partial runtime switch。
- [ ] RAC `111301.0 / 23,25` 為 HTTP 200 且 exact transition primary TL 是 `23`。
- [ ] Mainline、LOW S1、LMC 維持 HTTP 200；true gaps/ambiguity/unknown 維持 422。
- [ ] TML output、coverage、Expected TLs、Diagnostic Gaps、save、export 都是 mainline-only。
- [ ] Approved siding 不形成 conflict 或 diagnostic；unknown 值有 actionable error。
- [ ] Analysis 不再以 Siding dataset filter 隱藏合法 mixed-direction mainline records。
- [ ] Staged semantics、legend、summary、keyboard/focus、light/dark 全部符合核准 contract。
- [ ] `線耗計算邏輯` 從四個 tabs 可達，dialog 描述與 backend 真實順序一致。
- [ ] About React 是唯一 runtime source；legacy HTML artifact 保留。
- [ ] Full pytest、四 Vitest shards、ESLint、production build 與 Playwright acceptance 完成或逐項如實列出不可用原因。
- [ ] Final graph re-index 與 affected-scope verification 完成。
- [ ] Final status 保留所有原有 user changes/artifacts，feature commits 未包含 screenshots/workbooks/metadata files。
- [ ] Final report 列出 exact hashes、test counts/results、unavailable deleted fixtures、screenshots path、affected scope與 residual risks。
