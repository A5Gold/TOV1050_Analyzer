# Wear Calculator Section-Aware TL Resolution Design

日期：2026-07-16
狀態：已由使用者核准
影響等級：HIGH / CRITICAL

## 1. 背景與問題

Wear Calculator 的 complete-cycle preview 會載入整條路線的所有 tension-length metadata，然後以 Line、Track、Chainage 與 Exception Report 的 raw Tension Length 判定每筆量測所屬 TL。Exception Report parser 已讀取 `Section`，但目前 resolver 沒有使用該欄位，metadata loader 也會把複合 TL 欄位拆成同等候選，因而錯誤產生 ambiguity。

已用真實檔案驗證：

- `20260617_EAL_D3_LOW-TAP_Exception_Report.xlsx` 的 chainage `130170.25` 為 `Section=Mainline`，raw TL 為 `70, X32, L02`。
- `20260511_TML_D5-D3_TUM-HUH_Exception_Report.xlsx` 的 chainage `126335.25` 為 `Section=Mainline`，raw TL 為 `48,50`。
- EAL Mainline metadata row 以 `70` 為第一個 token；對應 LMC row 以 `L02` 為第一個 token。
- TML overlap metadata row 以 `48` 為第一個 token。

掃描 EAL 與 TML metadata 的所有複合 TL row 後，第一個 token 一貫代表該 sheet/range 的主要 TL，後續 token 代表 overlap 伴隨 TL。現行 loader 丟失這項順序資訊。

此外，Wear store 把 cycle preview 狀態放在全域 store level。`setActiveTab()` 切換分析工作分頁時會主動清除 preview、檔案快照、錯誤及 loading，因此使用者返回原分頁時看不到已完成結果。

## 2. 目標

1. 以 Exception Report 的 Section 正確區分 EAL Mainline、RAC、LOW S1 與 LMC metadata。
2. 保留 metadata 複合 TL row 的 token priority，以 primary TL 解決正常 overlap。
3. 對真正的 metadata primary conflict 繼續回報 422，不以猜測掩蓋資料錯誤。
4. 每個 Wear 分析工作分頁獨立保存完整 cycle workflow state。
5. 將 Wear Calculator Logic Dialog 的所有可見內容改為繁體中文，並描述實際 resolver 行為。
6. 保留現有業務彙總、validation、儲存及匯出行為。

## 3. 非目標

- 不修改 `config/EAL metadata.xlsx` 或 `config/TML metadata.xlsx`。
- 不以最窄 interval 作為 TL 判定規則。
- 不把一筆 `wear_min` 複製至所有 overlap TL。
- 不改變 WearResult 以 tension length 為 cycle business key 的既有聚合規則。
- 不重設 Wear Calculator 的視覺語言、導覽架構或功能分頁。
- 不清理、還原、暫存或提交目前 worktree 內既有的使用者變更與分析產物。

## 4. Domain Decision

採用 `Section + metadata row token priority`。

每個 metadata lookup row 的複合 TL 欄位依原始順序展開。第一個 token 的 `source_priority` 為 `0`，第二個為 `1`，依此類推。Resolver 只在符合 record Section、Track、Chainage 與 raw TL 候選的 intervals 中比較 priority。

判定結果：

- EAL Mainline `70, X32, L02` 選擇 `70`。
- EAL LMC `L02, 70, X38` 選擇 `L02`。
- TML Mainline `48,50` 選擇 `48`。
- 如果同一 Section 與 chainage 有兩個不同 TL 均來自獨立 primary row，兩者 priority 同為 `0`，維持 ambiguity error。

此規則不依 interval 長度猜測，也不重複量測值。

### 4.1 Geometry invariance

