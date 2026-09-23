# TOV1050 Analyzer：Key Module Algorithms & Functions

本文件配合 [技術海報](./07-key-module-algorithm-poster.png) 使用。海報是簡報視覺示意；下列規則以目前 repository 程式碼為準。

## 1. Threshold Determination

`ExceptionDetector._get_vectorized_threshold` 先依 `Exc Type` 篩選 threshold rows，再依 `Track Type` 保留指定 track、空值或 `both`。接著以 `Class` 建立向量化 lookup，讓每筆量測資料取得對應 threshold。

若 class 沒有定義，才使用 `both` fallback；如果 class 有定義但 threshold 是 `NaN`，保留 `NaN`，代表該 class 不進行該項 detection。這個差異避免把「明確沒有 threshold」誤當成預設 threshold。

參考：[analyzers.py](../../backend/app/core/analyzers.py:327)；TOV1050 threshold adapter：[tov1050_metadata.py](../../backend/app/core/tov1050_metadata.py:1)。

## 2. Chain Rule：History Compare

History Compare 先依檔名中的 `YYYYMMDD` 由新到舊排序，再以 accumulator 逐份與前一份報告交集比對。`RepeatedExceptionFinder._standardize_columns` 將新舊 Excel 欄位統一成 `FromM`、`ToM`、`exception type`、`maxLocation` 等名稱。

對同一 `exception type`，兩個 interval 的交集為：

```text
i_start = max(FromM_latest, FromM_previous)
i_end   = min(ToM_latest, ToM_previous)
```

只有 `i_start <= i_end`，而且兩份資料的 `maxLocation` 都落在交集內，才算 repeated match。每輪只保留同一 latest `id` 的第一個 match，並把 previous ID 與 previous geometry 附加到結果。

參考：[analysis.py](../../backend/app/api/endpoints/analysis.py:430)、[repeated_finder.py](../../backend/app/core/repeated_finder.py:9)、[repeated_finder.py](../../backend/app/core/repeated_finder.py:38)。

## 3. Matching Criteria：Valid Match、Gap、Peak Shift

- **Valid Match**：interval 有有效交集，且 latest/previous 的 peak 都在交集內。
- **Gap**：兩個 interval 沒有交集，或交集為空；因此無法形成 repeated chain。
- **Peak Shift**：interval 仍可能重疊，但其中一份 peak 落在交集外；這不是目前 strict intersection 判定的 valid match。

海報將 Gap 與 Peak Shift 分開，是為了讓維護人員看到「區間不相交」與「區間相交但異常峰位漂移」的不同診斷。程式核心目前採 fail-closed 的 strict rule，沒有在 `find_repeated` 內偷偷套用 nearest-point tolerance。

參考：[repeated_finder.py](../../backend/app/core/repeated_finder.py:61)。

## 4. 線耗計算邏輯

`calculate_wear_percentage(mean_remaining)` 將剩餘半徑 `r` 與線材原始半徑 `R` 轉成圓弓形磨耗面積，再除以完整圓截面面積：

```text
cos(theta) = (r - R) / R
worn_area  = theta * R^2 - R * sin(theta) * (r - R)
wear_%     = worn_area / cross_section * 100
```

輸入會先 clamp 到 `[-1, 1]`，輸出 clamp 到 `0..100` 並四捨五入兩位。`mean_remaining == 0` 回傳 `0%`；幾何計算遇到 domain 或除零錯誤時回傳 `100%`，這是現行 defensive behavior。

參考：[wear_calculator.py](../../backend/app/core/calculation/wear_calculator.py:34)。

## 5. Stagger Algorithm Explain

stagger engine 將 span、等效風力係數 `k_eq`、tension 與固定物理係數合成 `B` 值：

```text
B = air/drag/shape factors × (reference wind speed × k_eq)^2
    × area factor × span^2 / (32 × tension)
```

量測與參考 stagger 先形成：

```text
P = abs((stg_x + stg_i) / 2)
S = abs(stg_x - stg_i)
E = S^2 / (16 × B)       (B <= 0 時 E = 0)
allowable = 505 - (B + E) - height_correction
short-circuit pass ⇔ S >= 4 × B
```

TML 的 `k_eq` 使用 threshold strategy：`chi > boundary` 時取 `above`，否則取 `below_or_equal`。metadata loader 將 strategy 與 geometry 一起提供給計算層。

參考：[stagger_formula.py](../../backend/app/core/calculation/stagger_formula.py:10)、[stagger_formula.py](../../backend/app/core/calculation/stagger_formula.py:22)、[stagger_formula.py](../../backend/app/core/calculation/stagger_formula.py:26)、[stagger_formula.py](../../backend/app/core/calculation/stagger_formula.py:30)、[stagger_formula.py](../../backend/app/core/calculation/stagger_formula.py:36)、[stagger_formula.py](../../backend/app/core/calculation/stagger_formula.py:44)、[stagger_keq.py](../../backend/app/core/calculation/stagger_keq.py:51)。

## 6. Trend Analysis Logic

`analyze_trend` 針對 L2 wire-wear records，依 exception ID（有 repeated report 時）或 latest-cycle L2 條件選出候選。它在每個 exception 的 `FromM..ToM` 範圍內，對每個 inspection date 取 `wear_min`，再以日期 ordinal 做線性 regression。

判定使用最新 trend point：

```text
logic_1 = trend_latest <= L2_THRESHOLD
logic_2 = abs(observed_latest - trend_latest) > TOLERANCE
```

結果分成 `no action required`、`verify on site` 或 `confirmed valid L2`。`fit_tl_trend` 則以每個日期的平均剩餘厚度估算 slope、R²、mm/year 與 wear percentage/year；資料不足或斜率非正時會回傳對應狀態。

參考：[trend_analyzer.py](../../backend/app/core/calculation/trend_analyzer.py:87)、[wear_cycle_analytics.py](../../backend/app/core/calculation/wear_cycle_analytics.py:77)。

## 7. SQLite Database Management

`DatabaseManager` 是 thread-safe singleton。`_get_connection` 以 thread-local 儲存每個執行緒的 SQLite connection，開啟 foreign keys、WAL、`synchronous=NORMAL` 與 64 MB cache。`get_connection` 是 transaction context：正常離開時 commit，例外時 rollback。

啟動時 `_init_database` 讀取 `schema.sql`，先套用 repeated、wire-wear 與 cycle migrations，再執行 schema statements；若 packaged build 有 approved seed，則在 schema commit 後以獨立 atomic boundary 初始化。`save_analysis_session` 將 line、section、track、日期、原始檔案資訊等保存為可重建的 analysis session。

參考：[database.py](../../backend/app/core/database.py:116)、[database.py](../../backend/app/core/database.py:188)、[database.py](../../backend/app/core/database.py:204)、[database.py](../../backend/app/core/database.py:845)、[database.py](../../backend/app/core/database.py:944)。

## Presentation caveats

1. Chainage 的 canonical unit 是公尺；`Km * 1000 -> Chainage_m`，例如 `98150.2` 是 `98,150.2 m`。
2. chart downsampling 只作用於 chart payload；detector、threshold crossing、peak、trend source 與 export raw data 使用完整 raw data。
3. 海報上的數字、日期與曲線是教學用 visual demo，不代表某一筆實際維修紀錄。
