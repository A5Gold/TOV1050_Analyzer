import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import WearCalculatorView from '../WearCalculatorView';
import { useWearStore, type WearTab } from '../../store/useWearStore';
import { useWearRecordsStore } from '../../store/useWearRecordsStore';
import * as calculationApi from '../../api/client';

vi.mock('../../components/Calculation/WearResultTable', () => ({
  default: ({ rows }: { rows: unknown[] }) => <div data-testid="wear-result-table">{rows.length}</div>,
}));

vi.mock('../../components/Calculation/WearAlgorithmDialog', () => ({
  default: ({ open, onClose }: { open: boolean; onClose: () => void }) => open ? (
    <div role="dialog" aria-label="線耗計算邏輯">
      <button onClick={onClose}>關閉計算邏輯</button>
    </div>
  ) : null,
}));

vi.mock('../../components/Calculation/WearRecordsPanel', () => ({
  default: () => <div data-testid="wear-records-panel" />,
}));

vi.mock('../../components/Calculation/WearAnalysisCharts', () => ({
  default: ({ rows }: { rows: unknown[] }) => <div data-testid="wear-analysis-charts">{rows.length}</div>,
}));

vi.mock('../../components/Calculation/WearCycleStatusPanel', () => ({
  default: ({ onSave }: { onSave: () => void }) => <button onClick={onSave}>Save Records</button>,
}));

vi.mock('../../components/Calculation/WearDashboardPanel', () => ({
  default: () => <div data-testid="wear-dashboard-panel" />,
}));

vi.mock('../../components/Calculation/WearProjectionPanel', () => ({
  default: () => <div data-testid="wear-projection-panel" />,
}));

function makeTab(overrides: Partial<WearTab> = {}): WearTab {
  return {
    id: 'tab-1',
    label: 'Tab 1',
    line: 'EAL',
    lineClass: 'EAL',
    uploadedFiles: [],
    isLoading: false,
    error: null,
    date: '',
    wearResults: [],
    hasAnalyzed: false,
    acceptedConflictIds: [],
    cyclePreview: null,
    cyclePreviewFiles: [],
    cyclePreviewLoading: false,
    cycleSaveLoading: false,
    cycleError: null,
    lastCycleSave: null,
    ...overrides,
  };
}

