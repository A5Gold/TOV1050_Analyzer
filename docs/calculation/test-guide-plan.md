# 計算模組 — 測試指南計劃

> 語言：繁體中文 | 最後更新：2026-03-16

---

## 1. 測試環境設置

### 前置條件

| 項目 | 版本 / 說明 |
|------|------------|
| Python | 3.10+ |
| Node.js | 18+ |
| Backend | FastAPI，運行於 `http://localhost:8000` |
| Frontend | Vite + React，運行於 `http://localhost:5173` |
| 參考測試檔案 | `Reference_Expired/Test data/TML/TML D3/20251128_TML_D3_MEF-HUH_Exception_Report.xlsx` |

### 啟動服務

```bash
# 終端機 1 — 後端
cd backend
uvicorn app.main:app --reload --port 8000

# 終端機 2 — 前端
cd frontend
npm run dev
```

---

## 2. 單元測試（開發人員）

### 執行全部單元測試

```bash
cd backend
pytest tests/ -v --tb=short
```

---

### 2.1 excel_parser.py

| 測試 ID | 描述 | 預期結果 |
|---------|------|---------|
| UT-EP-01 | 從參考 Excel 解析 Wire Wear 工作表 | 回傳 `WireWearRecord` 列表，含正確 Run Date、TL、MaxValue |
| UT-EP-02 | 從參考 Excel 解析 ChartData 工作表 | 回傳 `ChartDataRecord` 列表，含正確 task_run_date、TL、wear_min |
| UT-EP-03 | 缺少工作表時拋出明確錯誤 | `ValueError`，訊息包含工作表名稱 |
| UT-EP-04 | 空工作表回傳空列表 | `[]` |

```bash
pytest tests/test_excel_parser.py -v
```

---

### 2.2 wear_calculator.py

| 測試 ID | 描述 | 預期結果 |
|---------|------|---------|
| UT-WC-01 | TL "6" 的 avg_wear_min（參考資料） | `12.826 ± 0.001` |
| UT-WC-02 | TL "4" 的 avg_wear_min（參考資料） | `12.768 ± 0.001` |
| UT-WC-03 | SD 計算正確 | 符合 `pandas std(ddof=1)` |
| UT-WC-04 | 全為 NaN 的 wear_min TL 被排除 | 該 TL 不出現在結果中 |
| UT-WC-05 | from_m = min(Chainage)，to_m = max(Chainage) | 邊界值正確 |
| UT-WC-06 | wear_percentage 為參考欄位，不影響邏輯 | 欄位存在但不用於判斷 |

```bash
pytest tests/test_wear_calculator.py -v
```

---

### 2.3 trend_analyzer.py

| 測試 ID | 描述 | 預期結果 |
|---------|------|---------|
| UT-TA-01 | 單一日期輸入，無法計算趨勢（< 2 點） | `trend_points` 為空或 None |
| UT-TA-02 | 兩個日期產生有效斜率/截距 | 斜率不為零 |
| UT-TA-03 | 投影使用實際日期運算，非固定 30 天 | 下一點 = 最後日期 + cycle_days |
| UT-TA-04 | EAL 週期 = 30 天投影 | 日期偏移正確 |
| UT-TA-05 | TML/LMC 週期 = 90 天投影 | 日期偏移正確 |
| UT-TA-06 | logic_1：trend_next ≤ 10.2 | 投影值 ≤ 10.2 時為 True |
| UT-TA-07 | logic_2：\|record_points[0] - trend_next\| > 0.2 | 差值 > 0.2 時為 True |
| UT-TA-08 | recommendation = 'confirmed valid L2' | logic_1=True，logic_2=False |
| UT-TA-09 | recommendation = 'verify on site' | logic_1=True，logic_2=True |
| UT-TA-10 | recommendation = 'no action required' | logic_1=False |

```bash
pytest tests/test_trend_analyzer.py -v
```

---

## 3. API 整合測試

### 3.1 健康檢查

```bash
curl http://localhost:8000/api/calculation/health
```

預期：`{"status": "ok"}`

---

### 3.2 上傳單一 Excel

```bash
curl -X POST http://localhost:8000/api/calculation/upload \
  -F "files[]=@Reference_Expired/Test data/TML/TML D3/20251128_TML_D3_MEF-HUH_Exception_Report.xlsx" \
  -F "line=TML"
```

預期：
- HTTP 200
- `wear_results` 陣列含 29 個 TL 項目
- TL "6" 的 `avg_wear_min` ≈ 12.826
- `trend_results` 為空或單點（單一檔案無法計算趨勢）

---

### 3.3 上傳多個 Excel（趨勢分析）

```bash
curl -X POST http://localhost:8000/api/calculation/upload \
  -F "files[]=@file1.xlsx" \
  -F "files[]=@file2.xlsx" \
  -F "line=TML"
```

