# TOV640 Analyzer Web UI Review Comment Triage

日期：2026-05-08  
來源：使用者對 TOV640 Analyzer web UI 的 32 條 review comments 整理

## 總結

這批 comments 的主軸很集中，主要落在四個方向：

1. **資訊層級不清楚**：重要結果區、關鍵欄位、判斷結果沒有被放在最優先的位置。
2. **結果區優先權不足**：多個模組都出現 upload 區、功能列、統計卡佔用過多高度，壓縮主要表格與分析結果。
3. **縮窗適配不足**：視窗縮小後 toolbar、固定欄位、表格與按鈕會擠壓、重疊或變形。
4. **圖表與演算法說明可讀性不足**：圖表標示樣式、sticky/frozen 行為、Trace 呈現方式、演算法說明圖都仍可提升。

以下將 comments 分成 `Bug List`、`Quick Wins`、`Enhancement Plan` 三類，並合併重複項目，讓下一個 session 可以直接接手。

---

## Bug List

### B1. Web 測試模式無法上傳檔案
- **原 comment 編號**：#1
- **模組/頁面**：Exception Generator / web test mode
- **問題摘要**：在 web 測試模式下，使用者無法正常上傳檔案；畫面仍偏向 Electron/desktop 的檔案選擇流程。
- **建議處理方式**：確認 browser mode 是否缺少 `<input type="file">` 可用流程、事件綁定或 mock path fallback。將此項標記為 `web-mode compatibility bug`，避免與正式桌面版功能混淆。
- **優先級**：High

### B2. Summary 表格橫向捲動時 frozen 欄位與移動欄位重疊
- **原 comment 編號**：#27
- **模組/頁面**：Stagger Calculation / Summary table
- **問題摘要**：使用者向右捲動表格時，固定欄位與可捲動欄位發生視覺重疊與遮擋。
- **建議處理方式**：檢查 DataGrid pinned/frozen column 設定、z-index、背景色與陰影分隔，必要時減少預設固定欄數。
- **優先級**：High

### B3. 縮窗後 History Compare 功能列按鈕擠壓變形
- **原 comment 編號**：#3
- **模組/頁面**：History Compare
- **問題摘要**：視窗不是全螢幕時，工具列按鈕寬度被壓縮並出現不自然展開，易造成誤讀與誤點。
- **建議處理方式**：將頂部工具列改為可換行或分組收納，為關鍵按鈕設定穩定 min-width / icon-only 模式 / overflow menu。
- **優先級**：High

---

## Quick Wins

### Q1. 表格欄寬與 auto-fit 可用性改善
- **原 comment 編號**：#4、#10、#11
- **合併說明**：三則 comment 都在反映欄位可讀性不足。
- **模組/頁面**：History Compare、Wear Calculator、Database Record
- **問題摘要**：缺少 auto-fit 欄寬功能，`Track`、`ID` 等欄位無法完整顯示內容。
- **建議處理方式**：新增 `Auto-fit column widths` 按鈕；同步調整 `Track`、`ID` 的預設最小寬度，並針對常見長字串欄位設定較合理的 `minWidth`。
- **優先級**：High

### Q2. 移除重複操作按鈕，減少介面雜訊
- **原 comment 編號**：#19、#20
- **合併說明**：兩則 comment 都指出 `更換主檔` / `更換 n_Repeated` 與檔名 chip 的 `x` 刪除操作重複。
- **模組/頁面**：Stagger Calculation
- **問題摘要**：同一件事提供兩種入口，增加操作列寬度與認知負擔。
- **建議處理方式**：若 `x` 已足夠完成移除與重選流程，可移除「更換」按鈕；若仍需保留，應改成更明確的 secondary action。
- **優先級**：High

### Q3. Tab 區加入 Reset All，並將主要切換控制放上方
- **原 comment 編號**：#8、#21
- **合併說明**：兩則 comment 都要求在 tab 區附近補 `Reset All`，並提升 cycle/tab 控制的可見性。
- **模組/頁面**：Trend Analyzer、Stagger Calculation
- **問題摘要**：多 tab / multi-cycle 流程缺少明確全域重設入口，且控制位置不夠直覺。
- **建議處理方式**：在 tab bar 右側加入 `Reset All`，並將 cycle 選擇與新增按鈕統一置頂。
- **優先級**：Medium

