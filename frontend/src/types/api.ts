// Request Types
export interface AnalyzeRequest {
  file_path: string;
  line: string;
  section: string;
  track: string;
  date_str: string;
  // Optional fields for custom file naming
  task_no?: string;
  station_start?: string;
  station_end?: string;
}

// Response Types
export interface AnalysisResponse {
  status: string;
  params: AnalyzeRequest;
  exceptions: Record<string, ExceptionRecord[]>;
  boundaries: BoundaryRecord[];
  chart_data: Record<string, (number | null)[]>; // Column-oriented data
}

export interface ExceptionRecord {
  id: string;
  'exception type': string;
  level: string;
  FromM: number;
  ToM: number;
  length: number;
  maxValue: number;
  maxLocation: number;
  'Track Type': string;
  Overlap: string | null;
  'Tension Length': number | string | null;
  Landmark: string | null;
  Class: string;
  'Threshold Value': number | null;
  Section: string;
  'Previous ID'?: string;
}

export interface BoundaryRecord {
  Class: string;
  FromM: number;
  ToM: number;
}

export interface CompareResponse {
    status: string;
    repeated: Record<string, ExceptionRecord[]>;
    stats: {
        total: number;
        breakdown: Record<string, number>;
    };
    chain_order: string[];
    chart_data?: (Record<string, (number | null)[]> | null)[];
}

export interface AlignedMetricResult {
    status: 'ready' | 'unavailable';
    reason?: string | null;
    shift_m: number | null;
    rmse: number | null;
    normalized_rmse: number | null;
    overlap_from: number | null;
    overlap_to: number | null;
    overlap_length: number | null;
    valid_points: number;
    chainage: number[];
    latest: (number | null)[][];
    previous: (number | null)[][];
    difference: (number | null)[][];
}

export interface AlignedComparison {
    status: 'ready' | 'unavailable';
    reason?: string | null;
    latest_file?: string;
    previous_file?: string;
    step_m: number;
    max_shift_m: number;
    metrics: Partial<Record<'height' | 'stagger' | 'wear', AlignedMetricResult>>;
}

export type VersionDifferenceComparisonKey = import(
  '../constants/versionDifferenceCycles'
).VersionDifferenceComparisonKey;

export interface VersionDifferenceComparison extends AlignedComparison {
    key: VersionDifferenceComparisonKey;
    previous_file: string;
}

export interface VersionDifferenceResponse {
    status: 'ready' | 'unavailable';
    reason?: string | null;
    latest_file: string;
    comparisons: VersionDifferenceComparison[];
}

export interface MetadataRow {
  Class: string;
  "Track Type"?: string;
  "Exc Type": string;
  [key: string]: string | number | null | undefined;
}

// =============================================================================
// STATEFUL TRANSFORMATION TYPES (Phase 7.3)
// =============================================================================

/**
 * Historical analysis session from database (Stateful Transformation)
 */
export interface HistoricalSession {
  id: string;                        // UUID
  line: string;                      // TOV1050 line identifier
  section: string;                   // Mainline / RAC / LOW / LMC
  track: string;                     // UP / DOWN
  date_str: string;                  // YYYYMMDD
  status: string;                    // pending / completed / failed / archived
  created_at: string;                // ISO timestamp
  analyzed_at: string | null;        // ISO timestamp
  total_exceptions: number;
  l1_count: number;
  l2_count: number;
  l3_count: number;
  task_no: string | null;
  station_start: string | null;
  station_end: string | null;
  raw_data_file_name: string | null;
}/**
 * Exception record from database (linked to a session)
 */
export interface DatabaseException {
  id: string;
  session_id: string;
  exception_type: string;
  level: string;
  from_m: number;
  to_m: number;
  length: number | null;
  max_value: number | null;
  max_location: number | null;
  track_type: string | null;
  overlap: string | null;
  tension_length: string | null;
  landmark: string | null;
  class: string | null;
  threshold_value: number | null;
  section: string | null;
  current_status: string;            // pending / in_progress / resolved / deferred / false_positive
  notes: string | null;
  assigned_to: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  detected_at: string;
}