預期：
- `trend_results` 含 `record_points` 長度 = 2 的項目
- `trend_points` 投影至下次巡查日期

---

### 3.4 無效檔案

```bash
curl -X POST http://localhost:8000/api/calculation/upload \
  -F "files[]=@somefile.txt"
```

預期：HTTP 422，含明確錯誤訊息

---

### 3.5 Swagger UI 手動測試

開啟 `http://localhost:8000/docs` → `POST /api/calculation/upload` → Try it out → 上傳參考 Excel → Execute

---

## 4. UAT 場景（用戶驗收測試）

> **測試人員：** 維修工程師
> **測試環境：** 本機開發環境或 staging
> **參考檔案：** `20251128_TML_D3_MEF-HUH_Exception_Report.xlsx`

---

### UAT-01：單一檔案磨損分析

**目標：** 驗證單一 Exception Report 的平均磨損計算結果正確

**前置條件：** 服務已啟動，參考 Excel 已備妥

**步驟：**

| 步驟 | 操作 | 預期畫面 |
|------|------|---------|
| 1 | 開啟應用程式，點擊左側導航「導線磨損計算」 | 進入 Calculation 頁面，顯示上傳面板 |
| 2 | 在「線路」下拉選單選擇 `TML` | 下拉顯示 TML |
| 3 | 點擊「選擇 Excel 檔案」，選取參考 Excel | 顯示「1 個檔案已選擇」 |
| 4 | 點擊「開始計算」 | 顯示載入中動畫 |
| 5 | 等待結果載入 | 平均磨損結果表格出現 |

**通過標準：**
- [ ] 表格顯示所有來自 ChartData 的 Tension Length
- [ ] TL "6" 的 `avg_wear_min` = 12.826
- [ ] TL "K16" 的 `avg_wear_min` = 12.927
- [ ] SD 欄位有數值
- [ ] 無錯誤訊息

---

### UAT-02：多檔案趨勢分析

**目標：** 驗證多個不同日期的 Excel 能正確產生 L2 趨勢分析

**前置條件：** 備妥 2 個不同巡查日期的 Exception Report Excel

**步驟：**

| 步驟 | 操作 | 預期畫面 |
|------|------|---------|
| 1 | 進入 Calculation 頁面 | 顯示上傳面板 |
| 2 | 選擇線路（EAL 或 TML） | 下拉顯示選擇值 |
| 3 | 點擊「選擇 Excel 檔案」，同時選取 2 個 Excel | 顯示「2 個檔案已選擇」 |
| 4 | 點擊「開始計算」 | 載入中 |
| 5 | 結果載入後，切換至「Trend Analysis」分頁 | 顯示趨勢圖與趨勢結果表 |
| 6 | 在趨勢圖的 Tension Length 下拉選擇不同 TL | 圖表更新 |

**通過標準：**
- [ ] 趨勢圖 X 軸顯示實際 `task_run_date`（非固定間隔）
- [ ] 每個 TL 顯示 2 個資料點
- [ ] 趨勢線投影至下次巡查日期
- [ ] Recommendation 欄位顯示正確值（confirmed valid L2 / verify on site / no action required）
- [ ] 圖表有 L2 閾值參考線（10.2mm 紅色虛線）

---

### UAT-03：L2 篩選驗證

**目標：** 確認趨勢分析只包含 L2 且無 ACTION 的異常

**步驟：**

| 步驟 | 操作 | 預期畫面 |
|------|------|---------|
| 1 | 上傳含 L1、L2、L3 異常的 Excel | — |
| 2 | 點擊「開始計算」 | — |
| 3 | 查看趨勢結果表 | 僅顯示 L2 項目 |

**通過標準：**
- [ ] L1 異常不出現在趨勢表
- [ ] L3 異常不出現在趨勢表
- [ ] 已有 ACTION 的 L2 異常不出現在趨勢表
- [ ] 無 ACTION 的 L2 異常全部出現

---

### UAT-04：錯誤處理

**目標：** 驗證上傳非 Excel 檔案時的錯誤提示

**步驟：**

| 步驟 | 操作 | 預期畫面 |
|------|------|---------|
| 1 | 點擊「選擇 Excel 檔案」，選取 `.pdf` 或 `.txt` 檔案 | 顯示「1 個檔案已選擇」 |
| 2 | 點擊「開始計算」 | 顯示錯誤訊息 |

**通過標準：**
- [ ] 顯示明確錯誤訊息（紅色 Alert）
- [ ] 應用程式不崩潰
- [ ] 可重新選擇正確檔案並再次計算

---

### UAT-05：無檔案提交

**目標：** 驗證未選擇檔案時的提示

**步驟：**

| 步驟 | 操作 | 預期畫面 |
|------|------|---------|
| 1 | 不選擇任何檔案，直接點擊「開始計算」 | 顯示提示訊息 |