### Q4. 演算法說明對話框格式需與整體 UI 一致
- **原 comment 編號**：#2
- **模組/頁面**：History Compare / Algorithm Logic dialog
- **問題摘要**：結果欄位說明區塊的視覺樣式與其他說明卡不一致，顯得突兀。
- **建議處理方式**：改為與其他 info card 相同的 spacing、底色、字級與標題層級，避免深色大塊區域破壞一致性。
- **優先級**：Medium

### Q5. Stagger Case A / Case B 說明需拆成兩個獨立區塊
- **原 comment 編號**：#17
- **模組/頁面**：Stagger Calculation
- **問題摘要**：Case A / Case B 說明被寫在同一長列訊息中，不利掃讀。
- **建議處理方式**：拆成左右或上下兩個獨立資訊卡，分別說明資料來源、適用情境與差異。
- **優先級**：Medium

### Q6. 統計卡高度過大，可改為更緊湊資訊卡
- **原 comment 編號**：#22、#23、#24、#25
- **合併說明**：四則 comment 都在要求 `已載入檔案 / 分析結果 / 需注意項目 / 已套用 Case` 的卡片縮小。
- **模組/頁面**：Stagger Calculation
- **問題摘要**：統計卡僅呈現單一數字與狀態，卻佔用過多垂直空間。
- **建議處理方式**：改為低高度 KPI strip、緊湊卡片或單列 stats bar，將更多高度讓給結果區。
- **優先級**：Medium

---

## Enhancement Plan

### E1. Database Record 版面重整，以資料表為主體
- **原 comment 編號**：#5
- **模組/頁面**：Database Record
- **問題摘要**：最重要的 database table 可視區太小，卻被 section tab、filters、function buttons 佔去過多空間。
- **建議處理方式**：重設頁面資訊層級，優先放大 table 區；filters 改為可收合或單列；bulk actions 與 export 操作收斂到次級工具列。
- **優先級**：High

### E2. Metadata Editor 功能列瘦身與操作流程簡化
- **原 comment 編號**：#6
- **模組/頁面**：Metadata Editor
- **問題摘要**：功能列佔位過大，視覺上不夠清楚，也不夠容易使用。
- **建議處理方式**：將 `Add Row`、篩選器、儲存操作重整成緊湊工具列；明確區分「篩選」與「編輯動作」。
- **優先級**：Medium

### E3. Upload 區縮小，避免壓縮主結果區
- **原 comment 編號**：#7、#12、#18
- **合併說明**：三則 comment 都指出 upload 區太大，應縮小或移到側邊。
- **模組/頁面**：Trend Analyzer、Wear Calculator、Stagger Calculation
- **問題摘要**：drag-and-drop 區與說明區佔用過多高度，導致主要分析結果區被迫下移。
- **建議處理方式**：將 upload 區改為更矮的 compact dropzone，或採左右分欄，把主要結果區盡量拉到首屏。
- **優先級**：High

### E4. 分析結果區應擴大，成為模組主視覺焦點
- **原 comment 編號**：#13、#14、#26
- **合併說明**：三則 comment 都指出結果區是核心資訊，但目前顯示面積不足。
- **模組/頁面**：Wear Calculator、Trend Analyzer、Stagger Calculation
- **問題摘要**：分析後的圖表、表格、summary 區域被過多前置控制壓縮。
- **建議處理方式**：重排版面，讓 chart/table/summary 區在分析完成後取得更多高度，必要時支援 results-first layout。
- **優先級**：High

### E5. 圖表在頁面捲動時保持可持續參照
- **原 comment 編號**：#9、#15
- **合併說明**：兩則 comment 都要求 graph 在往下捲動時仍能保持可視或具 sticky/frozen 參照效果。
- **模組/頁面**：Wear Calculator、Trend Analyzer
- **問題摘要**：使用者往下查看表格時，無法同時持續參照上方圖表。
- **建議處理方式**：評估 sticky chart header、縮略固定圖、同步 hover/highlight，或將圖表與表格改為上下分割可調面板。
- **優先級**：Medium

