import { create } from 'zustand';
import { analyzeVersionDifference } from '../api/client';
import {
  VERSION_DIFFERENCE_CYCLES,
  createEmptyVersionDifferenceFiles,
  type VersionDifferenceFileRole,
  type VersionDifferenceFiles,
} from '../constants/versionDifferenceCycles';
import type { VersionDifferenceResponse } from '../types/api';

export type { VersionDifferenceFileRole } from '../constants/versionDifferenceCycles';

export interface VersionDifferenceTab {
  id: string;
  label: string;
  files: VersionDifferenceFiles;
  response?: VersionDifferenceResponse;
  loading: boolean;
  error: string | null;
}

interface VersionDifferenceStoreState {
  tabs: VersionDifferenceTab[];
  activeTabId: string;
  nextTabNumber: number;
  addTab: () => void;
  closeTab: (id: string) => void;
  setActiveTab: (id: string) => void;
  setFile: (role: VersionDifferenceFileRole, file: File | null) => void;
  setError: (message: string | null) => void;
  compareActive: () => Promise<void>;
  reset: () => void;
}

export const MAX_VERSION_DIFFERENCE_TABS = 6;

const makeTab = (id: string, tabNumber: number): VersionDifferenceTab => ({
  id,
  label: `Comparison ${tabNumber}`,
  files: createEmptyVersionDifferenceFiles(),
  response: undefined,
  loading: false,
  error: null,
});

const makeInitialState = () => ({
  tabs: [makeTab('version-difference-1', 1)],
  activeTabId: 'version-difference-1',
  nextTabNumber: 2,
});

const updateTab = (
  tabs: VersionDifferenceTab[],
  id: string,
  patch: Partial<VersionDifferenceTab>,
) => tabs.map(tab => tab.id === id ? { ...tab, ...patch } : tab);

const createTabId = () => (
  typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `version-difference-${Date.now()}-${Math.random().toString(36).slice(2)}`
);

export const useVersionDifferenceStore = create<VersionDifferenceStoreState>((set, get) => ({
  ...makeInitialState(),

  addTab: () => set(state => {
    if (state.tabs.length >= MAX_VERSION_DIFFERENCE_TABS) return state;
    const tab = makeTab(createTabId(), state.nextTabNumber);
    return {
      tabs: [...state.tabs, tab],
      activeTabId: tab.id,
      nextTabNumber: state.nextTabNumber + 1,
    };
  }),

  closeTab: id => set(state => {
    if (state.tabs.length <= 1) return state;
    const closingIndex = state.tabs.findIndex(tab => tab.id === id);
    if (closingIndex < 0) return state;
    const tabs = state.tabs.filter(tab => tab.id !== id);
    const activeTabId = state.activeTabId === id
      ? tabs[Math.min(closingIndex, tabs.length - 1)].id
      : state.activeTabId;
    return { tabs, activeTabId };
  }),

  setActiveTab: id => set(state => (
    state.tabs.some(tab => tab.id === id) ? { activeTabId: id } : state
  )),

  setFile: (role, file) => set(state => ({
    tabs: updateTab(state.tabs, state.activeTabId, {
      files: {
        ...state.tabs.find(tab => tab.id === state.activeTabId)!.files,
        [role]: file,
      },
      response: undefined,
      error: null,
    }),
  })),

  setError: message => set(state => ({
    tabs: updateTab(state.tabs, state.activeTabId, { error: message }),
  })),

  compareActive: async () => {
    const state = get();
    const tab = state.tabs.find(item => item.id === state.activeTabId);
    if (!tab?.files.latest || !tab.files.previous1 || tab.loading) return;

    const tabId = tab.id;
    const latest = tab.files.latest;
    const previous1 = tab.files.previous1;
    const files = { ...tab.files };
    const optionalFiles = VERSION_DIFFERENCE_CYCLES
      .filter(cycle => !cycle.required)
      .map(cycle => files[cycle.role]);
    const lastOptionalFileIndex = optionalFiles.reduce(
      (lastIndex, file, index) => file ? index : lastIndex,
      -1,
    );
    const requestOptionalFiles = optionalFiles.slice(
      0,
      Math.max(1, lastOptionalFileIndex + 1),
    ) as [File | null, (File | null)?, (File | null)?];
    set(current => ({
      tabs: updateTab(current.tabs, tabId, {
        loading: true,
        error: null,
        response: undefined,
      }),
    }));

    try {
      const response = await analyzeVersionDifference(latest, previous1, ...requestOptionalFiles);
      set(current => ({
        tabs: updateTab(current.tabs, tabId, { response, loading: false }),
      }));
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      set(current => ({
        tabs: updateTab(current.tabs, tabId, {
          error: typeof detail === 'string' ? detail : 'Version Difference analysis failed.',
          loading: false,
        }),
      }));
    }
  },

  reset: () => set(makeInitialState()),
}));
