export interface GuideNavItem {
  id: string;
  label: string;
}

export interface GuideFlowStep {
  title: string;
  detail: string;
}

export interface GuideMatrixRow {
  cells: string[];
}

export const operatorNavItems: GuideNavItem[] = [
  { id: 'operator-workflow', label: '工作流程' },
  { id: 'operator-tov1050-input', label: '雙系統輸入' },
  { id: 'operator-chart', label: '圖表與資料品質' },
  { id: 'operator-version-difference', label: 'Version Difference' },
  { id: 'operator-threshold', label: 'Threshold' },
  { id: 'operator-repeat', label: 'Repeat' },
  { id: 'operator-year', label: '1 Year' },
  { id: 'operator-wear', label: 'Wear' },
  { id: 'operator-trend-stagger', label: 'Trend 與 Stagger' },
  { id: 'operator-save', label: '保存與診斷' },
];

export const developerNavItems: GuideNavItem[] = [
  { id: 'developer-architecture', label: '架構' },
  { id: 'developer-tov1050-contract', label: '雙系統資料契約' },
  { id: 'developer-cleaning', label: '格式清洗與中位樣本' },
  { id: 'developer-chart', label: '圖表與快照生命週期' },
  { id: 'developer-version-difference', label: 'Version Difference API' },
  { id: 'developer-check-1-year', label: 'Check 1 Year API' },
  { id: 'developer-api-state', label: 'API 與 state' },
  { id: 'developer-contracts', label: '資料合約' },
  { id: 'developer-errors', label: '錯誤分類' },
  { id: 'developer-verification', label: '驗證層' },
  { id: 'developer-diagnostics', label: '執行環境' },
];

export const operatorWorkflowSteps: GuideFlowStep[] = [
  {
    title: '匯入量測',
    detail: '原始資料選 .datac 或 .csv；下游選 Exception Report 或 n_Repeated Report，保留來源與日期身份。',
  },
  {
    title: '對齊 metadata',
    detail: '確認主 Line、Branch、Direction、Section 與公尺 Chainage；功能依核准 metadata 與工程配置開放。',
  },
  {
    title: '執行判斷',
    detail: '依工作需要執行 Threshold、Repeat、1 Year、Wear、Trend 或 Stagger。',
  },
  {
    title: '檢查預覽',
    detail: '先處理 conflict、coverage、blocking reason 及 trace，再決定是否保存。',
  },
  {
    title: '保存或匯出',
    detail: '通過閘門後原子保存；需要修正時保留 staged changes 或依診斷回到來源資料。',
  },
];

export const versionDifferenceRoles: GuideFlowStep[] = [
  { title: 'Latest', detail: '目前要檢查的報表，作為對齊與 difference 的基準。' },
  { title: 'Previous 1', detail: '最近一期歷史報表。可再加入 Previous 2 至 Previous 4。' },
  { title: 'Previous 2-4', detail: '較早的比較週期，角色順序固定，最多五檔含 Latest。' },
  { title: '同一 X 軸', detail: '所有 raw 與 difference 圖共用 X range；每張圖保留自己的 Y range。' },
];

export const versionDifferenceLimits: GuideMatrixRow[] = [
  { cells: ['檔案數量', '最多 5 檔：Latest、Previous 1、Previous 2、Previous 3、Previous 4。'] },
  { cells: ['日常容量', '每檔約 50,000 ChartData 列；解析及 response 會維持 bounded memory。'] },
  { cells: ['單檔上限', '320,000 ChartData rows 或 64 MiB；超過 row／欄位規則回 422，超過 bytes 回 413。'] },
  { cells: ['請求總量', '五個 uploaded payload 合計最多 320 MiB，不含 multipart framing。'] },
  { cells: ['圖表點數', '每個 comparison／metric 最多 8,000 display points；statistics 仍以完整資料計算。'] },
];

export const check1YearDecisionRows: GuideMatrixRow[] = [
  { cells: ['Stagger L3', 'Stagger Left／Right 可互配；命中 L3、L2、L1 均可 auto_verified，不依賴既有 ACTION。'] },
  { cells: ['Stagger L2/L1', 'Stagger Left／Right 可互配，只命中 L2/L1 並排除 L3；Low Height 與 High Height 不可互配。'] },
  { cells: ['Low／High Height', '同 family、同 level scope、同 section／line／track／位置，且在 365 日 window 內。'] },
  { cells: ['Wire Wear L2/L1', '命中且既有 ACTION 為三個 canonical no-action 字串之一時 auto_verified；其他 ACTION 產生 review_required。'] },
  { cells: ['未命中／既有 ACTION', 'L3 產生 Keep monitoring；L2/L1 保持 Pending；目前已有非空且非 Pending ACTION 時 status=skipped 並保持原值。'] },
  { cells: ['候選排序', '先取 365 日邊界內候選，再按有效日期由新至舊；同日以 record_id 由大至小穩定排序，排除 self-match。'] },
];

