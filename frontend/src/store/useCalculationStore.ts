import { create } from 'zustand';
import { uploadStaggerFile } from '../api/client';
import type { StaggerResult, StaggerTrace } from '../types/api';

export interface CalculationCycleState {
  id: string;
  name: string;
  uploadedFiles: File[];
  repeatedFile: File | null;
  isLoading: boolean;
  error: string | null;
  warnings: string[];
  results: StaggerResult[];
  traces: StaggerTrace[];
  detailTab: number;
  selectedResultId: string | null;
}

interface CalculationStoreState {
  cycles: CalculationCycleState[];
  activeCycleId: string;
  setUploadedFile: (file: File) => void;
  removeUploadedFile: (name: string) => void;
  setRepeatedFile: (file: File | null) => void;
  createCycle: () => void;
  closeCycle: (id: string) => void;
  setActiveCycle: (id: string) => void;
  setDetailTab: (tab: number) => void;
  setSelectedResult: (resultId: string | null) => void;
  analyze: () => Promise<void>;
  resetActiveCycle: () => void;
  reset: () => void;
}

const newCycle = (id: string, name: string): CalculationCycleState => ({
  id,
  name,
  uploadedFiles: [],
  repeatedFile: null,
  isLoading: false,
  error: null,
  warnings: [],
  results: [],
  traces: [],
  detailTab: 0,
  selectedResultId: null,
});

const createInitialState = () => ({
  cycles: [newCycle('cycle-1', 'Cycle A')],
  activeCycleId: 'cycle-1',
});

const updateActiveCycle = (
  state: CalculationStoreState,
  updater: (cycle: CalculationCycleState) => CalculationCycleState,
) => ({
  cycles: state.cycles.map((cycle) => (
    cycle.id === state.activeCycleId ? updater(cycle) : cycle
  )),
});

const updateCycleById = (
  state: CalculationStoreState,
  cycleId: string,
  updater: (cycle: CalculationCycleState) => CalculationCycleState,
) => ({
  cycles: state.cycles.map((cycle) => (
    cycle.id === cycleId ? updater(cycle) : cycle
  )),
});

export const useCalculationStore = create<CalculationStoreState>((set, get) => ({
  ...createInitialState(),

  setUploadedFile: (file) => {
    set((state) => updateActiveCycle(state, (cycle) => ({
      ...cycle,
      uploadedFiles: [file],
      error: null,
      warnings: [],
      results: [],
      traces: [],
      selectedResultId: null,
    })));
  },

  removeUploadedFile: (name) => {
    set((state) => updateActiveCycle(state, (cycle) => ({
      ...cycle,
      uploadedFiles: cycle.uploadedFiles.filter((file) => file.name !== name),
      error: null,
      warnings: [],
      results: [],
      traces: [],
      detailTab: 0,
      selectedResultId: null,
    })));
  },

  setRepeatedFile: (file) => {
    set((state) => updateActiveCycle(state, (cycle) => ({
      ...cycle,
      repeatedFile: file,
      error: null,
      warnings: [],
      results: [],
      traces: [],
      selectedResultId: null,
    })));
  },

  createCycle: () => {
    set((state) => {
      const nextIndex = state.cycles.length + 1;
      const id = `cycle-${nextIndex}`;
      return {
        cycles: [...state.cycles, newCycle(id, `Cycle ${String.fromCharCode(64 + nextIndex)}`)],
        activeCycleId: id,
      };
    });
  },

  closeCycle: (id) => {
    set((state) => {
      if (state.cycles.length === 1) {
        return state;
      }
      const nextCycles = state.cycles.filter((cycle) => cycle.id !== id);
      return {
        cycles: nextCycles,
        activeCycleId: state.activeCycleId === id ? nextCycles[0].id : state.activeCycleId,
      };
    });
  },

  setActiveCycle: (id) => set({ activeCycleId: id }),

  setDetailTab: (tab) => {
    set((state) => updateActiveCycle(state, (cycle) => ({ ...cycle, detailTab: tab })));
  },

  setSelectedResult: (resultId) => {
    set((state) => updateActiveCycle(state, (cycle) => ({ ...cycle, selectedResultId: resultId })));
  },

  analyze: async () => {
    const { cycles, activeCycleId } = get();
    const activeCycle = cycles.find((cycle) => cycle.id === activeCycleId);
    if (!activeCycle || activeCycle.uploadedFiles.length === 0) {
      return;
    }
    const targetCycleId = activeCycle.id;

    set((state) => updateCycleById(state, targetCycleId, (cycle) => ({
      ...cycle,
      isLoading: true,
      error: null,
      warnings: [],
    })));

    try {
      const response = await uploadStaggerFile(
        activeCycle.uploadedFiles[0],
        activeCycle.repeatedFile ?? null,
      );
      const resultsWithSpanCalculations = response.results.map((result, index) => ({
        ...result,
        span_results: response.traces[index]?.spans,
      }));

      set((state) => updateCycleById(state, targetCycleId, (cycle) => ({
        ...cycle,
        results: resultsWithSpanCalculations,
        traces: response.traces,
        warnings: response.warnings ?? [],
        isLoading: false,
        selectedResultId: response.results[0]?.id ?? null,
      })));
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      const errorMessage = Array.isArray(detail)
        ? detail.map((item: any) => item.msg ?? JSON.stringify(item)).join('; ')
        : (typeof detail === 'string' ? detail : error.message) || 'Analysis failed';

      set((state) => updateCycleById(state, targetCycleId, (cycle) => ({
        ...cycle,
        error: errorMessage,
        isLoading: false,
      })));
      throw error;
    }
  },

  resetActiveCycle: () => {
    const { cycles, activeCycleId } = get();
    const activeCycle = cycles.find((cycle) => cycle.id === activeCycleId);
    if (!activeCycle) {
      return;
    }

    set((state) => updateCycleById(
      state,
      activeCycleId,
      () => newCycle(activeCycle.id, activeCycle.name),
    ));
  },

  reset: () => set(createInitialState()),
}));

export default useCalculationStore;
