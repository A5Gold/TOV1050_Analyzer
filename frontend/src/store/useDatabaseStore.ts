/**
 * TOV640 Analyzer - Database Store
 * =================================
 * Zustand store for Database Record Module
 * 
 * Manages:
 * - Sub-module 2: Saved Repeated Exception Records & Follow-up Actions
 * 
 * NOTE: Sub-module 1 (Exception Records) has been DEPRECATED as of 2026-01-31.
 * All exceptionRecords state and actions have been removed.
 * 
 * Version: 1.1
 * Date: 2026-01-31
 */

import { create } from 'zustand';
import apiClient from '../api/client';
import {
  SavedRepeatedRecord,
  DatabaseFilters,
  RepeatedRecordsResponse,
  RepeatedRecordSectionCounts,
  SaveRecordsResponse,
  SaveRepeatedRecordsRequest,
  UpdateRepeatedRecordRequest,
  ApiSuccessResponse,
  ExceptionRecord,
  ImportRecordsRequest,
  ImportRecordsResponse,
  Check1YearRequest,
  Check1YearResponse,
} from '../types/api';
import { TOV1050_LINES } from '../config/tov1050';

// =============================================================================
// STORE TYPES
// =============================================================================

interface DatabaseStoreState {
  // Sub-module 2: Repeated Records (Primary storage)
  repeatedRecords: SavedRepeatedRecord[];
  repeatedRecordsLoading: boolean;
  repeatedRecordsError: string | null;
  repeatedRecordsTotal: number;
  repeatedRecordSectionCounts: RepeatedRecordSectionCounts;
  
  // Current Filters
  repeatedFilters: Partial<DatabaseFilters>;
  
  // Saving State
  isSaving: boolean;
  saveError: string | null;
  
  // Import State (NEW)
  isImporting: boolean;
  importError: string | null;
  
  // Feature-002: Batch Save State
  pendingChanges: Map<number, UpdateRepeatedRecordRequest>;
  hasPendingChanges: boolean;
  isBatchSaving: boolean;
  
  // Phase 10.10-C: Distinct Values Cache for Dynamic Dropdowns
  distinctValuesCache: Record<string, string[]>;
  distinctValuesLoading: boolean;
  
  // Phase 12 Bug 4: Line Counts
  lineCounts: Record<string, number>;
  lineCountsLoading: boolean;
  
  // Actions - Sub-module 2 (Repeated Records)
  fetchRepeatedRecords: (filters?: Partial<DatabaseFilters>) => Promise<void>;
  saveRepeatedRecords: (request: SaveRepeatedRecordsRequest) => Promise<SaveRecordsResponse>;
  updateRepeatedRecord: (recordId: number, updates: UpdateRepeatedRecordRequest) => Promise<{ success: boolean; message: string }>;
  deleteRepeatedRecord: (recordId: number) => Promise<boolean>;
  exportRepeatedRecords: (filters?: Partial<DatabaseFilters>) => Promise<void>;
  
  // Import Actions (NEW)
  importRepeatedRecords: (request: ImportRecordsRequest) => Promise<ImportRecordsResponse>;
  
  // Check 1 Year Record Action (NEW)
  check1YearRecords: (request: Check1YearRequest) => Promise<Check1YearResponse>;
  
  // Feature-002: Batch Save Actions
  queueChange: (recordId: number, updates: UpdateRepeatedRecordRequest) => void;
  batchSaveChanges: () => Promise<{ success: boolean; updated_count: number; message: string }>;
  discardChanges: () => void;
  
  // Phase 10.10-C: Distinct Values for Dynamic Dropdown Filters
  fetchDistinctValues: (field: string, line?: string) => Promise<string[]>;
  
  // Phase 12 Bug 4: Line Counts
  fetchLineCounts: () => Promise<void>;
  
  // Filter Actions
  setRepeatedFilters: (filters: Partial<DatabaseFilters>) => void;
  clearRepeatedFilters: () => void;
  
  // Reset
  reset: () => void;
}

// =============================================================================
// INITIAL STATE
// =============================================================================

const initialState = {
  repeatedRecords: [],
  repeatedRecordsLoading: false,
  repeatedRecordsError: null,
  repeatedRecordsTotal: 0,
  repeatedRecordSectionCounts: {
    all: 0,
    mainline: 0,
    rac: 0,
    low_s1: 0,
    lmc: 0,
    unknown: 0,
  } as RepeatedRecordSectionCounts,
  
  repeatedFilters: {},
  
  isSaving: false,
  saveError: null,
  
  isImporting: false,
  importError: null,
  
  // Feature-002: Batch Save State
  pendingChanges: new Map<number, UpdateRepeatedRecordRequest>(),
  hasPendingChanges: false,
  isBatchSaving: false,
  
  // Phase 10.10-C: Distinct Values Cache
  distinctValuesCache: {} as Record<string, string[]>,
  distinctValuesLoading: false,
  
  // Phase 12 Bug 4: Line Counts
  lineCounts: Object.fromEntries(TOV1050_LINES.map((line) => [line, 0])) as Record<string, number>,
  lineCountsLoading: false,
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Build query string from filters, excluding empty/null/undefined values
 */
const buildQueryParams = (filters: Partial<DatabaseFilters>): string => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '' && value !== 'All') {
      params.append(key, String(value));
    }
  });
  return params.toString();
};

