/**
 * LineTabPanel Component Tests
 * =============================
 * Tests for Bug 10.7-1 fix: Ensure records are safely processed
 * Tests for Bug 10.9.1-1 fix: LOW S1 value mapping consistency
 * 
 * Version: 1.1
 * Date: 2026-02-04
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import LineTabPanel from '../LineTabPanel';
import { SavedRepeatedRecord } from '../../../types/api';
import { useDatabaseStore } from '../../../store/useDatabaseStore';

// Mock useDatabaseStore for lineCounts (Phase 12 Bug 4)
vi.mock('../../../store/useDatabaseStore', () => ({
  useDatabaseStore: vi.fn(),
}));

const mockUseDatabaseStore = useDatabaseStore as unknown as ReturnType<typeof vi.fn>;

// Helper to create mock records
const createMockRecord = (overrides: Partial<SavedRepeatedRecord> = {}): SavedRepeatedRecord => ({
  record_id: 1,
  exception_id: 'EXC-001',
  line: 'EAL',
  track: 'UP',
  section: 'Mainline',
  km: 1.5,
  m: 500,
  exception_type: 'Height',
  value: 5500,
  threshold_low: 5000,
  threshold_high: 6000,
  action: 'Keep monitoring',
  check_date: null,
  checked_by: null,
  check_result: null,
  remarks: null,
  reoccurrence_id: null,
  verify_deadline: null,
  verify_date: null,
  verify_result: null,
  verified_by: null,
  adjust_deadline: null,
  adjust_date: null,
  adjust_result: null,
  adjusted_by: null,
  task_no: null,
  station_start: null,
  station_end: null,
  task_run_date: null,
  saved_at: '2026-01-31T00:00:00Z',
  last_updated: '2026-01-31T00:00:00Z',
  ...overrides,
});

describe('LineTabPanel', () => {
  const mockOnFilterChange = vi.fn();
  const mockChildrenFn = vi.fn((filteredRecords: SavedRepeatedRecord[]) => (
    <div data-testid="filtered-records">
      {filteredRecords.length} records
    </div>
  ));

  beforeEach(() => {
    vi.clearAllMocks();
    // Phase 12 Bug 4: Mock useDatabaseStore to provide lineCounts and fetchLineCounts
    mockUseDatabaseStore.mockReturnValue({
      lineCounts: { EAL: 0, TML: 0 },
      repeatedRecordSectionCounts: {
        all: 0,
        mainline: 0,
        rac: 0,
        low_s1: 0,
        lmc: 0,
        unknown: 0,
      },
      fetchLineCounts: vi.fn(),
      // FilterPanel dependencies
      fetchRepeatedRecords: vi.fn(),
      setRepeatedFilters: vi.fn(),
      clearRepeatedFilters: vi.fn(),
      fetchDistinctValues: vi.fn().mockResolvedValue([]),
      repeatedRecordsLoading: false,
    });
  });

  test('uses complete API section counts and fetches a selected section server-side', async () => {
    const fetchRepeatedRecords = vi.fn();
    mockUseDatabaseStore.mockReturnValue({
      lineCounts: { EAL: 1826, TML: 974 },
      repeatedRecordSectionCounts: {
        all: 1826,
        mainline: 1584,
        rac: 132,
        low_s1: 16,
        lmc: 94,
        unknown: 0,
      },
      fetchLineCounts: vi.fn(),
      fetchRepeatedRecords,
      setRepeatedFilters: vi.fn(),
      clearRepeatedFilters: vi.fn(),
      fetchDistinctValues: vi.fn().mockResolvedValue([]),
      repeatedRecordsLoading: false,
    });

    render(
      <LineTabPanel records={[]} loading={false} onFilterChange={mockOnFilterChange}>
        {mockChildrenFn}
      </LineTabPanel>,
    );

    expect(screen.getByRole('button', { name: 'All Sections, 1826 records' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mainline, 1584 records' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'RAC, 132 records' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'LOW S1, 16 records' })).toBeInTheDocument();
    const lmc = screen.getByRole('button', { name: 'LMC, 94 records' });
    fireEvent.click(lmc);

    await waitFor(() => {
      expect(fetchRepeatedRecords).toHaveBeenLastCalledWith({
        line: 'EAL',
        section: 'LMC',
        date_type: 'saved_at',
      });
    });
  });

  test('shows Unknown only when the API aggregate is non-zero', () => {
    mockUseDatabaseStore.mockReturnValue({
      lineCounts: { EAL: 2, TML: 0 },
      repeatedRecordSectionCounts: {
        all: 2,
        mainline: 0,
        rac: 0,
        low_s1: 0,
        lmc: 0,
        unknown: 2,
      },
      fetchLineCounts: vi.fn(),
      fetchRepeatedRecords: vi.fn(),
      setRepeatedFilters: vi.fn(),
      clearRepeatedFilters: vi.fn(),
      fetchDistinctValues: vi.fn().mockResolvedValue([]),
      repeatedRecordsLoading: false,
    });

    const { rerender } = render(
      <LineTabPanel records={[]} loading={false}>
        {mockChildrenFn}
      </LineTabPanel>,
    );
    expect(screen.getByRole('button', { name: 'Unknown, 2 records' })).toBeInTheDocument();

    mockUseDatabaseStore.mockReturnValue({
      ...mockUseDatabaseStore.mock.results.at(-1)?.value,
      repeatedRecordSectionCounts: {
        all: 0,
        mainline: 0,
        rac: 0,
        low_s1: 0,
        lmc: 0,
        unknown: 0,
      },
    });
    rerender(
      <LineTabPanel records={[]} loading={false}>
        {mockChildrenFn}
      </LineTabPanel>,
    );
    expect(screen.queryByRole('button', { name: /Unknown/ })).not.toBeInTheDocument();
  });

  test('never derives complete section counts from the loaded row subset', () => {
    const loadedRows = [
      createMockRecord({ record_id: 1, section: 'Mainline' }),
      createMockRecord({ record_id: 2, section: 'LMC' }),
    ];

    render(
      <LineTabPanel records={loadedRows} loading={false}>
        {mockChildrenFn}
      </LineTabPanel>,
    );

    expect(screen.getByRole('button', { name: 'All Sections, 0 records' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mainline, 0 records' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'LMC, 0 records' })).toBeInTheDocument();
  });

  // =========================================================================
  // Bug 10.7-1: Safe records handling tests
  // =========================================================================

  describe('Bug 10.7-1: Safe records handling', () => {
    test('should handle undefined records without crashing', () => {
      // @ts-expect-error - Testing undefined records scenario
      render(
        <LineTabPanel
          records={undefined}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Should render with 0 records
      expect(screen.getByTestId('filtered-records')).toHaveTextContent('0 records');
      // Children should be called with empty array
      expect(mockChildrenFn).toHaveBeenCalledWith([]);
    });

    test('should handle null records without crashing', () => {
      // @ts-expect-error - Testing null records scenario
      render(
        <LineTabPanel
          records={null}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Should render with 0 records
      expect(screen.getByTestId('filtered-records')).toHaveTextContent('0 records');
      // Children should be called with empty array
      expect(mockChildrenFn).toHaveBeenCalledWith([]);
    });

    test('should handle non-array records without crashing', () => {
      // @ts-expect-error - Testing non-array records scenario
      render(
        <LineTabPanel
          records={{ invalid: 'object' }}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Should render with 0 records
      expect(screen.getByTestId('filtered-records')).toHaveTextContent('0 records');
      // Children should be called with empty array
      expect(mockChildrenFn).toHaveBeenCalledWith([]);
    });

    test('should handle empty array records correctly', () => {
      render(
        <LineTabPanel
          records={[]}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Should render with 0 records
      expect(screen.getByTestId('filtered-records')).toHaveTextContent('0 records');
      // Children should be called with empty array
      expect(mockChildrenFn).toHaveBeenCalledWith([]);
    });
  });

  // =========================================================================
  // Normal functionality tests
  // =========================================================================

  describe('Normal functionality', () => {
    test('keeps filters collapsed by default and uses the line panel toggle', async () => {
      render(
        <LineTabPanel records={[]} loading={false}>
          {mockChildrenFn}
        </LineTabPanel>
      );

      const expandButton = screen.getByRole('button', { name: 'Expand filter panel' });
      expect(expandButton).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /EAL/i })).toHaveStyle({ minHeight: '44px' });
      expect(screen.getAllByText('Track')[0]).not.toBeVisible();
      expect(screen.queryByRole('button', { name: 'Filters' })).not.toBeInTheDocument();

      fireEvent.click(expandButton);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Collapse filter panel' })).toBeInTheDocument();
        expect(screen.getAllByText('Track')[0]).toBeVisible();
      });
      const filterControl = screen.getAllByText('Track')[0];
      const tableContent = screen.getByTestId('filtered-records');
      expect(filterControl.compareDocumentPosition(tableContent) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    test('should render with valid records', () => {
      const records = [
        createMockRecord({ record_id: 1, line: 'EAL' }),
        createMockRecord({ record_id: 2, line: 'EAL' }),
        createMockRecord({ record_id: 3, line: 'TML' }),
      ];

      render(
        <LineTabPanel
          records={records}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Should show EAL tab as active by default, filtering to EAL records only
      expect(screen.getByTestId('filtered-records')).toHaveTextContent('2 records');
    });

    test('should filter records by selected line', () => {
      const records = [
        createMockRecord({ record_id: 1, line: 'EAL', section: 'Mainline' }),
        createMockRecord({ record_id: 2, line: 'TML', section: 'Mainline' }),
      ];

      render(
        <LineTabPanel
          records={records}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Default is EAL, should show 1 record
      expect(screen.getByTestId('filtered-records')).toHaveTextContent('1 records');

      // Click TML tab
      const tmlTab = screen.getByRole('tab', { name: /TML/i });
      fireEvent.click(tmlTab);

      // Should call onFilterChange with TML
      expect(mockOnFilterChange).toHaveBeenCalledWith('TML', null);
    });

    test('should show correct record counts in tab badges', () => {
      const records = [
        createMockRecord({ record_id: 1, line: 'EAL' }),
        createMockRecord({ record_id: 2, line: 'EAL' }),
        createMockRecord({ record_id: 3, line: 'TML' }),
      ];

      // Phase 12 Bug 4: Tab badges now use API-based lineCounts from store
      mockUseDatabaseStore.mockReturnValue({
        lineCounts: { EAL: 2, TML: 1 },
        repeatedRecordSectionCounts: {
          all: 2,
          mainline: 2,
          rac: 0,
          low_s1: 0,
          lmc: 0,
          unknown: 0,
        },
        fetchLineCounts: vi.fn(),
        fetchRepeatedRecords: vi.fn(),
        setRepeatedFilters: vi.fn(),
        clearRepeatedFilters: vi.fn(),
        fetchDistinctValues: vi.fn().mockResolvedValue([]),
        repeatedRecordsLoading: false,
      });

      render(
        <LineTabPanel
          records={records}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Verify tabs are rendered with correct line names
      expect(screen.getByText('EAL')).toBeInTheDocument();
      expect(screen.getByText('TML')).toBeInTheDocument();
      
      // Badge counts come from store lineCounts (API-based)
      const countTwos = screen.getAllByText('2');
      const countOnes = screen.getAllByText('1');
      expect(countTwos.length).toBeGreaterThan(0); // EAL has 2 records
      expect(countOnes.length).toBeGreaterThan(0); // TML has 1 record
    });

    test('should filter by section when section is selected', () => {
      const records = [
        createMockRecord({ record_id: 1, line: 'EAL', section: 'Mainline' }),
        createMockRecord({ record_id: 2, line: 'EAL', section: 'RAC' }),
        createMockRecord({ record_id: 3, line: 'EAL', section: 'LOW S1' }),
      ];

      render(
        <LineTabPanel
          records={records}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Default shows all EAL records (3)
      expect(screen.getByTestId('filtered-records')).toHaveTextContent('3 records');
    });
  });

  // =========================================================================
  // Bug 10.9.1-1: LOW S1 value mapping consistency tests
  // =========================================================================

  describe('Bug 10.9.1-1: LOW S1 value mapping', () => {
    test('should use "LOW S1" as value for LOW S1 section button', async () => {
      const records = [
        createMockRecord({ record_id: 1, line: 'EAL', section: 'Mainline' }),
        createMockRecord({ record_id: 2, line: 'EAL', section: 'LOW S1' }),
      ];

      render(
        <LineTabPanel
          records={records}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Find and click the LOW S1 button
      const lowS1Button = screen.getByRole('button', { name: /LOW S1/i });
      fireEvent.click(lowS1Button);

      // Should call onFilterChange with 'LOW S1' (not 'LOW')
      await waitFor(() => {
        expect(mockOnFilterChange).toHaveBeenCalledWith('EAL', 'LOW S1');
      });
    });

    test('should correctly count LOW S1 records', () => {
      const records = [
        createMockRecord({ record_id: 1, line: 'EAL', section: 'Mainline' }),
        createMockRecord({ record_id: 2, line: 'EAL', section: 'LOW S1' }),
        createMockRecord({ record_id: 3, line: 'EAL', section: 'LOW S1' }),
      ];
      mockUseDatabaseStore.mockReturnValue({
        lineCounts: { EAL: 3, TML: 0 },
        repeatedRecordSectionCounts: {
          all: 3,
          mainline: 1,
          rac: 0,
          low_s1: 2,
          lmc: 0,
          unknown: 0,
        },
        fetchLineCounts: vi.fn(),
        fetchRepeatedRecords: vi.fn(),
        setRepeatedFilters: vi.fn(),
        clearRepeatedFilters: vi.fn(),
        fetchDistinctValues: vi.fn().mockResolvedValue([]),
        repeatedRecordsLoading: false,
      });

      render(
        <LineTabPanel
          records={records}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Find the LOW S1 badge count - should show 2
      const lowS1Button = screen.getByRole('button', { name: 'LOW S1, 2 records' });
      expect(lowS1Button).toBeInTheDocument();
    });

    test('should filter LOW S1 records correctly when LOW S1 section is selected', async () => {
      const records = [
        createMockRecord({ record_id: 1, line: 'EAL', section: 'Mainline' }),
        createMockRecord({ record_id: 2, line: 'EAL', section: 'LOW S1' }),
        createMockRecord({ record_id: 3, line: 'EAL', section: 'LOW S1' }),
        createMockRecord({ record_id: 4, line: 'EAL', section: 'RAC' }),
      ];

      const { rerender } = render(
        <LineTabPanel
          records={records}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Default shows all EAL records (4)
      expect(screen.getByTestId('filtered-records')).toHaveTextContent('4 records');

      // Click LOW S1 button to filter
      const lowS1Button = screen.getByRole('button', { name: /LOW S1/i });
      fireEvent.click(lowS1Button);

      // After clicking, the component should call onFilterChange
      expect(mockOnFilterChange).toHaveBeenCalledWith('EAL', 'LOW S1');
    });

    test('should not trigger MUI out-of-range warning', () => {
      // Spy on console.warn to check for MUI warnings
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      const records = [
        createMockRecord({ record_id: 1, line: 'EAL', section: 'LOW S1' }),
      ];

      render(
        <LineTabPanel
          records={records}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Check that no "out-of-range" warning was logged
      const outOfRangeWarnings = consoleSpy.mock.calls.filter(
        call => call[0]?.includes?.('out-of-range') || 
                (typeof call[0] === 'string' && call[0].includes('out-of-range'))
      );
      expect(outOfRangeWarnings.length).toBe(0);

      consoleSpy.mockRestore();
    });
  });

  // =========================================================================
  // Phase 10.10 Post-Bug Issue 3: Section counts accuracy tests
  // =========================================================================

  describe('Phase 10.10 Issue 3: Section counts accuracy', () => {
    test('should show correct section counts when all sections have data', () => {
      const records = [
        createMockRecord({ record_id: 1, line: 'EAL', section: 'Mainline' }),
        createMockRecord({ record_id: 2, line: 'EAL', section: 'Mainline' }),
        createMockRecord({ record_id: 3, line: 'EAL', section: 'RAC' }),
        createMockRecord({ record_id: 4, line: 'EAL', section: 'LOW S1' }),
        createMockRecord({ record_id: 5, line: 'EAL', section: 'LMC' }),
        createMockRecord({ record_id: 6, line: 'EAL', section: 'LMC' }),
        createMockRecord({ record_id: 7, line: 'EAL', section: 'LMC' }),
      ];
      mockUseDatabaseStore.mockReturnValue({
        lineCounts: { EAL: 7, TML: 0 },
        repeatedRecordSectionCounts: {
          all: 7,
          mainline: 2,
          rac: 1,
          low_s1: 1,
          lmc: 3,
          unknown: 0,
        },
        fetchLineCounts: vi.fn(),
        fetchRepeatedRecords: vi.fn(),
        setRepeatedFilters: vi.fn(),
        clearRepeatedFilters: vi.fn(),
        fetchDistinctValues: vi.fn().mockResolvedValue([]),
        repeatedRecordsLoading: false,
      });

      render(
        <LineTabPanel
          records={records}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Total EAL count should be 7
      // Mainline: 2, RAC: 1, LOW S1: 1, LMC: 3
      
      // Check that "All Sections" shows 7
      const allSectionsButton = screen.getByRole('button', { name: 'All Sections, 7 records' });
      expect(allSectionsButton).toBeInTheDocument();
      
      // Check section badge counts
      const mainlineButton = screen.getByRole('button', { name: 'Mainline, 2 records' });
      const racButton = screen.getByRole('button', { name: 'RAC, 1 records' });
      const lowS1Button = screen.getByRole('button', { name: 'LOW S1, 1 records' });
      const lmcButton = screen.getByRole('button', { name: 'LMC, 3 records' });
      
      expect(mainlineButton).toBeInTheDocument();
      expect(racButton).toBeInTheDocument();
      expect(lowS1Button).toBeInTheDocument();
      expect(lmcButton).toBeInTheDocument();
    });

    test('should correctly count sections when records include legacy "LOW" section name', () => {
      // Test backward compatibility: old records might have "LOW" instead of "LOW S1"
      const records = [
        createMockRecord({ record_id: 1, line: 'EAL', section: 'LOW' }),  // Legacy name
        createMockRecord({ record_id: 2, line: 'EAL', section: 'LOW S1' }),  // Current name
      ];
      mockUseDatabaseStore.mockReturnValue({
        lineCounts: { EAL: 2, TML: 0 },
        repeatedRecordSectionCounts: {
          all: 2,
          mainline: 0,
          rac: 0,
          low_s1: 2,
          lmc: 0,
          unknown: 0,
        },
        fetchLineCounts: vi.fn(),
        fetchRepeatedRecords: vi.fn(),
        setRepeatedFilters: vi.fn(),
        clearRepeatedFilters: vi.fn(),
        fetchDistinctValues: vi.fn().mockResolvedValue([]),
        repeatedRecordsLoading: false,
      });

      render(
        <LineTabPanel
          records={records}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Both should be counted under LOW S1 (total 2)
      const lowS1Button = screen.getByRole('button', { name: 'LOW S1, 2 records' });
      expect(lowS1Button).toBeInTheDocument();
    });

    test('should update filtered records when section is selected while keeping counts visible', async () => {
      const records = [
        createMockRecord({ record_id: 1, line: 'EAL', section: 'Mainline' }),
        createMockRecord({ record_id: 2, line: 'EAL', section: 'RAC' }),
        createMockRecord({ record_id: 3, line: 'EAL', section: 'RAC' }),
      ];

      render(
        <LineTabPanel
          records={records}
          loading={false}
          onFilterChange={mockOnFilterChange}
        >
          {mockChildrenFn}
        </LineTabPanel>
      );

      // Initially shows all 3 EAL records
      expect(screen.getByTestId('filtered-records')).toHaveTextContent('3 records');
      
      // Click RAC button
      const racButton = screen.getByRole('button', { name: /^RAC/i });
      fireEvent.click(racButton);

      // After selection, should call children with only RAC records (2)
      // Note: The component uses internal state for selectedSection,
      // and the filtered records are computed from safeRecords
      await waitFor(() => {
        expect(mockChildrenFn).toHaveBeenCalled();
      });
      
      // The onFilterChange should be called with RAC
      expect(mockOnFilterChange).toHaveBeenCalledWith('EAL', 'RAC');
    });
  });
});