/**
 * Sessions list API response
 */
export interface SessionsListResponse {
  status: string;
  total: number;
  sessions: HistoricalSession[];
}

/**
 * Single session API response
 */
export interface SessionResponse {
  status: string;
  session: HistoricalSession;
}

/**
 * Session exceptions API response
 */
export interface SessionExceptionsResponse {
  status: string;
  total: number;
  exceptions: DatabaseException[];
}

// =============================================================================
// DATABASE RECORD TYPES (Sub-module 1 & 2)
// =============================================================================

/**
 * Filters for database record queries
 */
export interface DatabaseFilters {
  /** TOV1050 line/session contract. `section` remains the backend wire name. */
  line?: string;
  track?: string;
  section?: string;
  session?: import('../config/tov1050').Tov1050Session;
  date_from?: string;
  date_to?: string;
  level?: string;
  exception_type?: string;
  class?: string;
  overlap?: string;
  action?: string;
  // Feature-003: Task Number filter
  task_number?: string;
  // Chainage range filters (partial overlap logic)
  from_m_min?: number;
  from_m_max?: number;
  to_m_min?: number;
  to_m_max?: number;
  // NEW: Chainage simplified range (Phase 8.3)
  chainage_from?: number;
  chainage_to?: number;
  // NEW: Task Run Date filters (Phase 8.3)
  task_run_date_from?: string;
  task_run_date_to?: string;
  // NEW: saved_at date filter (Phase 8.3)
  saved_at_date?: string;
  // Feature-003: Date type toggle (task_run_date or saved_at)
  date_type?: 'task_run_date' | 'saved_at';
  limit?: number;
  offset?: number;
}


/**
 * Saved repeated exception record (Sub-module 2)
 * Enhanced (2026-01-31): Added 9 new workflow columns
 */
export interface SavedRepeatedRecord {
  record_id: number;
  exception_id: string;
  exception_type: string;
  level: string;
  from_m: number;
  to_m: number;
  length: number | null;
  max_value: number | null;
  max_location: number | null;
  track_type: string | null;
  overlap: string | null;
  tension_length: string | null;
  landmark: string | null;
  class: string | null;
  threshold_value: number | null;
  section: string | null;
  previous_1: string | null;
  previous_2: string | null;
  repeat_count: number;
  // Reoccurrence Tracking (NEW)
  reoccurrence_id: string | null;
  // Initial Check workflow
  action: string | null;
  check_date: string | null;
  checked_by: string | null;
  check_result: string | null;
  remarks: string | null;
  // Site Verification workflow (NEW)
  verify_deadline: string | null;
  verify_date: string | null;
  verify_result: string | null;
  verified_by: string | null;
  // Final Adjustment workflow (NEW)
  adjust_deadline: string | null;
  adjust_date: string | null;
  adjust_result: string | null;
  adjusted_by: string | null;
  // Task Run Data / Metadata
  line: string;
  track: string;
  date_str: string;
  task_run_date: string | null;  // NEW: Phase 8.1 (2026-02-01)
  task_no: string | null;
  station_start: string | null;
  station_end: string | null;
  latest_file_name: string | null;
  comparison_files: string | null;
  saved_at: string;
  last_updated: string;
  saved_by: string | null;
}

/**
 * Request to save repeated records (Sub-module 2)
 */
export interface SaveRepeatedRecordsRequest {
  line: string;
  track: string;
  date_str: string;
  repeated_exceptions: ExceptionRecord[];
  task_no?: string;
  station_start?: string;
  station_end?: string;
  latest_file_name?: string;
  comparison_files?: string[];
  saved_by?: string;
  task_run_date?: string;  // NEW: Phase 8.1 (2026-02-01)
  approved_recurrence_links?: Array<{
    exception_id: string;
    target_record_id: number;
    target_version: string;
  }>;
}

/**
 * Request to update repeated record workflow fields
 * Enhanced (2026-01-31): Now supports 13 workflow fields
 */
