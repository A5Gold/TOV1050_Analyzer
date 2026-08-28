import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWearRecordsStore } from '../useWearRecordsStore';
import * as client from '../../api/client';

vi.mock('../../api/client', () => ({
  fetchWireWearWorkbench: vi.fn(),
  addManualWireWearRecords: vi.fn(),
  updateWireWearRecord: vi.fn(),
  deleteWireWearRecord: vi.fn(),
  exportWireWearRecords: vi.fn(),
  exportWireWearSyncPackage: vi.fn(),
  importWireWearSyncPackage: vi.fn(),
  applyWireWearChanges: vi.fn(),
  mapWireWearChangeSetResult: vi.fn((value) => value),
}));

describe('useWearRecordsStore workbench actions', () => {
  beforeEach(() => {
    useWearRecordsStore.getState().reset();
    vi.clearAllMocks();
  });

  it('loads workbench data for a selected line', async () => {
    vi.mocked(client.fetchWireWearWorkbench).mockResolvedValue({
      line_group: 'EAL',
      line_class: 'EAL',
      tension_lengths: ['X1'],
      history_rows: [{ cycle_date: '2026-02-01', values: { X1: 11 } }],
      latest_summary_rows: [{ metric: 'Latest Wear %', values: { X1: '12.00 %' } }],
      detail_records: { X1: [] },
      raw_records: [],
    });

    await useWearRecordsStore.getState().loadWorkbench({ line_group: 'EAL' });

    expect(client.fetchWireWearWorkbench).toHaveBeenCalledWith({ line_group: 'EAL' });
    expect(useWearRecordsStore.getState().workbench?.tension_lengths).toEqual(['X1']);
  });

  it('adds a manual record and reloads the selected line workbench', async () => {
    vi.mocked(client.addManualWireWearRecords).mockResolvedValue({
      saved_count: 1,
      updated_count: 0,
      duplicate_count: 0,
      duplicates: [],
    });
    vi.mocked(client.fetchWireWearWorkbench).mockResolvedValue({
      line_group: 'EAL',
      line_class: 'EAL',
      tension_lengths: ['X1'],
      history_rows: [],
      latest_summary_rows: [],
      detail_records: { X1: [] },
      raw_records: [],
    });

    await useWearRecordsStore.getState().addManualRecord({
      line_group: 'EAL',
      line_class: 'EAL',
      track: 'UP',
      section: 'Mainline',
      cycle_date: '2026-02-01',
      source_file_names: [],
      records: [{ tension_length: 'X1', from_m: 0, to_m: 10, avg_wear_min: 11, sd: 0, wear_percentage: 12 }],
    });

    expect(client.addManualWireWearRecords).toHaveBeenCalled();
    expect(client.fetchWireWearWorkbench).toHaveBeenCalledWith({
      line_group: 'EAL', line_class: 'EAL',
    });
  });

  it('exports and imports offline sync packages', async () => {
    const syncBlob = new Blob(['{"package_type":"tov640-wire-wear-sync"}'], { type: 'application/json' });
    vi.mocked(client.exportWireWearSyncPackage).mockResolvedValue(syncBlob);
    vi.mocked(client.importWireWearSyncPackage).mockResolvedValue({
      backup_path: 'C:\\data\\sync-backups\\analysis-sync-backup.db',
      inserted_count: 1,
      updated_count: 2,
      skipped_count: 3,
      skipped_rows: [],
      source_label: 'Laptop B',
      exported_at: '2026-07-08T03:00:00',
    });
    vi.mocked(client.fetchWireWearWorkbench).mockResolvedValue({
      line_group: 'EAL',
      line_class: 'EAL',
      tension_lengths: ['X1'],
      history_rows: [],
      latest_summary_rows: [],
      detail_records: { X1: [] },
      raw_records: [],
    });

    const exported = await useWearRecordsStore.getState().exportSyncPackage('Laptop A');
    await useWearRecordsStore.getState().importSyncPackage(new File(['{}'], 'sync.json'));

    expect(exported).toBe(syncBlob);
    expect(client.exportWireWearSyncPackage).toHaveBeenCalledWith('Laptop A');
    expect(client.importWireWearSyncPackage).toHaveBeenCalledWith(expect.any(File));
    expect(useWearRecordsStore.getState().lastSyncImportSummary?.inserted_count).toBe(1);
    expect(client.fetchWireWearWorkbench).toHaveBeenCalledWith({
      line_group: 'EAL', line_class: 'EAL',
    });
  });

  it('retains pending changes and commit errors when the atomic save fails', async () => {
    vi.mocked(client.applyWireWearChanges).mockRejectedValueOnce(new Error('conflict'));
    useWearRecordsStore.getState().hydrate({
      line_group: 'EAL', line_class: 'EAL', columns: [], matrix_rows: [], latest_summary: [], records: [], wire_wear_data_version: 3,
    });
    useWearRecordsStore.getState().stageDeleteRow('EAL', '2026-05-28');

    await useWearRecordsStore.getState().saveChanges();

    const state = useWearRecordsStore.getState();
    expect(state.pendingChanges).toEqual([{
      kind: 'delete_row', lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-05-28',
    }]);
    expect(state.commitErrors).toEqual(['conflict']);
    expect(state.hasPendingChanges).toBe(true);
  });
});
