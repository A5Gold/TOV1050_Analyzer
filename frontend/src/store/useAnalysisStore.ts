import { create } from 'zustand';
import { AnalysisResponse, ExceptionRecord } from '../types/api';

// --- Session Types ---

export interface AnalysisSession {
  id: string; // UUID
  label: string; // e.g., "20260115_AEL_UT_HUH_TAP.csv"
  
  // Config State
  filePath: string;
  line: string;
  section: string;
  track: string;
  dateStr: string;
  
  // Optional fields for custom file naming
  taskNo?: string;
  stationStart?: string;
  stationEnd?: string;
  
  // Analysis Result
  result: AnalysisResponse | null; // The heavy analysis result
  loading: boolean;
  error: string | null;
  
  // View State
  viewMode: 'graph' | 'table';
  selectedExceptionId: string | null;
}

export interface CompareSession {
  id: string; // UUID
  label: string; // e.g., "Comparison 1"
  
  // Files
  latestFile: File | null; // Slot 1 (Mandatory)
  closestPreviousFile: File | null; // Slot 2 (Mandatory)
  olderPreviousFiles: File[]; // Slot 3 (Optional)
  
  // Optional fields for custom file naming
  taskNo?: string;
  stationStart?: string;
  stationEnd?: string;
  
  // Result
  repeatedData: ExceptionRecord[]; // The comparison result
  latestFileName: string;
  chartData?: (Record<string, (number | null)[]> | null)[];
  loading: boolean;
  error: string | null;
  
  // View State
  tabIndex: number; // For internal "Summary" vs "Previous" tabs
}

interface AnalysisStoreState {
  // --- Exception Generator State ---
  analysisSessions: AnalysisSession[];
  activeAnalysisTabId: string | null;

  // --- History Compare State ---
  compareSessions: CompareSession[];
  activeCompareTabId: string | null;

  // --- Actions ---
  
  // Analysis Actions
  addAnalysisSession: (session: AnalysisSession) => void;
  removeAnalysisSession: (id: string) => void;
  updateAnalysisSession: (id: string, updates: Partial<AnalysisSession>) => void;
  setActiveAnalysisTab: (id: string | null) => void;
  resetAnalysisSessions: () => void;

  // Compare Actions
  addCompareSession: (session: CompareSession) => void;
  removeCompareSession: (id: string) => void;
  updateCompareSession: (id: string, updates: Partial<CompareSession>) => void;
  setActiveCompareTab: (id: string | null) => void;
  resetCompareSessions: () => void;
}

export const useAnalysisStore = create<AnalysisStoreState>((set) => ({
  // Initial State
  analysisSessions: [],
  activeAnalysisTabId: null,
  compareSessions: [],
  activeCompareTabId: null,

  // --- Analysis Actions ---
  addAnalysisSession: (session) => set((state) => ({
    analysisSessions: [...state.analysisSessions, session],
    activeAnalysisTabId: session.id
  })),

  removeAnalysisSession: (id) => set((state) => {
    const newSessions = state.analysisSessions.filter(s => s.id !== id);
    let newActiveId = state.activeAnalysisTabId;
    
    if (state.activeAnalysisTabId === id) {
      newActiveId = newSessions.length > 0 ? newSessions[newSessions.length - 1].id : null;
    }
    
    return {
      analysisSessions: newSessions,
      activeAnalysisTabId: newActiveId
    };
  }),

  updateAnalysisSession: (id, updates) => set((state) => ({
    analysisSessions: state.analysisSessions.map(s => 
      s.id === id ? { ...s, ...updates } : s
    )
  })),

  setActiveAnalysisTab: (id) => set({ activeAnalysisTabId: id }),

  resetAnalysisSessions: () => set({ 
    analysisSessions: [], 
    activeAnalysisTabId: null 
  }),

  // --- Compare Actions ---
  addCompareSession: (session) => set((state) => ({
    compareSessions: [...state.compareSessions, session],
    activeCompareTabId: session.id
  })),

  removeCompareSession: (id) => set((state) => {
    const newSessions = state.compareSessions.filter(s => s.id !== id);
    let newActiveId = state.activeCompareTabId;

    if (state.activeCompareTabId === id) {
      newActiveId = newSessions.length > 0 ? newSessions[newSessions.length - 1].id : null;
    }

    return {
      compareSessions: newSessions,
      activeCompareTabId: newActiveId
    };
  }),

  updateCompareSession: (id, updates) => set((state) => ({
    compareSessions: state.compareSessions.map(s => 
      s.id === id ? { ...s, ...updates } : s
    )
  })),

  setActiveCompareTab: (id) => set({ activeCompareTabId: id }),

  resetCompareSessions: () => set({ 
    compareSessions: [], 
    activeCompareTabId: null 
  }),
}));
