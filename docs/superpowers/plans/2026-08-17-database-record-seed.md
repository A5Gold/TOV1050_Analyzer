# 一年 Database Record 預載實作與測試方案

## 資料整理

1. 建立可重複執行的轉換程式，讀取 `docs/1 year database record/` 的兩個來源 Excel。
2. 僅取有例外欄位的工作表，從第 2 列讀取欄名，從第 3 列讀取資料。
3. 將來源欄名轉換為 `IMPORT_HEADER_MAP` 既有格式，日期轉為 `YYYYMMDD` 文字。
4. 套用設計文件的資料品質規則，輸出兩個單一工作表 Excel 與 JSON 品質報告至 `config/database-records/`。
5. 驗證輸出有 2,706 筆資料、沒有空白 `ID` 或 `MaxLocation`、每一列的 line/track/section/date 都可用於一年比對。

## 後端實作

1. 在 database core 新增受限的 seed reader，僅接收標準化活頁簿及明確欄名。
2. 以 `openpyxl` read-only 模式讀取，避免在啟動時載入完整樣式與工作簿物件。
3. 將所有輸入先驗證，再以單一交易呼叫既有的資料庫寫入邏輯或等效的 bulk insert。
4. 在 `DatabaseManager` 初始化完成 schema 後呼叫 seed reader，並以 `saved_repeated_exceptions` 是否為空作為唯一寫入條件。
5. 將 seed state 寫入 `system_metadata`，包括版本、來源雜湊與匯入筆數。
6. 在 seed 缺失、格式不符或寫入失敗時 rollback 並繼續啟動，不建立部分資料。

## 打包

1. 確認 `config/database-records/` 會由現有 `package.json` 的 `extraResources` 規則複製至打包後的 `resources/config/database-records/`。
2. 執行根目錄支援的 package 指令，不直接呼叫 Vite、Electron 或 electron-builder。
3. 驗證產物的 `resources/config/database-records/` 含兩個 Excel 與 JSON 品質報告。

## 測試

1. 單元測試：活頁簿 reader、欄名檢查、日期正規化、資料品質報告與雜湊。
2. 資料庫整合測試：空 DB 建立 2,706 筆，第二次初始化不重覆插入，含任意既有紀錄的 DB 不被 seed 改寫。
3. 失敗測試：缺檔、未知欄名、壞 Excel、單列資料錯誤與中途寫入錯誤均不留下部分資料。
4. 一年檢查測試：用預載資料驗證 line、track、section、exception type、chainage 與 365 日窗的匹配。
5. 打包驗證：確認 Windows directory target 的資源路徑及第一次啟動資料庫。

## 完成條件

- 兩個整理後 Excel 能被現有程式匯入欄位契約讀取。
- `npm run dev` 的全新資料庫自動取得 2,706 筆一年紀錄。
- packaged runtime 的全新資料庫取得相同資料。
- 現有使用者資料從不因 seed 而被覆寫。
- 專案測試及受影響的打包驗證成功。