/**
 * Trigger file download from blob response
 */
const downloadBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// =============================================================================
// STORE IMPLEMENTATION
// =============================================================================

export const useDatabaseStore = create<DatabaseStoreState>((set, get) => ({
  ...initialState,
  
  // =========================================================================
  // SUB-MODULE 2: REPEATED RECORDS (PRIMARY)
  // =========================================================================
  
  fetchRepeatedRecords: async (filters = {}) => {
    set({
      repeatedRecordsLoading: true,
      repeatedRecordsError: null,
      repeatedRecordSectionCounts: {
        all: 0,
        mainline: 0,
        rac: 0,
        low_s1: 0,
        lmc: 0,
        unknown: 0,
      },
    });
    
    try {
      const mergedFilters = { ...get().repeatedFilters, ...filters };
      const queryString = buildQueryParams(mergedFilters);
      
      const response = await apiClient.get<RepeatedRecordsResponse>(
        `/database/repeated-records?${queryString}`
      );
      
      set({
        repeatedRecords: response.data.records,
        repeatedRecordsTotal: response.data.total,
        repeatedRecordSectionCounts: response.data.section_counts,
        repeatedRecordsLoading: false,
        repeatedFilters: mergedFilters,
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to fetch repeated records';
      set({
        repeatedRecordsError: errorMessage,
        repeatedRecordsLoading: false,
        repeatedRecordSectionCounts: {
          all: 0,
          mainline: 0,
          rac: 0,
          low_s1: 0,
          lmc: 0,
          unknown: 0,
        },
      });
      console.error('Error fetching repeated records:', error);
    }
  },
  
  saveRepeatedRecords: async (request) => {
    set({ isSaving: true, saveError: null });
    
    try {
      const response = await apiClient.post<SaveRecordsResponse>(
        '/database/repeated-records',
        request
      );
      
      set({ isSaving: false });
      
      // Refresh data after save
      await get().fetchRepeatedRecords();
      
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to save repeated records';
      set({
        saveError: errorMessage,
        isSaving: false,
      });
      console.error('Error saving repeated records:', error);
      throw error;
    }
  },
  
  updateRepeatedRecord: async (recordId, updates) => {
    try {
      const response = await apiClient.patch<ApiSuccessResponse>(
        `/database/repeated-records/${recordId}`,
        updates
      );
      
      if (response.data.status === 'success') {
        // Update local state
        set((state) => ({
          repeatedRecords: state.repeatedRecords.map((r) =>
            r.record_id === recordId
              ? { ...r, ...updates, last_updated: new Date().toISOString() }
              : r
          ),
        }));
        return { success: true, message: response.data.message };
      }
      return { success: false, message: 'Update failed' };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail 
        || error.message 
        || 'Failed to update record';
      console.error('Error updating repeated record:', errorMessage);
      return { success: false, message: errorMessage };
    }
  },
  
  deleteRepeatedRecord: async (recordId) => {
    try {
      const response = await apiClient.delete<ApiSuccessResponse>(
        `/database/repeated-records/${recordId}`
      );
      
      if (response.data.status === 'success') {
        // Update local state
        set((state) => ({
          repeatedRecords: state.repeatedRecords.filter((r) => r.record_id !== recordId),
          repeatedRecordsTotal: state.repeatedRecordsTotal - 1,
        }));
        return true;
      }
      return false;
    } catch (error: any) {
      console.error('Error deleting repeated record:', error);
      return false;
    }
  },
  
  exportRepeatedRecords: async (filters = {}) => {
    try {
      const mergedFilters = { ...get().repeatedFilters, ...filters };
      const queryString = buildQueryParams(mergedFilters);
      
      const response = await apiClient.get(
        `/database/repeated-records/export?${queryString}`,
        { responseType: 'blob' }
      );
      
      // Generate filename - Phase 11 Issue 5: New naming format
      const line = mergedFilters.line || 'All';
      const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      const filename = `${today}_${line} Exception Follow-up Master List.xlsx`;
      
      downloadBlob(response.data, filename);
    } catch (error: any) {
      console.error('Error exporting repeated records:', error);
      throw error;
    }
  },
  
  // =========================================================================
  // IMPORT ACTIONS (NEW 2026-01-31)
  // =========================================================================
  
  importRepeatedRecords: async (request) => {
    set({ isImporting: true, importError: null });
    
    try {
      const response = await apiClient.post<ImportRecordsResponse>(
        '/database/repeated-records/import',
        request
      );
      
      set({ isImporting: false });
      
      // Refresh data after import
      await get().fetchRepeatedRecords();
      
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to import records';
      set({
        importError: errorMessage,
        isImporting: false,
      });
      console.error('Error importing repeated records:', error);
      throw error;
    }
  },
  
  // =========================================================================
  // CHECK 1 YEAR RECORDS ACTION (NEW 2026-01-31)
  // =========================================================================
  
  check1YearRecords: async (request) => {
    try {
      const response = await apiClient.post<Check1YearResponse>(
        '/database/repeated-records/check-1-year',
        request
      );
      
      return response.data;
    } catch (error: any) {
      console.error('Error checking 1 year records:', error);
      throw error;
    }
  },
  
  // =========================================================================
  // FEATURE-002: BATCH SAVE ACTIONS
  // =========================================================================
  
  /**
   * Queue a change for batch save
   * Accumulates changes for a record until batchSaveChanges is called
   */
  queueChange: (recordId, updates) => {
    set((state) => {
      const newMap = new Map(state.pendingChanges);
      const existing = newMap.get(recordId) || {};
      newMap.set(recordId, { ...existing, ...updates });
      
      // Also update local state optimistically for immediate UI feedback
      const updatedRecords = state.repeatedRecords.map((r) =>
        r.record_id === recordId
          ? { ...r, ...updates }
          : r
      );
      
      return { 
        pendingChanges: newMap, 
        hasPendingChanges: true,
        repeatedRecords: updatedRecords,
      };
    });
  },
  
  /**
   * Batch save all pending changes to the database
   * Returns count of successfully updated records
   */
  batchSaveChanges: async () => {
    const { pendingChanges } = get();
    
    if (pendingChanges.size === 0) {
      return { success: true, updated_count: 0, message: 'No changes to save' };
    }
    
    set({ isBatchSaving: true });
    
    try {
      // Convert Map to array of updates with record_id
      const updates = Array.from(pendingChanges.entries()).map(([recordId, data]) => ({
        record_id: recordId,
        ...data
      }));
      
      const response = await apiClient.post<{ status: string; updated_count: number }>(
        '/database/repeated-records/batch-update',
        { updates }
      );
      
      // Clear pending changes on success
      set({ 
        pendingChanges: new Map(), 
        hasPendingChanges: false,
        isBatchSaving: false,
      });
      
      // Refresh data to get updated last_updated timestamps
      await get().fetchRepeatedRecords();
      
      return { 
        success: true, 
        updated_count: response.data.updated_count,
        message: `Successfully saved ${response.data.updated_count} records`
      };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to batch save changes';
      console.error('Error batch saving changes:', errorMessage);
      set({ isBatchSaving: false });
      return { success: false, updated_count: 0, message: errorMessage };
    }
  },
  
  /**
   * Discard all pending changes and revert to database state
   */
  discardChanges: () => {
    set({ 
      pendingChanges: new Map(), 
      hasPendingChanges: false 
    });
    // Refresh to revert any optimistic updates
    get().fetchRepeatedRecords();
  },
  
  // =========================================================================
  // PHASE 10.10-C: DISTINCT VALUES FOR DYNAMIC DROPDOWNS
  // =========================================================================
  
  /**
   * Fetch distinct values for a field from the API.
   * Uses cache key `field` or `field:line` to avoid redundant API calls.
   */
  fetchDistinctValues: async (field: string, line?: string) => {
    const cacheKey = line ? `${field}:${line}` : field;
    
    // Return cached values if available
    const cached = get().distinctValuesCache[cacheKey];
    if (cached) return cached;
    
    set({ distinctValuesLoading: true });
    
    try {
      const params = new URLSearchParams({ field });
      if (line) params.append('line', line);
      
      const response = await apiClient.get<{ status: string; values: string[]; count: number }>(
        `/database/repeated-records/distinct-values?${params.toString()}`
      );
      
      const values = response.data.values;
      
      // Update cache
      set((state) => ({
        distinctValuesCache: { ...state.distinctValuesCache, [cacheKey]: values },
        distinctValuesLoading: false,
      }));
      
      return values;
    } catch (error: any) {
      console.error(`Error fetching distinct values for ${field}:`, error);
      set({ distinctValuesLoading: false });
      return [];
    }
  },
  
  // =========================================================================
  // PHASE 12 BUG 4: LINE COUNTS
  // =========================================================================
  
  /**
   * Fetch record counts grouped by TOV1050 line.
   * Used for Tab count indicators in LineTabPanel.
   */
  fetchLineCounts: async () => {
    set({ lineCountsLoading: true });
    
    try {
      const response = await apiClient.get<{ status: string; counts: Record<string, number> }>(
        '/database/repeated-records/counts'
      );
      
      set({
        lineCounts: response.data.counts,
        lineCountsLoading: false,
      });
    } catch (error: any) {
      console.error('Error fetching line counts:', error);
      set({ lineCountsLoading: false });
    }
  },
  
  // =========================================================================
  // FILTER ACTIONS
  // =========================================================================
  
  setRepeatedFilters: (filters) => {
    set({ repeatedFilters: { ...get().repeatedFilters, ...filters } });
  },
  
  clearRepeatedFilters: () => {
    set({ repeatedFilters: {} });
  },
  
  // =========================================================================
  // RESET
  // =========================================================================
  
  reset: () => {
    set(initialState);
  },
}));

export default useDatabaseStore;
