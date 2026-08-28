# Version Difference 五週期與 Database Record 完整數量設計

日期：2026-08-19

狀態：設計已獲使用者批准，等待書面規格審閱

延伸：`2026-08-04-version-difference-independent-module-design.md`

取代：`2026-08-17-database-record-seed-design.md` 內「非空資料庫永不覆寫」的 v1 seed 行為

## Design Read

本次修改服務鐵路維護人員的高密度 Windows 分析工作台，不改變既有操作架構或資料判讀流程。

- DESIGN_VARIANCE：3。沿用 MUI、Plotly、既有 comparison tabs 與 Database Record tabs。
- MOTION_INTENSITY：2。只保留拖放、焦點、loading 與資料切換所需的狀態回饋。
- VISUAL_DENSITY：8。五個 cycle、完整數量與 loaded subset 必須可快速掃描。
- Impeccable product register 是主要介面框架；Taste Skill 只用於層級、間距、色彩與響應式節奏，不引入 landing-page 模式。

`PRODUCT.md` 已審閱，產品目的、使用者與工作原則不變。`DESIGN.md` 需補充五週期 series palette 與「色彩必須搭配文字角色」規則。

## 背景與已核實問題

### Version Difference

獨立 Version Difference 模組目前只接受 Latest、Previous 1 與 optional Previous 2。三檔限制分散於 FastAPI multipart 參數、API client、Zustand file role、view slots、response types 與 Plotly 色彩/標籤。

使用者需要最多五個明確週期：Latest、Previous 1、Previous 2、Previous 3、Previous 4。Latest 與 Previous 1 必填，其餘獨立選填。上傳槽必須與圖表週期顏色一致。

### Database Record 數量

目前 `GET /database/repeated-records` 預設最多回傳 1,000 筆，並錯把 `len(records)` 當成 `total`。Line tab 使用獨立全庫 COUNT，但 Section badges 從這 1,000 筆在前端重算，因此會出現：

- EAL line tab：1,732
- All Sections：1,000
- Mainline + RAC + LOW：1,000

正確口徑已由使用者確認：頂部總數代表目前 line、active section 與其他 filters 的完整資料庫筆數；每個 Section badge 則代表目前 line 與其他 non-section filters 下，選擇該 Section 後會得到的完整筆數。兩者都不是前端已載入筆數。前端可以繼續只載入有限明細以控制 CPU 與記憶體。

### 新 EAL seed

使用者更新的 `config/database-records/EAL-1-year-database-record.xlsx` 已唯讀核實：

| Section | 筆數 |
| --- | ---: |
| Mainline | 1,584 |
| RAC | 132 |
| LOW | 16 |
| LMC | 94 |
| EAL 合計 | 1,826 |

該 workbook 有 34 欄、`Database Records!A1:AH1827`，沒有 composite-key 重複。SHA-256 為 `ddc3d385c65e5a2475e8a1070fe8eff401f7967866cef11fc370c0a975f80fad`。

現有 TML seed 維持 974 筆，SHA-256 為 `1d9d989663f9ee67bd60c4bc7d9496a823d263fd3be67e341838d780d1a94165`。v2 完整 seed 因此為 EAL 1,826 + TML 974 = 2,800 筆。

目前程式資料庫已確認為 seed `2025-2026-v1`，實際筆數 EAL 1,732、TML 974。使用者明確授權以新版 Excel 覆寫這批測試資料。

## 目標

1. Version Difference 接受二至五個具固定角色的 Excel reports。
2. 上傳槽、multipart keys、response keys、圖表 labels 與 colors 由同一 ordered cycle descriptor 驅動。
3. 五個週期在 raw overlay 中保持固定顏色，並對每個已提供的 Previous cycle 產生 Latest-based difference。
4. Database Record 的頂部 total、目前 Section total 與所有 Section badges 使用完整 filtered database counts。
5. 明細仍以現有 1,000 筆上限載入，介面明確區分 total 與 loaded。
6. Section 切換改為 server-side filter，使 LMC 等未落入原始 1,000 筆 subset 的資料仍可查看。
7. 將新版 EAL/TML seed 定義為 `2025-2026-v2`，以交易方式一次性取代已確認的 v1 測試 seed。
8. 開發、現有安裝升級及 Windows packaged runtime 使用同一組 seed assets。

