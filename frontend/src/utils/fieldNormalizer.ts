/**
 * Field Normalizer Utility
 * ========================
 * Provides consistent field name normalization across frontend components.
 * Converts various field naming formats to snake_case standard.
 * 
 * Problem: Different parts of the system use different naming conventions:
 * - Backend DB: snake_case (exception_type, from_m, max_value)
 * - Frontend Grid: mixed (exception type, FromM, maxValue)
 * - Excel Export: Display format (Exception Type, MaxLocation)
 * 
 * This utility provides bidirectional mapping to ensure consistency.
 * 
 * @version 1.0
 * @date 2026-02-03
 */

// =============================================================================
// FIELD MAPPING: Various formats → snake_case
// =============================================================================

/**
 * Maps various field name formats to snake_case standard.
 * Keys are the source formats, values are the normalized snake_case names.
 */
export const FIELD_MAP: Record<string, string> = {
  // ID Fields
  'id': 'exception_id',
  'ID': 'exception_id',
  
  // Exception Details - Space format
  'exception type': 'exception_type',
  'Exception Type': 'exception_type',
  'Track Type': 'track_type',
  'Tension Length': 'tension_length',
  'Previous 1': 'previous_1',
  'Previous 2': 'previous_2',
  'Previous ID': 'previous_1',
  'Threshold Value': 'threshold_value',
  
  // Exception Details - PascalCase format
  'FromM': 'from_m',
  'ToM': 'to_m',
  'Overlap': 'overlap',
  'Section': 'section',
  'Landmark': 'landmark',
  'Class': 'class',
  
  // Exception Details - camelCase format
  'maxValue': 'max_value',
  'maxLocation': 'max_location',
  
  // Legacy prev_X format (from transformData)
  'prev_0': 'previous_1',
  'prev_1': 'previous_2',
};

// =============================================================================
// DISPLAY MAPPING: snake_case → User-friendly display format
// =============================================================================

/**
 * Maps snake_case field names to user-friendly display format for Excel export
 * and column headers.
 */
export const DISPLAY_MAP: Record<string, string> = {
  // ID
  'exception_id': 'ID',
  
  // Task Run Data
  'line': 'Line',
  'track': 'Track',
  'section': 'Section',
  'task_no': 'Task Number',
  'station_start': 'Station Start',
  'station_end': 'Station End',
  'task_run_date': 'Task Run Date',
  
  // Exception Details
  'exception_type': 'Exception Type',
  'level': 'Level',
  'from_m': 'FromM',
  'to_m': 'ToM',
  'length': 'Length',
  'max_value': 'MaxValue',
  'max_location': 'MaxLocation',
  'track_type': 'Track Type',
  'overlap': 'Overlap',
  'tension_length': 'Tension Length',
  'landmark': 'Landmark',
  'class': 'Class',
  'threshold_value': 'Threshold',
  'previous_1': 'Previous 1',
  'previous_2': 'Previous 2',
  'reoccurrence_id': 'Reoccurrence ID',
  'remarks': 'Remarks',
  
  // Workflow - Initial Check
  'action': 'ACTION',
  'check_date': 'CHECK DATE',
  'checked_by': 'CHECK BY',
  'check_result': 'CHECK RESULT',
  
  // Workflow - Site Verification
  'verify_deadline': 'VERIFY DEADLINE',
  'verify_date': 'VERIFY DATE',
  'verified_by': 'VERIFIED BY',
  'verify_result': 'VERIFY RESULT',
  
  // Workflow - Final Adjustment
  'adjust_deadline': 'ADJUST DEADLINE',
  'adjust_date': 'ADJUST DATE',
  'adjusted_by': 'ADJUSTED BY',
  'adjust_result': 'ADJUST RESULT',
  
  // Database Metadata
  'record_id': 'Record ID',
  'saved_at': 'Saved At',
  'last_updated': 'Last Updated',
};

// =============================================================================
// NORMALIZATION FUNCTIONS
// =============================================================================

/**
 * Normalize a single field name to snake_case.
 * If the field is not in the mapping, returns it unchanged.
 * 
 * @param fieldName - The field name to normalize
 * @returns The normalized snake_case field name
 * 
 * @example
 * normalizeFieldName('exception type') // returns 'exception_type'
 * normalizeFieldName('FromM') // returns 'from_m'
 * normalizeFieldName('maxValue') // returns 'max_value'
 * normalizeFieldName('already_snake') // returns 'already_snake' (unchanged)
 */
export const normalizeFieldName = (fieldName: string): string => {
  return FIELD_MAP[fieldName] || fieldName;
};

/**
 * Normalize all field names in a record to snake_case.
 * Creates a new object with normalized keys, preserving original values.
 * 
 * Special handling:
 * - 'id' field is mapped to both 'exception_id' and 'id' (for DataGrid compatibility)
 * - Already normalized fields are passed through unchanged
 * 
 * @param record - The record with mixed field naming
 * @returns A new record with snake_case field names
 * 
 * @example
 * normalizeRecord({ id: 'exc-001', 'exception type': 'Low Height', FromM: 100 })
 * // returns { exception_id: 'exc-001', id: 'exc-001', exception_type: 'Low Height', from_m: 100 }
 */
