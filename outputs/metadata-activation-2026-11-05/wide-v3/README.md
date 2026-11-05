# Wide v3 正式啟用紀錄

2026-11-05使用者批准後8份metadata已啟用，16 routes preflight及npm run dev真UI smoke通過。正式release：config/tov1050-metadata-release.json。

- activation.json：正式／候選SHA、備份與preflight結果。
- smoke.json、smoke.log、dev.log、activation-ui.png：正式config啟用檢查；真實CSV小樣本raw810／median81／0例外，不作peak證據。
- cdp-attempt.log：Electron25與Playwright CDP相容性限制；最終以headless browser操作同一Vite UI及FastAPI通過。
- 備份：config/backups/2026-11-05-wide-v3-activation-01，含原8份workbook、舊release及backup-manifest.json；回復方法見正式release。

使用獨立DB測試，正式DB未改；本次自建dev程序樹已關閉。完整報表及History驗收見 outputs/validation-2026-11-05/wide-enrichment。一般環境Excel寫檔偏慢仍為後續事項。
