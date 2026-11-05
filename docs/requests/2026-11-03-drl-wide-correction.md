# DRL wide metadata 與已確認路線／TL 規則修正

- 日期：2026-11-03
- Linear project：TOV1050_Analyzer
- Linear issue：DAV-21
- 負責人：Codex
- 狀態：候選標準化與驗證完成；正式啟用尚未進行

## 需求與設計

使用者明確更正：OCS Wire Wear L1 已改 9.1；需要 wide format；DRL 只有 UT 與獨立 PL 路線，不存在 DT，也不把 PL 分配 UT／DT。Location 已由使用者在正式檔改成 Open／Tunnel／Open。DRL 各 TL 支架最小／最大里程可作 TL 邊界，不要求補 Contact 雙端。

本輪沿已批准的「先標準化候選、再手修」流程，產生新版本候選 workbook，不覆寫正式檔或使用者已編輯候選。以當前 config/DRL metadata.xlsx 為 threshold／class／track 權威來源，以前輪 Brackets 點表及 provenance 為點資料來源。threshold 轉成其他線相同的 15 欄 wide schema；Stagger Left／Right 使用相同 magnitude；其他情境數值保持原值。Exception Boundarys 改用明確 UT／PL 欄，不製造 DN。Boundary Review 改為 TL Boundaries，採 user-confirmed min/max，保存來源列與規則。Landmark 未有新區間，不推定。

## 範圍與限制

- 僅建立標準化候選／來源與驗證報告、更新錯誤的舊清單與 Linear；本輪不改 production loader／UI／config／DB，也不聲稱新 workbook 已啟用。
- 現有 loader 的 wide boundary prefix 僅 UP／DN，PL 仍受舊方向模型限制；新 UT／PL schema 接正式程式需後續路線契約調整，不應要求使用者把 PL 改成 UT／DT。
- Track Type 原值未確認錯誤，不要求人工重填。單位轉換依 schema km×1000 一次並保留來源數值。
- Location source 的 43599–43600 m、44300–44301 m 間隔保留並列為邊界語義確認，不靜默延伸。

## 驗收標準與開發計畫

1. 先記錄新來源 SHA，保留現有檔案與編輯。
2. 轉 wide threshold；每個 level 與 long source 逐值比較，OCS 9.1，ORCR 既有 7.44 不改。
3. 三段 Location 與 10／7 個 track intervals 轉 m，UT／PL route 明確。九組 TL 邊界與 Brackets min/max 一致。
4. artifact-tool 產生新 workbook、讀回與視覺驗證；記錄來源 SHA 前後相同。
5. 更新 DAV-21，交付新檔與精確剩餘問題。

## 執行紀錄

已核對當前正式 DRL SHA eb14b76d2c355459e2df684902a3482ef5d54a056e0bf85e8210ab37cef93208。threshold E18/E20/E22/E24 均9.1；location type A2:C4 為 Open 40–43.599、Tunnel 43.6–44.3、Open 44.301–45.5 km。前輪候選仍舊值，不能繼續當最新手修檔。

### 實作與驗證結果

- 候選：`outputs/metadata-review-2026-11-03/drl-wide-v2/DRL metadata (wide UT-PL candidate).xlsx`。共10頁；40列 wide threshold（15欄）、3列明確 UT／PL Class、UT／PL Track Type 10／7列、支架214／80點、TL9組，Overlap sweep UT19／PL15個含精確closure的 atoms。
- `threshold!G4/G9/G14/G19` 的 OCS Wear L1 均9.1；ORCR L1保留7.44。未配置的L3留空，不推定值。
- `Exception Boundarys!D2:G4` 依當前正式來源轉m，D:E=UT、F:G=PL；沒有DN欄。保留來源Open／Tunnel／Open與小間隔。
- `TL Boundaries!A2:H10` 已填 min/max 與user-confirmed規則，取代舊Boundary Review，不要求補Contact。`DRL UT/PL!D:G` 為按TL區間sweep結果，K欄記both／neither，禁止舊closed-both mapper忽略K欄後直接啟用；所有active TL集合皆保留。N僅表示現有點表所列TL集合沒有重疊，域外未知。
- Landmark A:C仍空：沒有提供新的真實區間，不從支架推造。點表差異仍保留原始證據，本輪沒有依舊差異清單任意刪改支架。
- 命令（使用 bundled runtimes）：`python scripts/prepare_drl_wide_correction.py`、`node scripts/build_drl_wide_candidate.mjs outputs/metadata-review-2026-11-03/drl-wide-v2`、`python scripts/validate_drl_wide_correction.py` 全通過。
- 5,002格逐值讀回一致；9組TL min/max獨立核對、每個Overlap atom端點／中點對active TL核對通過；來源3檔SHA前後相同；10頁已render並查看，無公式錯誤。完整結果：同目錄`validation.json`／`source-and-checks.json`。
- Final candidate SHA：0b8fdbed43a37945ff4ed358490141577cbb3e692a76d215710b31a1ca5dfb47。
- 本輪未提交修改：此request、舊median request的DRL superseded註記、3個新候選產生／驗證scripts及新outputs。正式config、前輪候選、DB、偵測程式皆未寫入。這是候選轉換工作，不宣稱runtime已接受新schema。

## Linear 同步

本工作階段已實際掛載 Linear MCP 並讀回 DAV-21。候選轉換／驗證已完成；DAV-21維持In Progress，後續開發action為讓正式loader／context／UI接受獨立UT／PL及精確closure，再以候選與新來源SHA回歸並替換正式檔。資料決策覆蓋歷史DRL缺DT／PL direction／缺Contact端點結論；其他線不擴大套用。

最終已同步 DAV-21 description 最上方的最新決策與next action；驗收comment為 `d0eb1b9a-5d24-4081-bdb9-a2965294fc86`。本輪候選工作完成，正式程式相容工作未標成Done。
