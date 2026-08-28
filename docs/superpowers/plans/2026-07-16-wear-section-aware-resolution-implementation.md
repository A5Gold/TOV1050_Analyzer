# Wear Calculator Section-Aware Resolution Development Plan

> **執行要求：** 開始 development 時，主 agent 必須啟用至少一個 subagent，負責 bounded implementation 或獨立驗證。所有 agent 共用 canonical worktree，必須先劃分檔案 ownership，禁止同時修改同一檔案。

**日期：** 2026-07-16

**狀態：** 已核准，development 已完成

**設計依據：** `docs/superpowers/specs/2026-07-16-wear-section-aware-resolution-design.md`

**Canonical workspace：** `C:\Smart Maintanence\TOV640_Analyzer`，branch `main`
**風險等級：** HIGH / CRITICAL

## 1. 目標

修正 Wear Calculator complete-cycle preview 的兩個使用者可見問題：

1. Exception Report 已提供 Section，但後端未用它區分 EAL Mainline、RAC、LOW S1 與 LMC，造成正常 metadata overlap 被誤判為 ambiguity 並回傳 422。
2. Wear cycle preview/save 狀態未完整隸屬個別分析 tab，切換 tab 或非同步回應返回時，結果會被清除或寫入錯誤 tab。

同時將 `Wear Calculator Logic` 對話框所有可見內容改為繁體中文，且說明文字必須與實際 Section-aware resolver 一致。

## 2. 已確認根因

### 2.1 後端 metadata classification

現行資料有兩種合法重疊：

- 不同 Section 共用 chainage envelope，例如 EAL Mainline 與 RAC/LMC/LOW S1。
- 同一 metadata source row 的 `Tension Length` 包含 primary TL 及 overlap TL，例如 `70, X32, L02`、`48,50`。

原 resolver 只以 Line、Track、Chainage 和 raw TL token 找候選。Metadata loader 又把複合 TL 拆成失去來源 row 與順序的同等 interval，因此無法知道：

- Exception Report 的量測屬於哪個 Section。
- 哪個 token 是該 source row 的 primary TL。
- 多個候選是否來自同一複合 row，或來自真正衝突的獨立 rows。

這會使以下合法量測被錯誤拒絕：

- EAL Mainline，chainage `130170.25`，raw TL `70, X32, L02`。
- TML Mainline，chainage `126335.25`，raw TL `48,50`。

### 2.2 Frontend tab lifecycle

Cycle preview、loading、error、save result 與 preview file snapshot 若放在 store-level shared state，`setActiveTab()`、reset 或稍後返回的 request response 會影響目前 active tab，而不是最初發出 request 的 tab。結果是切頁後 preview 消失、不同 tab 狀態互相洩漏，或 stale response 恢復已失效結果。

## 3. 核准解法

### 3.1 Section-aware resolver

每個 `MetadataInterval` 保存兩類 bounds：

- canonical `section`
- `source_priority`
- 完整 `source_tension_lengths` tuple
- canonical `from_m/to_m`：維持既有複合 row 等分後 geometry
- `source_from_m/source_to_m`：原始複合 row 完整 bounds，只供 measurement source matching

Metadata loader 必須把既有等分後 geometry 與原始 source-row context 合併，不能用 full source bounds 取代 canonical bounds。Resolver 依下列固定順序判定：

1. Normalize Line、Track、Section、Chainage 與 raw TL tokens。
2. 僅保留 Section、Track、Chainage 與 candidate TL 相符的 intervals。
3. 若 raw TL 是複合值，優先選取完整 `source_tension_lengths` signature 相符的 source row。
4. 在保留候選中選取最低 `source_priority` 的 distinct TL。
5. 最低 priority 只有一個 TL 時回傳該 TL。
6. 無候選時回報 gap；同最低 priority 仍有多個 TL 時保留 ambiguity 422。

不得採用「最窄 interval 優先」，不得將一筆 measurement 複製到所有 overlap TL，也不得修改 metadata workbooks。

EAL DN `70,X32,L02` 的 regression contract 必須保持：`70=130126–130143.6333`、`X32=130143.6333–130161.2667`、`L02=130161.2667–130178.9`；full source bounds `130126–130178.9` 只能用於 source-row matching。

### 3.2 Section source and validation

- 優先使用 Exception Report ChartData record 的 `Section`。
- 空白 Section 才由已偵測的 filename/source segments 推導。
- 明確 Section 與 segment 不一致時回傳可追查的 422，不靜默改寫。
- Error detail 保留 filename、raw TL、Section、Track、Chainage 與 resolver reason。