Source-row identity 與 canonical TL geometry 是兩個不同 contract，必須同時保留。既有 `_aggregate_tension_lengths()` 會把複合 row 的 overlap range 等分給各 TL；這些分段 bounds 繼續供 canonical TL、coverage、aggregation、save 及 export 使用。Resolver 另存原始 source-row bounds，只用來判斷某 chainage 是否屬於該複合 row 及比對完整 token signature。

例如 EAL DN `70,X32,L02` 的既有 canonical geometry 為：

- `70`：`130126–130143.6333`
- `X32`：`130143.6333–130161.2667`
- `L02`：`130161.2667–130178.9`

不得把三個 TL 的 canonical bounds 都擴成原始 row 的 `130126–130178.9`。

## 5. Backend Design

### 5.1 Metadata model

擴充 `MetadataInterval`：

- `section`：該 interval 所屬的 canonical Section。
- `source_priority`：TL 在原始 metadata row 複合欄位內的 zero-based index。
- `source_tension_lengths`：原始 metadata row 的完整 normalized TL token tuple，用來把 Exception Report 的 raw composite TL 對回同一 source row。
- `source_from_m` / `source_to_m`：原始複合 row 的完整 bounds，只供 measurement source-row matching 使用；既有 `from_m` / `to_m` 繼續代表等分後 canonical geometry。

新欄位提供向後相容預設值，使既有測試 fixture 及其他 Wear cycle consumers 不需全面改寫。

### 5.2 Metadata loading

`load_line_metadata()` 繼續透過 `METADATA_SOURCES` 載入所有 line metadata。Loader 必須同時取得既有等分後 geometry 與原始 source-row context，在展開複合 TL 時：

1. 保存目前 source tuple 的 Section。
2. 使用 token index 保存 `source_priority`。
3. 在每個展開後的 interval 保存相同的完整 `source_tension_lengths` tuple。
4. 保存原始 source row 的 normalized full bounds，但不以它取代 canonical `from_m` / `to_m`。
5. 保留現行 from/to normalization、track 與 deterministic sorting。

排序鍵需納入 Section 與 priority，確保相同輸入得到相同順序。

### 5.3 Section normalization

新增集中式 Section normalization：

- EAL canonical values：`Mainline`、`RAC`、`LOW S1`、`LMC`。
- TML canonical value：`Mainline`。
- 接受既有大小寫及已知 LOW aliases，但不接受無法識別的自由文字。

每筆 ChartData record 優先使用 Excel `Section`。欄位缺失或空白時，由已偵測的 source segment 推導 Section：RAC segments 對應 `RAC`，LOW 對應 `LOW S1`，LMC segments 對應 `LMC`，其餘對應 `Mainline`。

如果明確 Section 與 filename/source segment 不相容，回報包含 filename、raw Section 與 segment 的 validation error，不靜默改寫。

### 5.4 Measurement resolution

`resolve_measurement_tension_length()` 增加 Section input，處理順序如下：

1. Normalize Line、Track、Section 與 Chainage。
2. 依 raw TL 保留原始 candidate order並去除重複值。
3. 找出 Section、Track、Chainage 與 candidate TL 均符合的 metadata intervals。
4. 如果 raw TL 包含多個 token，優先保留 `source_tension_lengths` 與 raw token tuple 完整一致的 metadata source row；這可排除同一 chainage 上屬於其他 single/composite row 的候選。
5. 如果沒有完整 signature match，保留所有符合 Section、Track、Chainage 與 candidate TL 的 intervals 作安全 fallback。
6. 在保留的 intervals 中，依 distinct TL 取其最佳 `source_priority`。
7. 若最低 priority 只有一個 distinct TL，回傳該 TL。
8. 若沒有 match，回報 measurement gap，錯誤內容加入 Section。
9. 若最低 priority 有多個 distinct TL，回報真正 ambiguity，錯誤內容加入 Section、候選 TL 與來源 sheet。

`_parse_complete_cycle_source()` 必須把每筆 `record.section` 的 canonical value 傳入 resolver。Section 僅參與解析，不改變既有跨 track/section 合併相同 TL 的 cycle aggregation contract。

