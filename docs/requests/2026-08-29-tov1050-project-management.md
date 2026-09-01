# TOV1050 Analyzer 專案管理與交付路線圖

- 日期：2026-08-29
- Linear project：TOV1050_Analyzer
- Linear project URL：https://linear.app/david-chu/project/tov1050-analyzer-d897dfced2f1
- Linear issue：DAV-5（https://linear.app/david-chu/issue/DAV-5/tov1050-analyzer建立專案-triage-與交付路線圖）
- 狀態：Done

## 需求與目的

建立可持續的設計、實作、測試、debug 與功能增強 workflow，讓 repo 文件、Linear backlog 與驗收證據保持一致。每項工作都必須先理解現況，再以需求紀錄與 Linear issue 追蹤交付。

## 現況盤點

TOV1050 Analyzer 是 Windows Electron desktop application，前端使用 React/Vite/MUI/Plotly，後端使用 Python/FastAPI，並以 SQLite、Excel/CSV 匯入匯出支援鐵路接觸網維護分析。主要工作面包含：

- 分析與 Exception Generator
- Database Record workbench 與重複異常
- Wear-cycle preview、save、sync 與歷史 workbook
- TOV1050 metadata、section resolution 與 Excel 相容性
- 前端工作流、狀態呈現與測試
- release baseline、debug 與封裝驗收

目前 repo 有既有未提交修改，不能覆蓋或回退。codebase-memory 索引顯示約 3,659 個節點、17,221 條關係，並辨識出 backend、frontend、tests 等主要模組；主要 API route 涵蓋 cycles、changes、historical、candidates、metadata-preview、sync、dashboard 與 export。

## 工作流程

1. 需求澄清：記錄使用者、流程、限制、成功標準與不在範圍。
2. 設計：確認資料流、錯誤處理、相容性與測試策略。
3. 實作：依既有 backend/frontend 邊界修改，保留驗證與資料正確性。
4. 測試：執行相關 Python、Vitest、Playwright、lint 或 build，記錄命令與結果。
5. Debug／review：將失敗案例、根因、修正與剩餘風險同步 Linear。
6. 驗收：確認 issue 狀態、next action、相關檔案與測試證據。

## Linear 分工與 next actions

- DAV-5：總控 triage、依賴、release baseline 與交付路線圖。
- DAV-6（https://linear.app/david-chu/issue/DAV-6/設計盤點-tov1050-使用者流程與狀態模型）：整理使用者流程、狀態模型與驗收條件。
- DAV-7（https://linear.app/david-chu/issue/DAV-7/實作建立分析資料庫與-wear-cycle-交付-backlog）：依功能面拆分可交付的 backend/frontend 工作。
- DAV-8（https://linear.app/david-chu/issue/DAV-8/測試與-debug建立-release-baseline-與失敗案例追蹤）：建立 baseline、追蹤失敗與回歸風險。
- DAV-9（https://linear.app/david-chu/issue/DAV-9/功能增強收納-uimetadata-與報表改善候選）：收納已確認但不阻塞 baseline 的改善。

## 驗收標準

- Project、milestone、issues 與 labels 已建立並可互相追溯。
- 每張 issue 有明確範圍、驗收條件、狀態與 next action。
- Repo 需求紀錄與 `AGENTS.md` 規範已建立。
- 測試／debug／阻塞結果會在實作期間持續更新，而不是只在結束時補寫。

## 本次執行結果

- Repo 文件：已建立 `AGENTS.md`、本紀錄與 `TEMPLATE.md`。
- Linear：已確認 workspace/team/project/DAV-5；milestone、labels 與拆分 issues 見 Linear 回報。
- 測試：backend regression 31 passed；frontend focused tests 9 passed；production build 成功。
- 阻塞：無阻塞。保留 React `act()`、xlsx dynamic import 與 bundle size warnings 作為後續非阻塞改善項目。

## 2026-08-29 實作同步

- DAV-6 設計已批准並完成；正式設計紀錄為 `docs/requests/2026-08-29-tov1050-data-contract-design.md`。
- DAV-7 已完成：canonical workbook adapter/write-back、任意合法 CSV basename 分析、UI context authoritative 與 422 錯誤契約。
- DAV-8 已完成：backend 31、frontend focused 9 tests passed；production build 成功。
- DAV-9 已完成：About／操作指南／開發者參考與 MetadataEditor sheet label 相容映射已更新。
- 後續：效能 bundle 分割與 React `act()` 測試清理另開 issue，不阻塞目前 release baseline。
