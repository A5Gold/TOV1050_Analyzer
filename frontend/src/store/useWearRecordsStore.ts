import { create } from 'zustand';
import {
  addManualWireWearRecords,
  applyWireWearSyncPreview,
  applyWireWearChanges,
  deleteWireWearRecord,
  discoverHistoricalWearWorkbook,
  exportWireWearSyncPackage,
  exportWireWearRecords,
  fetchWireWearDashboard,
  fetchWireWearProjection,
  fetchWireWearRemainingLife,
  fetchWireWearRecords,
  fetchWireWearWorkbench,
  fetchWearCycleWorkbench,
  importWireWearSyncPackage,
  previewHistoricalWearWorkbook,
  previewWireWearSyncPackage,
  previewWearRecordCandidates,
  saveWireWearRecords,
  updateWireWearRecord,
} from '../api/client';
import type {
  WireWearDashboardResponse,
  WearCycleMatrixRow,
  WearRecordChange,
  WireWearLineClass,
  WireWearLineGroup,
  WireWearProjectionResponse,
  WireWearRemainingLifeResponse,
  WireWearRecordsResponse,
  WireWearSaveRequest,
  WireWearSavedRecord,
  WireWearSyncImportSummary,
  WireWearUpdateRequest,
  WireWearWorkbenchResponse,
  WearCycleWorkbenchResponse,
  WearCandidatePreview,
  WearCandidatePreviewRequest,
  WearChangeOrigin,
  WearHistoricalWorkbookDiscovery,
  WearHistoricalWorkbookPreview,
  WearSyncApplySummary,
  WearSyncConflictChoice,
  WearSyncConflictDecision,
  WearSyncPreview,
} from '../types/api';

interface DuplicateConflict {
  duplicate_count: number
  duplicates: Array<Partial<WireWearSavedRecord>>
}