### 3.3 Tab-scoped async state

每個 `WearTab` 自己保存 preview、preview files、loading、save loading、error、accepted conflicts 與 last save。Preview/save request 以 `tabId + requestId` 鎖定原 tab；輸入變更、reset 或 close tab 時使舊 request 失效。切換 active tab 本身不得清除任何 cycle state。

### 3.4 UI 文案

保留現有 MUI Dialog 結構、theme、密度與操作，只翻譯可見文案並修正 resolver 說明。此為 operational tool，不加入新視覺語言、動畫或 dependency。

## 4. 影響分析與安全界線

codebase-memory 已把以下呼叫鏈標為 HIGH/CRITICAL：

- `MetadataManager.get_tension_length_lookup` / source row loading
- `load_line_metadata`
- `resolve_measurement_tension_length`
- `_parse_complete_cycle_source` 與 `POST /api/calculation/wear`
- frontend `previewCycle`、`acceptConflict`、save flow、`WearCalculatorView`

因此每個 task 完成後必須執行 focused regression tests；最後必須重新 index repository 並驗證 affected scope，才可提交。

Subagent review 另確認目前 draft 有兩個 P1，development 必須先修正才可視為完成：

- 直接把 full source bounds 複製給所有 tokens 會改變 canonical geometry、coverage、save 及 export contract。
- 每筆 measurement 重建 `_group_intervals_by_tl()` 會造成大型 TML 報表近似 `measurements × intervals`；一次 141,216-row 實測曾達 438.2 秒。

不得改動或清理：

- `config/EAL metadata.xlsx`、`config/TML metadata.xlsx`
- `docs/test data/` 的既有刪除
- `.codex-temp/`、`.codex_tmp/`、`docs/Chainge metadata comparison/`
- `docs/Tension Length Drawing/`、`outputs/`、`tmp_old.xlsx`、`work/`

先前使用者工作已保存於 checkpoint commit `97c416c chore: checkpoint latest workspace updates`。Feature commit 只能包含本 plan 明列的檔案。

## 5. Subagent 執行協議

開始 Task 2 前必須啟用 subagent。建議 ownership：

- **Backend subagent：** Task 2 至 Task 4 的 resolver、API contract 與 backend tests，或對主 agent 的 backend 實作做獨立 review。
- **主 agent：** Task 1、Task 5、Task 6、整合、測試、browser workflow 與提交。

共享 worktree 規則：

1. 每次只允許一個 agent 編輯某個檔案。
2. Subagent 不得 stage、commit、restore、delete 或 clean。
3. 每次 production symbol 編輯前，使用 codebase-memory `search_graph` 與 `trace_path` 做 impact analysis。
4. Subagent 完成後，主 agent 必須重讀 diff、執行測試並對結果負責。
5. 若發現 scope 外修改，保留它並停止 staging 該檔案，不得自行還原。

## 6. 實作工作

### Task 1：建立 regression baseline 與真實案例 fixture

**Files：**

- Test: `backend/tests/test_wear_cycle_metadata.py`
- Test: `backend/tests/test_calculation_api.py`
- Reference only: `.codex-temp/metadata-analysis/*.mjs`
- Reference only: `.codex_tmp/inspect_tml_metadata.mjs`

- [ ] 以 codebase-memory 定位 resolver、parser、metadata loader 及 direct callers。
- [ ] 寫出 EAL `70, X32, L02` 與 TML `48,50` 的 failing unit tests。
- [ ] 寫出同 chainage、不同 EAL Section 的 tests。
- [ ] 寫出未知非空 Section 與跨 line Section alias 必須被拒絕的 tests。
- [ ] 寫出兩個獨立 primary rows 仍 ambiguity 的 safety test。
- [ ] 寫出 composite signature `40,44` 優先於重疊 single `44` row 的 regression test。
- [ ] 寫出複合 row canonical geometry 仍按既有規則等分的 regression test。
- [ ] 寫出 complete-cycle preview 只建立一次 metadata resolution index 的 call-count test。
- [ ] 驗證 RED 失敗原因確實是缺少 Section/source-row 身分，不是 fixture 錯誤。

Focused command：

```powershell
cd backend
python -m pytest tests/test_wear_cycle_metadata.py -q
```

### Task 2：保存 metadata source row 身分

**Files：**