### E6. Trend Analyzer 關鍵欄位往左移，提升判讀效率
- **原 comment 編號**：#16
- **模組/頁面**：Trend Analyzer
- **問題摘要**：`Logic 1`、`Logic 2`、`Recommendation` 是關鍵資訊，但目前偏右，閱讀成本高。
- **建議處理方式**：調整欄位順序，將判斷邏輯與建議靠左；可搭配色彩、badge 或 icon 讓結果更易掃讀。
- **優先級**：High

### E7. Trace tab 改為可視化判斷面板
- **原 comment 編號**：#28、#29
- **合併說明**：兩則 comment 都在指出 Trace 現在太像文字 dump，不利理解。
- **模組/頁面**：Stagger Calculation / Trace tab
- **問題摘要**：`資料來源` 與 `判斷結果` 雖有內容，但缺少視覺層次與 Pass/Fail 聚焦。
- **建議處理方式**：把 `S >= 4B` 與 `P <= Allowable` 拆成兩個可視化 criteria block，明確顯示 key parameter、比較式、結果狀態與最終判定。
- **優先級**：High

### E8. Raw Data 圖表樣式需更接近分析語意
- **原 comment 編號**：#30
- **模組/頁面**：Stagger Calculation / Raw Data chart
- **問題摘要**：`Alarm Range`、`MaxLocation` 的視覺標示不夠直覺，文字與圖形也稍嫌干擾。
- **建議處理方式**：將 `Alarm Range` 改成更透明的灰色區塊並隱藏文字；將 `MaxLocation` 改為紅色虛線與貼近 x 軸的小三角標記。
- **優先級**：Medium

### E9. About 頁需要整體視覺重做
- **原 comment 編號**：#31
- **模組/頁面**：About
- **問題摘要**：About 頁整體觀感不佳，缺少更成熟一致的產品介紹設計。
- **建議處理方式**：重新整理頁面層級、模組卡、文案節奏與留白，讓 About 頁更像產品總覽而不是文字堆疊。
- **優先級**：Low

### E10. 演算法說明視窗導入正式 PNG 與結構化解說
- **原 comment 編號**：#32
- **模組/頁面**：Stagger Calculation / Algorithm explain dialog
- **問題摘要**：現有說明圖不如 `Stagger Calculation Algorithm.png` 完整，應改用正式圖並補充文字導讀。
- **建議處理方式**：在對話框中置入 `docs/stagger/Algorithm Explain/Stagger Calculation Algorithm.png`，下方補簡短名詞說明與演算流程摘要。
- **優先級**：High

---

## 建議實作順序

1. **先處理明確 bug**
   - B1 `web mode 無法上傳`
   - B2 `frozen 欄位重疊`
   - B3 `History Compare 縮窗工具列變形`

2. **再做低風險高回報 quick wins**
   - Q1 `欄寬與 auto-fit`
   - Q2 `移除重複更換按鈕`
   - Q3 `tab 區 reset all`
   - Q6 `統計卡縮小`

3. **接著做結果優先的版面調整**
   - E3 `upload 區縮小`
   - E4 `結果區放大`
   - E6 `關鍵欄位左移`
   - E5 `圖表 sticky / frozen 參照`

4. **最後做較完整的 UX 強化**
   - E1 `Database Record 重整`
   - E2 `Metadata Editor 重整`
   - E7 `Trace 可視化`
   - E8 `Raw Data 圖樣式`
   - E10 `演算法圖導入`
   - E9 `About 頁重做`

---

## 合併 comment 群組摘要

- `#4 + #10 + #11`：表格欄寬 / auto-fit
- `#19 + #20`：重複的更換檔案操作
- `#8 + #21`：tab 區 reset all / 控制位置
- `#22 + #23 + #24 + #25`：統計卡過大
- `#7 + #12 + #18`：upload 區太大
- `#13 + #14 + #26`：結果區應放大
- `#9 + #15`：scroll 時圖表需保持可參照
- `#28 + #29`：Trace tab 可視化