export const check1YearStatuses: GuideFlowStep[] = [
  { title: 'auto_verified', detail: '回傳 canonical ACTION 與 historical exception_id，automatic append 為 idempotent。' },
  { title: 'review_required', detail: '保留原值，提供 proposed ACTION／Reoccurrence ID、target record、exception 與 version。' },
  { title: 'keep_monitoring', detail: '未命中 L3 時回傳 Keep monitoring，不建立 recurrence link。' },
  { title: 'unmatched／skipped', detail: '保持原資料；日期、位置、identity 或 level 無法解析時以 skipped 加 reason。' },
];

export const architectureLayers: GuideFlowStep[] = [
  {
    title: 'Electron desktop shell',
    detail: '建立桌面視窗、啟動本機 backend 並載入已建置的 React frontend。',
  },
  {
    title: 'React、MUI 與 Zustand',
    detail: 'views 與 components 呈現工作流；stores 擁有 tab-scoped UI、預覽與 staged state。',
  },
  {
    title: 'API client',
    detail: 'Axios helpers 在 TypeScript UI contract 與 FastAPI wire contract 之間做請求及欄位映射。',
  },
  {
    title: 'FastAPI routes',
    detail: 'analysis、database、calculation、wear records、metadata、sessions 與 diagnostics routers 提供 HTTP 邊界。',
  },
  {
    title: 'Core services',
    detail: 'parser、resolver、detector、comparison、trend、stagger、coverage 與 persistence services 執行規則。',
  },
  {
    title: 'SQLite 與 config workbooks',
    detail: 'SQLite 保存分析與追蹤紀錄；各 line/branch/direction 的 metadata workbooks 提供門檻與可用能力。',
  },
];

export const tov1050InputRows: GuideMatrixRow[] = [
  { cells: ['TOV640', 'EAL、TML；原始 .datac。LMC 是 EAL 的分支，不是獨立主 Line。'] },
  { cells: ['TOV1050', 'AEL、TCL、KTL、ISL、TWL、TKL、DRL；原始 .csv。TKS 是 TKL 分支；DRL 分支 UT／PL，UT 對應舊 Mainline。'] },
  { cells: ['分支與方向', '先選 Line，再選 Branch 與 Direction。UT／UP 為上行、DT／DN／DOWN 為下行；DRL branch UT 與 track UT 是不同維度。保留既有 LOW／RAC Section 語義。'] },
  { cells: ['原始檔 context', '確認 Date、Line、Branch、Direction、Section、Task、Station Start／End；原始設備 Line 標籤及 basename 只作來源證據。'] },
  { cells: ['既有報表 context', '下游讀取 workbook 欄位與 _Metadata；缺值才以檔名補正，衝突須處理，不能把 AEL 自動改成 EAL。'] },
  { cells: ['輸出命名', 'YYYYMMDD_LINE_TRACK_SESSION_START_END_Exception_Report.xlsx；省去 _MedianSample，演算法仍記在 workbook metadata。舊檔名仍可匯入。'] },
];

export const measurementFlow: GuideFlowStep[] = [
  { title: '格式專屬清洗', detail: 'DATAC 與 CSV 分別處理 header、invalid、修剪及座標，統一公尺與 channel 名稱。' },
  { title: 'Context 與 metadata', detail: '保存主線／分支／方向、來源列、pass/segment；依核准範圍取得 Class、Track Type 與門檻。' },
  { title: '中位實測樣本', detail: '相鄰精確同 chainage 群內，每個 channel 選一個真實 finite 中位樣本；不跨 gap、pass 或 context 混合。' },
  { title: '判定與報表', detail: 'detector、Excel 與 ChartData 使用同 revision 的代表資料；圖表顯示取樣不改判定或匯出。' },
];

