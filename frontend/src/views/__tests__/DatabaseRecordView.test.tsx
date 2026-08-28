import React from 'react';
import { render, fireEvent, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import DatabaseRecordView from '../DatabaseRecordView';
import { useDatabaseStore } from '../../store/useDatabaseStore';
import * as XLSX from 'xlsx';

vi.mock('../../components/DatabaseRecord/RepeatedRecordTable', () => ({
  __esModule: true,
  default: () => <div data-testid="repeated-record-table" />,
}));

vi.mock('../../store/useDatabaseStore', () => ({
  useDatabaseStore: vi.fn(),
}));

vi.mock('xlsx', () => ({
  read: vi.fn(),
  utils: {
    sheet_to_json: vi.fn(),
  },
}));

type StoreState = {
  repeatedRecords: unknown[];
  repeatedRecordsLoading: boolean;
  repeatedRecordsTotal: number;
  repeatedRecordSectionCounts: Record<string, number>;
  repeatedRecordsError: string | null;
  fetchRepeatedRecords: ReturnType<typeof vi.fn>;
  exportRepeatedRecords: ReturnType<typeof vi.fn>;
  importRepeatedRecords: ReturnType<typeof vi.fn>;
  setRepeatedFilters: ReturnType<typeof vi.fn>;
  clearRepeatedFilters: ReturnType<typeof vi.fn>;
  fetchDistinctValues: ReturnType<typeof vi.fn>;
  isImporting: boolean;
  // Feature-002: Batch save state
  hasPendingChanges: boolean;
  pendingChanges: Map<number, unknown>;
  batchSaveChanges: ReturnType<typeof vi.fn>;
  discardChanges: ReturnType<typeof vi.fn>;
  isBatchSaving: boolean;
  // Phase 12 Bug 4: Line Counts
  lineCounts: Record<string, number>;
  lineCountsLoading: boolean;
  fetchLineCounts: ReturnType<typeof vi.fn>;
  // Phase 10.10-D: Queue change
  queueChange: ReturnType<typeof vi.fn>;
};

const createStoreState = (overrides: Partial<StoreState> = {}): StoreState => ({
  repeatedRecords: [],
  repeatedRecordsLoading: false,
  repeatedRecordsTotal: 0,
  repeatedRecordSectionCounts: {
    all: 0,
    mainline: 0,
    rac: 0,
    low_s1: 0,
    lmc: 0,
    unknown: 0,
  },
  repeatedRecordsError: null,
  fetchRepeatedRecords: vi.fn().mockResolvedValue(undefined),
  exportRepeatedRecords: vi.fn().mockResolvedValue(undefined),
  importRepeatedRecords: vi.fn().mockResolvedValue({ created_count: 1, updated_count: 0 }),
  setRepeatedFilters: vi.fn(),
  clearRepeatedFilters: vi.fn(),
  fetchDistinctValues: vi.fn().mockResolvedValue([]),
  isImporting: false,
  // Feature-002: Batch save state
  hasPendingChanges: false,
  pendingChanges: new Map(),
  batchSaveChanges: vi.fn().mockResolvedValue({ success: true, updated_count: 0, message: 'No changes' }),
  discardChanges: vi.fn(),
  isBatchSaving: false,
  // Phase 12 Bug 4: Line Counts
  lineCounts: { EAL: 0, TML: 0 },
  lineCountsLoading: false,
  fetchLineCounts: vi.fn().mockResolvedValue(undefined),
  // Phase 10.10-D: Queue change
  queueChange: vi.fn(),
  ...overrides,
});

describe('DatabaseRecordView', () => {
  const mockUseDatabaseStore = useDatabaseStore as unknown as ReturnType<typeof vi.fn>;
  const mockXlsxRead = XLSX.read as unknown as ReturnType<typeof vi.fn>;
  const mockSheetToJson = XLSX.utils.sheet_to_json as unknown as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('loads repeated records on mount', async () => {
    const storeState = createStoreState();
    mockUseDatabaseStore.mockReturnValue(storeState);

    render(<DatabaseRecordView />);

    await waitFor(() => {
      // Phase 10.10-C: FilterPanel now handles initial fetch with line + date_type
      expect(storeState.setRepeatedFilters).toHaveBeenCalledWith({ line: 'EAL', date_type: 'saved_at' });
      expect(storeState.fetchRepeatedRecords).toHaveBeenCalledWith({ line: 'EAL', date_type: 'saved_at' });
    });
  });

  test('distinguishes complete total from loaded rows and scopes batch edit to loaded rows', () => {
    const loadedRecords = [
      { record_id: 1, line: 'EAL', section: 'Mainline' },
      { record_id: 2, line: 'EAL', section: 'Mainline' },
    ];
    mockUseDatabaseStore.mockReturnValue(createStoreState({
      repeatedRecords: loadedRecords,
      repeatedRecordsTotal: 1826,
      repeatedRecordSectionCounts: {
        all: 1826,
        mainline: 1584,
        rac: 132,
        low_s1: 16,
        lmc: 94,
        unknown: 0,
      },
    }));

    render(<DatabaseRecordView />);

    expect(screen.getByText('1,826 total · 2 loaded')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Batch Edit Loaded (2)' })).toHaveAttribute(
      'title',
      'Batch edit the 2 records currently loaded in the table',
    );
  });

  test('imports Excel file and calls import API with defaults', async () => {
    const storeState = createStoreState();
    mockUseDatabaseStore.mockReturnValue(storeState);

    const records = [
      {
        exception_id: 'EX-001',
        line: 'EAL',
        track: 'UP',
        date_str: '20250101',
      },
    ];

    mockXlsxRead.mockReturnValue({
      SheetNames: ['Sheet1'],
      Sheets: { Sheet1: {} },
    });
    mockSheetToJson.mockReturnValue(records);

    const { container } = render(<DatabaseRecordView />);

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File([new Uint8Array([1, 2, 3])], 'records.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    Object.defineProperty(file, 'arrayBuffer', {
      value: vi.fn().mockResolvedValue(new ArrayBuffer(8)),
    });

    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(storeState.importRepeatedRecords).toHaveBeenCalledWith({
        records,
        line: 'EAL',
        track: 'UP',
        date_str: '20250101',
      });
    });
  });

  // Bug-002: Filter Reset Tests
  describe('Bug-002: Filter reset functionality', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    test('Clear All button resets all filters and fetches data', async () => {
      const storeState = createStoreState();
      mockUseDatabaseStore.mockReturnValue(storeState);

      const { getByText } = render(<DatabaseRecordView />);
      
      // Find and click Clear All button
      const clearButton = getByText('Clear All');
      fireEvent.click(clearButton);

      // Verify clearRepeatedFilters was called
      expect(storeState.clearRepeatedFilters).toHaveBeenCalled();
      
      expect(storeState.fetchRepeatedRecords).toHaveBeenCalledWith({ line: 'EAL', date_type: 'saved_at' });
    });

    test('selecting "All" option should clear that specific filter', async () => {
      const storeState = createStoreState();
      mockUseDatabaseStore.mockReturnValue(storeState);

      render(<DatabaseRecordView />);
      
      // Advance timer to trigger debounced fetch
      vi.advanceTimersByTime(400);
      
      // Phase 10.10-C: FilterPanel always includes line in filters
      expect(storeState.setRepeatedFilters).toHaveBeenLastCalledWith({ line: 'EAL', date_type: 'saved_at' });
    });

    test('filter state should not retain old values after clearing', async () => {
      const storeState = createStoreState();
      mockUseDatabaseStore.mockReturnValue(storeState);

      const { getByText } = render(<DatabaseRecordView />);

      // Simulate initial fetch
      vi.advanceTimersByTime(100);
      
      // Click Clear All
      const clearButton = getByText('Clear All');
      fireEvent.click(clearButton);

      const lastCall = storeState.fetchRepeatedRecords.mock.calls[
        storeState.fetchRepeatedRecords.mock.calls.length - 1
      ];
      expect(lastCall[0]).toEqual({ line: 'EAL', date_type: 'saved_at' });
    });
  });
});