export interface UpdateRepeatedRecordRequest {
  // Initial Check
  action?: string;
  check_date?: string;
  checked_by?: string;
  check_result?: string;
  remarks?: string;
  // Site Verification (NEW)
  verify_deadline?: string;
  verify_date?: string;
  verify_result?: string;
  verified_by?: string;
  // Final Adjustment (NEW)
  adjust_deadline?: string;
  adjust_date?: string;
  adjust_result?: string;
  adjusted_by?: string;
  // Reoccurrence (NEW)
  reoccurrence_id?: string;
}

/**
 * Generic API success response
 */
export interface ApiSuccessResponse {
  status: string;
  message: string;
}

/**
 * Save records API response
 */
export interface SaveRecordsResponse {
  status: string;
  message: string;
  saved_count: number;
  filtered_mock_count?: number;
}


/**
 * Repeated records list API response
 */
export interface RepeatedRecordSectionCounts {
  all: number;
  mainline: number;
  rac: number;
  low_s1: number;
  lmc: number;
  unknown: number;
}

export interface RepeatedRecordsResponse {
  status: string;
  total: number;
  section_counts: RepeatedRecordSectionCounts;
  records: SavedRepeatedRecord[];
}

// =============================================================================
// NEW TYPES (2026-01-31): IMPORT AND CHECK 1 YEAR RECORD
// =============================================================================

/**
 * Request to import repeated records from Excel data
 */
export interface ImportRecordsRequest {
  records: Record<string, any>[];
  line: string;
  track: string;
  date_str: string;
}

/**
 * Response from import operation
 */
export interface ImportRecordsResponse {
  status: string;
  message: string;
  created_count: number;
  updated_count: number;
  error_count: number;
}

/**
 * Exception data for Check 1 Year Record feature
 */
export interface Check1YearException {
  id: string;
  exception_type: string;
  level: string;
  max_location: number;
  from_m: number;
  to_m: number;
  line: string;
  track: string;
  section?: string;  // Feature-001: Optional section filter
  task_run_date?: string;  // FIX: Required for 1-year date range calculation
  action?: string;  // FIX: Use 'action' to match backend field name
  current_check_result?: string;
}

/**
 * Request for Check 1 Year Record feature
 */
export interface Check1YearRequest {
  current_date: string;
  line: string;
  track: string;
  exceptions: Check1YearException[];
  // Feature-001: Optional filter parameters for scoped queries
  section?: string;
  date_from?: string;
  date_to?: string;
}

/**
 * Match result from Check 1 Year Record
 */
export interface Check1YearMatch {
  exception_id: string;
  db_record_id: string;
  action: string;
  matched_date: string;
  matched_location?: number;
}

/**
 * Response from Check 1 Year Record operation
 * Supports both backend format (status/match_count/exceptions) and legacy format
 */
export interface Check1YearResponse {
  success?: boolean;
  status?: string;
  message: string;
  matched_count?: number;
  match_count?: number;
  checked_count?: number;
  auto_verified_count?: number;
  review_required_count?: number;
  keep_monitoring_count?: number;
  unmatched_count?: number;
  skipped_count?: number;
  review_proposals?: Array<Record<string, any>>;
  matches?: Check1YearMatch[];
  exceptions?: Array<Record<string, any>>;
}

// =============================================================================
// CALCULATION TYPES
// =============================================================================

export interface WearResult {
  tension_length: string
  from_m: number
  to_m: number
  line: string
  track: string
  section?: string
  cycle_date?: string
  avg_wear_min: number
  sd: number
  wear_percentage: number
  dates: string[]
  record_points: number[]
  task_run_date?: string
}

export interface WearResponse {
  date: string
  wear_results: WearResult[]
}

export type WireWearLineGroup = 'EAL' | 'TML'
export type WireWearLineClass = 'EAL' | 'LMC' | 'TML'

export interface WireWearRecordInput {
  tension_length: string
  from_m: number
  to_m: number
  avg_wear_min: number
  sd: number
  wear_percentage: number
}

export interface WireWearSaveRequest {
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  track: string
  section: string
  cycle_date: string
  source_file_names: string[]
  saved_by?: string
  records: WireWearRecordInput[]
}