## 非目標

- 不支援超過五個 cycle 或動態增加任意 cycle。
- 不比較 Previous cycles 彼此之間的差值。
- 不改變 chainage alignment 演算法、搜尋範圍、取樣步距或可信度門檻。
- 不把 Database Record 表格改成完整 server-side pagination。
- 不移除 1,000 筆明細上限，也不讓 batch edit 暗中作用於未載入資料。
- 不改變 EAL/TML line tab 的既有全庫數量語意；active filters 可令頂部/section counts 與全庫 line badge 不同。
- 不覆寫無 v1 seed metadata、筆數不符或版本未知的非空資料庫。
- 不修改其他 SQLite tables 或其他模組的分析資料。

## Version Difference 架構

### Shared Cycle Descriptor

新增一個 frontend ordered descriptor，集中下列欄位：

| Role | Form field | Comparison key | Label | Required | Color |
| --- | --- | --- | --- | --- | --- |
| `latest` | `latest` | 無 | Latest | 是 | `#c74444` |
| `previous1` | `previous_1` | `previous_1` | Previous 1 | 是 | `#2b63c9` |
| `previous2` | `previous_2` | `previous_2` | Previous 2 | 否 | `#2f8a67` |
| `previous3` | `previous_3` | `previous_3` | Previous 3 | 否 | `#b8791b` |
| `previous4` | `previous_4` | `previous_4` | Previous 4 | 否 | `#9467bd` |

Store file role、view slots、FormData、response labels 與 chart traces 必須從此 descriptor 派生，不能各自再維護五組 ternary 或 color maps。

Optional roles 彼此獨立。Previous 3 可以在 Previous 2 空白時上傳；request 保留 `previous_3`，response 也保留 `previous_3`，不可重新編號。

### Backend API

`POST /analyze/version-difference` 保留 explicit multipart contract，新增：

- `previous_3`: optional Excel file
- `previous_4`: optional Excel file

Latest 與 Previous 1 維持 required。Backend 按固定角色順序組成 uploads，逐檔只讀取 `ChartData`，再將每個已提供 Previous cycle 獨立與 Latest 對齊。

Response shape 維持向後相容：

```json
{
  "status": "ready",
  "latest_file": "latest.xlsx",
  "comparisons": [
    { "key": "previous_1", "previous_file": "p1.xlsx" },
    { "key": "previous_3", "previous_file": "p3.xlsx" }
  ]
}
```

`comparisons` 只包含實際提供的 Previous cycles，並維持 descriptor 順序。每個 comparison 繼續保有 height、stagger、wear 的 ready/unavailable 狀態，單一 optional file 或 metric 不可令其他結果消失。

### Frontend Store 與 Request

每個既有 comparison tab 將 files 擴為五個固定 roles。替換或移除任一檔案會清除該 tab 的 stale response/error；loading tab 仍禁止變更輸入。跨 tab concurrency、關閉 loading tab 後忽略 late response、最多六個 comparison tabs 等既有行為維持不變。

Compare enablement 仍只要求 Latest 與 Previous 1。API client 遍歷 descriptor append required/available fields，避免中間空槽造成重新編號。

### Upload UI

五個 upload slots 使用相同結構與穩定高度：

- Header 保留 `Latest`、`Previous N` 與 `Optional` 文字。
- 每個 slot 使用對應週期色的完整 outline、固定 accent/swatch，以及低透明度 drag-active background。
- Filename、remove action、validation message 維持中性色與清楚 focus state。
- 色彩不作為唯一識別；所有 slot、chart controls、hover 與差值標題都保留文字 role。
- 長檔名使用可讀的 ellipsis/tooltip，不可撐大 slot 或遮蓋 remove button。
- 響應式 columns 為 1 / 2 / 3 / 5：手機一欄、小型視窗兩欄、中型桌面三欄、足夠寬度才五欄。

### Chart UI

五檔完整結果最多產生：