interface WearRecordsState {
  records: WireWearRecordsResponse['records']
  workbench: WireWearWorkbenchResponse | null
  dashboard: WireWearDashboardResponse | null
  projection: WireWearProjectionResponse | null
  isProjectionLoading: boolean
  projectionError: string | null
  remainingLife: WireWearRemainingLifeResponse | null
  isRemainingLifeLoading: boolean
  remainingLifeError: string | null
  wearThresholdMm: number
  selectedLineGroup: WireWearLineGroup
  selectedLineClass: WireWearLineClass
  selectedTensionLength: string | null
  isLoading: boolean
  isSaving: boolean
  isExporting: boolean
  isSyncing: boolean
  error: string | null
  lastSyncImportSummary: WireWearSyncImportSummary | null
  duplicateConflict: DuplicateConflict | null
  cycleWorkbench: WearCycleWorkbenchResponse | null
  committedSnapshot: WearCycleWorkbenchResponse | null
  pendingChanges: WearRecordChange[]
  optimisticMatrixRows: WearCycleMatrixRow[]
  changeSummary: { added: number; edited: number; deletedCells: number; deletedRows: number }
  commitErrors: string[]
  hasPendingChanges: boolean
  shouldBlockNavigation: boolean
  wireWearDataVersion: number
  candidatePreview: WearCandidatePreview | null
  historicalDiscovery: WearHistoricalWorkbookDiscovery | null
  historicalPreview: WearHistoricalWorkbookPreview | null
  historicalExcludedDiagnosticIds: string[]
  isPreviewingCandidates: boolean
  previewError: string | null
  pendingOrigin: WearChangeOrigin
  lastBackupPath: string | null
  syncPreview: WearSyncPreview | null
  syncConflictDecisions: Record<string, WearSyncConflictChoice>
  syncApplySummary: WearSyncApplySummary | null
  syncGuardState: 'none' | 'unsupported_package' | 'stale_preview' | 'backup_failure' | 'apply_failure'
  syncGuardMessage: string | null
  isPreviewingSync: boolean
  isApplyingSync: boolean
  saveAnalysisResults: (payload: WireWearSaveRequest, overwrite?: boolean) => Promise<void>
  saveAnalysisBatches: (payloads: WireWearSaveRequest[], overwrite?: boolean) => Promise<void>
  loadRecords: (params?: Record<string, string | undefined>) => Promise<void>
  loadWorkbench: (params?: Record<string, string | undefined>) => Promise<void>
  loadCycleWorkbench: (params?: { lineGroup?: WireWearLineGroup; lineClass?: WireWearLineClass; tensionLengthQuery?: string; selectedTensionLength?: string; summaryOnly?: boolean; dateFrom?: string; dateTo?: string }) => Promise<void>
  setSelectedLineGroup: (lineGroup: WireWearLineGroup) => void
  setSelectedLineClass: (lineClass: WireWearLineClass) => void
  setSelectedTensionLength: (tensionLength: string | null) => void
  addManualRecord: (payload: WireWearSaveRequest) => Promise<void>
  updateRecord: (recordId: number, payload: WireWearUpdateRequest) => Promise<void>
  deleteRecord: (recordId: number) => Promise<void>
  exportRecords: (params?: Record<string, string | undefined>) => Promise<Blob | null>
  exportSyncPackage: (sourceLabel?: string) => Promise<Blob | null>
  importSyncPackage: (file: File) => Promise<WireWearSyncImportSummary | null>
  previewSyncPackage: (file: File) => Promise<WearSyncPreview | null>
  resolveSyncConflict: (rowId: string, choice: WearSyncConflictChoice) => void
  applySyncPreview: () => Promise<WearSyncApplySummary | null>
  clearSyncImport: () => void
  loadDashboard: () => Promise<void>
  loadProjection: (thresholdMm?: number) => Promise<void>
  loadRemainingLife: (thresholdMm?: number) => Promise<void>
  setWearThresholdMm: (thresholdMm: number) => void
  loadAll: () => Promise<void>
  clearDuplicateConflict: () => void
  reset: () => void
  hydrate: (workbench: WearCycleWorkbenchResponse) => void
  stageAdd: (key: { lineGroup: WireWearLineGroup; lineClass?: WireWearLineClass; cycleDate: string; tensionLength: string }, avgWearMin: number) => void
  stageEdit: (key: { lineGroup: WireWearLineGroup; lineClass?: WireWearLineClass; cycleDate: string; tensionLength: string }, avgWearMin: number, expectedUpdatedAt?: string) => void
  stageDeleteCell: (key: { lineGroup: WireWearLineGroup; lineClass?: WireWearLineClass; cycleDate: string; tensionLength: string }, expectedUpdatedAt?: string) => void
  stageDeleteRow: (lineGroup: WireWearLineGroup, cycleDate: string, lineClass?: WireWearLineClass) => void
  previewCandidateRows: (payload: WearCandidatePreviewRequest) => Promise<WearCandidatePreview | null>
  discoverHistoricalWorkbook: (file: File) => Promise<WearHistoricalWorkbookDiscovery | null>
  previewHistoricalWorkbook: (file: File, selectedSheets: string[]) => Promise<WearHistoricalWorkbookPreview | null>
  setHistoricalErrorExcluded: (rowId: string, excluded: boolean) => void
  clearImportPreviews: () => void
  stageBatch: (preview: WearCandidatePreview, origin?: WearChangeOrigin) => boolean
  stageHistoricalPreview: () => boolean
  saveChanges: () => Promise<void>
  discardChanges: () => void
}

const initialState = {
  records: [],
  workbench: null,
  dashboard: null,
  projection: null,
  isProjectionLoading: false,
  projectionError: null,
  remainingLife: null,
  isRemainingLifeLoading: false,
  remainingLifeError: null,
  wearThresholdMm: 10.2,
  selectedLineGroup: 'EAL' as WireWearLineGroup,
  selectedLineClass: 'EAL' as WireWearLineClass,
  selectedTensionLength: null,
  isLoading: false,
  isSaving: false,
  isExporting: false,
  isSyncing: false,
  error: null,
  lastSyncImportSummary: null,
  duplicateConflict: null,
  cycleWorkbench: null,
  committedSnapshot: null,
  pendingChanges: [],
  optimisticMatrixRows: [],
  changeSummary: { added: 0, edited: 0, deletedCells: 0, deletedRows: 0 },
  commitErrors: [],
  hasPendingChanges: false,
  shouldBlockNavigation: false,
  wireWearDataVersion: 0,
  candidatePreview: null,
  historicalDiscovery: null,
  historicalPreview: null,
  historicalExcludedDiagnosticIds: [],
  isPreviewingCandidates: false,
  previewError: null,
  pendingOrigin: 'manual' as WearChangeOrigin,
  lastBackupPath: null,
  syncPreview: null,
  syncConflictDecisions: {},
  syncApplySummary: null,
  syncGuardState: 'none' as const,
  syncGuardMessage: null,
  isPreviewingSync: false,
  isApplyingSync: false,
};

