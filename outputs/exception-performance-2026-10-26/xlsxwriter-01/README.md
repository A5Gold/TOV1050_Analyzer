# XlsxWriter constant_memory 隔離概念評估

本目錄只保存可丟棄的實驗，不是 production writer。主代理已決定本輪維持現有 writer，不安裝至 venv、不修改 requirements。

## 環境與量測

- Python 3.12.8、openpyxl 3.1.5／LXML=False；XlsxWriter 3.2.9 安裝至本目錄 `target/`。pip 使用相容 pure Python wheel，沒有繞過 TLS。
- 固定 deterministic 10,000×31 ChartData，其中 19 欄數字；含 null、NaN、正負無窮、日期時間、空字串、中文、XML 特殊字元及公式字串。另有全部五種 exception sheets、Summary、統計及 hidden metadata。
- 兩引擎使用相同 legacy Summary／exception preparation；XlsxWriter 只替換最終逐列寫入。
- 每引擎暖機一次、正式三次；正式順序 ABBAAB。現有 full benchmark 同時執行，背景負載會影響絕對耗時，非無負載或真實 full A/B。
- openpyxl 正式 19.058／21.880／19.703 秒；XlsxWriter 12.867／11.741／12.262 秒。中位數 19.703→12.262 秒，約 1.607 倍，少 37.8%。讀回驗證時間不計入 writer 耗時。

## 等價驗證與診斷

初次 `summary.json`／`process.log` 記錄不等及 assertion failure，保留原檔。原因是 openpyxl 未儲存的空白格讀回 `EmptyCell.number_format=None`，XlsxWriter 明確空白格為 `General`。Excel 的缺省數字格式同為 General，核對時正規化這個差異；null 的 XML cell type 亦正規化為 blank。

`validate_existing.py` 使用相同八份原產物重新核對，不重寫報表、不重跑時間。結果保存至 `validated-summary.json`／`validation.log`。核對項目為每份工作簿所有工作表的每個值、非空白資料型別、數字格式、行列順序、工作表順序／hidden 狀態及 ZIP 完整性。數字／日期沒有因比較方便作顯示精度 rounding。

## 本次未涵蓋的相容風險

- prototype 的 header 只近似常用外觀，沒有證明全部 font／fill／border／alignment／protection、layout 等價。
- 空白格 XML 表示不相同；需要依賴 cell type 的下游程式仍可能觀察到差異。
- 公式 cached value、特殊字串 escaping、URL／公式辨識、1900 日期系統與完整 Excel type 邊界須正式契約測試。
- 未驗 cancellation／timeout／temporary file cleanup、Windows 檔案鎖、寫入失敗釋放、ZIP64／超大型報表、PyInstaller 封裝及啟動。
- 未量測記憶體峰值，未執行真實 partial/full candidate 匯出；不可把 synthetic 1.607 倍直接推論成使用者資料耗時。

若未來採納，需先具體設計 production adapter，完成以上契約及最終真實資料逐列驗證；本輪不變更引擎。