- Raw overlay：5 cycles x 4 channels = 20 traces。
- Difference：Latest - Previous 1 至 Latest - Previous 4，共 4 plots，每圖 4 channel traces。

每個 cycle 顏色固定，每個 channel 繼續以 solid/dash/dot/dash-dot 區分。既有 per-chart visibility、opacity、trace order、synchronized zoom、Reset Zoom 與 unavailable states 維持。Difference plots 依 response comparisons 動態生成，不為未上傳的 optional cycle 建立空容器。

## Database Record 完整數量架構

### 單一 Filter Predicate Builder

將 `query_repeated_records` 內目前分散的 SQL predicates 抽成一個受限 helper，輸入現有 filter dictionary，輸出 parameterized `WHERE` clause 與 params。下列查詢必須共用它：

1. 明細 SELECT，加 `ORDER BY`、`LIMIT`、`OFFSET`。
2. 完整 `COUNT(*)`，不加 limit/offset。
3. Section aggregate GROUP BY，使用與 count 相同的非 section filters。

Helper 必須涵蓋 endpoint 現有的 line、track、section、level、action、exception type、task number、date type/range 與 chainage overlap rules，也保留 core function 已支援的 class、overlap、from/to range、task-run range 及 saved-at date。所有 values 以 SQLite parameters 傳入。

### Section Canonicalization

Section aggregate 採同一 canonical rule：

- 空白或 NULL -> `unknown`
- 包含 `LOW` -> `low_s1`
- Mainline -> `mainline`
- RAC -> `rac`
- LMC -> `lmc`
- 其他未識別值 -> `unknown`

API 永遠回傳完整 keys：`all`、`mainline`、`rac`、`low_s1`、`lmc`、`unknown`。`all` 必須等於其餘五項總和。Frontend 顯示 `LOW S1`；`unknown > 0` 時增加可選的 Unknown tab，不能靜默漏掉。

### Section Filter Scope

選擇 Section 後改由 API 篩選明細，而不是只篩目前已載入的 1,000 筆。

- `records` 與 `total` 套用 active section 及所有其他 filters。
- `section_counts` 套用相同 line 與其他 filters，但刻意排除 active section，讓所有 Section badges 保持可導航的完整 counts。
- 未選 Section 時，`total == section_counts.all`。
- 選擇 Section 時，`total` 等於該 Section badge，明細最多載入其中 1,000 筆。

### API Response

`RecordsListResponse` 擴充為：

```json
{
  "status": "success",
  "total": 1826,
  "section_counts": {
    "all": 1826,
    "mainline": 1584,
    "rac": 132,
    "low_s1": 16,
    "lmc": 94,
    "unknown": 0
  },
  "records": []
}
```

`total` 和 `section_counts` 在同一 read transaction/connection 中計算後再回傳，避免一次 refresh 內看到不同 database snapshots。

### Frontend State 與語意

Zustand store 保存 `repeatedRecordsTotal` 與 `repeatedRecordSectionCounts`。`LineTabPanel` 不再從 records 本機推導 badge counts；FilterPanel 在 line 或 section 改變時將兩者都送到 API。

顯示規則：

- `total <= records.length`：頂部顯示 `N records`。
- `total > records.length`：頂部顯示 `N total · M loaded`。
- Section badge 永遠顯示完整 aggregate。
- `Batch Edit All (M)` 改為 `Batch Edit Loaded (M)`，title/tooltip 說明只修改已載入明細。
- Section controls 的 accessible name 包含 label 與完整 count，例如 `LMC, 94 records`。
- Loading 期間保留穩定幾何；request 失敗時沿用既有 error alert，不以舊 badge 假裝新 query 已成功。

EAL/TML line tab 的 counts endpoint 維持全庫語意，不受目前 filters 影響。這項全庫 badge 與頂部 filtered total 是不同指標，不能互相代用。

## Database Record Seed v2

### Assets 與 Manifest

更新 `database-record-seed-quality.json` 為 `database-record-seed-quality-v2`：

