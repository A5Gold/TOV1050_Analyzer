# npm run dev 新報表測試

2026-11-03，以 `npm run dev` 啟動Vite、Electron及FastAPI，使用正式config、隔離DB。UI自動化透過瀏覽器連接相同dev服務，file-picker adapter只提供真實CSV路徑，沒有攔截API。

## 新產物

| 輸出 | raw筆數 | median ChartData | 例外數 | UI分析連匯出 |
| --- | ---: | ---: | ---: | ---: |
| [20260907 Exception Report](20260907_TWL_UT_MAINLINE_CEN_TSW_Exception_Report.xlsx) | 838859 | 83963 | 289 | 166.49秒 |
| [20260630 Exception Report](20260630_TWL_UT_MAINLINE_CEN_TSW_Exception_Report.xlsx) | 830792 | 83244 | 330 | 172.89秒 |

[History Comparison](20260907_TWL_UT_MAINLINE_CEN_TSW_Exception_Report_2_Repeated.xlsx)直接使用上述兩份新報表；提交約1.09秒，UI約78.57秒顯示完成，worker約76.14秒。重複例外共15筆：Low Height 4、Stagger Left 6、Stagger Right 5。本機單次量測，不作固定效能保證。

兩份報表Stagger Left／Right分別為118／103及112／123。例外偵測仍用完整清理後raw，匯出ChartData為chainage_median。

## 已知限制與待辦

- 正式metadata補值仍未完成：Overlap／Tension Length／Landmark表頭存在，但Summary仍為空白。前輪wide候選尚未promotion；本輪不修改正式config。此功能持續由DAV-21追蹤，不能把生成成功當作補值完成。
- 完整UI流程沒有failed API request；兩次非必要Exception頁截圖各5秒逾時，保留warning，未阻斷報表生成。History截圖見history-ready.png（若已成功保存）。
- Electron已真實啟動，但Electron25的CDP不支援Playwright Browser.setDownloadBehavior，因此UI操作採同dev服務的瀏覽器。沒有驗證原生檔案對話框的人工操作。
- 另發現dev:local硬編wait-on tcp:5174，與dev-latest自動改port不一致；非5174啟動會等待錯誤port。本輪使用預設5174完成，後續由DAV-27追蹤。
- 初輪測試腳本未填量測日期；錯日期產物保留於initial-default-date，不作交付。最終兩份已重新生成，POST date_str與原始CSV日期一致。

## 證據

validation.json記錄實際UI輸出、jobs、counts、runtime diagnostics、耗時、錯誤及來源／config SHA不變結果。readback.json已passed：兩份ChartData／Summary符合上述列數，raw偵測及median匯出provenance正確；比較Excel包含全部15個exception IDs。兩份Summary的metadata三欄分別289／330筆皆空白，屬未完成功能。dev.log為npm啟動及真實HTTP紀錄。測試使用獨立isolated.db，未寫入正式DB；產品程式未修改。