export const normalizeRecord = <T extends Record<string, any>>(
  record: T
): Record<string, any> => {
  const normalized: Record<string, any> = {};
  
  for (const [key, value] of Object.entries(record)) {
    const normalizedKey = normalizeFieldName(key);
    
    // Special handling for ID field - keep both formats for compatibility
    if (key === 'id' && !record.exception_id) {
      normalized['exception_id'] = value;
      normalized['id'] = value; // Keep 'id' for DataGrid row identifier
    } else {
      normalized[normalizedKey] = value;
    }
  }
  
  // Ensure 'id' exists for DataGrid compatibility
  if (!normalized['id'] && normalized['exception_id']) {
    normalized['id'] = normalized['exception_id'];
  }
  
  return normalized;
};

/**
 * Normalize an array of records.
 * 
 * @param records - Array of records with mixed field naming
 * @returns Array of records with snake_case field names
 */
export const normalizeRecords = <T extends Record<string, any>>(
  records: T[]
): Record<string, any>[] => {
  return records.map(normalizeRecord);
};

/**
 * Get user-friendly display header for a snake_case field name.
 * Used for Excel export and column headers.
 * 
 * @param fieldName - The snake_case field name
 * @returns The user-friendly display name
 * 
 * @example
 * getDisplayHeader('exception_type') // returns 'Exception Type'
 * getDisplayHeader('max_location') // returns 'MaxLocation'
 */
export const getDisplayHeader = (fieldName: string): string => {
  return DISPLAY_MAP[fieldName] || fieldName;
};

// =============================================================================
// COMPATIBILITY HELPERS
// =============================================================================

/**
 * Get a field value from a record, checking multiple possible key formats.
 * Useful for reading data that may come in different formats.
 * 
 * @param record - The record to read from
 * @param standardKey - The standard snake_case key
 * @param defaultValue - Default value if field not found
 * @returns The field value or default
 * 
 * @example
 * const excType = getFieldValue(row, 'exception_type', '')
 * // Checks: row['exception_type'], row['exception type'], row['Exception Type']
 */
export const getFieldValue = <T = any>(
  record: Record<string, any>,
  standardKey: string,
  defaultValue: T
): T => {
  // Try standard snake_case first
  if (standardKey in record && record[standardKey] !== undefined) {
    return record[standardKey];
  }
  
  // Find alternative keys that map to this standard key
  const alternativeKeys = Object.entries(FIELD_MAP)
    .filter(([_, value]) => value === standardKey)
    .map(([key, _]) => key);
  
  for (const altKey of alternativeKeys) {
    if (altKey in record && record[altKey] !== undefined) {
      return record[altKey];
    }
  }
  
  return defaultValue;
};

/**
 * Check if a field exists in a record under any of its possible name formats.
 * 
 * @param record - The record to check
 * @param standardKey - The standard snake_case key
 * @returns True if the field exists in any format
 */
export const hasField = (
  record: Record<string, any>,
  standardKey: string
): boolean => {
  if (standardKey in record) return true;
  
  const alternativeKeys = Object.entries(FIELD_MAP)
    .filter(([_, value]) => value === standardKey)
    .map(([key, _]) => key);
  
  return alternativeKeys.some(altKey => altKey in record);
};

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

/**
 * Normalized exception record with all snake_case field names.
 * This is the target format for all exception data.
 */
export interface NormalizedExceptionRecord {
  // Required ID
  exception_id: string;
  id?: string; // Alias for DataGrid compatibility
  
  // Task Run Data
  line?: string;
  track?: string;
  section?: string;
  task_no?: string;
  station_start?: string;
  station_end?: string;
  task_run_date?: string;
  
  // Exception Details
  exception_type: string;
  level: string;
  from_m: number;
  to_m: number;
  length?: number;
  max_value?: number;
  max_location?: number;
  track_type?: string;
  overlap?: string;
  tension_length?: string | number;
  landmark?: string;
  class?: string;
  threshold_value?: number;
  previous_1?: string;
  previous_2?: string;
  reoccurrence_id?: string;
  remarks?: string;
  
  // Workflow - Initial Check
  action?: string;
  check_date?: string;
  checked_by?: string;
  check_result?: string;
  
  // Workflow - Site Verification
  verify_deadline?: string;
  verify_date?: string;
  verified_by?: string;
  verify_result?: string;
  
  // Workflow - Final Adjustment
  adjust_deadline?: string;
  adjust_date?: string;
  adjusted_by?: string;
  adjust_result?: string;
  
  // Database Metadata
  record_id?: string;
  saved_at?: string;
  last_updated?: string;
}
