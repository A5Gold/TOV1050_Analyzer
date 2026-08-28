# TOV1050 Analyzer Development Plan

## 1. Objective

將目前複製自 TOV640 Analyzer 的 Windows Electron desktop analyzer 收斂為完整的 TOV1050 模式：

`TOV1050 CSV -> 清洗/預處理 -> TOV640 detector contract -> exceptions/report/charts`

TOV640 專案只作為演算法規格與回歸參考，絕不修改 `C:\Smart Maintanence\TOV640_Analyzer`。

## 2. Non-negotiable Constraints

- 所有 TOV640 演算法相關變更前，先閱讀來源專案的 `docs/architecture.md`、TOV1050 migration Background、mapping workbook、Raw data 與 config。
- TOV1050 專案所有修改只發生在 `C:\Smart Maintanence\TOV1050_Analyzer`。
- `Km` 直接成為 `Chainage`，不合併 `KM`/`LOCATION`。
- `HeightWire1..4`、`StaggerWire1..4`、`WearWire1..4` 必須轉成 canonical columns。
- `1.#IO` 轉成 NaN 並忽略；原始前 100 rows 與後 100 rows 忽略。
- Height 不套用 TOV640 的 `+5300` 修正。
- 保留原始 row number、清洗統計、錯誤診斷。
- AEL/TCL 是邏輯 line；`LAR_AEL metadata.xlsx` 與 `LAR_TCL metadata.xlsx` 是 workbook 名稱。
- `TKS` 是 TKL session，使用 `TKS metadata.xlsx`，不是獨立 line。
- 輸出檔名必須包含使用者選定的 session，並保留 station start/end。
- 不在 TOV1050 UI 暴露 EAL/TML 名稱或選項。

## 3. Current Product Profile

### Lines

`AEL`, `TCL`, `DRL`, `ISL`, `KTL`, `TWL`, `TKL`

### Sessions

- AEL/TCL/ISL/KTL/TWL: `Mainline`
- DRL: `Mainline`, `PL`
- TKL: `Mainline`, `TKS`

### Directions

`UT`, `DT`

### Metadata mapping

| Logical line/session | Workbook |
|---|---|
| AEL / Mainline | `LAR_AEL metadata.xlsx` |
| TCL / Mainline | `LAR_TCL metadata.xlsx` |
| DRL / Mainline | `DRL metadata.xlsx` |
| DRL / PL | `DRL metadata.xlsx`, `PL track type` sheet |
| ISL / Mainline | `ISL metadata.xlsx` |
| KTL / Mainline | `KTL metadata.xlsx` |
| TWL / Mainline | `TWL metadata.xlsx` |
| TKL / Mainline | `TKL metadata.xlsx` |
| TKL / TKS | `TKS metadata.xlsx` |

TOV1050 workbook sheets are discovered from the workbook. Typical sheets are `threshold`, `UT track type`, `DT track type`, optional `PL track type`, and `location type`.

### TOV1050 與 TOV640 差異

下表是實作時必須維持的產品差異。TOV640 的 detector 判定語意可以重用，但輸入、metadata、命名與資料庫產品設定不可直接沿用。