- `seed_version`: `2025-2026-v2`
- `source_record_count`: 2,800，代表兩個已標準化 runtime input workbooks 的資料列
- `retained_record_count`: 2,800
- `retained_by_line`: EAL 1,826、TML 974
- `retained_by_section`: EAL Mainline 1,584、RAC 132、LOW 16、LMC 94；TML Mainline 974
- `excluded_record_count`: 0，因 v2 runtime inputs 已是整理完成的 canonical assets
- `source_sha256` 與 `output_sha256`: 都以兩個實際 runtime workbook filenames 為 keys，使用本規格核實的 EAL/TML hashes
- `provenance`: 記錄 base seed `2025-2026-v1`、EAL 由使用者於 2026-08-19 提供更新後 canonical workbook、TML 由 v1 延續
- `historical_rules` 與 `historical_exclusions`: 搬移 v1 的九筆排除 audit history，不把它們誤計為 v2 runtime input 的新 exclusions

Root `package.json` 已以 `extraResources` 將整個 `config` 複製到 packaged `resources/config`，預期不需改 packaging rule，但必須驗證生成物中的三個 seed assets。

### 一次性替換資格

Seed 初始化器只允許以下狀態：

1. 空白 table：正常 seed v2。
2. 非空且 metadata version 已是 v2：`skipped_up_to_date`。
3. 非空且同時符合以下條件：執行 v1 -> v2 一次性替換。
   - `database_record_seed_version == 2025-2026-v1`
   - metadata count 為 2,706，line counts 為 EAL 1,732 / TML 974
   - table 實際 count 與 line counts 也完全相同
4. 其他非空狀態：`skipped_non_empty`，不刪除、不合併、不覆寫。

v1 replacement 不以舊 output hash 作唯一資格，因已核實的 v1 測試資料曾由不同但同筆數的有效 build 產生。版本 metadata、metadata counts 與實際 table counts 三者必須同時吻合。

### Transaction 與 Metadata

執行替換前先完整讀取並驗證兩個 v2 workbooks、manifest、headers、hashes、筆數與 composite-key uniqueness。只有 validation 全部成功才進入 savepoint：

1. 刪除 `saved_repeated_exceptions` 的 v1 rows。
2. 插入全部 2,800 筆 v2 rows。
3. 更新 seed version、總數、line counts、output/source hashes。
4. 記錄 replacement source version 與完成狀態。
5. release savepoint。

任何 delete、insert 或 metadata 錯誤都 rollback 至 savepoint，v1 rows 與 v1 metadata 必須完整保留。替換不觸及其他 tables。完成後同一初始化流程再次執行必須 idempotent。

## 錯誤與邊界狀態

### Version Difference

- Latest 或 Previous 1 缺少：Compare disabled；直接 API request 仍由 FastAPI 回 422。
- Latest 缺 ChartData：整體 422。
- 任一 optional Previous 缺 ChartData：該 comparison unavailable，其他 comparisons 繼續。
- 中間 optional slot 空白：後續 role 不重新編號。
- 單一 metric unavailable：只影響對應 comparison/metric。
- 五檔大圖 loading 使用與結果相近的穩定 skeleton，不造成 layout shift。

### Database Record

- filtered total 為 0：所有 section aggregates 為 0，records 為空。
- unknown section：計入 All 並顯示 Unknown tab。
- limit/offset 不影響 total 或 section counts。
- count/aggregate query failure：整個 endpoint 回 500，不回傳部分或互相矛盾的數量。
- Section 切換 request failure：保留錯誤訊息，不把 local subset 當完整結果。

### Seed

- asset/hash/header/count 不符：不進入 delete，startup 繼續並記錄明確 error。
- v1 實際 counts 不符 metadata：不覆寫。
- 插入中途失敗：v1 rows 與 metadata 回復。
- v2 已完成：後續啟動不再覆寫使用者之後的修改。

## 測試策略

### Version Difference Backend

- 二至五檔 request 回傳 1 至 4 個 comparisons。
- previous_2 空白但 previous_3 存在時，key 保持 `previous_3`。
- 四個 Previous cycles 分別對齊 Latest，順序固定。
- optional file/metric unavailable 不影響其他 comparison。
- 既有 two/three-file contract 維持。

### Version Difference Frontend