export const dualSystemCleaningRows: GuideMatrixRow[] = [
  { cells: ['來源與 header', '分號 DATAC；LINE/TRACK/KM/LOCATION、WHGT1c/STG1c/RWH1mm 等映射為共同欄。', 'UTF-8 BOM CSV，偵測逗號／分號／tab；Line、Km、HeightWire1 [mm] 等完整量測 headers 必須存在。'] },
  { cells: ['修剪', '資料超過 40 行才移除首尾各 20 行；40 行或以下保留。', '首 100 行及其餘尾部最多 100 行移除；過短或清洗後無量測會回具體錯誤。'] },
  { cells: ['公尺座標', '沿用 KM 整數與格式化 LOCATION 合成 Chainage 的 legacy 規則。', 'Decimal Km × 1000 後才轉 float，只換算一次；保留 source_chainage_km。'] },
  { cells: ['Invalid 與空值', '移除重複 KM header；數值不可解析為 NaN；wear 精確 6.56 設 NaN；缺 KM/LOCATION 的列移除。', '精確字串 1.#IO 設為 NaN；各 channel 數值解析；移除無效 Km 或全部量測無值的列。'] },
  { cells: ['高度', '有效 height1–4 各加 5300 mm 的既有校正。', '已是毫米實測值，不套 DATAC 的 +5300 校正；不套 6.56 wear 特例。'] },
  { cells: ['處理與來源', '保留 source_row_number 與來源標籤；不覆寫原檔。', '50,000 行 chunks；保留來源列、SampleCount（若有）及 cleaning summary；不加入 noise filter。'] },
];

export const chartContractRows: GuideMatrixRow[] = [
  { cells: ['Overview / detail', 'Overview 保留 min/max envelope、首尾、段界及例外位置；detail 用相同代表資料切 window，再取樣，不改量測值。'] },
  { cells: ['Marker 焦點', '點 marker 或右側例外清單，以 maxLocation ±100m 顯示；邊界取資料 domain 交集，三 panel 共用 X；同 dot 可再次聚焦。'] },
  { cells: ['門檻線', '預設顯示，可獨立開關；threshold_segments 使用同 revision 的 detector resolver 與 signed value，只畫實際配置 level，不靠已發生例外推算全線門檻。'] },
  { cells: ['快照隔離', 'client_session_id 是分析分頁身份，與 railway branch/session 不同。detail 以 analysis_revision、mode、window、max_points 隔離；取消或舊 response 不能覆蓋新結果。'] },
  { cells: ['Raw overview', '略過中位精簡與例外偵測，只供清洗後原始量測概覽；不可匯出例外報表。detail cache 有界且有 TTL，離開 raw view 釋放；快取過期需重讀來源檔，可取消並保留現圖。'] },
  { cells: ['來源漂移與重試', 'Raw cache 檢查來源 identity/size/mtime，變動重驗 SHA；來源變更／刪除要求重新匯入。範圍外回空資料；一般失敗保留最後圖，可重試此範圍。'] },
];

export const metadataCanonicalRows: GuideMatrixRow[] = [
  { cells: ['Threshold schema', '`Class`、`Track Type`、`Exc Type` 與各異常 L1/L2/L3 欄位。'] },
  { cells: ['Input formats', 'TOV1050 long table 與 TOV640 legacy wide table 都先轉成 canonical model。'] },
  { cells: ['Mixed workbook', '混合欄位、缺欄、非數值或 threshold 順序錯誤會 fail closed，錯誤需帶 sheet／列號。'] },
  { cells: ['Threshold 空值', 'Class 未定義才 fallback both；Class 已定義但 threshold 為 NaN 不 fallback。沒有配置的 level 不偵測亦不畫線。'] },
  { cells: ['Write-back', '原 metadata 不靜默覆寫；先輸出候選、provenance 與 audit，確認核准來源及端點政策後再安排寫回。'] },
];

export const apiOwnershipRows: GuideMatrixRow[] = [
  {
    cells: ['Exception 分析', 'useAnalysisStore', 'POST /api/analysis/jobs；GET /api/jobs/{id}；GET /api/jobs/{id}/result', '格式 loader、metadata、median、detector 與 revision snapshot；legacy /api/analyze 保留相容'],
  },
  {
    cells: ['歷史比對', 'useHistoryStore', 'POST /api/analyze/compare', 'RepeatedExceptionFinder 與 comparison export'],
  },
  {
    cells: ['1 Year 與紀錄', 'useDatabaseStore', '/api/database/repeated-records*', 'SQLite repeated-record workflow'],
  },
  {
    cells: ['Wear 預覽與保存', 'useWearStore', '/api/calculation/wear-records/cycles/*', 'cycle preview、resolver、coverage、atomic save'],
  },
  {
    cells: ['Wear staged workbench', 'useWearRecordsStore', '/api/calculation/wear-records/changes', 'change set validation 與 data version'],
  },
  {
    cells: ['Trend', 'useTrendStore', 'POST /api/calculation/trend', 'L2 candidate、regression、recommendation'],
  },
  {
    cells: ['Stagger', 'useCalculationStore', 'POST /api/calculation/stagger', 'candidate selection、support lookup、span trace'],
  },
];