- Modify: `backend/app/core/calculation/wear_cycle_types.py`
- Modify: `backend/app/core/metadata.py`
- Modify: `backend/app/core/calculation/wear_cycle_metadata.py`
- Test: `backend/tests/test_metadata_manager.py`
- Test: `backend/tests/test_wear_cycle_metadata.py`

- [ ] 擴充 `MetadataInterval` 的 `section`、`source_priority`、`source_tension_lengths`、`source_from_m`、`source_to_m`，提供相容預設值。
- [ ] 新增只供 wear-cycle resolver 使用的 enriched loader；它必須同時提供既有等分後 geometry 與原始 source-row context，不得破壞 aggregated lookup contract。
- [ ] 清理千位分隔符、空白 row 與 reversed bounds，保留完整複合 TL cell。
- [ ] `load_line_metadata()` 保存 canonical split bounds、full source bounds、相同 source signature 與 token index。
- [ ] 明確測試 EAL DN `70,X32,L02` 三個 canonical bounds 沒有被擴成同一 full row。
- [ ] Sorting key 納入 Section、priority 與 source signature，確保 deterministic output。
- [ ] 執行 metadata manager 與 wear metadata focused tests。

### Task 3：實作 Section normalization 與 deterministic resolution

**Files：**

- Modify: `backend/app/core/calculation/wear_cycle_metadata.py`
- Test: `backend/tests/test_wear_cycle_metadata.py`

- [ ] 新增 EAL/TML 明確 Section aliases；禁止模糊 substring 推測。
- [ ] 未知非空 Section、EAL/TML 跨 line aliases 必須明確拒絕，不得 fallback。
- [ ] 新增 segment-to-Section mapping，並拒絕跨 Section segment set。
- [ ] Resolver 新增 optional Section，保留舊 fixture 的相容入口。
- [ ] 建立 immutable `MeasurementResolutionIndex`，在一個 preview 開始時把 intervals 分組及驗證一次。
- [ ] 套用 exact composite source signature，再比較 source priority。
- [ ] Gap 與 ambiguity error 加入 canonical Section。
- [ ] 確認 `M07,M05` 等非第一 token 唯一 match 的舊行為仍正確。
- [ ] 確認 track 不會透過 broad `Siding` bounds 錯誤跨方向匹配。
- [ ] Resolver measurement loop 使用預建 index，不得逐筆呼叫 `_group_intervals_by_tl()`。

### Task 4：把 Exception Report Section 傳入 API flow

**Files：**

- Modify: `backend/app/api/endpoints/calculation.py`
- Test: `backend/tests/test_calculation_api.py`

- [ ] `_parse_complete_cycle_source()` 從 detected segments 建立 source Section。
- [ ] `_build_complete_cycle_preview()` 建立一次 resolution index，並傳給所有 source parsers。
- [ ] 每筆 record 有明確 Section 時 normalize；空白時 fallback 到 source Section。
- [ ] 明確 record Section 與 source segments 衝突時回傳 422。
- [ ] 呼叫 resolver 時傳入 measurement Section。
- [ ] Error detail 包含 filename、TL、Section、Track 與 Chainage。
- [ ] 執行 API contract tests，確認兩個正常 overlap 不再 422，真正 ambiguity 仍 422。

Focused command：

```powershell
cd backend
python -m pytest tests/test_metadata_manager.py tests/test_wear_cycle_metadata.py tests/test_calculation_api.py -q
```

### Task 5：把 cycle workflow state 完整移入 WearTab

**Files：**

- Modify: `frontend/src/store/useWearStore.ts`
- Modify: `frontend/src/views/WearCalculatorView.tsx`
- Test: `frontend/src/store/__tests__/useWearStore.test.ts`
- Test: `frontend/src/views/__tests__/WearCalculatorView.test.tsx`

- [ ] 先使用 codebase-memory trace `previewCycle`、`saveCycle`、`acceptConflict`、`setActiveTab` 與 view callers。
- [ ] 將 cycle preview/save/error/loading state 納入 `WearTab` 與 `makeTab()`。
- [ ] `setActiveTab()` 僅改 active ID，不清除 tab state。
- [ ] Preview/save request 以發出時的 tab ID 和 request ID 更新原 tab。
- [ ] Input mutation、reset、close tab 時 invalidate 該 tab 舊 requests。
- [ ] Save 只在 digest 仍相同時清除該 preview，避免覆蓋更新中的分析。
- [ ] View 只從 `activeTab` 讀取 cycle state。
- [ ] 測試切頁保留結果、跨 tab request completion、stale response、save race 與 last-save persistence。

### Task 6：繁體中文 Logic Dialog