export interface WireWearSavedRecord extends WireWearRecordInput {
  record_id: number
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  track: string
  section: string
  cycle_date: string
  source_file_names: string[]
  saved_by?: string | null
  created_at: string
  updated_at: string
}

export interface WireWearSaveResponse {
  saved_count: number
  updated_count: number
  duplicate_count: number
  duplicates: WireWearSavedRecord[]
}

export interface WireWearRecordsResponse {
  records: WireWearSavedRecord[]
}

export interface WireWearHistoryRow {
  cycle_date: string
  values: Record<string, number | null>
}

export interface WireWearLatestSummaryRow {
  metric: string
  values: Record<string, string>
}

export interface WireWearWorkbenchResponse {
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  tension_lengths: string[]
  history_rows: WireWearHistoryRow[]
  latest_summary_rows: WireWearLatestSummaryRow[]
  detail_records: Record<string, WireWearSavedRecord[]>
  raw_records: WireWearSavedRecord[]
}

export type WireWearUpdateRequest = Partial<
  Pick<
    WireWearSavedRecord,
    | 'line_group'
    | 'line_class'
    | 'track'
    | 'section'
    | 'cycle_date'
    | 'tension_length'
    | 'from_m'
    | 'to_m'
    | 'avg_wear_min'
    | 'sd'
    | 'wear_percentage'
    | 'source_file_names'
    | 'saved_by'
  >
>

export interface WireWearRateRow {
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  track?: string | null
  section?: string
  tension_length: string
  latest_cycle_date: string
  latest_wear_percentage: number
  latest_avg_wear_min: number
  wear_percent_per_year: number | null
  wear_mm_per_year: number | null
  record_count: number
  r_squared: number | null
  trend_status: string
}

export interface WireWearDashboardResponse {
  line_groups: Record<WireWearLineGroup, {
    top_max_rate: WireWearRateRow[]
    top_min_rate: WireWearRateRow[]
    top_current_wear: WireWearRateRow[]
  }>
}

export interface WearProjectionRecord {
  lineGroup: WireWearLineGroup
  lineClass: WireWearLineClass
  tensionLength: string
  track: string | null
  fromM: number | null
  toM: number | null
  latestCycleDate: string | null
  latestAvgWearMin: number | null
  latestWearPercentage: number | null
  wearRatePercentPerYear: number | null
  wearRateMmPerYear: number | null
  observationCount: number
  rSquared: number | null
  trendStatus: string
  projectedCrossingDate?: string | null
  projectedYear?: number
  yearsToThreshold?: number
}

export interface WearProjectionLineGroup {
  yearBuckets: Array<{ year: number; count: number; records: WearProjectionRecord[] }>
  alreadyAtThreshold: WearProjectionRecord[]
  insufficientData: WearProjectionRecord[]
  nonPositiveRate: WearProjectionRecord[]
}

export interface WireWearProjectionResponse {
  thresholdMm: number
  thresholdPercentage: number
  horizonYears: number
  lineGroups: Record<WireWearLineGroup, WearProjectionLineGroup>
}

export interface WearRemainingLifeRow extends WearProjectionRecord {
  projectedCrossingDate: string | null
  remainingDays: number | null
  curve: Array<{ date: string; remaining_days: number }>
}

export interface WireWearRemainingLifeResponse {
  thresholdMm: number
  rows: WearRemainingLifeRow[]
  defaultRows: WearRemainingLifeRow[]
}

/** Normalized complete-cycle contracts (wire format remains snake_case). */
export interface WireWearCycleSegment {
  segment_name: string
  is_present: boolean
  coverage_percentage: number
  diagnostic_gaps: string[]
  source_file_names: string[]
  acquisition_dates?: string[]
  acquisition_date_from?: string | null
  acquisition_date_to?: string | null
  [key: string]: unknown
}

export interface WireWearCycleConflict {
  conflict_id?: string
  measurement_identity: string
  source_values: Array<[string, number]>
  selected_wear_min: number
  is_accepted?: boolean
  accepted_at?: string | null
  [key: string]: unknown
}

