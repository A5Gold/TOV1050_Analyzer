/**
 * TOV640 Analyzer - History Store
 * ================================
 * Zustand store for Stateful Transformation - Historical Sessions Management
 * 
 * Manages:
 * - Historical analysis sessions from database
 * - Session exceptions and their statuses
 * - Exception status updates
 * 
 * Version: 1.0
 * Date: 2026-01-30
 */

import { create } from 'zustand';
import apiClient from '../api/client';
import {
  HistoricalSession,
  DatabaseException,
  SessionsListResponse,
  SessionResponse,
  SessionExceptionsResponse,
  DatabaseFilters,
  ApiSuccessResponse,
} from '../types/api';

// =============================================================================
// STORE TYPES
// =============================================================================

interface HistoryStoreState {
  // Sessions List
  sessions: HistoricalSession[];
  sessionsLoading: boolean;
  sessionsError: string | null;
  sessionsTotal: number;
  
  // Selected Session Detail
  selectedSession: HistoricalSession | null;
  selectedSessionLoading: boolean;
  selectedSessionError: string | null;
  
  // Session Exceptions
  sessionExceptions: DatabaseException[];
  exceptionsLoading: boolean;
  exceptionsError: string | null;
  exceptionsTotal: number;
  
  // Current Filters
  filters: Partial<DatabaseFilters>;
  
  // Actions
  fetchSessions: (filters?: Partial<DatabaseFilters>) => Promise<void>;
  fetchSessionById: (sessionId: string) => Promise<void>;
  fetchSessionExceptions: (
    sessionId: string, 
    filters?: { level?: string; exception_type?: string; current_status?: string }
  ) => Promise<void>;
  updateExceptionStatus: (
    exceptionId: string,
    status: string,
    options?: { notes?: string; assigned_to?: string; resolved_by?: string }
  ) => Promise<boolean>;
  
  // Filter Actions
  setFilters: (filters: Partial<DatabaseFilters>) => void;
  clearFilters: () => void;
  
  // Selection Actions
  selectSession: (session: HistoricalSession | null) => void;
  clearSelection: () => void;
  
  // Reset
  reset: () => void;
}

// =============================================================================
// INITIAL STATE
// =============================================================================

const initialState = {
  sessions: [],
  sessionsLoading: false,
  sessionsError: null,
  sessionsTotal: 0,
  
  selectedSession: null,
  selectedSessionLoading: false,
  selectedSessionError: null,
  
  sessionExceptions: [],
  exceptionsLoading: false,
  exceptionsError: null,
  exceptionsTotal: 0,
  
  filters: {},
};

// =============================================================================
// STORE IMPLEMENTATION
// =============================================================================

export const useHistoryStore = create<HistoryStoreState>((set, get) => ({
  ...initialState,
  
  // =========================================================================
  // FETCH SESSIONS
  // =========================================================================
  
  fetchSessions: async (filters = {}) => {
    set({ sessionsLoading: true, sessionsError: null });
    
    try {
      // Build query params
      const params = new URLSearchParams();
      Object.entries({ ...get().filters, ...filters }).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '' && value !== 'All') {
          params.append(key, String(value));
        }
      });
      
      const response = await apiClient.get<SessionsListResponse>(
        `/sessions?${params.toString()}`
      );
      
      set({
        sessions: response.data.sessions,
        sessionsTotal: response.data.total,
        sessionsLoading: false,
        filters: { ...get().filters, ...filters },
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to fetch sessions';
      set({
        sessionsError: errorMessage,
        sessionsLoading: false,
      });
      console.error('Error fetching sessions:', error);
    }
  },
  
  // =========================================================================
  // FETCH SESSION BY ID
  // =========================================================================
  
  fetchSessionById: async (sessionId: string) => {
    set({ selectedSessionLoading: true, selectedSessionError: null });
    
    try {
      const response = await apiClient.get<SessionResponse>(`/sessions/${sessionId}`);
      
      set({
        selectedSession: response.data.session,
        selectedSessionLoading: false,
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to fetch session';
      set({
        selectedSessionError: errorMessage,
        selectedSessionLoading: false,
      });
      console.error('Error fetching session:', error);
    }
  },
  
  // =========================================================================
  // FETCH SESSION EXCEPTIONS
  // =========================================================================
  
  fetchSessionExceptions: async (sessionId, filters = {}) => {
    set({ exceptionsLoading: true, exceptionsError: null });
    
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '' && value !== 'All') {
          params.append(key, String(value));
        }
      });
      
      const response = await apiClient.get<SessionExceptionsResponse>(
        `/sessions/${sessionId}/exceptions?${params.toString()}`
      );
      
      set({
        sessionExceptions: response.data.exceptions,
        exceptionsTotal: response.data.total,
        exceptionsLoading: false,
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to fetch exceptions';
      set({
        exceptionsError: errorMessage,
        exceptionsLoading: false,
      });
      console.error('Error fetching exceptions:', error);
    }
  },
  
  // =========================================================================
  // UPDATE EXCEPTION STATUS
  // =========================================================================
  
  updateExceptionStatus: async (exceptionId, status, options = {}) => {
    try {
      const response = await apiClient.patch<ApiSuccessResponse>(
        `/exceptions/${exceptionId}/status`,
        {
          status,
          notes: options.notes,
          assigned_to: options.assigned_to,
          resolved_by: options.resolved_by,
        }
      );
      
      if (response.data.status === 'success') {
        // Update local state
        set((state) => ({
          sessionExceptions: state.sessionExceptions.map((exc) =>
            exc.id === exceptionId
              ? {
                  ...exc,
                  current_status: status,
                  notes: options.notes ?? exc.notes,
                  assigned_to: options.assigned_to ?? exc.assigned_to,
                  resolved_by: options.resolved_by ?? exc.resolved_by,
                }
              : exc
          ),
        }));
        return true;
      }
      return false;
    } catch (error: any) {
      console.error('Error updating exception status:', error);
      return false;
    }
  },
  
  // =========================================================================
  // FILTER ACTIONS
  // =========================================================================
  
  setFilters: (filters) => {
    set({ filters: { ...get().filters, ...filters } });
  },
  
  clearFilters: () => {
    set({ filters: {} });
  },
  
  // =========================================================================
  // SELECTION ACTIONS
  // =========================================================================
  
  selectSession: (session) => {
    set({ selectedSession: session });
  },
  
  clearSelection: () => {
    set({
      selectedSession: null,
      sessionExceptions: [],
      exceptionsTotal: 0,
    });
  },
  
  // =========================================================================
  // RESET
  // =========================================================================
  
  reset: () => {
    set(initialState);
  },
}));

export default useHistoryStore;
