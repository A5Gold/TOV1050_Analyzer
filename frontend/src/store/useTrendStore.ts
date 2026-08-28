import { create } from 'zustand';
import { uploadTrendFiles } from '../api/client';
import type { TrendResult } from '../types/api';

export interface TrendTab {
  id: string;
  label: string;
  uploadedFiles: File[];
  repeatedFile: File | null;
  isLoading: boolean;
  error: string | null;
  trendResults: TrendResult[];
  selectedResult: TrendResult | null;
  hasAnalyzed: boolean;
}

interface TrendStoreState {
  tabs: TrendTab[];
  activeTabId: string;
  addTab: () => void;
  closeTab: (id: string) => void;
  setActiveTab: (id: string) => void;
  addFile: (file: File) => void;
  removeFile: (name: string) => void;
  setRepeatedFile: (file: File | null) => void;
  setSelectedResult: (result: TrendResult | null) => void;
  analyze: () => Promise<void>;
  resetTab: () => void;
}

const makeTab = (id: string, label: string): TrendTab => ({
  id,
  label,
  uploadedFiles: [],
  repeatedFile: null,
  isLoading: false,
  error: null,
  trendResults: [],
  selectedResult: null,
  hasAnalyzed: false,
});

const updateActive = (tabs: TrendTab[], activeTabId: string, patch: Partial<TrendTab>): TrendTab[] =>
  tabs.map((t) => (t.id === activeTabId ? { ...t, ...patch } : t));

const inferLineFromFiles = (files: File[]): 'EAL' | 'TML' => {
  const names = files.map((file) => file.name.toUpperCase());
  const hasTml = names.some((name) => /(^|_)TML(_|$)/.test(name));
  const hasEal = names.some((name) => /(^|_)EAL(_|$)/.test(name));
  return hasTml && !hasEal ? 'TML' : 'EAL';
};

export const useTrendStore = create<TrendStoreState>((set, get) => ({
  tabs: [makeTab('tab-1', 'Tab 1')],
  activeTabId: 'tab-1',

  addTab: () => {
    const { tabs } = get();
    if (tabs.length >= 6) return;
    const n = tabs.length + 1;
    const id = crypto.randomUUID();
    const tab = makeTab(id, `Tab ${n}`);
    set({ tabs: [...tabs, tab], activeTabId: id });
  },

  closeTab: (id) => {
    const { tabs, activeTabId } = get();
    if (tabs.length <= 1) return;
    const idx = tabs.findIndex((t) => t.id === id);
    const next = tabs.filter((t) => t.id !== id);
    let newActive = activeTabId;
    if (activeTabId === id) {
      newActive = next[Math.max(0, idx - 1)].id;
    }
    set({ tabs: next, activeTabId: newActive });
  },

  setActiveTab: (id) => set({ activeTabId: id }),

  addFile: (file) => {
    const { tabs, activeTabId } = get();
    set({ tabs: updateActive(tabs, activeTabId, {
      uploadedFiles: [...tabs.find(t => t.id === activeTabId)!.uploadedFiles.filter(f => f.name !== file.name), file],
      hasAnalyzed: false,
      trendResults: [],
      selectedResult: null,
      error: null,
    }) });
  },

  removeFile: (name) => {
    const { tabs, activeTabId } = get();
    const tab = tabs.find(t => t.id === activeTabId)!;
    set({ tabs: updateActive(tabs, activeTabId, {
      uploadedFiles: tab.uploadedFiles.filter(f => f.name !== name),
      hasAnalyzed: false,
      trendResults: [],
      selectedResult: null,
      error: null,
    }) });
  },

  setRepeatedFile: (file) => {
    const { tabs, activeTabId } = get();
    set({ tabs: updateActive(tabs, activeTabId, {
      repeatedFile: file,
      hasAnalyzed: false,
      trendResults: [],
      selectedResult: null,
      error: null,
    }) });
  },

  setSelectedResult: (result) => {
    const { tabs, activeTabId } = get();
    set({ tabs: updateActive(tabs, activeTabId, { selectedResult: result }) });
  },

  analyze: async () => {
    const { tabs, activeTabId } = get();
    const tab = tabs.find(t => t.id === activeTabId)!;
    if (!tab.uploadedFiles.length) return;
    const tabId = activeTabId;
    set({ tabs: updateActive(tabs, tabId, { isLoading: true, error: null }) });
    try {
      const line = inferLineFromFiles([
        ...tab.uploadedFiles,
        ...(tab.repeatedFile ? [tab.repeatedFile] : []),
      ]);
      const res = await uploadTrendFiles(tab.uploadedFiles, tab.repeatedFile, line);
      const { tabs: t2 } = get();
      set({
        tabs: updateActive(t2, tabId, {
          trendResults: res.trend_results,
          selectedResult: null,
          hasAnalyzed: true,
          isLoading: false,
        }),
      });
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d: any) => d.msg ?? JSON.stringify(d)).join('; ')
        : (typeof detail === 'string' ? detail : err.message) || 'Analysis failed';
      const { tabs: t2 } = get();
      set({ tabs: updateActive(t2, tabId, { error: msg, hasAnalyzed: false, isLoading: false }) });
    }
  },

  resetTab: () => {
    const { tabs, activeTabId } = get();
    const tab = tabs.find(t => t.id === activeTabId)!;
    set({ tabs: updateActive(tabs, activeTabId, makeTab(tab.id, tab.label)) });
  },
}));