### 5.5 Preview-level resolution index

完整 preview 只可把 metadata intervals 分組及驗證一次。`_build_complete_cycle_preview()` 建立 immutable measurement-resolution index，再傳給每個 source parser；resolver 不得為每筆 measurement 重建 `_group_intervals_by_tl()`。此要求避免大型 TML Exception Report 退化成 `measurements × intervals`，造成 UI 長時間看似沒有結果。

## 6. Frontend State Design

Cycle workflow state 應由各 `WearTab` 擁有，而不是由整個 store 共用。每個 tab 保存：

- `cyclePreview`
- `cyclePreviewFiles`
- `cyclePreviewLoading`
- `cycleSaveLoading`
- `cycleError`
- `lastCycleSave`

行為規則：

- `setActiveTab()` 只切換 `activeTabId`，不清除任何 tab 的 cycle state。
- Line、line class、cycle date、uploaded files 等輸入變更，只清除目前 tab 的失效 preview。
- 關閉 tab 只移除該 tab 狀態。
- Preview 與 save response 必須更新發出請求的原 tab，不可因使用者切換 tab 而寫入目前 active tab。
- 每個 tab 使用獨立 request generation/revision guard。輸入改變、reset 或 tab 關閉後，舊回應不得覆蓋新狀態。
- 切回已完成 tab 時，preview、錯誤、conflict acceptance 與 save result 必須完整恢復。

View 仍透過 active tab 顯示狀態，功能分頁 `Analysis`、`Wire Wear Records`、`Dashboard` 與 `Projection` 的既有導覽和 pending-change guard 保持不變。

## 7. Logic Dialog Design

維持現有 MUI Dialog、Grid、Paper、Chip、theme tokens、響應式排列及操作流程，不新增 dependency，也不進行視覺重設。

所有可見文字改為繁體中文，包括：

- `Wear Calculator Logic` 改為 `線耗計算邏輯`。
- 分析彙總流程、批次彙總規則、顏色判定、線耗紀錄工作區及延伸作業內容。
- `Close` 改為 `關閉`。

TL resolution 說明必須準確描述：先依 Section、Track 與 Chainage 選取 metadata，再依 metadata row 的 primary token 判定 TL；只有真正的 primary conflict 才會停止分析。

介面沿用現有低變異、低動效、高資訊密度的 operational product register。不得加入行銷式版面、裝飾動畫或新的卡片層級。

## 8. Error Handling

- 本次兩個正常 overlap 案例不再產生 422。
- 真正 metadata gap、未知 Section、Section/segment 衝突及多個 primary candidate 仍回傳 422。
- Error detail 應包含 filename、raw TL、Track、Section、Chainage 與具體 resolver reason，讓 metadata 問題可追查。
- Frontend 保留既有 contextual error 顯示，不把 validation error 降級為成功或空結果。

## 9. Testing Strategy

### Backend unit and API tests

- `load_line_metadata()` 保存 Section 與 token priority。
- 複合 row 保存完整 source bounds，但 canonical TL bounds/coverage 與既有等分 geometry 完全相同。
- EAL Mainline `70, X32, L02` 在 `130170.25` 解析為 `70`。
- 相同 chainage 的 LMC row 解析為 `L02`。
- TML Mainline `48,50` 在 `126335.25` 解析為 `48`。
- TML Mainline `40,44` 在同時重疊 single `44` row 時，優先匹配完整 composite signature 並解析為 `40`。
- 非第一 token 是唯一 chainage match 時仍可正確選取，保留既有 `M07,M05` regression behavior。
- 沒有完整 composite signature match且兩個獨立 primary rows 同時匹配時，仍拋出 ambiguity。
- 空白 Section fallback、未知 Section、Section/segment conflict 均有明確測試。
- 未知非空 Section 與跨 line Section alias 不得 fallback，均須有明確 rejection test。
- `_parse_complete_cycle_source()` 確實傳遞 record Section。
- 一個 complete-cycle preview 只建立一次 resolver index；measurement loop 不重建 interval grouping。