| 項目 | TOV640 Analyzer | TOV1050 Analyzer | 實作要求 |
|---|---|---|---|
| 原始檔案格式 | `.datac`，通常以分號 `;` 分隔 | `.csv`，通常以逗號 `,` 分隔 | TOV1050 上傳、拖放、Electron file dialog 與提示文字使用 CSV |
| 資料規模 | 約 50,000 rows、約 10 MB | 約 900,000 rows、約 150 MB | 使用 chunk processing，避免多次完整 DataFrame 複製 |
| Chainage 來源 | 由 `KM` 與 `LOCATION` 組合或換算 | `Km` 已是 Chainage | 直接映射 `Km -> Chainage`，不得合併 `KM`/`LOCATION` |
| Height 欄位 | `WHGT1c..4` | `HeightWire1..4` | 轉為 canonical `height1..4` |
| Height 修正 | 需要套用 `+5300` | 已是實際值 | TOV1050 不得套用 `+5300` |
| Stagger 欄位 | `STG1c..4` | `StaggerWire1..4` | 轉為 canonical `stagger1..4` |
| Wear 欄位 | `RWH1mm..4` | `WearWire1..4` | 轉為 canonical `wear1..4` |
| 缺測值 | 空白，以及部分 wear sentinel（例如 `6.56`） | 字串 `1.#IO` | 先轉成 NaN，再從 detector 輸入忽略，並計入清洗統計 |
| 啟動/結束資料 | 忽略前後 20 rows | 忽略前後 100 rows | 依原始 row number trim，不能以清洗後 row number 取代 |
| 原始 row lineage | 以 TOV640 loader 的 row context 為主 | 必須保留原始 row number 與清洗原因 | 分析 response、診斷輸出與錯誤訊息保留 lineage |
| Line | 主要是 `EAL`、`TML` 等 TOV640 line | `AEL`、`TCL`、`DRL`、`ISL`、`KTL`、`TWL`、`TKL` | TOV1050 UI/API 只暴露 TOV1050 lines；`TKS` 不是 line |
| Track / direction | 原始資料通常提供 `UP` / `DN` 的 `TRACK` 欄位 | CSV 沒有可靠的 track 欄位 | 由使用者選擇 `UT` 或 `DT`，再注入分析 context |
| Session / section | `Mainline`、`RAC`、`LOW S1`、`LMC` 等 TOV640 分類 | AEL/TCL/ISL/KTL/TWL: `Mainline`；DRL: `Mainline`/`PL`；TKL: `Mainline`/`TKS` | session 由 line 動態限制；`TKS` 使用 TKS metadata |
| SHO_AWE | 不作為 TOV640 session 概念 | 代表 station start 到 station end | 應放在檔名與 task context 的 station range，不得當 session |
| Metadata workbook | `EAL metadata.xlsx`、`TML metadata.xlsx` | `LAR_AEL metadata.xlsx`、`LAR_TCL metadata.xlsx`、DRL/ISL/KTL/TKL/TKS/TWL workbooks | 由 line + session 明確 mapping；不可 fallback 到 EAL/TML workbook |
| Metadata sheets | 常見 `Exception Boundarys`、`EAL UP`、`EAL DN`、`LMC UP` 等固定 sheet | `threshold`、`UT track type`、`DT track type`、`PL track type`、`location type` | 先讀取實際 workbook sheet/header，再渲染或解析 |
| Threshold schema | 以 `Class` 及多個 `... L1/L2/L3` wide 欄位為主 | `Location Type`、`Track Type`、`Exc Type`、`min`、`max`、`remark` long form | TOV1050 editor 保留 long form；adapter 只在 detector boundary 做 normalization |
| Location mapping | 以 TOV640 boundary/class interval 對應 | `location type` sheet 的 `startKM`/`endKM` 對應 location class | 無法唯一解析、缺 sheet 或 interval 重疊時 fail closed |
| Detector | Height/Wear/Stagger aggregate、threshold gate、L1/L2/L3、consecutive grouping、最嚴重點選取等 | 使用相同 exception algorithm contract | 重用判定核心；差異只放在輸入 adapter 與 metadata adapter |
| 輸出檔名 | 舊格式可能只含 line/track/section 或 task/station | `YYYYMMDD_LINE_TRACK_SESSION_STATION_START_STATION_END_ARTIFACT.ext` | 所有 TOV1050 report/raw/repeated export 都帶 session 與 station range |
| Database Record 預置資料 | 可包含 EAL/TML 一年期 seed | TOV1050 fresh database 應為空 | EAL/TML seed 只能顯式 opt-in 給 legacy regression，不可在產品啟動自動載入 |
| Packaged config | 舊版可能只帶 TOV640 metadata | 必須包含全部 TOV1050 workbook 與 config | Electron development/packaged mode 使用同一套 TOV1050 config resolution |

### 相同與不同的邊界

- **可以重用**：TOV640 的 threshold gate、aggregate 規則、L1/L2/L3 分級、consecutive-mask grouping、每組最嚴重點選取、exception ID 與 report 欄位語意。
- **必須改寫或包裝**：CSV loader、canonical column mapping、缺測值處理、前後 100 rows trim、row lineage、TOV1050 metadata workbook/sheet mapping、session/direction validation、輸出命名與 packaged config。
- **不可直接移植**：`+5300` Height 修正、KM/LOCATION 合併、EAL/TML 選單、固定 `Exception Boundarys`/`EAL UP`/`TML UP` sheet 假設，以及 EAL/TML built-in database seed。

## 4. Work Packages

### WP0: Baseline and repository safety

1. Run codebase-memory indexing and inspect architecture, routes, stores, Electron startup, and database initialization.
2. Record `git status`; never reset or overwrite unrelated user changes.
3. Confirm no file under TOV640 is modified.
4. Establish targeted test commands and a clean temporary database strategy.

Exit criteria: baseline build/test results and a documented list of legacy TOV640 dependencies.

### WP1: TOV1050 contract and adapter

1. Keep `tov1050_contract.py`, `tov1050_data_ingestion.py`, and `tov1050_metadata.py` as the boundary around copied TOV640 code.
2. Validate CSV headers, delimiter, numeric coercion, `1.#IO`, trimming, row lineage, and diagnostics.
3. Validate filename parsing and output naming:
   `YYYYMMDD_LINE_TRACK_SESSION_STATION_START_STATION_END_ARTIFACT.ext`.
4. Ensure metadata resolution is explicit and fail-closed. No nearest interval or silent legacy fallback.
5. Keep detector semantics unchanged after canonical conversion.

Exit criteria: adapter tests pass on the supplied 476-row fixture (`276` retained after 100/100 trim), and large-file processing has measured memory/time behavior.

### WP2: Backend analysis and exports

1. Use TOV1050 loader and metadata manager whenever the selected line is a TOV1050 line.
2. Preserve original row number and cleaning statistics in the analysis response and diagnostic export.
3. Pass selected direction/session to the detector as context without changing TOV640 threshold/grouping semantics.
4. Ensure raw/report/repeated exports use the TOV1050 filename contract and selected session.
5. Verify packaged config resolution includes all TOV1050 workbooks.

