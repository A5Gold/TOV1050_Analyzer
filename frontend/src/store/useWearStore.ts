import { create } from 'zustand';
import { previewWearCycle, saveWearCycle, uploadWearFiles } from '../api/client';
import type { WearCyclePreview, WearCycleSaveResponse, WearResult, WireWearLineClass } from '../types/api';

type WearCycleTabState = {
  cyclePreview: WearCyclePreview | null;
  cyclePreviewFiles: File[];
  cyclePreviewLoading: boolean;
  cycleSaveLoading: boolean;
  cycleError: string | null;
  lastCycleSave: WearCycleSaveResponse | null;
};

export interface WearTab extends WearCycleTabState {
  id: string;
  label: string;
  line: 'EAL' | 'TML';
  lineClass: WireWearLineClass;
  uploadedFiles: File[];
  isLoading: boolean;
  error: string | null;
  date: string;
  wearResults: WearResult[];
  hasAnalyzed: boolean;
  acceptedConflictIds: string[];
}

interface WearStoreState {
  tabs: WearTab[];
  activeTabId: string;
  addTab: () => void;
  closeTab: (id: string) => void;
  setActiveTab: (id: string) => void;
  setLine: (line: 'EAL' | 'TML') => void;
  setLineClass: (lineClass: WireWearLineClass) => void;
  setCycleDate: (date: string) => void;
  addFile: (file: File) => void;
  removeFile: (name: string) => void;
  analyze: () => Promise<void>;
  resetTab: () => void;
  resetAll: () => void;
  previewCycle: (options?: { cycleDate?: string; acceptedConflictIds?: string[] }) => Promise<void>;
  saveCycle: () => Promise<WearCycleSaveResponse | null>;
  acceptConflict: (conflictId: string) => Promise<void>;
  clearCyclePreview: () => void;
}

const emptyCycleState = (): WearCycleTabState => ({
  cyclePreview: null,
  cyclePreviewFiles: [],
  cyclePreviewLoading: false,
  cycleSaveLoading: false,
  cycleError: null,
  lastCycleSave: null,
});

const clearedPreviewState = (): Pick<
  WearCycleTabState,
  'cyclePreview' | 'cyclePreviewFiles' | 'cyclePreviewLoading' | 'cycleError'
> => ({
  cyclePreview: null,
  cyclePreviewFiles: [],
  cyclePreviewLoading: false,
  cycleError: null,
});

const makeTab = (id: string, label: string): WearTab => ({
  id,
  label,
  line: 'EAL',
  lineClass: 'EAL',
  uploadedFiles: [],
  isLoading: false,
  error: null,
  date: '',
  wearResults: [],
  hasAnalyzed: false,
  acceptedConflictIds: [],
  ...emptyCycleState(),
});

const updateTab = (tabs: WearTab[], tabId: string, patch: Partial<WearTab>): WearTab[] =>
  tabs.map((tab) => (tab.id === tabId ? { ...tab, ...patch } : tab));

const cycleErrorMessage = (error: any, fallback: string): string => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') {
    const reasons = detail.blocking_reasons ?? detail.blockingReasons ?? [];
    const unresolved = detail.unresolved ?? [];
    const parts = Array.isArray(reasons) ? reasons.map(String) : [];
    if (Array.isArray(unresolved) && unresolved.length) {
      parts.push(`${unresolved.length} unresolved measurement${unresolved.length === 1 ? '' : 's'}`);
      parts.push(String(unresolved[0]));
    }
    if (parts.length) return parts.join(': ');
  }
  return error?.message || fallback;
};

let requestSequence = 0;
const previewRequestByTab = new Map<string, number>();
const saveRequestByTab = new Map<string, number>();

const beginPreviewRequest = (tabId: string): number => {
  const requestId = ++requestSequence;
  previewRequestByTab.set(tabId, requestId);
  return requestId;
};

const invalidatePreview = (tabId: string): void => {
  previewRequestByTab.set(tabId, ++requestSequence);
};

const beginSaveRequest = (tabId: string): number => {
  const requestId = ++requestSequence;
  saveRequestByTab.set(tabId, requestId);
  return requestId;
};

const invalidateTabRequests = (tabId: string): void => {
  invalidatePreview(tabId);
  saveRequestByTab.set(tabId, ++requestSequence);
};

