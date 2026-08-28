import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { MockedFunction } from 'vitest';

vi.mock('../../api/client', () => ({
  saveWireWearRecords: vi.fn(),
  fetchWireWearRecords: vi.fn(),
  fetchWireWearDashboard: vi.fn(),
  fetchWireWearProjection: vi.fn(),
  applyWireWearChanges: vi.fn(),
  previewWearRecordCandidates: vi.fn(),
  discoverHistoricalWearWorkbook: vi.fn(),
  previewHistoricalWearWorkbook: vi.fn(),
  mapWireWearChangeSetResult: vi.fn((value) => ({
    added: value.added,
    edited: value.edited,
    deleted: value.deleted,
    wireWearDataVersion: value.wire_wear_data_version,
  })),
  fetchWearCycleWorkbench: vi.fn(),
}));

import {
  fetchWireWearDashboard,
  fetchWireWearProjection,
  fetchWireWearRecords,
  saveWireWearRecords,
} from '../../api/client';
import { useWearRecordsStore } from '../useWearRecordsStore';
import {
  applyWireWearChanges,
  discoverHistoricalWearWorkbook,
  fetchWearCycleWorkbench,
  previewHistoricalWearWorkbook,
  previewWearRecordCandidates,
} from '../../api/client';

const cycleWorkbench = {
  line_group: 'EAL' as const,
  line_class: 'EAL' as const,
  columns: [],
  matrix_rows: [{ cycle_date: '2026-05-28', values: { TL1: 4, TL2: 8 } }],
  latest_summary: [],
  records: [],
  wire_wear_data_version: 3,
};

const mockedSave = saveWireWearRecords as MockedFunction<typeof saveWireWearRecords>;
const mockedFetchRecords = fetchWireWearRecords as MockedFunction<typeof fetchWireWearRecords>;
const mockedFetchDashboard = fetchWireWearDashboard as MockedFunction<typeof fetchWireWearDashboard>;
const mockedFetchProjection = fetchWireWearProjection as MockedFunction<typeof fetchWireWearProjection>;

