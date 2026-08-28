import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { MockedFunction } from 'vitest';

vi.mock('../../api/client', () => ({
  uploadStaggerFile: vi.fn(),
}));

import { uploadStaggerFile } from '../../api/client';
import { useCalculationStore } from '../useCalculationStore';

const mockedUploadStaggerFile = uploadStaggerFile as MockedFunction<typeof uploadStaggerFile>;

describe('useCalculationStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useCalculationStore.getState().reset();
  });

  it('keeps results isolated between cycle tabs', async () => {
    mockedUploadStaggerFile.mockResolvedValueOnce({
      results: [
        {
          id: 'SG-001',
          line: 'EAL',
          track: 'up',
          exception_type: 'Stagger Left',
          max_location: 121000,
          chi: 121000,
          spt_a: 120900,
          spt_i: 121020,
          spt_b: 121120,
          span_ai: 120,
          span_ib: 100,
          k_eq: 1.32,
          overall_result: 'pass',
          trace_available: true,
          remark: ['Case A'],
        },
      ],
      traces: [
        {
          case_type: 'A',
          k_eq: 1.32,
          reference: { chi: 121000, spt_a: 120900, spt_i: 121020, spt_b: 121120 },
          spans: {},
        },
      ],
    });

    const fileA = new File(['cycle-a'], 'cycle-a.xlsx');
    const fileB = new File(['cycle-b'], 'cycle-b.xlsx');

    const store = useCalculationStore.getState();
    store.setUploadedFile(fileA);
    store.createCycle();

    const cycleBId = useCalculationStore.getState().activeCycleId;
    useCalculationStore.getState().setUploadedFile(fileB);

    useCalculationStore.getState().setActiveCycle('cycle-1');
    await useCalculationStore.getState().analyze();

    const state = useCalculationStore.getState();
    const cycleA = state.cycles.find((cycle) => cycle.id === 'cycle-1');
    const cycleB = state.cycles.find((cycle) => cycle.id === cycleBId);

    expect(cycleA?.results).toHaveLength(1);
    expect(cycleA?.traces).toHaveLength(1);
    expect(cycleB?.results).toHaveLength(0);
    expect(cycleB?.traces).toHaveLength(0);
    expect(mockedUploadStaggerFile).toHaveBeenCalledWith(fileA, null);
  });

  it('passes repeated report file for case B analysis', async () => {
    mockedUploadStaggerFile.mockResolvedValueOnce({
      results: [],
      traces: [],
    });

    const exceptionFile = new File(['exception'], 'exception-report.xlsx');
    const repeatedFile = new File(['repeated'], 'n_repeated.xlsx');

    useCalculationStore.getState().setUploadedFile(exceptionFile);
    useCalculationStore.getState().setRepeatedFile(repeatedFile);

    await useCalculationStore.getState().analyze();

    expect(mockedUploadStaggerFile).toHaveBeenCalledWith(exceptionFile, repeatedFile);
  });

  it('attaches trace span calculations to results for export', async () => {
    mockedUploadStaggerFile.mockResolvedValueOnce({
      results: [
        {
          id: 'SG-001',
          line: 'EAL',
          track: 'up',
          exception_type: 'Stagger Left',
          max_location: 113569,
          chi: 113569,
          overall_result: 'pass',
          trace_available: true,
          remark: ['Case B'],
        },
      ],
      traces: [
        {
          case_type: 'B',
          spans: {
            ai: { b: 27.7, s: 514.96, p: 49.51, allowable: -121.11, result: 'pass_short_circuit' },
            ib: { b: 33.36, s: 482.97, p: 65.51, allowable: 34.68, result: 'pass_short_circuit' },
          },
        },
      ],
    });

    useCalculationStore.getState().setUploadedFile(new File(['exception'], 'exception-report.xlsx'));

    await useCalculationStore.getState().analyze();

    expect(useCalculationStore.getState().cycles[0].results[0].span_results).toEqual({
      ai: { b: 27.7, s: 514.96, p: 49.51, allowable: -121.11, result: 'pass_short_circuit' },
      ib: { b: 33.36, s: 482.97, p: 65.51, allowable: 34.68, result: 'pass_short_circuit' },
    });
  });

  it('keeps async analyze results bound to the original cycle even after active tab changes', async () => {
    let resolveCycleA: ((value: any) => void) | null = null;
    let resolveCycleB: ((value: any) => void) | null = null;

    mockedUploadStaggerFile
      .mockImplementationOnce(() => new Promise((resolve) => { resolveCycleA = resolve; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveCycleB = resolve; }));

    const fileA = new File(['cycle-a'], 'cycle-a.xlsx');
    const fileB = new File(['cycle-b'], 'cycle-b.xlsx');

    useCalculationStore.getState().setUploadedFile(fileA);
    const analyzeCycleA = useCalculationStore.getState().analyze();

    useCalculationStore.getState().createCycle();
    const cycleBId = useCalculationStore.getState().activeCycleId;
    useCalculationStore.getState().setUploadedFile(fileB);
    const analyzeCycleB = useCalculationStore.getState().analyze();

    useCalculationStore.getState().setActiveCycle('cycle-1');

    resolveCycleB?.({
      results: [{ id: 'SG-B', line: 'EAL', track: 'up', exception_type: 'Stagger Left', max_location: 100, chi: 100, overall_result: 'pass', trace_available: true, remark: ['Case A'] }],
      traces: [{ case_type: 'A', spans: {} }],
      warnings: [],
    });
    await analyzeCycleB;

    resolveCycleA?.({
      results: [{ id: 'SG-A', line: 'EAL', track: 'up', exception_type: 'Stagger Right', max_location: 200, chi: 200, overall_result: 'fail', trace_available: true, remark: ['Case A'] }],
      traces: [{ case_type: 'A', spans: {} }],
      warnings: [],
    });
    await analyzeCycleA;

    const state = useCalculationStore.getState();
    const cycleA = state.cycles.find((cycle) => cycle.id === 'cycle-1');
    const cycleB = state.cycles.find((cycle) => cycle.id === cycleBId);

    expect(cycleA?.results.map((item) => item.id)).toEqual(['SG-A']);
    expect(cycleB?.results.map((item) => item.id)).toEqual(['SG-B']);
    expect(cycleA?.isLoading).toBe(false);
    expect(cycleB?.isLoading).toBe(false);
  });
});

it('preserves backend warnings for case B no-match responses', async () => {
  mockedUploadStaggerFile.mockResolvedValueOnce({
    results: [],
    traces: [],
    warnings: [
      'Case B requested, but no stagger IDs from the n_Repeated summary matched the Exception Report summary. No fallback to Case A was applied.',
      'No stagger results yet.',
    ],
  });

  const exceptionFile = new File(['exception'], 'exception-report.xlsx');
  const repeatedFile = new File(['repeated'], 'n_repeated.xlsx');

  useCalculationStore.getState().setUploadedFile(exceptionFile);
  useCalculationStore.getState().setRepeatedFile(repeatedFile);

  await useCalculationStore.getState().analyze();

  const cycle = useCalculationStore.getState().cycles[0];
  expect(cycle.results).toEqual([]);
  expect(cycle.warnings).toHaveLength(2);
  expect(cycle.warnings[0]).toContain('Case B requested');
});
