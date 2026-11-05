# TOV1050 Analyzer 2.0.1 發布驗收

需求：docs/requests/2026-11-06-about-metadata-portable-release.md；Linear DAV-29。

原始碼與metadata：GitHub master已包含d6fd3a7及13544b1；後者加入build-only hook排除及封裝驗收工具。最終交付身份以portable-release.json的source_commit為準，後續純證據／文件commit不改runtime。

- commit-selection.json：原始dirty提交範圍；CSV、DATAC及輸出Exception Report排除，檔案保留本機。此清單記錄首次提交選擇，後續驗收工具／文件見Git commit。
- build-tools/sitecustomize.py：僅建置程序使用，繞過本機WMI卡住，封裝spec明確排除；不交付到runtime。
- backend-build.log：首輪重建，隨後發現build工具被收錄；backend-build-final.log才是排除後版本。
- frontend-build.log：commit後正式前端建置。
- 打包驗收命令：venv/Scripts/python.exe scripts/verify_portable_release.py dist/portable-2.0.1-20261106/win-unpacked --output outputs/release-2026-11-06/package-verification.json。
- 啟動驗收命令：bundled Node執行 scripts/smoke_portable_release.mjs dist/portable-2.0.1-20261106/win-unpacked。

開發設定：project/config。Portable設定：EXE同層resources/config，app_settings.json、line_catalog.json、各線metadata.xlsx及release manifest都在此。Portable DB：EXE同層data/analysis.db，首次啟動建立；沒有從開發環境複製DB。請複製完整win-unpacked資料夾，不要只取EXE。

驗收狀態以package-verification.json及portable-smoke/result.json為準，兩者passed後才算交付完成。資料缺口或無Landmark來源仍沿用已確認規則，不因打包猜補；一般大型Excel匯出效能不在本次修正範圍。

2026-11-06 最終結果：package-verification.json、asar-verification.json、portable-smoke/result.json皆passed。交付來源5d8a58b；9份Electron／frontend dist檔、1499份backend檔及8份metadata核對一致。EXE health=2.0.1；About與兩個Logic驗收通過，首次backend ready約48秒。smoke資料庫保存於portable-smoke/generated-data（不提交），交付資料夾無DB／raw。驗收截圖about.png，細節見console.log。
