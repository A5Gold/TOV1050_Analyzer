# TOV1050 Analyzer 工作規範

## 每項工作的開始條件

1. 先理解需求、目前 repo 狀態、使用者流程、商業規則、限制與既有 API／測試行為。
2. 閱讀相關 `PRODUCT.md`、`DESIGN.md`、`docs/` 文件與程式碼；不得以猜測取代現況。
3. 在開始實作前建立或更新 `docs/requests/YYYY-MM-DD-<topic>.md`，記錄需求、設計、範圍與驗收標準。
4. 在 Linear 找到或建立對應 project issue；issue 必須連結本次需求紀錄並列出明確 next action。

### Linear MCP 可用性檢查

- 在第一次嘗試同步前，先檢查目前工作階段是否實際掛載 Linear MCP tools/resources；不可只根據過往工作階段、Linear URL 或 repo 文件推定可用。
- 若 Linear MCP 可用，使用 MCP 完成 project/issue 的查找、建立、更新與留言，並在回覆中提供實際操作結果。
- 若 Linear MCP 不可用或連線失效，立即向使用者明確說明「本工作階段未掛載 Linear MCP」，不得聲稱已建立、更新或同步 issue，也不得以猜測的 issue id 代替。
- Linear MCP 缺失時仍可在 repo 的 request/spec 文件記錄待同步內容，但必須標記為 `Linear sync blocked`，列出偵測到的工具狀態、影響與下一步（重新連接／啟用 Linear MCP 後再同步）；不可把 repo 文件當成 Linear 更新的替代品。
- 重新連接或恢復工具後，第一個動作應先同步累積的 request/spec、實作進度、測試結果與阻塞，再繼續新的開發工作。

## 執行與同步

- 設計、實作、測試、debug、功能增強與驗收結果都要同步回 Linear 對應 issue。
- 發現阻塞、需求缺口、資料或環境限制時，立即在 issue 記錄影響與需要的決策。
- 維持既有資料正確性、驗證、錯誤處理、版本／digest 與使用者流程；除非需求明確要求，不改變商業行為。
- 測試應與風險相稱，並記錄實際執行的命令與結果。

## 結束條件

結束前必須確認：

- Linear issue 狀態正確，且有下一個可執行 action 或明確的完成條件；若 Linear MCP 缺失，改為確認 request/spec 已標記 `Linear sync blocked` 並記錄恢復同步的明確 action。
- 需求紀錄包含設計、實作摘要、測試／debug、驗收結果與阻塞。
- 相關檔案、未提交修改與測試結果已列出。
- 若工作未完成，清楚標示剩餘風險、依賴與負責的下一步。

## 文件模板

新需求請以 `docs/requests/TEMPLATE.md` 為起點，檔名使用當日日期與短 topic。