export interface WireWearCyclePreview {
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  cycle_date: string
  records: Array<Record<string, unknown>>
  segments: WireWearCycleSegment[]
  conflicts: WireWearCycleConflict[]
  unresolved: string[]
  blocking_reasons: string[]
  can_save: boolean
  preview_digest: string
  expected_data_version: number
}

export interface WireWearCycleSaveResponse {
  cycle_id: number
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  cycle_date: string
  source_type: string
  completeness_state: string
  acquisition_date_from: string | null
  acquisition_date_to: string | null
  source_lineage: string[]
  records: Array<Record<string, unknown>>
  segments: Array<Record<string, unknown>>
  conflict_decisions: Array<Record<string, unknown>>
  wire_wear_data_version: number
  [key: string]: unknown
}

export interface WearCycleSaveResponse {
  cycleId: number
  lineGroup: WireWearLineGroup
  lineClass: WireWearLineClass
  cycleDate: string
  sourceType: string
  completenessState: string
  acquisitionDateFrom: string | null
  acquisitionDateTo: string | null
  sourceLineage: string[]
  records: WearCycleRecord[]
  segments: WearCycleSegment[]
  conflictDecisions: WearCycleConflict[]
  wireWearDataVersion: number
}

export type WireWearChangeOperation =
  | { kind: 'add'; key: { line_group: WireWearLineGroup; line_class: WireWearLineClass; cycle_date: string; tension_length: string }; avg_wear_min: number }
  | { kind: 'edit'; key: { line_group: WireWearLineGroup; line_class: WireWearLineClass; cycle_date: string; tension_length: string }; avg_wear_min: number; expected_updated_at: string }
  | { kind: 'delete_cell'; key: { line_group: WireWearLineGroup; line_class: WireWearLineClass; cycle_date: string; tension_length: string }; expected_updated_at: string }
  | { kind: 'delete_row'; line_group: WireWearLineGroup; line_class: WireWearLineClass; cycle_date: string }

export interface WireWearChangeSet {
  operations: WireWearChangeOperation[]
  expected_data_version?: number
  origin?: WearChangeOrigin
}

export interface WireWearChangeSetResponse {
  added: number
  edited: number
  deleted: number
  backup_path?: string | null
  wire_wear_data_version: number
  [key: string]: unknown
}

export interface WireWearMetadataCatalogItem {
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  tension_length: string
  track: string
  from_m: number
  to_m: number
  interval_count?: number
  intervals?: Array<{ track: string; from_m: number; to_m: number }>
}

export interface WireWearMetadataPreviewResponse {
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  catalog: WireWearMetadataCatalogItem[]
}

export interface WireWearCycleWorkbenchResponse {
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  columns: Array<Record<string, unknown>>
  matrix_rows: WireWearHistoryRow[]
  latest_summary: Array<Record<string, unknown>>
  records: Array<Record<string, unknown>>
  catalog?: WireWearMetadataCatalogItem[]
  selected_tension_length?: string | null
  summary_only?: boolean
  wire_wear_data_version: number
}

export interface WearCycleWorkbenchResponse {
  lineGroup: WireWearLineGroup
  lineClass: WireWearLineClass
  columns: WearWorkbenchColumn[]
  matrixRows: WearCycleMatrixRow[]
  latestSummary: WearLatestSummary[]
  records: WearCycleRecord[]
  catalog: WearMetadataCatalogItem[]
  selectedTensionLength?: string | null
  summaryOnly?: boolean
  wireWearDataVersion: number
  // Legacy aliases retained for existing store consumers during migration.
  line_group?: WireWearLineGroup
  line_class?: WireWearLineClass
  matrix_rows?: WireWearHistoryRow[]
  history_rows?: WireWearHistoryRow[]
  latest_summary_rows?: WearLatestSummary[]
  wire_wear_data_version?: number
}

export interface WearCycleMatrixRow {
  cycleDate: string
  values: Record<string, number | null>
}

export interface WearWorkbenchColumn {
  tensionLength: string
  track: WearTrack
  fromM: number
  toM: number
  intervalCount: number
  intervals: WearPhysicalInterval[]
}

