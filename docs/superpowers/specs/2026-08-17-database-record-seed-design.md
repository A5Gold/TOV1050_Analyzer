# 一年 Database Record 預載設計

## 目標

將 2025-2026 EAL 與 TML Exception Database Record Excel 轉換為程式可直接匯入的標準格式，並在開發模式及 Windows 打包版首次建立空白 SQLite 資料庫時，自動預載一年例外紀錄。使用者日後以介面上傳的檔案維持既有人工匯入流程。

## 範圍與非範圍

本項目包含基準 Excel 的整理、首次啟動 seed、打包資源宣告與測試。

本項目不改變 Database Record 的篩選、編輯、人工匯入、匯出或一年比對規則，不引入新的前端操作介面，也不覆寫已存在的使用者資料。

## 已核實來源資料

| 來源 | 可用工作表 | 原始列數 | 備註 |
| --- | ---: | ---: | --- |
| EAL | UP、DN、RAC UP、RAC DN、LOW S1 | 1,738 | 5 張例外紀錄表 |
| TML | UP、DN | 977 | `Sheet1` 是參考資料，不匯入 |
| 合計 | 7 張 | 2,715 | 第 1 列為群組標題，第 2 列才是欄名 |

## 標準化 Excel

每條線各產生一個來源檔，放在開發模式使用的 `config/database-records/`。打包後由 `extraResources` 複製到 `resources/config/database-records/`：

- `EAL-1-year-database-record.xlsx`
- `TML-1-year-database-record.xlsx`

每個活頁簿只有一張 `Database Records` 工作表。第 1 列為程式既有 `IMPORT_HEADER_MAP` 使用的欄名，不保留來源檔的分組標題或 TML `Sheet1`。欄位順序保留例外定位欄位、工作流程欄位與追溯欄位；至少包含 `Run Date`、`Line`、`Track`、`Section`、`ID`、`FromM`、`ToM`、`Exception Type`、`MaxLocation`、`ACTION`。

日期欄位儲存為 `YYYYMMDD` 文字，避免 SheetJS 將 Excel 日期轉為 serial number。數值欄位保留數值型別，ID、路線、軌道、section、tension length 與流程文字保留文字型別。

## 資料品質規則

原始檔保留在 `docs/1 year database record/`，不會覆寫。標準化輸出採取以下可重現規則：

1. 移除 5 組正規化後完全相同的重複列。
2. EAL `20251116_EAL_LOW_S1_W9` 留下欄位較完整的一列，並在報告記錄來源列差異。
3. TML `20250814_TML_TUM-HUH_DN_SL74` 的兩列 `Overlap` 值衝突，兩列都不進入 seed，並在資料品質報告保留值與來源列。
4. TML `20251127_TML_TUM-KSR_DN_SL37` 的 `MaxLocation` 為空，不能進行一年位置比對，不進入 seed。

預期 seed 總數為 2,706 筆。資料品質報告以 JSON 寫入相同目錄，列出原始總數、保留數、排除項目、規則與來源位置。

## Seed 行為

新增獨立的 Database Record seed 初始化器，由 `DatabaseManager` 完成 schema 初始化後呼叫。

初始化器會：

1. 從 `get_config_dir() / database-records` 找出兩個標準化活頁簿。
2. 只在 `saved_repeated_exceptions` 為空時執行。
3. 使用後端的只讀 Excel 解析，逐檔逐列轉換為現有 `import_repeated_records_from_data` 所需欄位。
4. 在同一個 SQLite 交易中寫入所有資料。任何檔案、格式或資料庫錯誤都 rollback，資料庫維持空白。
5. 寫入完成後記錄來源檔雜湊、版本與筆數，令後續啟動可跳過。
6. 資料表已有任何使用者或既有種子紀錄時，永不更新、合併或覆寫。

解析及寫入在後端進行，啟動期間不佔用 Electron renderer。2,706 筆資料僅於空白資料庫首次啟動時處理一次。

## 封裝行為

根目錄 `config` 已由 `package.json` `build.extraResources` 複製至打包資源的 `config`。將標準化檔案及品質報告放在來源 `config/database-records/`，打包後會位於 `dist/**/resources/config/database-records/`。開發模式讀取專案根目錄 `config`，因此 `npm run dev` 與 packaged runtime 使用同一組 seed。

## 失敗處理與可觀測性

缺少 seed、重複啟動、資料庫非空、格式錯誤和交易失敗都會輸出明確後端日誌。缺少 seed 不會阻止程式開啟；失敗 seed 不會留下部分記錄。前端既有 Database Record 畫面會以空資料狀態或已載入資料顯示，不需要新增 UI。

## 測試策略

測試覆蓋：標準化欄名與資料型別、品質規則與預期筆數、空資料庫首次 seed、重啟跳過、非空資料庫保護、缺檔/壞檔 rollback、開發與 frozen config 路徑、`check_1_year_records` 對已 seed 資料的整合比對，以及 `npm run package` 產物中的資源檔存在性。

## 產品與設計文件

已檢閱 `PRODUCT.md` 與 `DESIGN.md`。此變更只為既有 Database Record 工作流程提供預載資料，不改變產品目的、使用者工作流程或視覺系統，兩份文件維持不變。