Exit criteria: API tests cover every line/session/direction and generated filenames are deterministic.

### WP3: Database Record screen and persistence

1. Use the seven TOV1050 line tabs and dynamic session tabs.
2. Use `UT`/`DT` filters and TOV1050 sections only.
3. Use TOV1050 line/session values in batch deletion, import, export, and shared types.
4. Fresh TOV1050 databases must start empty; copied EAL/TML seed is disabled by default.
5. Keep explicit legacy seed tests/tools working only when they opt in.
6. Do not delete or rewrite an existing user's database automatically. Provide a diagnostic/migration path if an old database is detected.

Exit criteria: no EAL/TML seed rows appear in a fresh TOV1050 database; records imported through the UI retain line/session/station context.

### WP4: Exception Generator screen

1. Replace `.datac` wording and mock paths with `.csv` wording.
2. Use TOV1050 line, session, and `UT`/`DT` options.
3. Keep drag/drop, Electron browse, progress, error, chart, table, raw export, and report export workflows.
4. Validate line changes reset invalid sessions to `Mainline`.
5. Keep task number and station start/end available for naming, with `SHO_AWE` treated as station range rather than session.

Exit criteria: a user can complete CSV upload and report export without seeing EAL/TML labels or legacy file extensions.

### WP5: Settings / Metadata Editor screen

1. List only TOV1050 workbooks.
2. Discover sheets from the selected workbook.
3. Render TOV1050 `threshold` rows using `Location Type`, `Track Type`, `Exc Type`, `min`, `max`, and `remark`.
4. Render direction/location interval sheets using their actual workbook headers, not `Exception Boundarys`, `EAL UP`, or `LOW S1` assumptions.
5. Save only the selected sheet, preserving all other sheets and creating a backup.
6. Keep validation appropriate to the TOV1050 long-form threshold schema.

Exit criteria: every shipped workbook can be opened, inspected, edited, saved, reloaded, and backed up without schema loss.

### WP6: Shared types, Electron, and packaging

1. Replace shared default line/direction/session types used by the target screens with TOV1050 types.
2. Hide or explicitly disable unsupported copied TOV640-only wear/history UI instead of exposing EAL/TML controls.
3. Electron open-file filter prioritizes TOV1050 CSV while retaining only explicitly supported auxiliary formats.
4. Verify development startup and packaged startup use the same TOV1050 config directory and database policy.
5. Confirm `concurrently`, `wait-on`, and frontend dependencies are installed from the lockfile.

Exit criteria: `npm run dev` starts frontend, Electron, and backend; packaged resources contain all TOV1050 config workbooks.

## 5. Testing Strategy

### Unit tests

- Header canonicalization and numeric cleaning.
- `1.#IO` handling and ignored-row counts.
- First/last 100 raw rows removal.
- Km-to-Chainage identity and no Height offset.
- Filename parse/build and session validation.
- Workbook/session/sheet mapping.
- TOV1050 threshold normalization.
- Fresh database seed policy.

### Component tests

- Seven Database Record line tabs and dynamic sessions.
- TOV1050 line/session/direction selectors in Exception Generator.
- CSV wording and file dialog behavior.
- Metadata workbook list and dynamic sheet labels.
- No visible EAL/TML text in the three target screens.

### API/integration tests

- Analyze one fixture per line/session/direction where metadata exists.
- Export names include session and station range.
- Invalid metadata, missing sheet, overlapping interval, and missing chainage fail closed.
- Imported records round-trip through SQLite and report export.

### Performance tests

- 900,000-row / approximately 150 MB CSV.
- Measure wall-clock time, peak memory, retained rows, invalid rows, and diagnostics.
- Verify exception grouping across chunk boundaries produces the same result as a full-frame reference fixture.

## 6. Acceptance Criteria

- TOV1050 is the only product mode exposed by the three target screens.
- No TOV640 source file is modified.
- Fresh launch does not display copied EAL/TML seed records.
- Supplied sample produces 476 raw rows, 276 retained rows, and 100 rows trimmed from each end.
- `1.#IO` never creates an exception and is reported in cleaning statistics.
- Height values remain unchanged from input.
- All supported line/session/direction mappings resolve to the intended workbook/sheet.
- Detector grouping, severity levels, threshold gates, and exception IDs remain parity-compatible with the TOV640 contract after adapter conversion.
- Frontend TypeScript/Vite build passes.
- Targeted backend and frontend tests pass.
- `npm run dev` reaches a ready backend and opens the Electron window.

## 7. Development Order and Change Control

Implement one work package at a time in the order WP0 -> WP1 -> WP2 -> WP3 -> WP4 -> WP5 -> WP6. After each package:

1. Run its targeted tests.
2. Inspect `git diff --check` and `git status`.
3. Re-index codebase-memory after production source changes.
4. Record unresolved questions or behavior changes before starting the next package.

Do not perform broad TOV640-to-TOV1050 renames in copied legacy wear modules unless the module is still reachable from the TOV1050 UI/API. Prefer an adapter, a shared type boundary, or disabling an unsupported legacy screen.