describe('WearCalculatorView', () => {
  beforeEach(() => {
    useWearStore.setState({
      tabs: [makeTab()],
      activeTabId: 'tab-1',
    });
    useWearRecordsStore.getState().reset();
  });

  it('shows the exact four Wear Calculator feature tabs', () => {
    render(<WearCalculatorView />);

    expect(screen.getByRole('tab', { name: /Analysis/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Wire Wear Records/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Projection/i })).toBeInTheDocument();
    expect(['Analysis', 'Wire Wear Records', 'Dashboard', 'Projection'].map(name =>
      screen.getByRole('tab', { name }),
    )).toHaveLength(4);

    fireEvent.click(screen.getByRole('tab', { name: /Dashboard/i }));
    expect(screen.getByTestId('wear-dashboard-panel')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: /Projection/i }));
    expect(screen.getByTestId('wear-projection-panel')).toBeInTheDocument();
  });

  it('shows a completed empty-result message after wear analysis returns zero results', () => {
    useWearStore.setState({
      tabs: [
        makeTab({
          uploadedFiles: [new File(['exception'], 'exception-report.xlsx')],
          hasAnalyzed: true,
          date: '2026-01-16',
          wearResults: [],
        }),
      ],
      activeTabId: 'tab-1',
    });

    render(<WearCalculatorView />);

    expect(screen.getByText(/No wear records were found after filtering/i)).toBeInTheDocument();
    expect(screen.getByText(/The calculation completed successfully with 0 result/i)).toBeInTheDocument();
  });

  it('shows overwrite confirmation when save returns duplicates', () => {
    useWearRecordsStore.setState({
      duplicateConflict: {
        duplicate_count: 1,
        duplicates: [{ tension_length: 'H46', cycle_date: '2026-02-01' }],
      },
    } as any);

    render(<WearCalculatorView />);

    expect(screen.getByText(/already exist/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Overwrite/i })).toBeInTheDocument();
  });

  it('saves the complete backend preview without frontend regrouping', () => {
    const saveCycle = vi.fn();
    useWearStore.setState({
      tabs: [
        makeTab({
          uploadedFiles: [new File(['exception'], 'exception-report.xlsx')],
          hasAnalyzed: true,
          date: '2026-02-01',
          wearResults: [
            {
              tension_length: 'H01',
              from_m: 0,
              to_m: 50,
              line: 'EAL',
              track: 'UP',
              section: 'Mainline',
              cycle_date: '2026-01-01',
              avg_wear_min: 12,
              sd: 0.1,
              wear_percentage: 5,
              dates: [],
              record_points: [],
            },
            {
              tension_length: 'H01',
              from_m: 50,
              to_m: 100,
              line: 'EAL',
              track: 'DN',
              section: 'Mainline',
              cycle_date: '2026-02-01',
              avg_wear_min: 11,
              sd: 0.2,
              wear_percentage: 7,
              dates: [],
              record_points: [],
            },
          ],
          cyclePreview: {
            lineGroup: 'EAL', cycleDate: '2026-02-01', records: [], segments: [], conflicts: [], unresolved: [],
            blockingReasons: [], canSave: true, previewDigest: 'digest-1', expectedDataVersion: 8,
          },
        }),
      ],
      activeTabId: 'tab-1',
      saveCycle,
    });

    render(<WearCalculatorView />);
    fireEvent.click(screen.getByRole('button', { name: /Save Records/i }));

    expect(saveCycle).toHaveBeenCalledOnce();
  });

  it('shows only EAL and TML in the Analysis line selector', () => {
    render(<WearCalculatorView />);

    fireEvent.mouseDown(screen.getByLabelText(/Line/i));

    expect(screen.getByRole('option', { name: 'EAL' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'TML' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'LMC' })).not.toBeInTheDocument();
  });

  it('opens the shared calculation guide from every feature tab', () => {
    render(<WearCalculatorView />);

    for (const tabName of ['Analysis', 'Wire Wear Records', 'Dashboard', 'Projection']) {
      fireEvent.click(screen.getByRole('tab', { name: tabName }));
      fireEvent.click(screen.getByRole('button', { name: '線耗計算邏輯' }));
      expect(screen.getByRole('dialog', { name: '線耗計算邏輯' })).toBeInTheDocument();
      fireEvent.click(screen.getByRole('button', { name: '關閉計算邏輯' }));
      expect(screen.queryByRole('dialog', { name: '線耗計算邏輯' })).not.toBeInTheDocument();
    }
  });

  it('prefills Cycle Date from the backend preview and permits an override', () => {
    useWearStore.setState({ tabs: [makeTab({
      cyclePreview: {
        lineGroup: 'EAL', cycleDate: '2026-05-28', records: [], segments: [], conflicts: [], unresolved: [],
        blockingReasons: [], canSave: true, previewDigest: 'digest', expectedDataVersion: 1,
      },
    })] });
    render(<WearCalculatorView />);
    const input = screen.getByLabelText(/Cycle Date/i);
    expect(input).toHaveValue('2026-05-28');
    fireEvent.change(input, { target: { value: '2026-05-29' } });
    expect(input).toHaveValue('2026-05-29');
    expect(useWearStore.getState().tabs[0].cyclePreview).toBeNull();
  });

  it('downloads Excel for the committed line and cycle date', async () => {
    const exportSpy = vi.spyOn(calculationApi, 'exportWearCycleExcel').mockResolvedValue(new Blob(['report']));
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:report') });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });
    useWearStore.setState({ tabs: [makeTab({
      lastCycleSave: {
        cycleId: 1, lineGroup: 'EAL', cycleDate: '2026-05-28', sourceType: 'analysis', completenessState: 'complete',
        acquisitionDateFrom: null, acquisitionDateTo: null, sourceLineage: [], records: [], segments: [], conflictDecisions: [], wireWearDataVersion: 2,
      },
    })] });
    render(<WearCalculatorView />);
    expect(screen.getByText(/cycle saved/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /download excel/i }));
    await waitFor(() => expect(exportSpy).toHaveBeenCalledWith({ lineGroup: 'EAL', cycleDate: '2026-05-28' }));
  });

  it('guards feature tab changes with Save and keeps the requested destination', async () => {
    render(<WearCalculatorView />);
    fireEvent.click(screen.getByRole('tab', { name: 'Wire Wear Records' }));
    const saveChanges = vi.fn(async () => {
      useWearRecordsStore.setState({ hasPendingChanges: false, shouldBlockNavigation: false });
    });
    act(() => useWearRecordsStore.setState({
      hasPendingChanges: true,
      shouldBlockNavigation: true,
      pendingChanges: [{ kind: 'delete_row', lineGroup: 'EAL', cycleDate: '2026-05-28' }],
      saveChanges,
    } as any));

    fireEvent.click(screen.getByRole('tab', { name: 'Dashboard' }));
    expect(screen.getByRole('dialog', { name: /unsaved wire wear changes/i })).toBeInTheDocument();
    expect(screen.getByTestId('wear-records-panel')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() => expect(saveChanges).toHaveBeenCalledOnce());
    await waitFor(() => expect(screen.getByTestId('wear-dashboard-panel')).toBeInTheDocument());
  });

  it('supports Cancel and Discard in the pending-change tab guard', async () => {
    const discardChanges = vi.fn(() => {
      useWearRecordsStore.setState({ hasPendingChanges: false, shouldBlockNavigation: false });
    });
    render(<WearCalculatorView />);
    fireEvent.click(screen.getByRole('tab', { name: 'Wire Wear Records' }));
    act(() => useWearRecordsStore.setState({
      hasPendingChanges: true,
      shouldBlockNavigation: true,
      pendingChanges: [{ kind: 'delete_row', lineGroup: 'EAL', cycleDate: '2026-05-28' }],
      discardChanges,
    } as any));

    fireEvent.click(screen.getByRole('tab', { name: 'Projection' }));
    fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }));
    expect(screen.getByTestId('wear-records-panel')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('dialog', { name: /unsaved wire wear changes/i })).not.toBeInTheDocument());

    fireEvent.click(screen.getByRole('tab', { name: 'Projection' }));
    fireEvent.click(screen.getByRole('button', { name: /^discard$/i }));
    expect(discardChanges).toHaveBeenCalledOnce();
    expect(screen.getByTestId('wear-projection-panel')).toBeInTheDocument();
  });

  it('places the feature toolbar before the analysis content', () => {
    render(<WearCalculatorView />);

    const analysisTab = screen.getByRole('tab', { name: 'Analysis' });
    const uploadHeading = screen.getByRole('heading', { name: 'Upload files' });
    expect(
      analysisTab.compareDocumentPosition(uploadHeading) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it('renders the preview and error owned by the selected calculation tab', () => {
    useWearStore.setState({
      tabs: [
        makeTab({
          id: 'tab-1',
          label: 'First',
          uploadedFiles: [new File(['first'], 'first.xlsx')],
          cyclePreview: {
            lineGroup: 'EAL', cycleDate: '2026-05-28', records: [], segments: [], conflicts: [], unresolved: [],
            blockingReasons: [], canSave: true, previewDigest: 'first-preview', expectedDataVersion: 1,
          },
        }),
        makeTab({ id: 'tab-2', label: 'Second', date: '2026-05-29', cycleError: 'second-tab-error' }),
      ],
      activeTabId: 'tab-1',
    });

    render(<WearCalculatorView />);
    expect(screen.getByLabelText(/Cycle Date/i)).toHaveValue('2026-05-28');
    expect(screen.getByRole('button', { name: /Save Records/i })).toBeInTheDocument();
    expect(screen.queryByText('second-tab-error')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /Second/i }));
    expect(screen.getByLabelText(/Cycle Date/i)).toHaveValue('2026-05-29');
    expect(screen.getByText('second-tab-error')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Save Records/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /First/i }));
    expect(screen.getByLabelText(/Cycle Date/i)).toHaveValue('2026-05-28');
    expect(screen.getByRole('button', { name: /Save Records/i })).toBeInTheDocument();
  });
});