### Frontend tests

- 完成 preview 後切換 Wear 工作分頁再返回，結果仍存在。
- 不同 tab 的 preview、錯誤、loading、conflict 與 save result 不互相洩漏。
- 切換 tab 時進行中的請求完成後，只更新原 tab。
- 修改原 tab 輸入後，過期 response 不得恢復舊 preview。
- Logic Dialog 的標題、主要規則與按鈕均為繁體中文。

### Integration verification

- 使用兩份真實報告執行 parser/resolver 驗證，確認不再因指定 chainage 產生 ambiguity。
- 以真實或等量 synthetic TML measurement batch 驗證 indexing 次數固定為一次，並記錄 preview elapsed time，禁止 multi-minute regression。
- 執行相關 backend pytest、frontend Vitest 與 TypeScript checks。
- 第一個 npm/npx/npm exec 命令必須在該 process 設定 `NODE_USE_SYSTEM_CA=1`，並維持 HTTPS registry 與 `strict-ssl=true`。
- 啟動 canonical root dev server，使用 browser workflow 驗證 tab persistence、錯誤狀態及繁中 Logic Dialog。

## 10. Acceptance Criteria

1. EAL 指定報告的 `130170.25` 解析為 TL `70`，不再回傳 ambiguity 422。
2. TML 指定報告的 `126335.25` 解析為 TL `48`，不再回傳 ambiguity 422。
3. EAL RAC、LOW S1、LMC 與 Mainline 在重疊 chainage 下依 report Section 使用正確 metadata source。
4. 真正的同 Section primary metadata conflict 仍被拒絕。
5. Canonical TL bounds、coverage、aggregation、save 與 export geometry 不因 source signature 支援而改變。
6. 每次 preview 只建立一次 resolver index，大型報表不出現逐 measurement 重建 metadata grouping 的效能退化。
7. 切換 Wear 分析工作分頁不會重置已完成 cycle preview 或結果。
8. 不同 Wear tabs 不會顯示彼此的 preview、錯誤或 save state。
9. Wear Calculator Logic Dialog 所有可見文字均為繁體中文，且邏輯說明與實作一致。
10. 現有 aggregation、save、export、pending-change guard 及暗色/亮色 theme 行為不回歸。
11. 既有 dirty worktree 內容保持原樣，提交只包含本功能明確建立或修改的檔案。

## 11. Development Subagent Requirement

開始 development 時，主 agent 必須啟用至少一個 subagent 參與實作或獨立驗證，不可由主 agent 單獨完成全部 development。

建議分工：

- 主 agent：負責整體整合、frontend per-tab state、繁中 dialog、最終測試與 browser workflow。
- Subagent：負責 bounded backend task，例如 Section-aware metadata model/resolver 與 backend regression tests；或在 backend 由主 agent 實作時，負責獨立 code review 與真實 workbook validation。

所有 agent 共用同一 canonical worktree，因此必須先約定檔案 ownership，避免同時編輯同一檔案。Subagent 不得清理、還原、暫存或提交使用者既有 dirty changes。主 agent 在整合前仍須使用 codebase-memory MCP 重新檢查待編輯 symbol 的 impact，並對所有 subagent 產出負最終責任。

## 12. Rollout and Safety

- 先完成 backend resolver 與 regression tests，再遷移 frontend state，最後更新 dialog copy。
- 不做 metadata workbook migration。
- 保留 ambiguity error 作為 metadata integrity safety boundary。
- 若真實報告出現未在本規格定義的 Section alias，先新增明確 mapping 與測試，不採用模糊 substring 猜測。
- 完成程式變更後重新 index repository，使用 codebase-memory 驗證 affected scope，再進行提交。