**通過標準：**
- [ ] 顯示「請選擇至少一個 Exception Report Excel」
- [ ] 不發送 API 請求

---

## 5. E2E 測試計劃（Playwright）

### 測試檔案位置

```
frontend/tests/calculation.spec.ts
```

### 執行指令

```bash
cd frontend
npx playwright test tests/calculation.spec.ts --reporter=html
```

---

### E2E 測試案例

| 測試 ID | 場景 | 步驟 | 驗證點 |
|---------|------|------|--------|
| E2E-01 | 上傳並查看磨損結果 | 導航 → 上傳 → 計算 | DataGrid 渲染，TL 數量正確 |
| E2E-02 | 趨勢圖渲染 | 上傳 2 個檔案 → 切換 Trend 分頁 | 圖表 SVG 存在，2 個資料點 |
| E2E-03 | Recommendation 欄位 | 上傳 2 個檔案 → 查看趨勢表 | 至少一個 recommendation 儲存格可見 |
| E2E-04 | 無效檔案被拒絕 | 上傳 `.txt` 檔案 | 錯誤訊息可見 |
| E2E-05 | 無檔案提交 | 不選檔案直接點計算 | 驗證提示訊息出現 |

---

### E2E 測試程式碼範本

```typescript
// frontend/tests/calculation.spec.ts
import { test, expect } from '@playwright/test';
import path from 'path';

const REFERENCE_FILE = path.resolve(
  __dirname,
  '../../Reference_Expired/Test data/TML/TML D3/20251128_TML_D3_MEF-HUH_Exception_Report.xlsx'
);

test.describe('計算模組 E2E', () => {

  test('E2E-01: 上傳單一檔案並查看磨損結果', async ({ page }) => {
    await page.goto('http://localhost:5173');
    await page.click('text=導線磨損計算');
    await expect(page).toHaveURL(/calculation/);

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(REFERENCE_FILE);
    await expect(page.locator('text=1 個檔案已選擇')).toBeVisible();

    await page.click('text=開始計算');
    await expect(page.locator('.MuiDataGrid-root').first()).toBeVisible({ timeout: 15000 });

    const rows = page.locator('.MuiDataGrid-row');
    await expect(rows).toHaveCount(29, { timeout: 10000 });
  });

  test('E2E-02: 趨勢圖在上傳 2 個檔案後渲染', async ({ page }) => {
    await page.goto('http://localhost:5173/calculation');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles([REFERENCE_FILE, REFERENCE_FILE]); // 使用同一檔案模擬
    await page.click('text=開始計算');

    await page.click('text=Trend Analysis');
    await expect(page.locator('.recharts-responsive-container, [data-testid="trend-chart"]'))
      .toBeVisible({ timeout: 15000 });
  });

  test('E2E-03: Recommendation 欄位可見', async ({ page }) => {
    await page.goto('http://localhost:5173/calculation');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles([REFERENCE_FILE, REFERENCE_FILE]);
    await page.click('text=開始計算');
    await page.click('text=Trend Analysis');

    await expect(page.locator('text=confirmed valid L2, text=verify on site, text=no action required').first())
      .toBeVisible({ timeout: 15000 });
  });

  test('E2E-04: 無效檔案顯示錯誤訊息', async ({ page }) => {
    await page.goto('http://localhost:5173/calculation');

    // 建立假的 txt 檔案
    const buffer = Buffer.from('not an excel file');
    await page.locator('input[type="file"]').setInputFiles({
      name: 'test.txt',
      mimeType: 'text/plain',
      buffer,
    });
    await page.click('text=開始計算');

    await expect(page.locator('.MuiAlert-root')).toBeVisible({ timeout: 10000 });
  });

  test('E2E-05: 未選擇檔案時顯示提示', async ({ page }) => {
    await page.goto('http://localhost:5173/calculation');
    await page.click('text=開始計算');

    await expect(page.locator('text=請選擇至少一個 Exception Report Excel')).toBeVisible();
  });

});
```

---

## 6. 測試資料

| 檔案 | 日期 | 線路 | 軌道 | 備註 |
|------|------|------|------|------|
| `20251128_TML_D3_MEF-HUH_Exception_Report.xlsx` | 20251128 | TML | DN | 參考檔案，含 24 個 Wire Wear 異常 |

> **趨勢測試注意：** 若無第二個不同日期的 Excel，可在單元測試中使用合成資料（相同 schema，不同 `task_run_date`）模擬多日期場景。

---

## 7. 測試通過標準總覽

| 層級 | 通過標準 |
|------|---------|
| 單元測試 | 所有 pytest 測試通過，覆蓋率 ≥ 80% |
| API 整合 | 所有 curl 指令回傳預期 HTTP 狀態碼與資料結構 |
| UAT | UAT-01 至 UAT-05 全部通過 |
| E2E | E2E-01 至 E2E-05 全部通過 |