export const useWearStore = create<WearStoreState>((set, get) => ({
  tabs: [makeTab('tab-1', 'Tab 1')],
  activeTabId: 'tab-1',

  clearCyclePreview: () => {
    const { tabs, activeTabId } = get();
    invalidatePreview(activeTabId);
    set({ tabs: updateTab(tabs, activeTabId, clearedPreviewState()) });
  },

  addTab: () => {
    const { tabs } = get();
    if (tabs.length >= 6) return;
    const id = crypto.randomUUID();
    const tab = makeTab(id, `Tab ${tabs.length + 1}`);
    set({ tabs: [...tabs, tab], activeTabId: id });
  },

  closeTab: (id) => {
    const { tabs, activeTabId } = get();
    if (tabs.length <= 1) return;
    const idx = tabs.findIndex((tab) => tab.id === id);
    const next = tabs.filter((tab) => tab.id !== id);
    const newActive = activeTabId === id ? next[Math.max(0, idx - 1)].id : activeTabId;
    invalidateTabRequests(id);
    set({ tabs: next, activeTabId: newActive });
  },

  setActiveTab: (id) => {
    if (id === get().activeTabId || !get().tabs.some((tab) => tab.id === id)) return;
    set({ activeTabId: id });
  },

  setLine: (line) => {
    const { tabs, activeTabId } = get();
    invalidatePreview(activeTabId);
    set({ tabs: updateTab(tabs, activeTabId, {
      line,
      lineClass: line,
      date: '',
      wearResults: [],
      hasAnalyzed: false,
      acceptedConflictIds: [],
      error: null,
      ...clearedPreviewState(),
    }) });
  },

  setLineClass: (lineClass) => {
    const { tabs, activeTabId } = get();
    const line = lineClass === 'TML' ? 'TML' : 'EAL';
    invalidatePreview(activeTabId);
    set({ tabs: updateTab(tabs, activeTabId, {
      line,
      lineClass,
      date: '',
      wearResults: [],
      hasAnalyzed: false,
      acceptedConflictIds: [],
      error: null,
      ...clearedPreviewState(),
    }) });
  },

  addFile: (file) => {
    const { tabs, activeTabId } = get();
    const tab = tabs.find((item) => item.id === activeTabId)!;
    invalidatePreview(activeTabId);
    set({ tabs: updateTab(tabs, activeTabId, {
      uploadedFiles: [...tab.uploadedFiles.filter((item) => item.name !== file.name), file],
      date: '',
      wearResults: [],
      hasAnalyzed: false,
      acceptedConflictIds: [],
      error: null,
      ...clearedPreviewState(),
    }) });
  },

  removeFile: (name) => {
    const { tabs, activeTabId } = get();
    const tab = tabs.find((item) => item.id === activeTabId)!;
    invalidatePreview(activeTabId);
    set({ tabs: updateTab(tabs, activeTabId, {
      uploadedFiles: tab.uploadedFiles.filter((file) => file.name !== name),
      wearResults: [],
      hasAnalyzed: false,
      acceptedConflictIds: [],
      error: null,
      ...clearedPreviewState(),
    }) });
  },

  analyze: async () => {
    const { tabs, activeTabId } = get();
    const tab = tabs.find((item) => item.id === activeTabId)!;
    if (!tab.uploadedFiles.length) return;
    const tabId = activeTabId;
    set({ tabs: updateTab(tabs, tabId, {
      isLoading: true,
      error: null,
      hasAnalyzed: false,
      wearResults: [],
    }) });
    try {
      const section = tab.lineClass === 'LMC' ? 'LMC' : undefined;
      const analysisOptions = tab.date || tab.acceptedConflictIds.length
        ? { line: tab.line, cycleDate: tab.date || undefined, acceptedConflictIds: tab.acceptedConflictIds }
        : tab.line;
      const res = await uploadWearFiles(tab.uploadedFiles, analysisOptions, undefined, section);
      const current = get();
      if (!current.tabs.some((item) => item.id === tabId)) return;
      const validConflictIds = new Set(
        Array.isArray((res as any).conflicts)
          ? (res as any).conflicts.map((conflict: any) => conflict.conflict_id ?? conflict.conflictId)
          : tab.acceptedConflictIds,
      );
      set({ tabs: updateTab(current.tabs, tabId, {
        date: res.date,
        wearResults: res.wear_results,
        hasAnalyzed: true,
        isLoading: false,
        acceptedConflictIds: tab.acceptedConflictIds.filter((id) => validConflictIds.has(id)),
      }) });
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((item: any) => item.msg ?? JSON.stringify(item)).join('; ')
        : (typeof detail === 'string' ? detail : err.message) || 'Analysis failed';
      const current = get();
      if (!current.tabs.some((item) => item.id === tabId)) return;
      set({ tabs: updateTab(current.tabs, tabId, { error: msg, hasAnalyzed: false, isLoading: false }) });
    }
  },

  setCycleDate: (date) => {
    const { tabs, activeTabId } = get();
    invalidatePreview(activeTabId);
    set({ tabs: updateTab(tabs, activeTabId, {
      date,
      hasAnalyzed: false,
      wearResults: [],
      acceptedConflictIds: [],
      error: null,
      ...clearedPreviewState(),
    }) });
  },

  previewCycle: async (options = {}) => {
    const { tabs, activeTabId } = get();
    const tab = tabs.find((item) => item.id === activeTabId)!;
    if (!tab.uploadedFiles.length) return;
    const tabId = tab.id;
    const requestId = beginPreviewRequest(tabId);
    const requestedAcceptedIds = options.acceptedConflictIds ?? tab.acceptedConflictIds;
    const uploadedFiles = [...tab.uploadedFiles];
    set({ tabs: updateTab(tabs, tabId, { cyclePreviewLoading: true, cycleError: null }) });
    try {
      const preview = await previewWearCycle(uploadedFiles, {
        lineGroup: tab.line,
        cycleDate: options.cycleDate || tab.date || undefined,
        acceptedConflictIds: requestedAcceptedIds,
      });
      const current = get();
      if (previewRequestByTab.get(tabId) !== requestId || !current.tabs.some((item) => item.id === tabId)) return;
      const validConflictIds = new Set(preview.conflicts.map((conflict) => conflict.conflictId));
      set({ tabs: updateTab(current.tabs, tabId, {
        acceptedConflictIds: requestedAcceptedIds.filter((id) => validConflictIds.has(id)),
        cyclePreview: preview,
        cyclePreviewFiles: uploadedFiles,
        cyclePreviewLoading: false,
      }) });
    } catch (err: any) {
      const current = get();
      if (previewRequestByTab.get(tabId) !== requestId || !current.tabs.some((item) => item.id === tabId)) return;
      set({ tabs: updateTab(current.tabs, tabId, {
        cycleError: cycleErrorMessage(err, 'Cycle preview failed'),
        cyclePreviewLoading: false,
      }) });
    }
  },

  saveCycle: async () => {
    const { tabs, activeTabId } = get();
    const tab = tabs.find((item) => item.id === activeTabId)!;
    const { cyclePreview, cyclePreviewFiles } = tab;
    if (!cyclePreview || !cyclePreview.canSave || !cyclePreviewFiles.length || tab.cycleSaveLoading) return null;
    const tabId = tab.id;
    const requestId = beginSaveRequest(tabId);
    set({ tabs: updateTab(tabs, tabId, { cycleSaveLoading: true, cycleError: null }) });
    try {
      const result = await saveWearCycle(cyclePreviewFiles, {
        lineGroup: cyclePreview.lineGroup,
        cycleDate: cyclePreview.cycleDate,
        acceptedConflictIds: cyclePreview.conflicts.filter((conflict) => conflict.isAccepted).map((conflict) => conflict.conflictId),
        expectedPreviewDigest: cyclePreview.previewDigest,
        expectedDataVersion: cyclePreview.expectedDataVersion,
      });
      const current = get();
      const currentTab = current.tabs.find((item) => item.id === tabId);
      if (saveRequestByTab.get(tabId) !== requestId || !currentTab) return result;
      const previewIsCurrent = currentTab.cyclePreview?.previewDigest === cyclePreview.previewDigest;
      set({ tabs: updateTab(current.tabs, tabId, {
        cycleSaveLoading: false,
        cycleError: null,
        lastCycleSave: result,
        ...(previewIsCurrent ? { cyclePreview: null, cyclePreviewFiles: [] } : {}),
      }) });
      return result;
    } catch (err: any) {
      const current = get();
      if (saveRequestByTab.get(tabId) !== requestId || !current.tabs.some((item) => item.id === tabId)) return null;
      set({ tabs: updateTab(current.tabs, tabId, {
        cycleError: cycleErrorMessage(err, 'Cycle save failed'),
        cycleSaveLoading: false,
      }) });
      return null;
    }
  },

  acceptConflict: async (conflictId) => {
    const { tabs, activeTabId } = get();
    const tab = tabs.find((item) => item.id === activeTabId)!;
    const accepted = new Set(tab.acceptedConflictIds);
    accepted.add(conflictId);
    const acceptedConflictIds = [...accepted];
    set({ tabs: updateTab(tabs, activeTabId, { acceptedConflictIds }) });
    if (!tab.cyclePreview) return;
    await get().previewCycle({ cycleDate: tab.cyclePreview.cycleDate, acceptedConflictIds });
  },

  resetTab: () => {
    const { tabs, activeTabId } = get();
    const tab = tabs.find((item) => item.id === activeTabId)!;
    invalidateTabRequests(activeTabId);
    set({ tabs: updateTab(tabs, activeTabId, makeTab(tab.id, tab.label)) });
  },

  resetAll: () => {
    for (const tab of get().tabs) invalidateTabRequests(tab.id);
    set({ tabs: [makeTab('tab-1', 'Tab 1')], activeTabId: 'tab-1' });
  },
}));
