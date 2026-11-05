# P3 metadata 候選重驗紀錄

## 需求、設計與範圍

依已交接的 P3 review-only 範圍，沿用既有 provider 與 metadata review scripts，重驗 2026-10-29 batch-04，另產 2026-11-03 batch-01 審閱候選。不得覆寫原始／reference／runtime workbook、正式 manifest 或資料庫；只有具體 Contact 配對、方向、scope、coverage 核准後才能另行建立啟用資料。

## 驗收與結果

- 25 份來源 SHA 與 batch-04 一致；結束前讀取磁碟重新雜湊，零 mismatch。正式 config／reference config／TL-BK 的 git diff 無檔案。
- DRL 保留 runtime 門檻（Wear L1 8.9），不擅自改成 reference 9.1；UT／PL 點與 track 區間保留 provenance。DT 與方向缺口明確標示。
- TL-BK 14,437 點，零 invalid；382 組 TL 中 31 組 Contact 雙端候選。未核准 interval／coverage／Landmark 維持 unknown，批准欄留空。
- 候選讀回 parity：DRL 4,532 格、Contact review 7,152 格均通過；DRL H:J 與 Contact 黃色批准欄完成 render 目視檢查。
- 命令：`python scripts/validate_followup_metadata_workbooks.py --output outputs/metadata-review-2026-11-03/batch-01`。
- 命令：`python -m pytest backend/tests/test_tov1050_approved_intervals.py backend/tests/test_tov1050_boundary_review.py backend/tests/test_followup_metadata_review.py backend/tests/test_tov1050_adapter.py backend/tests/test_tov1050_capabilities.py -q`；77 passed in 32.02s。
- `git diff --check` 無 whitespace error；只有現有 LF／CRLF 警告。

## 交付與阻塞

候選與 audit：`outputs/metadata-review-2026-11-03/batch-01/`。狀態維持 review-only，不能作為正式三欄資料已完成的證據；本 P3 重驗未改核心程式或正式資料。既有其他工作階段未提交內容未動。

資料負責人的下一步：提供 Contact endpoints 配對、branch／direction scope、coverage、Landmark 區間及 DRL DT／方向決策；開發端之後才驗證具體批准 scope 的 sidecar。

## Linear 同步

本工作階段 Linear MCP 實際掛載，whoami 連線成功；DAV-27 留言 `c4e01aad-f723-4bc7-91f1-f4fb8ae77f3e`、DAV-21 留言 `9d89b6e7-9b59-4859-93af-d197cb26d558` 已記錄結果、限制與明確 next action。此子工作不更改整體 issue 狀態，由主代理統一整合。