const syncGuardForError = (err: any) => {
  const status = err.response?.status;
  const detail = err.response?.data?.detail;
  const message = String(detail?.message || detail || err.message || 'Wire Wear data package failed');
  const normalized = message.toLowerCase();
  if (status === 409) return { state: 'stale_preview' as const, message };
  if (status === 503 || normalized.includes('backup')) {
    return { state: 'backup_failure' as const, message };
  }
  if (
    status === 400
    || normalized.includes('unsupported')
    || normalized.includes('schema')
    || normalized.includes('package')
  ) {
    return { state: 'unsupported_package' as const, message };
  }
  return { state: 'apply_failure' as const, message };
};

const businessKey = (operation: WearRecordChange) => operation.kind === 'delete_row'
  ? `${operation.lineGroup}:${operation.lineClass}:${operation.cycleDate}`
  : `${operation.key.lineGroup}:${operation.key.lineClass}:${operation.key.cycleDate}:${operation.key.tensionLength}`;

const upsertStagedChange = (changes: WearRecordChange[], operation: WearRecordChange) => {
  const key = businessKey(operation);
  // A row delete supersedes all cell operations for that row. Conversely, a
  // subsequent cell operation re-opens that row and must remove its staged
  // row-delete so the wire payload remains executable in order.
  const rowDeleteIndex = changes.findIndex(existing => existing.kind === 'delete_row'
    && (operation.kind === 'delete_row'
      ? existing.lineGroup === operation.lineGroup
        && existing.lineClass === operation.lineClass
        && existing.cycleDate === operation.cycleDate
      : existing.lineGroup === operation.key.lineGroup
        && existing.lineClass === operation.key.lineClass
        && existing.cycleDate === operation.key.cycleDate));
  let nextChanges = changes;
  if (operation.kind === 'delete_row') {
    nextChanges = changes.filter(existing => !(existing.kind !== 'delete_row'
      ? existing.key.lineGroup === operation.lineGroup
        && existing.key.lineClass === operation.lineClass
        && existing.key.cycleDate === operation.cycleDate
      : existing.lineGroup === operation.lineGroup
        && existing.lineClass === operation.lineClass
        && existing.cycleDate === operation.cycleDate));
  } else if (rowDeleteIndex >= 0) {
    nextChanges = changes.filter((_, index) => index !== rowDeleteIndex);
  }

  const index = nextChanges.findIndex(existing => businessKey(existing) === key);
  if (index < 0) return [...nextChanges, operation];
  const existing = nextChanges[index];
  // An add followed by an edit is still an add: the edit only changes the
  // optimistic value before the batch is committed.
  if (existing.kind === 'add' && operation.kind === 'edit') {
    const next = [...nextChanges];
    next[index] = { ...existing, avgWearMin: operation.avgWearMin };
    return next;
  }
  // An add followed by deleting that same cell is a local no-op because the
  // row does not exist on the server yet.
  if (existing.kind === 'add' && operation.kind === 'delete_cell') {
    return nextChanges.filter((_, existingIndex) => existingIndex !== index);
  }
  const next = [...nextChanges];
  next[index] = operation;
  return next;
};

const deriveStagedState = (
  committedSnapshot: WearCycleWorkbenchResponse | null,
  pendingChanges: WearRecordChange[],
) => {
  const sourceRows = committedSnapshot?.matrixRows
    ?? committedSnapshot?.matrix_rows
    ?? committedSnapshot?.history_rows
    ?? [];
  const optimisticMatrixRows = sourceRows.map(row => ({
    cycleDate: 'cycleDate' in row ? row.cycleDate : row.cycle_date,
    values: { ...row.values },
  }));

  for (const change of pendingChanges) {
    if (change.kind === 'delete_row') {
      const index = optimisticMatrixRows.findIndex(row => row.cycleDate === change.cycleDate);
      if (index >= 0) optimisticMatrixRows.splice(index, 1);
      continue;
    }
    let row = optimisticMatrixRows.find(candidate => candidate.cycleDate === change.key.cycleDate);
    if (!row && change.kind === 'add') {
      row = { cycleDate: change.key.cycleDate, values: {} };
      optimisticMatrixRows.push(row);
    }
    if (!row) continue;
    if (change.kind === 'delete_cell') delete row.values[change.key.tensionLength];
    else row.values[change.key.tensionLength] = change.avgWearMin;
  }

  const changeSummary = pendingChanges.reduce((summary, change) => {
    if (change.kind === 'add') summary.added += 1;
    else if (change.kind === 'edit') summary.edited += 1;
    else if (change.kind === 'delete_cell') summary.deletedCells += 1;
    else summary.deletedRows += 1;
    return summary;
  }, { added: 0, edited: 0, deletedCells: 0, deletedRows: 0 });
  const hasPendingChanges = pendingChanges.length > 0;
  return { optimisticMatrixRows, changeSummary, hasPendingChanges, shouldBlockNavigation: hasPendingChanges };
};