describe('useWearRecordsStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useWearRecordsStore.getState().reset();
  });

  it('stores duplicate conflict for overwrite confirmation', async () => {
    mockedSave.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { detail: { duplicate_count: 1, duplicates: [{ tension_length: 'H46' }] } },
      },
    });

    await useWearRecordsStore.getState().saveAnalysisResults({
      line_group: 'EAL',
      line_class: 'LMC',
      track: 'UP',
      section: 'LMC',
      cycle_date: '2026-02-01',
      source_file_names: ['cycle.xlsx'],
      records: [],
    });

    expect(useWearRecordsStore.getState().duplicateConflict?.duplicate_count).toBe(1);
  });

  it('loads records dashboard and projection', async () => {
    mockedFetchRecords.mockResolvedValueOnce({ records: [] });
    mockedFetchDashboard.mockResolvedValueOnce({
      line_groups: {
        EAL: { top_max_rate: [], top_min_rate: [], top_current_wear: [] },
        TML: { top_max_rate: [], top_min_rate: [], top_current_wear: [] },
      },
    });
    mockedFetchProjection.mockResolvedValueOnce({
      thresholdMm: 10.2,
      thresholdPercentage: 20,
      horizonYears: 30,
      lineGroups: {
        EAL: { yearBuckets: [], alreadyAtThreshold: [], insufficientData: [], nonPositiveRate: [] },
        TML: { yearBuckets: [], alreadyAtThreshold: [], insufficientData: [], nonPositiveRate: [] },
      },
    });

    await useWearRecordsStore.getState().loadProjection(9.1);

    expect(mockedFetchProjection).toHaveBeenCalledWith(9.1);
  });

  it('preflights all analysis batches before saving any records', async () => {
    mockedSave
      .mockResolvedValueOnce({ saved_count: 0, updated_count: 0, duplicate_count: 0, duplicates: [] })
      .mockRejectedValueOnce({
        response: {
          status: 409,
          data: { detail: { duplicate_count: 1, duplicates: [{ tension_length: 'H02' }] } },
        },
      });

    await useWearRecordsStore.getState().saveAnalysisBatches([
      {
        line_group: 'EAL',
        line_class: 'EAL',
        track: 'UP',
        section: 'Mainline',
        cycle_date: '2026-02-01',
        source_file_names: [],
        records: [{ tension_length: 'H01', from_m: 0, to_m: 50, avg_wear_min: 12, sd: 0, wear_percentage: 4 }],
      },
      {
        line_group: 'EAL',
        line_class: 'EAL',
        track: 'DN',
        section: 'Mainline',
        cycle_date: '2026-02-01',
        source_file_names: [],
        records: [{ tension_length: 'H02', from_m: 50, to_m: 100, avg_wear_min: 11, sd: 0, wear_percentage: 8 }],
      },
    ]);

    expect(mockedSave).toHaveBeenCalledTimes(2);
    expect(mockedSave).toHaveBeenNthCalledWith(1, expect.objectContaining({ track: 'UP' }), false, true);
    expect(mockedSave).toHaveBeenNthCalledWith(2, expect.objectContaining({ track: 'DN' }), false, true);
    expect(useWearRecordsStore.getState().duplicateConflict?.duplicate_count).toBe(1);
    expect(mockedFetchRecords).not.toHaveBeenCalled();
  });

  it('coalesces cell changes and derives the optimistic matrix without HTTP', () => {
    useWearRecordsStore.getState().hydrate(cycleWorkbench);
    const added = { lineGroup: 'EAL' as const, lineClass: 'EAL' as const, cycleDate: '2026-05-28', tensionLength: 'TL3' };
    const edited = { lineGroup: 'EAL' as const, lineClass: 'EAL' as const, cycleDate: '2026-05-28', tensionLength: 'TL1' };
    useWearRecordsStore.getState().stageAdd(added, 9);
    useWearRecordsStore.getState().stageEdit(added, 10);
    useWearRecordsStore.getState().stageEdit(edited, 5, 'v1');
    useWearRecordsStore.getState().stageDeleteCell(edited, 'v1');

    const state = useWearRecordsStore.getState();
    expect(state.pendingChanges).toEqual([
      { kind: 'add', key: added, avgWearMin: 10 },
      { kind: 'delete_cell', key: edited, expectedUpdatedAt: 'v1' },
    ]);
    expect(state.optimisticMatrixRows[0].values).toEqual({ TL2: 8, TL3: 10 });
    expect(state.changeSummary).toEqual({ added: 1, edited: 0, deletedCells: 1, deletedRows: 0 });
    expect(state.hasPendingChanges).toBe(true);
    expect(state.shouldBlockNavigation).toBe(true);
  });

  it('coalesces add-delete to a no-op and lets delete row supersede cell changes', () => {
    useWearRecordsStore.getState().hydrate(cycleWorkbench);
    const newKey = { lineGroup: 'EAL' as const, cycleDate: '2026-05-28', tensionLength: 'TL3' };
    useWearRecordsStore.getState().stageAdd(newKey, 9);
    useWearRecordsStore.getState().stageDeleteCell(newKey);
    expect(useWearRecordsStore.getState().pendingChanges).toEqual([]);

    useWearRecordsStore.getState().stageEdit(
      { lineGroup: 'EAL', cycleDate: '2026-05-28', tensionLength: 'TL1' }, 5, 'v1',
    );
    useWearRecordsStore.getState().stageDeleteRow('EAL', '2026-05-28');

    expect(useWearRecordsStore.getState().pendingChanges).toEqual([
      { kind: 'delete_row', lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-05-28' },
    ]);
  });

  it('preserves the focused tension length while reloading a full matrix', async () => {
    useWearRecordsStore.setState({ selectedTensionLength: 'H48' });
    vi.mocked(fetchWearCycleWorkbench).mockResolvedValueOnce({
      lineGroup: 'EAL',
      lineClass: 'EAL',
      columns: [],
      matrixRows: [],
      latestSummary: [],
      records: [],
      catalog: [],
      selectedTensionLength: null,
      summaryOnly: false,
      wireWearDataVersion: 3,
    });

    await useWearRecordsStore.getState().loadCycleWorkbench({
      lineGroup: 'EAL',
      lineClass: 'EAL',
      summaryOnly: false,
    });

    expect(useWearRecordsStore.getState().selectedTensionLength).toBe('H48');
  });

  it('keeps EAL and LMC staged keys isolated for the same date and tension length', () => {
    useWearRecordsStore.getState().hydrate(cycleWorkbench);
    useWearRecordsStore.getState().stageEdit(
      { lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-05-28', tensionLength: 'TL1' },
      11,
      'eal-v1',
    );
    useWearRecordsStore.getState().stageEdit(
      { lineGroup: 'EAL', lineClass: 'LMC', cycleDate: '2026-05-28', tensionLength: 'TL1' },
      9,
      'lmc-v1',
    );

    expect(useWearRecordsStore.getState().pendingChanges).toHaveLength(2);
    expect(useWearRecordsStore.getState().pendingChanges.map(change => (
      change.kind === 'delete_row' ? change.lineClass : change.key.lineClass
    ))).toEqual(['EAL', 'LMC']);
  });

  it('stages a candidate batch in one transition and ignores informational rows', () => {
    useWearRecordsStore.getState().hydrate(cycleWorkbench);
    let transitions = 0;
    const unsubscribe = useWearRecordsStore.subscribe(() => { transitions += 1; });

    const staged = useWearRecordsStore.getState().stageBatch({
      lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-05-28',
      wireWearDataVersion: 3,
      counts: { new: 1, update: 1, no_change: 1, duplicate: 1, error: 1 },
      candidates: [
        { status: 'new', key: { lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-05-28', tensionLength: 'TL3' }, avgWearMin: 9, track: 'UP', existingAvgWearMin: null, expectedUpdatedAt: null, sourceType: 'manual', sourceSheet: null, sourceRow: 1, sourceCell: 'B1', originalValue: 9, excluded: false, rowId: '1', issues: [] },
        { status: 'update', key: { lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-05-28', tensionLength: 'TL1' }, avgWearMin: 5, track: 'UP', existingAvgWearMin: 4, expectedUpdatedAt: 'v1', sourceType: 'manual', sourceSheet: null, sourceRow: 2, sourceCell: 'B2', originalValue: 5, excluded: false, rowId: '2', issues: [] },
        { status: 'no_change', key: { lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-05-28', tensionLength: 'TL2' }, avgWearMin: 8, track: 'UP', existingAvgWearMin: 8, expectedUpdatedAt: 'v2', sourceType: 'manual', sourceSheet: null, sourceRow: 3, sourceCell: 'B3', originalValue: 8, excluded: false, rowId: '3', issues: [] },
        { status: 'error', key: null, avgWearMin: null, track: null, existingAvgWearMin: null, expectedUpdatedAt: null, sourceType: 'manual', sourceSheet: null, sourceRow: 4, sourceCell: 'B4', originalValue: 'bad', excluded: true, rowId: '4', issues: [{ code: 'invalid', message: 'bad', field: 'avg_wear_min', cell: 'B4' }] },
      ],
    });
    unsubscribe();

    expect(staged).toBe(true);
    expect(transitions).toBe(1);
    expect(useWearRecordsStore.getState().pendingChanges).toEqual([
      { kind: 'add', key: { lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-05-28', tensionLength: 'TL3' }, avgWearMin: 9 },
      { kind: 'edit', key: { lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-05-28', tensionLength: 'TL1' }, avgWearMin: 5, expectedUpdatedAt: 'v1' },
    ]);
    expect(useWearRecordsStore.getState().optimisticMatrixRows[0].values).toEqual({ TL1: 5, TL2: 8, TL3: 9 });
  });

  it('rejects a stale candidate preview without changing pending operations', () => {
    useWearRecordsStore.getState().hydrate(cycleWorkbench);
    useWearRecordsStore.getState().stageAdd(
      { lineGroup: 'EAL', cycleDate: '2026-05-28', tensionLength: 'TL3' }, 9,
    );
    const before = useWearRecordsStore.getState().pendingChanges;

    const staged = useWearRecordsStore.getState().stageBatch({
      lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-05-28',
      wireWearDataVersion: 2,
      counts: { new: 1, update: 0, no_change: 0, duplicate: 0, error: 0 },
      candidates: [{ status: 'new', key: { lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-05-28', tensionLength: 'TL4' }, avgWearMin: 7, track: 'UP', existingAvgWearMin: null, expectedUpdatedAt: null, sourceType: 'manual', sourceSheet: null, sourceRow: 1, sourceCell: 'B1', originalValue: 7, excluded: false, rowId: '1', issues: [] }],
    });

    expect(staged).toBe(false);
    expect(useWearRecordsStore.getState().pendingChanges).toEqual(before);
    expect(useWearRecordsStore.getState().commitErrors).toEqual([
      'Candidate preview is stale. Refresh the preview before staging.',
    ]);
  });

  it('blocks unresolved candidate errors and keeps excluded errors informational', () => {
    useWearRecordsStore.getState().hydrate(cycleWorkbench);
    const errorCandidate = {
      status: 'error' as const, key: null, avgWearMin: null, track: null,
      existingAvgWearMin: null, expectedUpdatedAt: null, sourceType: 'manual',
      sourceSheet: null, sourceRow: 1, sourceCell: 'B1', originalValue: 'bad',
      excluded: false, rowId: '1',
      issues: [{ code: 'invalid', message: 'bad', field: 'avg_wear_min', cell: 'B1' }],
    };
    const preview = {
      lineGroup: 'EAL' as const, lineClass: 'EAL' as const, cycleDate: '2026-05-28',
      wireWearDataVersion: 3,
      counts: { new: 0, update: 0, no_change: 0, duplicate: 0, error: 1 },
      candidates: [errorCandidate],
    };

    expect(useWearRecordsStore.getState().stageBatch(preview)).toBe(false);
    expect(useWearRecordsStore.getState().pendingChanges).toEqual([]);
    expect(useWearRecordsStore.getState().commitErrors).toEqual([
      'Resolve or exclude candidate errors before staging.',
    ]);

    expect(useWearRecordsStore.getState().stageBatch({
      ...preview,
      candidates: [{ ...errorCandidate, excluded: true }],
    })).toBe(true);
    expect(useWearRecordsStore.getState().pendingChanges).toEqual([]);
    expect(useWearRecordsStore.getState().commitErrors).toEqual([]);
  });

  it('restores the committed snapshot when changes are discarded', () => {
    useWearRecordsStore.getState().hydrate(cycleWorkbench);
    useWearRecordsStore.getState().stageDeleteRow('EAL', '2026-05-28');
    expect(useWearRecordsStore.getState().optimisticMatrixRows).toEqual([]);

    useWearRecordsStore.getState().discardChanges();

    const state = useWearRecordsStore.getState();
    expect(state.optimisticMatrixRows).toEqual([
      { cycleDate: '2026-05-28', values: { TL1: 4, TL2: 8 } },
    ]);
    expect(state.cycleWorkbench).toEqual(state.committedSnapshot);
    expect(state.hasPendingChanges).toBe(false);
  });

  it('refreshes the committed cycle snapshot after saving staged changes', async () => {
    vi.mocked(applyWireWearChanges).mockResolvedValueOnce({ added: 0, edited: 1, deleted: 0, wire_wear_data_version: 4 });
    vi.mocked(fetchWearCycleWorkbench).mockResolvedValueOnce({
      lineGroup: 'EAL', lineClass: 'EAL', columns: [], matrixRows: [{ cycleDate: '2026-05-28', values: { TL1: 5 } }],
      latestSummary: [], records: [], catalog: [], wireWearDataVersion: 4,
    });
    useWearRecordsStore.getState().hydrate(cycleWorkbench);
    useWearRecordsStore.getState().stageEdit({ lineGroup: 'EAL', cycleDate: '2026-05-28', tensionLength: 'TL1' }, 5, 'v1');

    await useWearRecordsStore.getState().saveChanges();

    const state = useWearRecordsStore.getState();
    expect(fetchWearCycleWorkbench).toHaveBeenCalledWith({ lineGroup: 'EAL', lineClass: 'EAL' });
    expect(state.committedSnapshot?.matrixRows[0].values.TL1).toBe(5);
    expect(state.optimisticMatrixRows[0].values.TL1).toBe(5);
    expect(state.pendingChanges).toEqual([]);
  });

  it('does not retain resendable operations when refresh fails after a successful mutation', async () => {
    vi.mocked(applyWireWearChanges).mockResolvedValueOnce({ added: 0, edited: 1, deleted: 0, wire_wear_data_version: 4 });
    vi.mocked(fetchWearCycleWorkbench).mockRejectedValueOnce(new Error('reload failed'));
    useWearRecordsStore.getState().hydrate(cycleWorkbench);
    useWearRecordsStore.getState().stageEdit({ lineGroup: 'EAL', cycleDate: '2026-05-28', tensionLength: 'TL1' }, 5, 'v1');

    await useWearRecordsStore.getState().saveChanges();

    const state = useWearRecordsStore.getState();
    expect(applyWireWearChanges).toHaveBeenCalledTimes(1);
    expect(state.pendingChanges).toEqual([]);
    expect(state.hasPendingChanges).toBe(false);
    expect(state.commitErrors).toEqual(['Changes saved, but failed to reload workbench: reload failed']);
    expect(state.wireWearDataVersion).toBe(4);
  });

  it('stages an excluded workbook preview with backup provenance and saves it atomically', async () => {
    const candidate = {
      status: 'new' as const,
      key: {
        lineGroup: 'EAL' as const,
        lineClass: 'EAL' as const,
        cycleDate: '2024-01-01',
        tensionLength: 'TL3',
      },
      avgWearMin: 9,
      track: 'UP',
      existingAvgWearMin: null,
      expectedUpdatedAt: null,
      sourceType: 'workbook',
      sourceSheet: 'EAL',
      sourceRow: 2,
      sourceCell: 'C2',
      originalValue: 9,
      excluded: false,
      rowId: 'EAL:C2',
      issues: [],
    };
    useWearRecordsStore.getState().hydrate(cycleWorkbench);
    useWearRecordsStore.setState({
      historicalPreview: {
        sheets: [],
        selectedSheets: ['EAL'],
        wireWearDataVersion: 3,
        sheetSummaries: [],
        totals: { skipped: 0, new: 1, update: 0, no_change: 0, duplicate: 0, error: 1, total: 2 },
        candidates: [candidate],
        diagnostics: [{
          code: 'invalid_heading', message: 'Invalid heading', sheet: 'EAL', cell: 'D1', originalValue: '202401A',
        }],
      },
    });

    expect(useWearRecordsStore.getState().stageHistoricalPreview()).toBe(false);
    useWearRecordsStore.getState().setHistoricalErrorExcluded('diagnostic:0', true);
    expect(useWearRecordsStore.getState().stageHistoricalPreview()).toBe(true);
    expect(useWearRecordsStore.getState().pendingOrigin).toBe('workbook');

    vi.mocked(applyWireWearChanges).mockResolvedValueOnce({
      added: 1,
      edited: 0,
      deleted: 0,
      backup_path: 'C:/temp/backups/wear.db',
      wire_wear_data_version: 4,
    });
    vi.mocked(fetchWearCycleWorkbench).mockResolvedValueOnce({
      ...cycleWorkbench,
      matrixRows: cycleWorkbench.matrix_rows.map(row => ({ cycleDate: row.cycle_date, values: row.values })),
      lineGroup: 'EAL',
      lineClass: 'EAL',
      latestSummary: [],
      records: [],
      catalog: [],
      wireWearDataVersion: 4,
    });

    await useWearRecordsStore.getState().saveChanges();

    expect(applyWireWearChanges).toHaveBeenCalledWith(expect.objectContaining({ origin: 'workbook' }));
    expect(useWearRecordsStore.getState().lastBackupPath).toBe('C:/temp/backups/wear.db');
    expect(useWearRecordsStore.getState().pendingOrigin).toBe('manual');
    expect(useWearRecordsStore.getState().pendingChanges).toEqual([]);
  });

  it('owns manual and workbook preview lifecycle at the central store boundary', async () => {
    const manualPreview = {
      lineGroup: 'EAL' as const,
      lineClass: 'EAL' as const,
      cycleDate: '2026-05-28',
      wireWearDataVersion: 3,
      counts: { new: 0, update: 0, no_change: 0, duplicate: 0, error: 0 },
      candidates: [],
    };
    const discovery = {
      sheets: [{
        name: 'EAL', support: 'supported' as const, selectedByDefault: true, enabled: true, reasonCode: 'supported',
      }],
    };
    const historicalPreview = {
      ...discovery,
      selectedSheets: ['EAL'],
      wireWearDataVersion: 3,
      sheetSummaries: [],
      totals: { skipped: 0, new: 0, update: 0, no_change: 0, duplicate: 0, error: 2, total: 2 },
      candidates: [{
        status: 'error' as const,
        key: null,
        avgWearMin: null,
        track: null,
        existingAvgWearMin: null,
        expectedUpdatedAt: null,
        sourceType: 'workbook',
        sourceSheet: 'EAL',
        sourceRow: 2,
        sourceCell: 'C2',
        originalValue: 'bad',
        excluded: false,
        rowId: 'EAL:C2',
        issues: [{ code: 'invalid_value', message: 'Invalid value', field: 'avg_wear_min', cell: 'C2' }],
      }],
      diagnostics: [{
        code: 'invalid_heading', message: 'Invalid heading', sheet: 'EAL', cell: 'D1', originalValue: '202601A',
      }],
    };
    vi.mocked(previewWearRecordCandidates).mockResolvedValueOnce(manualPreview);
    vi.mocked(discoverHistoricalWearWorkbook).mockResolvedValueOnce(discovery);
    vi.mocked(previewHistoricalWearWorkbook).mockResolvedValueOnce(historicalPreview);
    const file = new File(['xlsx'], 'history.xlsx');

    await useWearRecordsStore.getState().previewCandidateRows({ lineClass: 'EAL', cycleDate: '2026-05-28', rows: [] });
    await useWearRecordsStore.getState().discoverHistoricalWorkbook(file);
    await useWearRecordsStore.getState().previewHistoricalWorkbook(file, ['EAL']);

    const state = useWearRecordsStore.getState();
    expect(state.candidatePreview).toBe(manualPreview);
    expect(state.historicalDiscovery).toEqual(discovery);
    expect(state.historicalPreview?.candidates[0].excluded).toBe(true);
    expect(state.historicalExcludedDiagnosticIds).toEqual(['diagnostic:0']);
    expect(state.previewError).toBeNull();
  });

  it('stages ten thousand workbook candidates without dropping rows', () => {
    useWearRecordsStore.getState().hydrate(cycleWorkbench);
    const candidates = Array.from({ length: 10_000 }, (_, index) => ({
      status: 'new' as const,
      key: {
        lineGroup: 'EAL' as const,
        lineClass: 'EAL' as const,
        cycleDate: '2026-06-01',
        tensionLength: `TL-${index}`,
      },
      avgWearMin: 10 + index / 100_000,
      track: 'UP',
      existingAvgWearMin: null,
      expectedUpdatedAt: null,
      sourceType: 'workbook',
      sourceSheet: 'EAL',
      sourceRow: index + 2,
      sourceCell: `C${index + 2}`,
      originalValue: 10 + index / 100_000,
      excluded: false,
      rowId: `EAL:C${index + 2}`,
      issues: [],
    }));

    expect(useWearRecordsStore.getState().stageBatch({
      lineGroup: 'EAL',
      lineClass: 'EAL',
      cycleDate: '2026-06-01',
      wireWearDataVersion: 3,
      counts: { new: 10_000, update: 0, no_change: 0, duplicate: 0, error: 0 },
      candidates,
    }, 'workbook')).toBe(true);

    const state = useWearRecordsStore.getState();
    expect(state.pendingChanges).toHaveLength(10_000);
    expect(state.changeSummary.added).toBe(10_000);
  });
});