export interface WearLatestSummary {
  tensionLength: string
  latestCycleDate: string | null
  latestAvgWearMin: number | null
  latestWearPercentage: number | null
  historicalSd: number | null
  wearRateMmPerYear: number | null
  observationCount: number
  rSquared: number | null
  trendStatus: string
}

// UI-facing complete-cycle contracts. Keep snake_case confined to the wire
// interfaces above and map at the API client boundary.
export type WearLine = 'EAL' | 'TML'
export type WearTrack = 'UP' | 'DN' | 'Siding'

export interface WearPhysicalInterval {
  track: WearTrack
  fromM: number
  toM: number
}

export interface WearBusinessKey {
  lineGroup: WearLine
  lineClass: WireWearLineClass
  cycleDate: string
  tensionLength: string
}

export interface WearCycleRecord {
  key: WearBusinessKey
  track: WearTrack
  fromM: number
  toM: number
  intervalCount: number
  intervals: WearPhysicalInterval[]
  avgWearMin: number
  wearPercentage: number
  measurementSd: number | null
  hasDataConflict: boolean
  conflictIds: string[]
  updatedAt: string | null
}

export type WearRecordChange =
  | { kind: 'add'; key: WearBusinessKey; avgWearMin: number }
  | { kind: 'edit'; key: WearBusinessKey; avgWearMin: number; expectedUpdatedAt: string }
  | { kind: 'delete_cell'; key: WearBusinessKey; expectedUpdatedAt: string }
  | { kind: 'delete_row'; lineGroup: WearLine; lineClass: WireWearLineClass; cycleDate: string }

export interface WearChangeSet {
  operations: WearRecordChange[]
  expectedDataVersion: number
  origin?: WearChangeOrigin
}

export interface WearChangeSetResult {
  added: number
  edited: number
  deleted: number
  backupPath: string | null
  wireWearDataVersion: number
}

export type WearChangeOrigin = 'manual' | 'workbook'

export type WearCandidateStatus = 'new' | 'update' | 'no_change' | 'duplicate' | 'error'

export interface WearCandidateIssue {
  code: string
  message: string
  field: string
  cell: string | null
}

export interface WearCandidateRowInput {
  rowId?: string
  tensionLength: string
  avgWearMin: number | string | null
  tensionLengthCell?: string
  avgWearMinCell?: string
  excluded?: boolean
}

export interface WearCandidatePreviewRequest {
  lineClass: WireWearLineClass
  cycleDate: string
  rows: WearCandidateRowInput[]
}

export interface WearCandidatePreviewItem {
  status: WearCandidateStatus
  key: WearBusinessKey | null
  avgWearMin: number | null
  track: string | null
  existingAvgWearMin: number | null
  expectedUpdatedAt: string | null
  sourceType: string
  sourceSheet: string | null
  sourceRow: number | null
  sourceCell: string | null
  originalValue: unknown
  excluded: boolean
  rowId: string | null
  issues: WearCandidateIssue[]
}

export interface WearCandidatePreview {
  lineGroup: WireWearLineGroup
  lineClass: WireWearLineClass
  cycleDate: string
  wireWearDataVersion: number
  counts: Record<WearCandidateStatus, number>
  candidates: WearCandidatePreviewItem[]
}

export interface WireWearCandidatePreviewResponse {
  line_group: WireWearLineGroup
  line_class: WireWearLineClass
  cycle_date: string
  wire_wear_data_version: number
  counts: Record<WearCandidateStatus, number>
  candidates: Array<{
    status: WearCandidateStatus
    key: null | {
      line_group: WireWearLineGroup
      line_class: WireWearLineClass
      cycle_date: string
      tension_length: string
    }
    avg_wear_min: number | null
    track: string | null
    existing_avg_wear_min: number | null
    expected_updated_at: string | null
    source_type: string
    source_sheet: string | null
    source_row: number | null
    source_cell: string | null
    original_value: unknown
    excluded: boolean
    row_id: string | null
    issues: WearCandidateIssue[]
  }>
}

