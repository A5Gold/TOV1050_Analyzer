# 提交與推送現有工作狀態

- 日期：2026-10-29
- Linear project：TOV1050_Analyzer
- Linear issue：[DAV-25](https://linear.app/david-chu/issue/DAV-25)
- 負責人：Codex
- 狀態：In Progress

## 需求與目的

使用者要求將全部 dirty 工作狀態提交並推送 GitHub，隨後明確排除原始 CSV 與 DATAC。來源檔案留在本機；其他既有程式、metadata、文件、圖片、報表與驗收產物一併保存，包含既有刪除。

## 現況盤點

- 目前分支 master，遠端 origin 為 https://github.com/A5Gold/TOV1050_Analyzer.git。
- 起點 HEAD：2f6f1731715cf2b3345a74d6a8570870759296f0；git fetch origin 成功，起點與 origin/master 相同。
- 既有需求、設計及測試證據見同目錄 dual-system-test-feedback、docs/plans 與 docs/verification/2026-10-29-dual-system-validation.md。
- 實際掛載並成功讀取／更新 Linear MCP DAV-25；已先同步累積實作、測試與人工驗收限制。

## 設計

### 範圍與資料處理

將所有未被既有 ignore 排除的工作變更納入一次整合提交，排除 `00 Reference Document/Raw data/` 下的原始 CSV／DATAC。以 .gitignore 保護未追蹤來源，另以 staging pathspec 排除已追蹤的原始 CSV 修改。保留原始檔案內容與現有 Git 歷史，不移除既有歷史中的來源檔。不需 Git LFS。

分析／audit／coverage CSV 屬驗收產物，仍隨其他工作狀態提交；既有忽略的 runtime、環境與 log 維持原規則。

### 驗收標準

- 提交包含全部其餘可追蹤變更，原始 CSV／DATAC 無 staged change。
- 檢查 staged whitespace、來源 SHA 保護與 GitHub 單檔限制。
- 正常推送 master，遠端分支 SHA 等於本地 HEAD。
- 剩餘本機修改僅限使用者明確排除的原始資料，並同步 Linear。

## 執行紀錄

### 實作

- 更新原始資料 ignore 規則；其餘工作為保存現況，不新增產品行為。
- 不重新執行已完成的整套驗收；既有測試與 build 結果以 dual-system 驗收紀錄為準。

### 測試與 debug

- `git add --all` 搭配原始 CSV／DATAC exclude pathspec：成功；618 個 staged 檔案（含本文件）。
- `git diff --cached --check`：exit 2，問題限 outputs 內第三方 xlsxwriter／lxml 已解壓套件的空白格式；保留原始第三方內容。
- 排除上述第三方目錄後的 staged whitespace check：exit 0。
- 舊 `verify_sources.py --verify`：exit 1，原路徑 TWL `_MedianSample` 報表已不存在。另作逐檔 SHA 核對：三份 raw、十份 runtime metadata 與一份 AEL 報表 unchanged；20260907 TWL 同名去後綴候選內容 changed，20260630 舊報表 missing。這是本次開始時既有工作狀態，沒有回復或覆蓋。
- 沒有重新宣稱舊「16 檔全不變」結論成立於本次提交現況；先前功能測試／建置結果僅引用原驗收紀錄。

### 驗收結果

原始 CSV／DATAC 未 staged；其餘現有工作狀態已暫存。無 staged 檔案超過 GitHub 100 MiB 限制；最大為既有驗收報表 full-normal-raw.xlsx（98,655,329 bytes）。未暫存變更僅 20260822_AEL_UT_SHO_AWE.csv；未追蹤且未忽略檔案清單為空。待正常提交／推送後同步遠端結果至 Linear。

## Linear 同步

- 已同步：使用者授權提交／推送、既有實作與測試狀態；原先 LFS 計劃已由使用者排除原始資料的指示取代。
- Issue 狀態：In Review；提交工作不等同 Electron／原生 Excel 人工驗收通過。
- Next action：驗證 staged scope，提交推送後更新 GitHub commit／文件連結；後續由使用者執行既定人工驗收。

## 相關檔案

- `.gitignore`
- 本文件與 `docs/requests/2026-10-29-dual-system-test-feedback.md`
- 全部提交檔案可由本次 commit 的 `git show --stat`／GitHub 變更清單查閱。

## 推送與後續快照

- 主提交：74f49ee3726574554f76d4b0944a168f4dba8f46（618 檔）；第一次 HTTPS push 回 HTTP 408、exit 1，遠端仍是起點 2f6f173。
- 初次提交後，外部操作持續更新 runtime metadata（ISL／KTL／LAR_AEL／LAR_TCL／TKL／TKS）及刪除 Excel 鎖定檔；依「包含全部 dirty」授權以後續提交保存實際快照。先前逐檔 SHA 結論只代表檢查當刻。
- 下一動作：以命令範圍 `http.postBuffer=524288000` 重試 HTTPS push，不變更永久環境／TLS 憑證驗證；以 ls-remote 核實遠端 SHA。原始 CSV／DATAC 持續排除。