export const useWearRecordsStore = create<WearRecordsState>((set, get) => ({
  ...initialState,

  saveAnalysisResults: async (payload, overwrite = false) => {
    set({ isSaving: true, error: null, duplicateConflict: null });
    try {
      await saveWireWearRecords(payload, overwrite);
      set({ isSaving: false });
      await get().loadAll();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 409 && detail) {
        set({
          duplicateConflict: {
            duplicate_count: detail.duplicate_count,
            duplicates: detail.duplicates,
          },
          isSaving: false,
        });
        return;
      }
      set({
        error: detail?.message || detail || err.message || 'Failed to save wire wear records',
        isSaving: false,
      });
    }
  },

  saveAnalysisBatches: async (payloads, overwrite = false) => {
    if (!payloads.length) return;

    set({ isSaving: true, error: null, duplicateConflict: null });
    try {
      if (!overwrite) {
        const conflicts: DuplicateConflict = { duplicate_count: 0, duplicates: [] };
        for (const payload of payloads) {
          try {
            await saveWireWearRecords(payload, false, true);
          } catch (err: any) {
            const detail = err.response?.data?.detail;
            if (err.response?.status === 409 && detail) {
              conflicts.duplicate_count += detail.duplicate_count ?? 0;
              conflicts.duplicates.push(...(detail.duplicates ?? []));
              continue;
            }
            throw err;
          }
        }

        if (conflicts.duplicate_count > 0) {
          set({ duplicateConflict: conflicts, isSaving: false });
          return;
        }
      }

      for (const payload of payloads) {
        await saveWireWearRecords(payload, overwrite);
      }
      set({ isSaving: false });
      await get().loadAll();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      set({
        error: detail?.message || detail || err.message || 'Failed to save wire wear records',
        isSaving: false,
      });
    }
  },

  loadRecords: async (params = {}) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetchWireWearRecords(params);
      set({ records: response.records, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to load wire wear records', isLoading: false });
    }
  },

  loadWorkbench: async (params = {}) => {
    set({ isLoading: true, error: null });
    try {
      const workbench = await fetchWireWearWorkbench(params);
      set({
        workbench,
        records: workbench.raw_records,
        selectedLineGroup: workbench.line_group,
        selectedLineClass: workbench.line_class,
        selectedTensionLength: workbench.tension_lengths[0] ?? null,
        isLoading: false,
      });
    } catch (err: any) {
      set({ error: err.message || 'Failed to load wire wear workbench', isLoading: false });
    }
  },

  setSelectedLineGroup: (lineGroup) => set({
    selectedLineGroup: lineGroup,
    selectedLineClass: lineGroup,
  }),

  setSelectedLineClass: (lineClass) => set({
    selectedLineGroup: lineClass === 'TML' ? 'TML' : 'EAL',
    selectedLineClass: lineClass,
  }),

  setSelectedTensionLength: (tensionLength) => set({ selectedTensionLength: tensionLength }),

  addManualRecord: async (payload) => {
    set({ isSaving: true, error: null, duplicateConflict: null });
    try {
      await addManualWireWearRecords(payload);
      set({ isSaving: false });
      await get().loadWorkbench({
        line_group: payload.line_group,
        line_class: payload.line_class,
      });
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 409 && detail) {
        set({
          duplicateConflict: {
            duplicate_count: detail.duplicate_count,
            duplicates: detail.duplicates,
          },
          isSaving: false,
        });
        return;
      }
      set({ error: detail?.message || detail || err.message || 'Failed to add wire wear record', isSaving: false });
    }
  },

  updateRecord: async (recordId, payload) => {
    set({ isSaving: true, error: null });
    try {
      await updateWireWearRecord(recordId, payload);
      set({ isSaving: false });
      await get().loadWorkbench({
        line_group: get().selectedLineGroup,
        line_class: get().selectedLineClass,
      });
    } catch (err: any) {
      set({ error: err.message || 'Failed to update wire wear record', isSaving: false });
    }
  },

  deleteRecord: async (recordId) => {
    set({ isSaving: true, error: null });
    try {
      await deleteWireWearRecord(recordId);
      set({ isSaving: false });
      await get().loadWorkbench({
        line_group: get().selectedLineGroup,
        line_class: get().selectedLineClass,
      });
    } catch (err: any) {
      set({ error: err.message || 'Failed to delete wire wear record', isSaving: false });
    }
  },

  exportRecords: async (params = {}) => {
    set({ isExporting: true, error: null });
    try {
      const blob = await exportWireWearRecords(params);
      set({ isExporting: false });
      return blob;
    } catch (err: any) {
      set({ error: err.message || 'Failed to export wire wear records', isExporting: false });
      return null;
    }
  },

  exportSyncPackage: async (sourceLabel = 'TOV640 Analyzer') => {
    set({ isSyncing: true, error: null });
    try {
      const blob = await exportWireWearSyncPackage(sourceLabel);
      set({ isSyncing: false });
      return blob;
    } catch (err: any) {
      set({ error: err.message || 'Failed to export wire wear sync package', isSyncing: false });
      return null;
    }
  },

  previewSyncPackage: async (file) => {
    if (get().hasPendingChanges) return null;
    set({
      isPreviewingSync: true,
      syncPreview: null,
      syncConflictDecisions: {},
      syncApplySummary: null,
      syncGuardState: 'none',
      syncGuardMessage: null,
      error: null,
    });
    try {
      const syncPreview = await previewWireWearSyncPackage(file);
      set({ syncPreview, isPreviewingSync: false });
      return syncPreview;
    } catch (err: any) {
      const guard = syncGuardForError(err);
      set({
        isPreviewingSync: false,
        syncGuardState: guard.state,
        syncGuardMessage: guard.message,
      });
      return null;
    }
  },

  resolveSyncConflict: (rowId, choice) => set(state => ({
    syncConflictDecisions: {
      ...state.syncConflictDecisions,
      [rowId]: choice,
    },
  })),

  applySyncPreview: async () => {
    const state = get();
    if (!state.syncPreview || state.hasPendingChanges) return null;
    const decisions: WearSyncConflictDecision[] = state.syncPreview.rows.flatMap(row => {
      const choice = state.syncConflictDecisions[row.id];
      return row.status === 'conflict' && choice ? [{ key: row.key, choice }] : [];
    });
    set({
      isApplyingSync: true,
      syncApplySummary: null,
      syncGuardState: 'none',
      syncGuardMessage: null,
      error: null,
    });
    try {
      const summary = await applyWireWearSyncPreview(state.syncPreview, decisions);
      set({
        isApplyingSync: false,
        syncApplySummary: summary,
        lastBackupPath: summary.backupPath ?? null,
        wireWearDataVersion: summary.dataVersion,
      });
      await Promise.all([
        get().loadCycleWorkbench({
          lineGroup: get().selectedLineGroup,
          lineClass: get().selectedLineClass,
        }),
        get().loadRecords(),
        get().loadDashboard(),
        get().loadProjection(),
      ]);
      return summary;
    } catch (err: any) {
      const guard = syncGuardForError(err);
      set({
        isApplyingSync: false,
        syncGuardState: guard.state,
        syncGuardMessage: guard.message,
      });
      return null;
    }
  },

  clearSyncImport: () => set({
    syncPreview: null,
    syncConflictDecisions: {},
    syncApplySummary: null,
    syncGuardState: 'none',
    syncGuardMessage: null,
    isPreviewingSync: false,
    isApplyingSync: false,
  }),

  importSyncPackage: async (file) => {
    set({ isSyncing: true, error: null, lastSyncImportSummary: null });
    try {
      const summary = await importWireWearSyncPackage(file);
      set({ isSyncing: false, lastSyncImportSummary: summary });
      await get().loadWorkbench({
        line_group: get().selectedLineGroup,
        line_class: get().selectedLineClass,
      });
      return summary;
    } catch (err: any) {
      set({ error: err.message || 'Failed to import wire wear sync package', isSyncing: false });
      return null;
    }
  },

  loadDashboard: async () => {
    try {
      const dashboard = await fetchWireWearDashboard();
      set({ dashboard });
    } catch (err: any) {
      set({ error: err.message || 'Failed to load wire wear dashboard' });
    }
  },

  loadProjection: async (thresholdMm = 10.2) => {
    set({ wearThresholdMm: thresholdMm });
    set({ isProjectionLoading: true, projectionError: null });
    try {
      const projection = await fetchWireWearProjection(thresholdMm);
      set({ projection, isProjectionLoading: false });
    } catch (err: any) {
      set({
        projectionError: err.message || 'Failed to load wire wear projection',
        isProjectionLoading: false,
      });
    }
  },

  loadAll: async () => {
    set({ isLoading: true, error: null });
    try {
      const [records, dashboard, projection] = await Promise.all([
        fetchWireWearRecords(),
        fetchWireWearDashboard(),
        fetchWireWearProjection(),
      ]);
      set({ records: records.records, dashboard, projection, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to load wire wear data', isLoading: false });
    }
  },

  loadRemainingLife: async (thresholdMm = 10.2) => {
    set({ wearThresholdMm: thresholdMm });
    set({ isRemainingLifeLoading: true, remainingLifeError: null });
    try {
      const remainingLife = await fetchWireWearRemainingLife(thresholdMm);
      set({ remainingLife, isRemainingLifeLoading: false });
    } catch (err: any) {
      set({ remainingLifeError: err.message || 'Failed to load remaining life', isRemainingLifeLoading: false });
    }
  },

  setWearThresholdMm: (thresholdMm) => {
    if (Number.isFinite(thresholdMm) && thresholdMm > 0 && thresholdMm <= 13.2) {
      set({ wearThresholdMm: thresholdMm });
    }
  },

  previewCandidateRows: async (payload) => {
    set({ isPreviewingCandidates: true, previewError: null });
    try {
      const candidatePreview = await previewWearRecordCandidates(payload);
      set({ candidatePreview, isPreviewingCandidates: false });
      return candidatePreview;
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const message = detail?.message || detail || err.message || 'Failed to preview wire wear candidates';
      set({ candidatePreview: null, previewError: String(message), isPreviewingCandidates: false });
      return null;
    }
  },

  discoverHistoricalWorkbook: async (file) => {
    set({ isPreviewingCandidates: true, previewError: null, historicalPreview: null });
    try {
      const historicalDiscovery = await discoverHistoricalWearWorkbook(file);
      set({ historicalDiscovery, isPreviewingCandidates: false, historicalExcludedDiagnosticIds: [] });
      return historicalDiscovery;
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const message = detail?.message || detail || err.message || 'Failed to inspect historical workbook';
      set({ historicalDiscovery: null, previewError: String(message), isPreviewingCandidates: false });
      return null;
    }
  },

  previewHistoricalWorkbook: async (file, selectedSheets) => {
    set({ isPreviewingCandidates: true, previewError: null });
    try {
      const preview = await previewHistoricalWearWorkbook(file, selectedSheets);
      const historicalPreview = {
        ...preview,
        candidates: preview.candidates.map(candidate => (
          candidate.status === 'error' ? { ...candidate, excluded: true } : candidate
        )),
      };
      set({
        historicalPreview,
        historicalDiscovery: { sheets: historicalPreview.sheets },
        historicalExcludedDiagnosticIds: historicalPreview.diagnostics.map(
          (_diagnostic, index) => `diagnostic:${index}`,
        ),
        isPreviewingCandidates: false,
      });
      return historicalPreview;
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const message = detail?.message || detail || err.message || 'Failed to preview historical workbook';
      set({ historicalPreview: null, previewError: String(message), isPreviewingCandidates: false });
      return null;
    }
  },

  setHistoricalErrorExcluded: (rowId, excluded) => set(state => {
    if (rowId.startsWith('diagnostic:')) {
      const ids = new Set(state.historicalExcludedDiagnosticIds);
      if (excluded) ids.add(rowId); else ids.delete(rowId);
      return { historicalExcludedDiagnosticIds: [...ids] };
    }
    if (!state.historicalPreview) return {};
    return {
      historicalPreview: {
        ...state.historicalPreview,
        candidates: state.historicalPreview.candidates.map(candidate => (
          candidate.rowId === rowId ? { ...candidate, excluded } : candidate
        )),
      },
    };
  }),

  clearImportPreviews: () => set({
    candidatePreview: null,
    historicalDiscovery: null,
    historicalPreview: null,
    historicalExcludedDiagnosticIds: [],
    previewError: null,
    isPreviewingCandidates: false,
  }),

  hydrate: (workbench) => {
    const normalized: WearCycleWorkbenchResponse = workbench.matrixRows
      ? workbench
      : {
        lineGroup: workbench.line_group ?? 'EAL',
        lineClass: workbench.line_class ?? workbench.line_group ?? 'EAL',
        columns: workbench.columns ?? [],
        matrixRows: (workbench.matrix_rows ?? workbench.history_rows ?? []).map(row => ({
          cycleDate: row.cycle_date,
          values: { ...row.values },
        })),
        latestSummary: workbench.latestSummary ?? [],
        records: workbench.records ?? [],
        catalog: workbench.catalog ?? [],
        selectedTensionLength: workbench.selectedTensionLength ?? workbench.columns[0]?.tensionLength ?? null,
        summaryOnly: workbench.summaryOnly ?? false,
        wireWearDataVersion: workbench.wire_wear_data_version ?? 0,
        line_group: workbench.line_group,
        line_class: workbench.line_class,
        matrix_rows: workbench.matrix_rows,
        history_rows: workbench.history_rows,
        latest_summary_rows: workbench.latest_summary_rows,
        wire_wear_data_version: workbench.wire_wear_data_version,
      };
    set({
      cycleWorkbench: normalized,
      committedSnapshot: normalized,
      selectedLineGroup: normalized.lineGroup,
      selectedLineClass: normalized.lineClass,
      selectedTensionLength: normalized.selectedTensionLength ?? normalized.columns[0]?.tensionLength ?? null,
      wireWearDataVersion: normalized.wireWearDataVersion,
      pendingChanges: [],
      pendingOrigin: 'manual',
      lastBackupPath: null,
      commitErrors: [],
      error: null,
      ...deriveStagedState(normalized, []),
    });
  },

  stageAdd: (key, avgWearMin) => set(state => {
    const lineClass = key.lineClass ?? key.lineGroup;
    const pendingChanges = upsertStagedChange(state.pendingChanges, {
      kind: 'add', key: {
        lineGroup: key.lineGroup,
        lineClass,
        cycleDate: key.cycleDate,
        tensionLength: key.tensionLength,
      }, avgWearMin,
    });
    return { pendingChanges, commitErrors: [], ...deriveStagedState(state.committedSnapshot, pendingChanges) };
  }),

  stageEdit: (key, avgWearMin, expectedUpdatedAt = '') => set(state => {
    const lineClass = key.lineClass ?? key.lineGroup;
    const pendingChanges = upsertStagedChange(state.pendingChanges, {
      kind: 'edit', key: {
        lineGroup: key.lineGroup,
        lineClass,
        cycleDate: key.cycleDate,
        tensionLength: key.tensionLength,
      }, avgWearMin, expectedUpdatedAt,
    });
    return { pendingChanges, commitErrors: [], ...deriveStagedState(state.committedSnapshot, pendingChanges) };
  }),

  stageDeleteCell: (key, expectedUpdatedAt = '') => set(state => {
    const lineClass = key.lineClass ?? key.lineGroup;
    const pendingChanges = upsertStagedChange(state.pendingChanges, {
      kind: 'delete_cell', key: {
        lineGroup: key.lineGroup,
        lineClass,
        cycleDate: key.cycleDate,
        tensionLength: key.tensionLength,
      }, expectedUpdatedAt,
    });
    return { pendingChanges, commitErrors: [], ...deriveStagedState(state.committedSnapshot, pendingChanges) };
  }),

  stageDeleteRow: (lineGroup, cycleDate, requestedLineClass) => set(state => {
    const lineClass = requestedLineClass ?? (lineGroup === state.selectedLineGroup
      ? state.selectedLineClass
      : lineGroup);
    const pendingChanges: WearRecordChange[] = [
      ...state.pendingChanges.filter(change => !(change.kind !== 'delete_row'
        ? change.key.lineGroup === lineGroup
          && change.key.lineClass === lineClass
          && change.key.cycleDate === cycleDate
        : change.lineGroup === lineGroup
          && change.lineClass === lineClass
          && change.cycleDate === cycleDate)),
      { kind: 'delete_row', lineGroup, lineClass, cycleDate },
    ];
    return { pendingChanges, commitErrors: [], ...deriveStagedState(state.committedSnapshot, pendingChanges) };
  }),

  stageBatch: (preview, origin = 'manual') => {
    let staged = false;
    set(state => {
      if (preview.wireWearDataVersion !== state.wireWearDataVersion) {
        return {
          commitErrors: ['Candidate preview is stale. Refresh the preview before staging.'],
        };
      }
      if (preview.candidates.some(candidate => candidate.status === 'error' && !candidate.excluded)) {
        return {
          commitErrors: ['Resolve or exclude candidate errors before staging.'],
        };
      }
      const pendingChangesByKey = new Map(
        state.pendingChanges.map(change => [businessKey(change), change]),
      );
      for (const candidate of preview.candidates) {
        if (candidate.excluded || !candidate.key || candidate.avgWearMin === null) continue;
        const rowKey = `${candidate.key.lineGroup}:${candidate.key.lineClass}:${candidate.key.cycleDate}`;
        pendingChangesByKey.delete(rowKey);
        let operation: WearRecordChange | null = null;
        if (candidate.status === 'new') {
          operation = {
            kind: 'add', key: candidate.key, avgWearMin: candidate.avgWearMin,
          };
        } else if (candidate.status === 'update' && candidate.expectedUpdatedAt) {
          operation = {
            kind: 'edit', key: candidate.key, avgWearMin: candidate.avgWearMin,
            expectedUpdatedAt: candidate.expectedUpdatedAt,
          };
        }
        if (operation) {
          const key = businessKey(operation);
          const existing = pendingChangesByKey.get(key);
          pendingChangesByKey.set(
            key,
            existing?.kind === 'add' && operation.kind === 'edit'
              ? { ...existing, avgWearMin: operation.avgWearMin }
              : operation,
          );
        }
      }
      const pendingChanges = [...pendingChangesByKey.values()];
      staged = true;
      return {
        pendingChanges,
        pendingOrigin: state.pendingOrigin === 'workbook' || origin === 'workbook'
          ? 'workbook'
          : 'manual',
        commitErrors: [],
        ...deriveStagedState(state.committedSnapshot, pendingChanges),
      };
    });
    return staged;
  },

  stageHistoricalPreview: () => {
    const state = get();
    const preview = state.historicalPreview;
    if (!preview) return false;
    const unresolvedDiagnostics = preview.diagnostics.some(
      (_diagnostic, index) => !state.historicalExcludedDiagnosticIds.includes(`diagnostic:${index}`),
    );
    if (unresolvedDiagnostics) {
      set({ commitErrors: ['Resolve or exclude workbook diagnostics before staging.'] });
      return false;
    }
    return get().stageBatch({
      lineGroup: state.selectedLineGroup,
      lineClass: state.selectedLineClass,
      cycleDate: '',
      wireWearDataVersion: preview.wireWearDataVersion,
      counts: preview.totals,
      candidates: preview.candidates,
    }, 'workbook');
  },

  saveChanges: async () => {
    const { pendingChanges, wireWearDataVersion, pendingOrigin } = get();
    if (!pendingChanges.length) return;
    set({ isSaving: true, error: null, commitErrors: [] });
    let result;
    try {
      result = await applyWireWearChanges({
        expectedDataVersion: wireWearDataVersion,
        operations: pendingChanges,
        origin: pendingOrigin,
      });
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const message = detail?.message || detail || err.message || 'Failed to save wire wear changes';
      set({ error: message, commitErrors: [String(message)], isSaving: false });
      return;
    }

    const nextDataVersion = Number(result.wire_wear_data_version ?? 0);
    set(state => ({
      pendingChanges: [],
      pendingOrigin: 'manual',
      lastBackupPath: result.backup_path ?? null,
      wireWearDataVersion: nextDataVersion,
      isSaving: false,
      commitErrors: [],
      ...deriveStagedState(state.committedSnapshot, []),
    }));
    try {
      const selectedTensionLength = get().selectedTensionLength;
      const refreshed = await fetchWearCycleWorkbench({
        lineGroup: get().selectedLineGroup,
        lineClass: get().selectedLineClass,
        ...(selectedTensionLength ? { selectedTensionLength } : {}),
      });
      set({
        cycleWorkbench: refreshed,
        committedSnapshot: refreshed,
        wireWearDataVersion: nextDataVersion,
        ...deriveStagedState(refreshed, []),
      });
    } catch (err: any) {
      const message = `Changes saved, but failed to reload workbench: ${err.message || 'unknown error'}`;
      set({ error: message, commitErrors: [message] });
    }
  },

  loadCycleWorkbench: async (params = {}) => {
    set({ isLoading: true, error: null });
    try {
      const cycleWorkbench = await fetchWearCycleWorkbench({
        ...params,
        summaryOnly: params.summaryOnly ?? params.selectedTensionLength == null,
      });
      set(state => ({
        cycleWorkbench,
        committedSnapshot: cycleWorkbench,
        selectedTensionLength: params.summaryOnly === false && params.selectedTensionLength == null
          ? state.selectedTensionLength
          : cycleWorkbench.selectedTensionLength ?? null,
        selectedLineGroup: cycleWorkbench.lineGroup,
        selectedLineClass: cycleWorkbench.lineClass,
        wireWearDataVersion: cycleWorkbench.wireWearDataVersion,
        isLoading: false,
        ...deriveStagedState(cycleWorkbench, state.pendingChanges),
      }));
    } catch (err: any) {
      set({ error: err.message || 'Failed to load wire wear cycle workbench', isLoading: false });
    }
  },

  discardChanges: () => set(state => ({
    cycleWorkbench: state.committedSnapshot,
    pendingChanges: [],
    pendingOrigin: 'manual',
    commitErrors: [],
    error: null,
    ...deriveStagedState(state.committedSnapshot, []),
  })),

  clearDuplicateConflict: () => set({ duplicateConflict: null }),

  reset: () => set(initialState),
}));