export interface WireWearHistoricalSheetCapability {
  sheet_name: string
  support: 'supported' | 'reserved' | 'ignored'
  selected_by_default: boolean
  enabled: boolean
  reason_code: string
}

export interface WearHistoricalSheetCapability {
  name: string
  support: 'supported' | 'reserved' | 'ignored'
  selectedByDefault: boolean
  enabled: boolean
  reasonCode: string
}

export interface WearHistoricalWorkbookDiscovery {
  sheets: WearHistoricalSheetCapability[]
}

export interface WireWearHistoricalWorkbookDiscoveryResponse {
  sheets: WireWearHistoricalSheetCapability[]
}

export interface WearHistoricalSheetSummary {
  sheetName: string
  skipped: number
  new: number
  update: number
  noChange: number
  duplicate: number
  error: number
  total: number
}

export interface WearHistoricalDiagnostic {
  code: string
  message: string
  sheet: string
  cell: string | null
  originalValue: unknown
}

export interface WireWearHistoricalWorkbookPreviewResponse extends WireWearHistoricalWorkbookDiscoveryResponse {
  selected_sheets: string[]
  wire_wear_data_version: number
  sheet_summaries: Array<{
    sheet_name: string
    skipped: number
    new: number
    update: number
    no_change: number
    duplicate: number
    error: number
    total: number
  }>
  totals: Record<'skipped' | WearCandidateStatus | 'total', number>
  candidates: WireWearCandidatePreviewResponse['candidates']
  diagnostics: Array<{
    code: string
    message: string
    sheet: string
    cell: string | null
    original_value: unknown
  }>
}

export interface WearHistoricalWorkbookPreview extends WearHistoricalWorkbookDiscovery {
  selectedSheets: string[]
  wireWearDataVersion: number
  sheetSummaries: WearHistoricalSheetSummary[]
  totals: Record<'skipped' | WearCandidateStatus | 'total', number>
  candidates: WearCandidatePreviewItem[]
  diagnostics: WearHistoricalDiagnostic[]
}

export interface WearMetadataCatalogItem {
  lineGroup: WearLine
  lineClass: WireWearLineClass
  tensionLength: string
  track: WearTrack
  fromM: number
  toM: number
  intervalCount: number
  intervals: WearPhysicalInterval[]
}

export interface WearCycleConflict {
  conflictId: string
  measurementIdentity: string
  sourceValues: Array<[string, number]>
  selectedWearMin: number
  isAccepted: boolean
  acceptedAt: string | null
}

export interface WearCycleSegment {
  segmentName: string
  isPresent: boolean
  coveragePercentage: number
  diagnosticGaps: string[]
  sourceFileNames: string[]
  acquisitionDates?: string[]
  acquisitionDateFrom?: string | null
  acquisitionDateTo?: string | null
}

export interface WearCyclePreview {
  lineGroup: WearLine
  lineClass: WireWearLineClass
  cycleDate: string
  records: WearCycleRecord[]
  segments: WearCycleSegment[]
  conflicts: WearCycleConflict[]
  unresolved: string[]
  blockingReasons: string[]
  canSave: boolean
  previewDigest: string
  expectedDataVersion: number
}

export interface DiagnosticsResponse {
  database_path: string
  database_directory: string
  config_directory: string
  mode: 'portable' | 'standard'
  packaging: {
    recommended_target: 'dir'
    current_target: string
    writable_data_root?: string
    portable_database_pattern?: string
    single_exe_note: string
  }
}

export interface WireWearSyncImportSummary {
  backup_path?: string | null
  inserted_count: number
  updated_count: number
  skipped_count: number
  skipped_rows: Array<Record<string, unknown>>
  source_label?: string
  exported_at?: string
  metadata_hashes?: Array<Record<string, string>>
}

export type WearSyncActionStatus =
  | 'new'
  | 'update'
  | 'keep_local'
  | 'no_change'
  | 'conflict'
  | 'error'
  | 'delete'

export type WearSyncConflictChoice = 'local' | 'incoming'

export interface WearSyncKey {
  lineGroup: string
  lineClass: string
  cycleDate: string
  tensionLength: string
}

