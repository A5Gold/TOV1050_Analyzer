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
  { id: 'operator-tov1050-input', label: 'TOV1050 輸入' },
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
  { id: 'developer-tov1050-contract', label: 'TOV1050 契約' },
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
    detail: '選取 .datac、Exception Report 或 n_Repeated Report，保留原始檔案與日期身份。',
  },
  {
    title: '對齊 metadata',
    detail: '以 Line、Section、Track、Chainage、threshold、support 及張力段資料建立可追溯位置。',
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
    detail: 'SQLite 保存分析與追蹤紀錄；EAL/TML metadata workbooks 提供受版本控制的業務設定。',
  },
];

export const tov1050InputRows: GuideMatrixRow[] = [
  { cells: ['CSV basename', '只保留為來源 lineage；不要求符合報表命名格式。'] },
  { cells: ['表格 context', 'Date、Line、Direction、Section、Station Start／End 是分析與輸出的 authoritative 參數。'] },
  { cells: ['Filename parser', '只在表格欄位缺漏時 best-effort 補值；解析失敗不阻擋合法 CSV。'] },
  { cells: ['輸出命名', '使用 canonical `YYYYMMDD_LINE_TRACK_SESSION_START_END_<artifact>` 格式，供其他模組穩定引用。'] },
];

export const metadataCanonicalRows: GuideMatrixRow[] = [
  { cells: ['Threshold schema', '`Class`、`Track Type`、`Exc Type` 與各異常 L1/L2/L3 欄位。'] },
  { cells: ['Input formats', 'TOV1050 long table 與 TOV640 legacy wide table 都先轉成 canonical model。'] },
  { cells: ['Mixed workbook', '混合欄位、缺欄、非數值或 threshold 順序錯誤會 fail closed，錯誤需帶 sheet／列號。'] },
  { cells: ['Write-back', '只寫回 canonical 欄位並保留備份，避免舊欄位殘留造成 detector 與 UI 不一致。'] },
];

export const apiOwnershipRows: GuideMatrixRow[] = [
  {
    cells: ['Exception 分析', 'useAnalysisStore', 'POST /api/analyze', 'DataLoader、MetadataManager、ExceptionDetector'],
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
  'backend/app/core/analyzers.py',
  'backend/app/core/comparison.py',
  'backend/app/core/calculation/',
  'backend/app/api/endpoints/',
  'frontend/src/store/',
  'frontend/src/api/client.ts',
  'frontend/src/types/api.ts',
  'backend/tests/ 與 frontend/src/**/__tests__/',
];