- View 渲染五個具 accessible role name 的 slots，只有前兩槽必填。
- FormData 使用 `previous_1` 至 `previous_4`，中間缺檔不重新編號。
- Store 可保存/移除五個 roles，清除 stale result，維持跨 tab concurrency。
- 五週期完整結果產生 20 raw traces 與 4 difference plots。
- Slot outline/swatch 與 chart trace 共用 descriptor colors。
- 1/2/3/5 columns、長檔名、drag/focus、optional unavailable 等狀態在寬窄視窗可用。

### Database Record Backend

- records 超過 limit 時，`records.length < total` 且 total 正確。
- 每個 filter predicate 對 list、count、aggregates 產生一致 scope。
- active section 影響 records/total，但不縮小 section navigation aggregates。
- legacy `LOW` 正規化為 `low_s1`。
- unknown/null section 計入 Unknown，All 等於各類加總。
- no results、limit/offset、date type、chainage overlap 有回歸測試。

### Database Record Frontend

- Store 保存 records、完整 total 與 section counts。
- EAL 無 filters 顯示 All 1,826、Mainline 1,584、RAC 132、LOW S1 16、LMC 94。
- Header 在載入 1,000 / 總數 1,826 時顯示 `1,826 total · 1,000 loaded`。
- 點選 LMC 送出 server-side `section=LMC` 並顯示完整 LMC records subset。
- Batch action 使用 `Batch Edit Loaded` 語意。
- Section accessible names 包含 counts；Unknown 僅在 count > 0 時出現。

### Seed 與 Packaging

- Loader 驗證 2,800 筆、EAL/TML counts、EAL section counts 與 hashes。
- 空 DB seed v2；第二次執行 idempotent。
- 精確 v1 baseline 交易式替換成 v2。
- 未知非空 DB、v1 count drift 不被覆寫。
- validation failure 發生在 delete 前；mid-insert failure 完整 rollback。
- 實際 canonical AppData 測試 DB 從 2,706 變成 2,800，metadata 更新為 v2。
- Root package output 含兩個 Excel 與 manifest，並可由 packaged config path 載入。

## 影響與風險控制

codebase-memory impact analysis 將兩條路徑標示為 HIGH/CRITICAL：

- Version Difference：endpoint -> API client/store/view/chart -> App。
- Database Record：query/count/endpoint -> store/FilterPanel/LineTabPanel/DatabaseRecordView，以及 save/import/delete/batch-save 後的 refresh。

控制策略：

- 使用 additive multipart fields 與 response keys，保留二/三檔相容性。
- 用單一 cycle descriptor 防止五處 mapping drift。
- 用單一 SQL predicate builder 防止 list/count/aggregate drift。
- 只在精確 v1 baseline 上允許破壞性 replacement，並以 savepoint rollback。
- `frontend/src/types/api.ts` 已有其他未提交修改，實作時只 patch 相關 interfaces。
- 不回復或納入其他 dirty-worktree 變更。
- 實作完成後重新索引 codebase-memory 並再次驗證 callers/affected scope。

## 驗收條件

1. 使用者可上傳 Latest + Previous 1 至 Previous 4，最多五檔。
2. 五個 upload slots 的角色、顏色與 Plotly series 完全一致，且不只靠顏色辨識。
3. Optional slots 可留空或跳號，API/圖表保留原 role。
4. 五檔結果顯示 20 條 raw traces 及 4 個 Latest-based difference plots。
5. Database Record 未選 Section 時，頂部 total 等於 All Sections，All 等於各 Section 加總。
6. Active filters 與 active section 的 total 均為完整 database count，不受 1,000 筆明細上限影響。
7. EAL section counts 為 1,584 / 132 / 16 / 94，合計 1,826；TML 為 974。
8. UI 清楚區分 total 與 loaded，batch edit 不宣稱會修改未載入資料。
9. 現有 v1 測試資料只被替換一次，v2 完成後不再於每次啟動覆寫。
10. v2 seed 共 2,800 筆，LMC 94 筆可在 Database Record 中查看。
11. 任何 seed 驗證或 insert failure 都不留下空表或部分資料。
12. Targeted backend/frontend tests、frontend build、實際工作流程、窄視窗與 packaged resource 驗證全部通過。
