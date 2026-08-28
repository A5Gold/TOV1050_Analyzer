import { fireEvent, render, screen, waitFor, waitForElementToBeRemoved, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('xlsx', () => ({
  utils: {
    aoa_to_sheet: vi.fn((rows: unknown[][]) => rows),
    book_append_sheet: vi.fn(),
    book_new: vi.fn(() => ({})),
  },
  writeFile: vi.fn(),
}));

import WearRecordsPanel from '../WearRecordsPanel';
import { useWearRecordsStore } from '../../../store/useWearRecordsStore';
import * as XLSX from 'xlsx';

const workbench = {
  lineGroup: 'EAL' as const,
  columns: [
    { tensionLength: '28', track: 'Siding' as const, fromM: 100, toM: 120 },
    { tensionLength: 'X2', track: 'UP' as const, fromM: 200, toM: 220 },
  ],
  matrixRows: [{ cycleDate: '2026-05-28', values: { 28: 11.45, X2: null } }],
  latestSummary: [{
    tensionLength: '28', latestCycleDate: '2026-05-28', latestAvgWearMin: 11.45,
    latestWearPercentage: 12.4, historicalSd: 0.2, wearRateMmPerYear: 0.1,
    observationCount: 3, rSquared: 0.9, trendStatus: 'eligible',
  }],
  records: [{
    key: { lineGroup: 'EAL' as const, cycleDate: '2026-05-28', tensionLength: '28' },
    track: 'Siding' as const, fromM: 100, toM: 120, avgWearMin: 11.45,
    wearPercentage: 12.4, measurementSd: null, hasDataConflict: false,
    conflictIds: [], updatedAt: '2026-05-28T12:00:00Z',
  }],
  catalog: [
    { lineGroup: 'EAL' as const, tensionLength: '28', track: 'Siding' as const, fromM: 100, toM: 120 },
    { lineGroup: 'EAL' as const, tensionLength: 'X2', track: 'UP' as const, fromM: 200, toM: 220 },
  ],
  wireWearDataVersion: 3,
};

describe('WearRecordsPanel staged workbench', () => {
  beforeEach(() => {
    useWearRecordsStore.getState().reset();
    useWearRecordsStore.getState().hydrate(workbench);
    useWearRecordsStore.setState({ loadCycleWorkbench: vi.fn() } as any);
  });

  afterEach(() => vi.restoreAllMocks());

  it('opens metadata-owned Add and Edit dialogs from matrix cells', async () => {
    const user = userEvent.setup();
    render(<WearRecordsPanel />);

    await user.dblClick(screen.getByTestId('history-cell-2026-05-28-X2-empty'));
    const addDialog = screen.getByRole('dialog', { name: /add wire wear record/i });
    expect(within(addDialog).getByLabelText('Line')).toHaveValue('EAL');
    expect(within(addDialog).getByLabelText('Cycle Date')).toHaveValue('2026-05-28');
    expect(within(addDialog).getByLabelText('Tension Length')).toHaveValue('X2');
    expect(within(addDialog).getByLabelText('Track')).toHaveValue('UP');
    expect(within(addDialog).getByLabelText('Track')).toBeDisabled();
    expect(within(addDialog).queryByLabelText(/Measurement SD|^SD$/i)).not.toBeInTheDocument();
    await user.click(within(addDialog).getByRole('button', { name: /cancel/i }));

    await user.dblClick(screen.getByTestId('history-cell-2026-05-28-28'));
    expect(screen.getByRole('dialog', { name: /edit wire wear record/i })).toBeInTheDocument();
    expect(screen.getByLabelText('Avg Wear Min')).toHaveValue(11.45);
  });

  it('exposes batch, Excel, database, save, and normalized line-class workbench controls', async () => {
    const user = userEvent.setup();
    const loadCycleWorkbench = vi.fn();
    useWearRecordsStore.setState({ loadCycleWorkbench } as any);
    render(<WearRecordsPanel />);

    expect(screen.getByRole('button', { name: /add records/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /import excel/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /database/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /export excel/i })).toBeEnabled();
    expect(screen.getByRole('button', { name: /save changes/i })).toBeDisabled();

    await user.click(screen.getByLabelText('Line'));
    await user.click(screen.getByRole('option', { name: 'LMC' }));
    expect(loadCycleWorkbench).toHaveBeenCalledWith({ lineGroup: 'EAL', lineClass: 'LMC', summaryOnly: false });

    await user.click(screen.getByRole('button', { name: /add records/i }));
    expect(screen.getByRole('dialog', { name: /add wire wear records/i })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /close add wire wear records/i }));
    await waitForElementToBeRemoved(() => screen.queryByRole('dialog', { name: /add wire wear records/i }));

    await user.click(screen.getByRole('button', { name: /import excel/i }));
    expect(screen.getByRole('dialog', { name: /import wire wear excel/i })).toBeInTheDocument();
  }, 10_000);

  it('loads the full matrix and keeps the selected tension length highlighted', async () => {
    const user = userEvent.setup();
    const loadCycleWorkbench = vi.fn().mockResolvedValue(undefined);
    useWearRecordsStore.setState({ loadCycleWorkbench, selectedTensionLength: null } as any);
    render(<WearRecordsPanel />);

    await user.click(screen.getByRole('combobox', { name: /tension length/i }));
    await user.click(screen.getByRole('option', { name: 'X2' }));

    expect(loadCycleWorkbench).toHaveBeenCalledWith({
      lineGroup: 'EAL',
      lineClass: 'EAL',
      summaryOnly: false,
    });
    await waitFor(() => expect(useWearRecordsStore.getState().selectedTensionLength).toBe('X2'));
    expect(within(screen.getByTestId('history-header')).getByRole('columnheader', { name: 'X2' })).toHaveAttribute('aria-selected', 'true');
    expect(within(screen.getByTestId('latest-header')).getByRole('columnheader', { name: 'X2' })).toHaveAttribute('aria-selected', 'true');
  });

  it('exports the complete sorted historical matrix for the active line class', async () => {
    const user = userEvent.setup();
    useWearRecordsStore.getState().hydrate({
      ...workbench,
      columns: [
        { ...workbench.columns[0], tensionLength: 'X2' },
        { ...workbench.columns[0], tensionLength: 'H02' },
        { ...workbench.columns[0], tensionLength: 'H01' },
      ],
      matrixRows: [{
        cycleDate: '2026-05-28',
        values: { X2: 12.3, H02: 11.2, H01: 10.8 },
      }],
    });
    render(<WearRecordsPanel />);

    await user.click(screen.getByRole('button', { name: /export excel/i }));

    expect(vi.mocked(XLSX.utils.aoa_to_sheet)).toHaveBeenCalledWith([
      ['Cycle Date', 'H01', 'H02', 'X2'],
      ['2026-05-28', 10.8, 11.2, 12.3],
    ]);
    expect(vi.mocked(XLSX.writeFile)).toHaveBeenCalledWith(
      expect.anything(),
      'EAL_Historical_Avg_Wear_Min.xlsx',
    );
  });

  it('retains staged cell and row deletions with accessible commands until discard', async () => {
    const user = userEvent.setup();
    render(<WearRecordsPanel />);

    const cell = screen.getByTestId('history-cell-2026-05-28-28');
    fireEvent.focus(cell);
    await user.click(screen.getByRole('button', { name: /delete 28 on 2026-05-28/i }));
    await user.click(screen.getByRole('button', { name: /^confirm$/i }));
    expect(screen.getByText('11.450')).toHaveStyle({ textDecoration: 'line-through' });
    expect(cell).toHaveAttribute('data-pending', 'delete_cell');
    expect(within(cell).getByText('待刪除')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('刪除儲存格 1');

    await user.click(screen.getByRole('button', { name: /discard changes/i }));
    expect(cell).not.toHaveAttribute('data-pending');

    await user.click(screen.getByRole('button', { name: /delete row 2026-05-28/i }));
    await user.click(screen.getByRole('button', { name: /^confirm$/i }));
    expect(screen.getByTestId('history-row-2026-05-28')).toHaveAttribute('data-pending', 'delete-row');
    expect(within(screen.getByTestId('history-row-2026-05-28')).getByText('整列待刪除')).toBeInTheDocument();
  }, 10_000);

  it('labels staged add and edit cells plus a newly added cycle row', () => {
    const state = useWearRecordsStore.getState();
    state.stageAdd(
      { lineGroup: 'EAL', cycleDate: '2026-05-28', tensionLength: 'X2' },
      10.5,
    );
    state.stageEdit(
      { lineGroup: 'EAL', cycleDate: '2026-05-28', tensionLength: '28' },
      10.9,
      '2026-05-28T12:00:00Z',
    );
    state.stageAdd(
      { lineGroup: 'EAL', cycleDate: '2026-06-01', tensionLength: '28' },
      10.8,
    );

    render(<WearRecordsPanel />);

    const existingAdd = screen.getByTestId('history-cell-2026-05-28-X2');
    expect(existingAdd).toHaveAttribute('data-pending', 'add');
    expect(within(existingAdd).getByText('待新增')).toBeInTheDocument();
    expect(within(existingAdd).getByTestId('AddCircleOutlineIcon')).toBeInTheDocument();

    const edit = screen.getByTestId('history-cell-2026-05-28-28');
    expect(edit).toHaveAttribute('data-pending', 'edit');
    expect(within(edit).getByText('待更新')).toBeInTheDocument();
    expect(within(edit).getByTestId('EditOutlinedIcon')).toBeInTheDocument();

    const newRow = screen.getByTestId('history-row-2026-06-01');
    expect(within(newRow).getAllByText('待新增')).toHaveLength(2);
    expect(screen.getByRole('status')).toHaveTextContent(
      '待處理：新增 2、更新 1、刪除儲存格 0、刪除整列 0',
    );
  });

  it('saves atomically and keeps pending operations focused after a failed save', async () => {
    const user = userEvent.setup();
    const saveChanges = vi.fn().mockImplementation(async () => {
      useWearRecordsStore.setState({ commitErrors: ['Stale record'], error: 'Stale record' });
    });
    useWearRecordsStore.setState({ saveChanges } as any);
    render(<WearRecordsPanel />);

    await user.dblClick(screen.getByTestId('history-cell-2026-05-28-X2-empty'));
    await user.clear(screen.getByLabelText('Avg Wear Min'));
    await user.type(screen.getByLabelText('Avg Wear Min'), '10.5');
    await user.click(screen.getByRole('button', { name: /^stage add$/i }));
    await user.click(screen.getByRole('button', { name: /save changes/i }));

    expect(saveChanges).toHaveBeenCalledTimes(1);
    expect(useWearRecordsStore.getState().pendingChanges).toHaveLength(1);
    expect(screen.getByRole('alert')).toHaveTextContent('Stale record');
    expect(screen.getByRole('alert')).toHaveFocus();
  }, 10_000);

  it('translates shift-wheel into horizontal scrolling and exposes a scrollbar', () => {
    render(<WearRecordsPanel />);
    const scroller = screen.getByTestId('history-matrix-scroll');
    Object.defineProperty(scroller, 'scrollLeft', { value: 0, writable: true });
    fireEvent.wheel(scroller, { shiftKey: true, deltaY: 80 });
    expect(scroller.scrollLeft).toBe(80);
    expect(scroller).toHaveStyle({ overflowX: 'scroll' });
  });
});
