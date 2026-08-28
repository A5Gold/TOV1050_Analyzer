import { beforeEach, describe, expect, it, vi } from 'vitest';

const { analyzeSpy } = vi.hoisted(() => ({ analyzeSpy: vi.fn() }));

vi.mock('../../api/client', () => ({ analyzeVersionDifference: analyzeSpy }));

import { useVersionDifferenceStore } from '../useVersionDifferenceStore';

const responseFor = (latestFile: string) => ({
  status: 'ready',
  latest_file: latestFile,
  comparisons: [],
} as const);

describe('useVersionDifferenceStore', () => {
  beforeEach(() => {
    analyzeSpy.mockReset();
    useVersionDifferenceStore.getState().reset();
  });

  it('initializes every comparison tab with the five fixed cycle roles', () => {
    expect(Object.keys(useVersionDifferenceStore.getState().tabs[0].files)).toEqual([
      'latest',
      'previous1',
      'previous2',
      'previous3',
      'previous4',
    ]);
    expect(useVersionDifferenceStore.getState().tabs[0].files).toEqual({
      latest: null,
      previous1: null,
      previous2: null,
      previous3: null,
      previous4: null,
    });
  });

  it('clears stale response and error when Previous 3 or Previous 4 changes', () => {
    const previous3 = new File(['previous-3'], 'previous-3.xlsx');
    const previous4 = new File(['previous-4'], 'previous-4.xlsx');
    useVersionDifferenceStore.setState(state => ({
      tabs: state.tabs.map(tab => ({
        ...tab,
        response: responseFor('stale.xlsx'),
        error: 'stale error',
      })),
    }));

    useVersionDifferenceStore.getState().setFile('previous3', previous3);
    let tab = useVersionDifferenceStore.getState().tabs[0];
    expect(tab.files.previous3).toBe(previous3);
    expect(tab.response).toBeUndefined();
    expect(tab.error).toBeNull();

    useVersionDifferenceStore.setState(state => ({
      tabs: state.tabs.map(current => ({
        ...current,
        response: responseFor('stale-again.xlsx'),
        error: 'stale again',
      })),
    }));
    useVersionDifferenceStore.getState().setFile('previous4', previous4);
    useVersionDifferenceStore.getState().setFile('previous4', null);
    tab = useVersionDifferenceStore.getState().tabs[0];
    expect(tab.files.previous4).toBeNull();
    expect(tab.response).toBeUndefined();
    expect(tab.error).toBeNull();
  });

  it('requires only Latest and Previous 1 and snapshots all optional roles', async () => {
    analyzeSpy.mockResolvedValue(responseFor('latest.xlsx'));
    const latest = new File(['latest'], 'latest.xlsx');
    const previous1 = new File(['previous-1'], 'previous-1.xlsx');
    const previous3 = new File(['previous-3'], 'previous-3.xlsx');
    const previous4 = new File(['previous-4'], 'previous-4.xlsx');

    useVersionDifferenceStore.getState().setFile('latest', latest);
    useVersionDifferenceStore.getState().setFile('previous3', previous3);
    useVersionDifferenceStore.getState().setFile('previous4', previous4);
    await useVersionDifferenceStore.getState().compareActive();
    expect(analyzeSpy).not.toHaveBeenCalled();

    useVersionDifferenceStore.getState().setFile('previous1', previous1);
    await useVersionDifferenceStore.getState().compareActive();

    expect(analyzeSpy).toHaveBeenCalledWith(
      latest,
      previous1,
      null,
      previous3,
      previous4,
    );
  });

  it('isolates concurrent requests by their originating tab', async () => {
    let resolveFirst: (value: ReturnType<typeof responseFor>) => void = () => undefined;
    let resolveSecond: (value: ReturnType<typeof responseFor>) => void = () => undefined;
    analyzeSpy
      .mockImplementationOnce(() => new Promise(resolve => { resolveFirst = resolve; }))
      .mockImplementationOnce(() => new Promise(resolve => { resolveSecond = resolve; }));

    const firstLatest = new File(['first'], 'first.xlsx');
    useVersionDifferenceStore.getState().setFile('latest', firstLatest);
    useVersionDifferenceStore.getState().setFile('previous1', new File(['previous'], 'first-previous.xlsx'));
    const firstRequest = useVersionDifferenceStore.getState().compareActive();

    useVersionDifferenceStore.getState().addTab();
    const secondTabId = useVersionDifferenceStore.getState().activeTabId;
    const secondLatest = new File(['second'], 'second.xlsx');
    useVersionDifferenceStore.getState().setFile('latest', secondLatest);
    useVersionDifferenceStore.getState().setFile('previous1', new File(['previous'], 'second-previous.xlsx'));
    const secondRequest = useVersionDifferenceStore.getState().compareActive();

    resolveSecond(responseFor('second.xlsx'));
    await secondRequest;
    resolveFirst(responseFor('first.xlsx'));
    await firstRequest;

    const state = useVersionDifferenceStore.getState();
    expect(state.tabs.find(tab => tab.id === 'version-difference-1')?.response?.latest_file).toBe('first.xlsx');
    expect(state.tabs.find(tab => tab.id === secondTabId)?.response?.latest_file).toBe('second.xlsx');
    expect(state.tabs.every(tab => !tab.loading)).toBe(true);
  });

  it('ignores a response when its loading tab has been closed', async () => {
    let resolveComparison: (value: ReturnType<typeof responseFor>) => void = () => undefined;
    analyzeSpy.mockImplementation(() => new Promise(resolve => { resolveComparison = resolve; }));

    useVersionDifferenceStore.getState().addTab();
    const loadingTabId = useVersionDifferenceStore.getState().activeTabId;
    useVersionDifferenceStore.getState().setFile('latest', new File(['latest'], 'closed.xlsx'));
    useVersionDifferenceStore.getState().setFile('previous1', new File(['previous'], 'previous.xlsx'));
    const request = useVersionDifferenceStore.getState().compareActive();
    useVersionDifferenceStore.getState().closeTab(loadingTabId);

    resolveComparison(responseFor('closed.xlsx'));
    await request;

    expect(useVersionDifferenceStore.getState().tabs.some(tab => tab.id === loadingTabId)).toBe(false);
    expect(useVersionDifferenceStore.getState().tabs).toHaveLength(1);
  });
});