export interface WearSyncValueSnapshot {
  avgWearMin?: number | null
  track?: string | null
  updatedAt?: string | null
  deletedAt?: string | null
  source?: string | null
}

export interface WearSyncPreviewRow {
  id: string
  status: WearSyncActionStatus
  key: WearSyncKey
  local?: WearSyncValueSnapshot | null
  incoming?: WearSyncValueSnapshot | null
  detail?: string | null
}

export interface WearSyncPackageInfo {
  packageId: string
  sourceWorkstation?: string | null
  exportedAt?: string | null
  schema?: string | null
}

export interface WearSyncPreview {
  sourcePackage: Record<string, unknown>
  packageInfo: WearSyncPackageInfo
  rows: WearSyncPreviewRow[]
  expectedDataVersion: number
  previewDigest: string
  warnings: string[]
}

export interface WearSyncConflictDecision {
  key: WearSyncKey
  choice: WearSyncConflictChoice
}

export interface WearSyncApplySummary {
  created: number
  updated: number
  deleted: number
  keepLocal: number
  noChange: number
  conflictsResolved: number
  backupPath?: string | null
  dataVersion: number
}

export interface WireWearSyncPreviewResponse {
  source_package: Record<string, any>
  actions: Array<{
    key: [string, string, string, string]
    action: string
    status: WearSyncActionStatus
    detail?: string
    record?: Record<string, any> | null
    tombstone?: Record<string, any> | null
    local_record?: Record<string, any> | null
    local_tombstone?: Record<string, any> | null
  }>
  expected_data_version: number
  preview_digest: string
  warnings?: string[]
}

export interface WireWearSyncApplyResponse {
  created: number
  updated: number
  deleted: number
  keep_local: number
  no_change: number
  conflicts_resolved: number
  backup_path?: string | null
  wire_wear_data_version: number
}

export interface TrendResult {
  exception_id: string
  tension_length: string
  from_m: number
  to_m: number
  max_value: number
  max_location: number
  level: string
  task_run_date: string
  line: string
  track: string
  section: string
  task_no: string
  station_start: string
  station_end: string
  dates: string[]
  record_points: (number | null)[]
  trend_points: number[]
  trend_next: number
  logic_1: boolean
  logic_2: boolean
  recommendation: 'confirmed valid L2' | 'verify on site' | 'no action required'
}

export interface TrendResponse {
  trend_results: TrendResult[]
}

export interface CalculationResponse {
  wear_results: WearResult[]
  trend_results: TrendResult[]
}

export interface StaggerResult {
  id: string
  run_date?: string | null
  line: string
  track: string
  section?: string | null
  task_no?: string | null
  station_start?: string | null
  station_end?: string | null
  from_m?: number | null
  to_m?: number | null
  length?: number | null
  tension_length?: string | null
  overlap?: string | null
  track_type?: string | null
  level?: string | null
  landmark?: string | null
  asset_class?: string | null
  threshold_value?: number | null
  exception_type: string
  max_value?: number | null
  max_location: number
  chi: number
  spt_a?: number | null
  spt_i?: number | null
  spt_b?: number | null
  span_ai?: number | null
  span_ib?: number | null
  k_eq?: number | null
  overall_result: 'pass' | 'fail' | 'n/a'
  trace_available: boolean
  trace_status?: 'complete' | 'partial'
  chi_source?: string
  remark: string[]
  span_results?: Record<string, any>
}

export interface StaggerTrace {
  trace_status?: 'complete' | 'partial'
  case_type?: string
  chi_source?: string
  assumptions?: Record<string, string>
  record?: Record<string, any>
  reference?: {
    chi: number
    spt_a?: number | null
    spt_i?: number | null
    spt_b?: number | null
  }
  measurements?: Record<string, number | null>
  spans?: Record<string, any>
  k_eq?: number
  keq_components?: Record<string, number | null>
  notes?: string[]
  [key: string]: any
}

export interface StaggerResponse {
  results: StaggerResult[]
  traces: StaggerTrace[]
  warnings?: string[]
}