export const contractRows: GuideMatrixRow[] = [
  { cells: ['共同報表 context', '逐筆保留主 line＋branch＋direction＋section、task/stations 與來源標籤；來源系統與 run/date context 由 catalog／_Metadata 保存。LMC/TKS legacy aliases 由來源 adapter 解析，不全域替換 line 字串。'] },
  { cells: ['Algorithm provenance', '_Metadata 保存 algorithm、來源／metadata digest 與 revision；代表樣本的來源列在 ChartData 保留。表格、ChartData、Excel 同 revision；不以 _MedianSample 檔名後綴辨認演算法。'] },
  { cells: ['比較 scope', '同一次比較限相容主線／分支／方向；History／Version 遇多 Section 或不同 Section 明確拒絕，須先分拆。跨期以物理身份配對，日期作時間軸；不同 raw/median 模式不得混淆。舊 provenance 缺失標 unknown，可相容不代表 algorithm verified。'] },
  {
    cells: ['Section-aware resolution', '先以 Section、Track 與原始 Chainage 做 strict match；只有真正 gap 才可做 exact transition。'],
  },
  {
    cells: ['Composite source signature', '保留 ordered raw TL identity、source row、source bounds 及 primary TL，不把順序或來源壓平。'],
  },
  {
    cells: ['Canonical split geometry', '同一 TL 可有多個 physical intervals；顯示方向依 intervals，不用 canonical Track 取代幾何。'],
  },
  {
    cells: ['Preview-level index', '每次 preview 建立一次 resolution index，preview 與 save 使用同一決定資料。'],
  },
  {
    cells: ['Deterministic save', 'preview_digest、expected data_version、conflict audit 及 blocking reasons 必須在保存時仍有效。'],
  },
  {
    cells: ['Tab 與 staged state', 'Wear 分析狀態按 calculation tab 隔離；add、edit、delete_cell、delete_row 在提交前留在 change set。'],
  },
];

export const blockingErrorRows: GuideMatrixRow[] = [
  { cells: ['工程配置尚未核准', '報表可辨識不代表可運算；Stagger 缺該主線／分支／方向的係數或 support，須補核准配置，不借用另一條線的公式。'] },
  { cells: ['Enrichment 缺區間', 'Overlap／Tension Length／Landmark 顯示缺資料原因；observed bracket envelope 或單一點不是核准實體區間。unknown 不能補 N／0。'] },
  { cells: ['UNKNOWN TL identity', '列出 Line、sheet row、raw signature 與 identity，修正 metadata 或來源欄位。'] },
  { cells: ['位置或來源無效', '檢查 Section、Track、Chainage、source bounds 與 ordered source signature。'] },
  { cells: ['解析不唯一', '多個 exact transition rows 或多個 primary TL 一律 HTTP 422，不自動選最近值。'] },
  { cells: ['Conflict 未接受', '在 preview 中檢查來源值與較低值決定，接受後才可保存。'] },
  { cells: ['Preview 已過期', '重新預覽以更新 preview_digest 或 data_version，不覆蓋較新的資料。'] },
  { cells: ['必要 segment 缺失', '回到上載清單補齊指定 segment 或確認檔案分類。'] },
];

export const verificationRows: GuideMatrixRow[] = [
  { cells: ['單元層', 'classifier collision、resolver strict gap、coverage、aggregation、store 與 presentation helpers。'] },
  { cells: ['API 層', 'HTTP 200/422、preview/save determinism、conflict acceptance、atomic transaction 與 diagnostics。'] },
  { cells: ['真實檔案層', 'EAL Mainline、RAC、LOW S1、LMC 及 TML complete cycle；缺失 fixture 只記錄，不還原。'] },
  { cells: ['前端元件層', 'tabs、staged add/edit/delete、failed-save retention、dialog、About loading/success/failure。'] },
  { cells: ['瀏覽器層', 'light/dark、desktop/mobile、keyboard/focus、真實 EAL/TML 工作流與 screenshot audit。'] },
  { cells: ['建置層', 'full pytest、Vitest shards、ESLint、TypeScript、Vite production build 與 Electron path smoke test。'] },
];

export const guideSourceReferences = [
  'backend/app/core/data_ingestion.py',
  'backend/app/core/tov1050_data_ingestion.py',
  'backend/app/core/chainage_reduction.py',
  'backend/app/core/analyzers.py',
  'backend/app/core/comparison.py',
  'backend/app/core/calculation/',
  'backend/app/api/endpoints/',
  'frontend/src/store/',
  'frontend/src/api/client.ts',
  'frontend/src/types/api.ts',
  'backend/tests/ 與 frontend/src/**/__tests__/',
];
