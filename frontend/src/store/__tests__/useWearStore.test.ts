import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { MockedFunction } from 'vitest';

vi.mock('../../api/client', () => ({
  uploadWearFiles: vi.fn(),
  previewWearCycle: vi.fn(),
  saveWearCycle: vi.fn(),
}));

import { previewWearCycle, saveWearCycle, uploadWearFiles } from '../../api/client';
import { useWearStore } from '../useWearStore';

const mockedUploadWearFiles = uploadWearFiles as MockedFunction<typeof uploadWearFiles>;
const mockedPreviewWearCycle = previewWearCycle as MockedFunction<typeof previewWearCycle>;
const mockedSaveWearCycle = saveWearCycle as MockedFunction<typeof saveWearCycle>;

describe('useWearStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useWearStore.getState().resetAll();
  });

  it('marks the tab as analyzed when wear analysis returns an empty result set', async () => {
    mockedUploadWearFiles.mockResolvedValueOnce({ date: '2026-01-16', wear_results: [] });

    useWearStore.getState().addFile(new File(['exception'], 'exception-report.xlsx'));
    await useWearStore.getState().analyze();

    const activeTab = useWearStore.getState().tabs[0];
    expect(activeTab.hasAnalyzed).toBe(true);
    expect(activeTab.isLoading).toBe(false);
    expect(activeTab.wearResults).toEqual([]);
    expect(activeTab.date).toBe('2026-01-16');
  });

  it('clears analyzed state when uploaded files change after an empty-result success', async () => {
    mockedUploadWearFiles.mockResolvedValueOnce({ date: '2026-01-16', wear_results: [] });

    useWearStore.getState().addFile(new File(['exception'], 'exception-report.xlsx'));
    await useWearStore.getState().analyze();
    useWearStore.getState().addFile(new File(['next'], 'next-report.xlsx'));

    const activeTab = useWearStore.getState().tabs[0];
    expect(activeTab.hasAnalyzed).toBe(false);
    expect(activeTab.wearResults).toEqual([]);
    expect(activeTab.error).toBeNull();
  });

  it('maps LMC line class to EAL line with LMC section during analysis', async () => {
    mockedUploadWearFiles.mockResolvedValueOnce({ date: '2026-01-16', wear_results: [] });

    useWearStore.getState().setLine('EAL');
    useWearStore.getState().setLineClass('LMC');
    useWearStore.getState().addFile(new File(['exception'], 'exception-report.xlsx'));
    await useWearStore.getState().analyze();

    expect(mockedUploadWearFiles).toHaveBeenCalledWith(
      expect.any(Array),
      'EAL',
      undefined,
      'LMC',
    );
  });

  it('re-analyzes with accepted conflicts and an editable cycle date', async () => {
    mockedUploadWearFiles.mockResolvedValueOnce({ date: '2026-05-28', wear_results: [] });
    useWearStore.getState().addFile(new File(['cycle'], 'cycle.xlsx'));
    useWearStore.getState().setCycleDate('2026-05-28');
    await useWearStore.getState().acceptConflict('conflict-28');

    await useWearStore.getState().analyze();

    expect(mockedUploadWearFiles).toHaveBeenCalledWith(
      expect.any(Array),
      expect.objectContaining({
        line: 'EAL',
        cycleDate: '2026-05-28',
        acceptedConflictIds: ['conflict-28'],
      }),
      undefined,
      undefined,
    );
  });

  it('retains the editable cycle date when a file is removed', async () => {
    useWearStore.getState().addFile(new File(['a'], 'a.xlsx'));
    useWearStore.getState().setCycleDate('2026-05-28');
    await useWearStore.getState().acceptConflict('conflict-28');

    useWearStore.getState().removeFile('a.xlsx');

    expect(useWearStore.getState().tabs[0].acceptedConflictIds).toEqual([]);
    expect(useWearStore.getState().tabs[0].date).toBe('2026-05-28');
  });

  it('reconciles accepted conflicts against the successful preview audit', async () => {
    mockedPreviewWearCycle.mockResolvedValueOnce({
      lineGroup: 'EAL', cycleDate: '2026-05-28', records: [], segments: [], unresolved: [], blockingReasons: [],
      conflicts: [{ conflictId: 'still-valid', measurementIdentity: 'TL1', sourceValues: [], selectedWearMin: 11, isAccepted: true, acceptedAt: null }],
      canSave: true, previewDigest: 'digest', expectedDataVersion: 3,
    });
    useWearStore.getState().addFile(new File(['a'], 'a.xlsx'));
    await useWearStore.getState().acceptConflict('still-valid');
    await useWearStore.getState().acceptConflict('stale');

    await useWearStore.getState().previewCycle();

    expect(useWearStore.getState().tabs[0].acceptedConflictIds).toEqual(['still-valid']);
  });

  it('formats structured complete-cycle validation errors for the UI', async () => {
    mockedPreviewWearCycle.mockRejectedValueOnce({
      response: {
        data: {
          detail: {
            blocking_reasons: ['segment_missing', 'unresolved_tension_length'],
            unresolved: ['file.xlsx: tension length 3 has metadata gap 0.1'],
          },
        },
      },
    });
    useWearStore.getState().addFile(new File(['cycle'], 'cycle.xlsx'));

    await useWearStore.getState().previewCycle();

    expect(useWearStore.getState().tabs[0].cycleError).toContain('segment_missing');
    expect(useWearStore.getState().tabs[0].cycleError).toContain('1 unresolved measurement');
    expect(typeof useWearStore.getState().tabs[0].cycleError).toBe('string');
  });

  it('reconciles accepted conflicts against a successful re-analysis audit', async () => {
    mockedUploadWearFiles.mockResolvedValueOnce({
      date: '2026-05-28', wear_results: [],
      conflicts: [{ conflict_id: 'still-valid' }],
    } as any);
    useWearStore.getState().addFile(new File(['a'], 'a.xlsx'));
    await useWearStore.getState().acceptConflict('still-valid');
    await useWearStore.getState().acceptConflict('stale');

    await useWearStore.getState().analyze();

    expect(useWearStore.getState().tabs[0].acceptedConflictIds).toEqual(['still-valid']);
  });

  it('preserves each completed cycle preview when switching calculation tabs', async () => {
    const firstPreview = {
      lineGroup: 'EAL', cycleDate: '2026-05-28', records: [], segments: [], unresolved: [], blockingReasons: [],
      conflicts: [], canSave: true, previewDigest: 'first', expectedDataVersion: 1,
    } as const;
    const secondPreview = { ...firstPreview, cycleDate: '2026-05-29', previewDigest: 'second' };
    mockedPreviewWearCycle.mockResolvedValueOnce(firstPreview).mockResolvedValueOnce(secondPreview);

    useWearStore.getState().addFile(new File(['first'], 'first.xlsx'));
    await useWearStore.getState().previewCycle();
    const firstTabId = useWearStore.getState().activeTabId;
    useWearStore.getState().addTab();
    const secondTabId = useWearStore.getState().activeTabId;
    useWearStore.getState().addFile(new File(['second'], 'second.xlsx'));
    await useWearStore.getState().previewCycle();

    useWearStore.getState().setActiveTab(firstTabId);
    expect(useWearStore.getState().tabs.find(tab => tab.id === firstTabId)?.cyclePreview?.previewDigest).toBe('first');
    expect(useWearStore.getState().tabs.find(tab => tab.id === secondTabId)?.cyclePreview?.previewDigest).toBe('second');
  });

  it('updates the originating tab when a preview finishes after a tab switch', async () => {
    let resolvePreview!: (preview: any) => void;
    mockedPreviewWearCycle.mockReturnValueOnce(new Promise(resolve => { resolvePreview = resolve; }));
    useWearStore.getState().addFile(new File(['first'], 'first.xlsx'));
    const firstTabId = useWearStore.getState().activeTabId;

    const pending = useWearStore.getState().previewCycle();
    useWearStore.getState().addTab();
    const secondTabId = useWearStore.getState().activeTabId;
    resolvePreview({
      lineGroup: 'EAL', cycleDate: '2026-05-28', records: [], segments: [], unresolved: [], blockingReasons: [],
      conflicts: [], canSave: true, previewDigest: 'origin', expectedDataVersion: 1,
    });
    await pending;

    expect(useWearStore.getState().activeTabId).toBe(secondTabId);
    expect(useWearStore.getState().tabs.find(tab => tab.id === firstTabId)?.cyclePreview?.previewDigest).toBe('origin');
    expect(useWearStore.getState().tabs.find(tab => tab.id === secondTabId)?.cyclePreview).toBeNull();
  });

  it('ignores a stale preview after the originating tab input changes', async () => {
    let resolvePreview!: (preview: any) => void;
    mockedPreviewWearCycle.mockReturnValueOnce(new Promise(resolve => { resolvePreview = resolve; }));
    useWearStore.getState().addFile(new File(['first'], 'first.xlsx'));

    const pending = useWearStore.getState().previewCycle();
    useWearStore.getState().setCycleDate('2026-05-30');
    resolvePreview({
      lineGroup: 'EAL', cycleDate: '2026-05-28', records: [], segments: [], unresolved: [], blockingReasons: [],
      conflicts: [], canSave: true, previewDigest: 'stale', expectedDataVersion: 1,
    });
    await pending;

    expect(useWearStore.getState().tabs[0].cyclePreview).toBeNull();
    expect(useWearStore.getState().tabs[0].date).toBe('2026-05-30');
  });

  it('preserves the last saved cycle when new input invalidates only the preview', () => {
    const tab = useWearStore.getState().tabs[0];
    const lastCycleSave = { cycleId: 42, cycleDate: '2026-05-28', lineGroup: 'EAL' } as any;
    useWearStore.setState({ tabs: [{ ...tab, lastCycleSave }] });

    useWearStore.getState().setCycleDate('2026-05-30');

    expect(useWearStore.getState().tabs[0].cyclePreview).toBeNull();
    expect(useWearStore.getState().tabs[0].lastCycleSave).toBe(lastCycleSave);
  });

  it('updates only the originating tab when a save finishes after a tab switch', async () => {
    let resolveSave!: (result: any) => void;
    mockedSaveWearCycle.mockReturnValueOnce(new Promise(resolve => { resolveSave = resolve; }));
    const firstTab = useWearStore.getState().tabs[0];
    const preview = {
      lineGroup: 'EAL', cycleDate: '2026-05-28', records: [], segments: [], unresolved: [], blockingReasons: [],
      conflicts: [], canSave: true, previewDigest: 'save-origin', expectedDataVersion: 1,
    } as const;
    useWearStore.setState({ tabs: [{
      ...firstTab,
      uploadedFiles: [new File(['first'], 'first.xlsx')],
      cyclePreview: preview,
      cyclePreviewFiles: [new File(['first'], 'first.xlsx')],
    }] });
    const firstTabId = useWearStore.getState().activeTabId;

    const pending = useWearStore.getState().saveCycle();
    useWearStore.getState().addTab();
    const secondTabId = useWearStore.getState().activeTabId;
    const result = { cycleId: 42, cycleDate: '2026-05-28', lineGroup: 'EAL' };
    resolveSave(result);
    await pending;

    const state = useWearStore.getState();
    expect(state.activeTabId).toBe(secondTabId);
    expect(state.tabs.find(tab => tab.id === firstTabId)?.lastCycleSave).toBe(result);
    expect(state.tabs.find(tab => tab.id === firstTabId)?.cyclePreview).toBeNull();
    expect(state.tabs.find(tab => tab.id === secondTabId)?.lastCycleSave).toBeNull();
  });

  it('keeps newer input state when an older save response returns', async () => {
    let resolveSave!: (result: any) => void;
    mockedSaveWearCycle.mockReturnValueOnce(new Promise(resolve => { resolveSave = resolve; }));
    const tab = useWearStore.getState().tabs[0];
    const preview = {
      lineGroup: 'EAL', cycleDate: '2026-05-28', records: [], segments: [], unresolved: [], blockingReasons: [],
      conflicts: [], canSave: true, previewDigest: 'old-preview', expectedDataVersion: 1,
    } as const;
    useWearStore.setState({ tabs: [{
      ...tab,
      uploadedFiles: [new File(['first'], 'first.xlsx')],
      cyclePreview: preview,
      cyclePreviewFiles: [new File(['first'], 'first.xlsx')],
    }] });

    const pending = useWearStore.getState().saveCycle();
    useWearStore.getState().setCycleDate('2026-05-30');
    const result = { cycleId: 42, cycleDate: '2026-05-28', lineGroup: 'EAL' };
    resolveSave(result);
    await pending;

    const current = useWearStore.getState().tabs[0];
    expect(current.date).toBe('2026-05-30');
    expect(current.cyclePreview).toBeNull();
    expect(current.lastCycleSave).toBe(result);
    expect(current.cycleSaveLoading).toBe(false);
  });

  it('ignores a save response after its originating tab is closed', async () => {
    let resolveSave!: (result: any) => void;
    mockedSaveWearCycle.mockReturnValueOnce(new Promise(resolve => { resolveSave = resolve; }));
    const firstTab = useWearStore.getState().tabs[0];
    useWearStore.setState({ tabs: [{
      ...firstTab,
      uploadedFiles: [new File(['first'], 'first.xlsx')],
      cyclePreview: {
        lineGroup: 'EAL', cycleDate: '2026-05-28', records: [], segments: [], unresolved: [], blockingReasons: [],
        conflicts: [], canSave: true, previewDigest: 'closing-tab', expectedDataVersion: 1,
      },
      cyclePreviewFiles: [new File(['first'], 'first.xlsx')],
    }] });
    const firstTabId = useWearStore.getState().activeTabId;
    useWearStore.getState().addTab();
    const secondTabId = useWearStore.getState().activeTabId;
    useWearStore.getState().setActiveTab(firstTabId);

    const pending = useWearStore.getState().saveCycle();
    useWearStore.getState().closeTab(firstTabId);
    resolveSave({ cycleId: 42, cycleDate: '2026-05-28', lineGroup: 'EAL' });
    await pending;

    const state = useWearStore.getState();
    expect(state.activeTabId).toBe(secondTabId);
    expect(state.tabs).toHaveLength(1);
    expect(state.tabs[0].lastCycleSave).toBeNull();
  });

  it('does not clear a newer preview when an older save completes', async () => {
    let resolveSave!: (result: any) => void;
    mockedSaveWearCycle.mockReturnValueOnce(new Promise(resolve => { resolveSave = resolve; }));
    const tab = useWearStore.getState().tabs[0];
    const file = new File(['first'], 'first.xlsx');
    useWearStore.setState({ tabs: [{
      ...tab,
      uploadedFiles: [file],
      cyclePreview: {
        lineGroup: 'EAL', cycleDate: '2026-05-28', records: [], segments: [], unresolved: [], blockingReasons: [],
        conflicts: [], canSave: true, previewDigest: 'old-preview', expectedDataVersion: 1,
      },
      cyclePreviewFiles: [file],
    }] });

    const pendingSave = useWearStore.getState().saveCycle();
    mockedPreviewWearCycle.mockResolvedValueOnce({
      lineGroup: 'EAL', cycleDate: '2026-05-29', records: [], segments: [], unresolved: [], blockingReasons: [],
      conflicts: [], canSave: true, previewDigest: 'new-preview', expectedDataVersion: 2,
    });
    await useWearStore.getState().previewCycle();
    const result = { cycleId: 42, cycleDate: '2026-05-28', lineGroup: 'EAL' };
    resolveSave(result);
    await pendingSave;

    const current = useWearStore.getState().tabs[0];
    expect(current.cyclePreview?.previewDigest).toBe('new-preview');
    expect(current.lastCycleSave).toBe(result);
    expect(current.cycleSaveLoading).toBe(false);
  });
});
