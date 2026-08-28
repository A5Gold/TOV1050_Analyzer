/**
 * Column Order Constants
 * =======================
 * Single authoritative column order definition per Field_Mapping_Spec.
 * All frontend tables and backend exports reference these constants.
 *
 * Phase 11 - Issue 1: Column order consistency
 * Requirement: 1.1
 */

// =============================================================================
// COLUMN ORDER BY GROUP (Field_Mapping_Spec §1.1–1.6)
// =============================================================================

export const COLUMN_ORDER = {
  /** §1.1 Task Run Data (7 fields) */
  TASK_RUN_DATA: [
    'line', 'track', 'section', 'task_no',
    'station_start', 'station_end', 'task_run_date',
  ],
  /** §1.2 Exception Details (15 fields) */
  EXCEPTION_DETAILS: [
    'exception_id', 'from_m', 'to_m', 'length',
    'exception_type', 'max_value', 'max_location',
    'overlap', 'tension_length', 'track_type', 'level',
    'previous_1', 'previous_2', 'reoccurrence_id', 'remarks',
  ],
  /** §1.3 Initial Check (4 fields) */
  INITIAL_CHECK: [
    'action', 'check_date', 'checked_by', 'check_result',
  ],
  /** §1.4 Site Verification (4 fields) */
  SITE_VERIFICATION: [
    'verify_deadline', 'verify_date', 'verified_by', 'verify_result',
  ],
  /** §1.5 Final Adjustment (4 fields) */
  FINAL_ADJUSTMENT: [
    'adjust_deadline', 'adjust_date', 'adjusted_by', 'adjust_result',
  ],
  /** §1.6 Database (3 fields) */
  DATABASE: [
    'record_id', 'saved_at', 'last_updated',
  ],
} as const;

/** Full 37-field order (all groups concatenated) */
export const FULL_COLUMN_ORDER = [
  ...COLUMN_ORDER.TASK_RUN_DATA,
  ...COLUMN_ORDER.EXCEPTION_DETAILS,
  ...COLUMN_ORDER.INITIAL_CHECK,
  ...COLUMN_ORDER.SITE_VERIFICATION,
  ...COLUMN_ORDER.FINAL_ADJUSTMENT,
  ...COLUMN_ORDER.DATABASE,
] as const;