**Files：**

- Modify: `frontend/src/components/Calculation/WearAlgorithmDialog.tsx`
- Modify: `frontend/src/views/WearCalculatorView.tsx`
- Test: `frontend/src/components/Calculation/__tests__/WearAlgorithmDialog.test.tsx`

- [ ] 保留現有 MUI component structure、spacing、theme tokens 與 responsive behavior。
- [ ] 將標題、流程、規則、顏色、workspace、延伸作業與按鈕改為繁體中文。
- [ ] Tooltip 改為 `線耗計算邏輯`。
- [ ] 文案明確說明 `Section + Track + Chainage + source-row primary token`。
- [ ] 不使用「最窄 interval」或 ChartData TL fallback 等不正確描述。
- [ ] 驗證 keyboard close、focus、light/dark theme 行為不回歸。

Frontend commands，第一個 npm process 必須設定 system CA：

```powershell
$env:NODE_USE_SYSTEM_CA='1'
cd frontend
npm test -- --run src/store/__tests__/useWearStore.test.ts src/views/__tests__/WearCalculatorView.test.tsx src/components/Calculation/__tests__/WearAlgorithmDialog.test.tsx
npm run build
```

維持 `strict-ssl=true` 與 HTTPS registry，不得停用 TLS validation。

### Task 7：整合驗證、scope audit 與提交

**Files：** 不新增 production scope。

- [ ] 使用兩份真實 Exception Reports 執行 parser/resolver workflow。
- [ ] EAL chainage `130170.25` 解析為 TL `70`。
- [ ] TML chainage `126335.25` 解析為 TL `48`。
- [ ] 啟動 canonical root `npm run dev`，用實際 UI 驗證 tab persistence 與繁中 dialog。
- [ ] 執行完整 backend suite；若 property-based tests 長時間執行，保留可追查的完成/逾時狀態，不得宣稱通過。
- [ ] 以真實或 100k+ synthetic TML batch 記錄 elapsed time，並以 call-count 證明 grouping/index build 固定為一次；不得接受 multi-minute regression。
- [ ] 執行 frontend focused tests、build，並視現有 suite 時間執行 full Vitest。
- [ ] 重新 `index_repository(mode="moderate", persistence=true)`。
- [ ] 使用 codebase-memory 驗證 changed symbols 的 callers 與 affected scope。
- [ ] 執行 `git diff --check`、`git diff --name-only`、`git status --short`。
- [ ] 確認 feature diff 沒有 metadata workbook、analysis artifacts 或其他使用者檔案。
- [ ] 只 stage 本 plan 明列的 feature files，再建立單一清楚的 feature commit。

Backend full-suite command：

```powershell
cd backend
python -m pytest -q
```

## 7. Acceptance Criteria

- [ ] `POST /api/calculation/wear` 對指定 EAL/TML 合法 overlap 不再回傳 422。
- [ ] Mainline、RAC、LOW S1 與 LMC 在相同 chainage 下使用 report Section 對應 metadata。
- [ ] 真正同 Section、同 priority 的多 primary conflict 仍被拒絕。
- [ ] Canonical TL bounds、coverage、save 及 export geometry 與變更前相同。
- [ ] 每個 preview 只建立一次 resolution index，不存在逐 measurement metadata regrouping。
- [ ] 切換 Wear 分析 tabs 不會重置 preview、error、conflict acceptance 或 last save。
- [ ] 非同步回應只更新原 tab；stale response 不可恢復失效 preview。
- [ ] Logic Dialog 所有可見文字為繁體中文，並準確描述 resolver。
- [ ] Aggregation、save、export、pending-change guard 與 theme 行為沒有 regression。
- [ ] 既有 user changes 與 untracked artifacts 均保留。

## 8. Rollback 與資料安全

此變更不含 database schema migration，也不寫回 metadata workbooks。若 rollout 發現新 Section alias，先以明確 alias、fixture 與 regression test 補充；不得以任意 substring 或 interval width 猜測。若 resolver 無法唯一判定，維持 422 safety boundary，讓 metadata 問題可被發現與修正。

## 9. Development 開始門檻

Development 只有在以下條件全部成立後才開始：

- [ ] 使用者已審閱本 plan。
- [ ] Subagent ownership 已分配。
- [ ] Canonical checkout、branch、status 與 checkpoint commit 已再次確認。
- [ ] 待編輯 symbols 已完成 codebase-memory impact analysis。
- [ ] 第一個 production change 之前已有對應 failing regression test。
