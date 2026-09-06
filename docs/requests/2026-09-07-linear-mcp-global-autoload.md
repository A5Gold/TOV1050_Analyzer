# Linear MCP 全域自動掛載

- 日期：2026-09-07
- Linear project：TOV1050_Analyzer（0f597453-23e1-4209-a3ff-32261a5eac4d）
- Linear issue：DAV-10
- 負責人：使用者／Codex
- 狀態：Done

## 需求與目的

### 使用者與流程

使用者希望在 TOV1050 Analyzer 專案、Codex 與這台 Windows 電腦的 chatbox 工作階段中，自動掛載 Linear MCP，讓每次新工作階段都能直接查找、建立、更新 Linear project/issue。

### 商業規則與限制

- Linear MCP 必須使用 HTTPS endpoint `https://mcp.linear.app/mcp` 與 OAuth。
- 不可把設定存在誤認為目前 chatbox 工作階段已載入工具；OAuth 或設定恢復後必須重開 Codex 或建立新的 local task，再驗證工具清單。
- 本次工作階段未掛載 Linear MCP，因此不能聲稱已完成 Linear project/issue 同步。

## 現況盤點

- 相關程式碼：無；此需求涉及 Codex 全域設定與工作階段生命週期。
- 相關 API／資料流程：Codex MCP 設定 → `linear` streamable HTTP server → OAuth → 新工作階段載入 Linear tools。
- 現有測試：`codex mcp list` 顯示 `linear` enabled、OAuth；本工作階段工具清單沒有 Linear MCP tools。
- 已知風險或阻塞：完成登入與核准後，需重開 Codex 才能讓既有聊天載入新 MCP；本次重開後已驗證通過。

## 設計

### 範圍

確認並保留使用者層級 `linear` MCP 設定；確認 OAuth；說明專案不需另放一份重複設定，因 Codex 使用全域設定覆蓋所有專案。

### 不在範圍

不修改 TOV1050 應用程式商業邏輯、不新增假設的 Linear issue id、不把 token 寫入 repo 或回覆內容。

### 資料流與錯誤處理

若 `linear` 不存在，執行 `codex mcp add linear --url https://mcp.linear.app/mcp`；若已存在則不重複新增。必要時執行 `codex mcp login linear`，完成後重開 Codex／建立新的 local task，再以 `codex mcp list` 與新工作階段工具清單驗證。

### 驗收標準

- `codex mcp list` 顯示 `linear` enabled、OAuth。
- 新開的 Codex chatbox 工作階段工具清單實際包含 Linear MCP tools。
- request 文件記錄驗證結果、阻塞與下一步。

## 執行紀錄

### 實作

已確認 `C:\Users\chusiukd\.codex\config.toml` 已有：

```toml
[mcp_servers.linear]
url = "https://mcp.linear.app/mcp"
```

`codex mcp list` 顯示：`linear ... enabled ... OAuth`。不需在本專案新增第二份設定；專案層只需保留本需求與同步紀錄。

### 測試與 debug

```text
codex mcp list
# linear https://mcp.linear.app/mcp ... enabled OAuth

重開後 chatbox 的已掛載工具清單
# 已包含 mcp__linear__* tools

mcp__linear__list_projects({ query: "TOV1050", limit: 50 })
# 成功讀取 TOV1050_Analyzer project

mcp__linear__list_issues({ project: "TOV1050_Analyzer", query: "Linear MCP" })
# 成功讀取 DAV-10 與 DAV-5
```

### 驗收結果

重開 Codex 並在 Edge 完成 Linear 登入與核准後，本工作階段已實際載入 `mcp__linear__*` 工具，並成功讀取 TOV1050_Analyzer project、DAV-5 與 DAV-10。OAuth 加密憑證檔仍存在於 `C:\Users\chusiukd\.codex\secrets\mcp_oauth.age`，可供後續工作階段重用。

## Linear 同步

- 最後同步時間：2026-09-07
- Issue 狀態：DAV-10 已同步驗證結果，仍為 In Progress（該 issue 尚有原專案工作）；本 request 已完成。
- Next action：日後若再次出現登入循環，檢查是否使用相同的使用者設定目錄與 `mcp_oauth.age` 是否可讀。
- 阻塞／需要決策：目前無阻塞。

## 相關檔案

- `C:\Users\chusiukd\.codex\config.toml`
- `docs/requests/2026-09-07-linear-mcp-global-autoload.md`
