import { fireEvent, render, screen, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, expect, it, vi } from 'vitest';
import { createTheme, ThemeProvider } from '@mui/material/styles';

import WearHistoryPivotTable from '../WearHistoryPivotTable';
import WearLatestSummaryTable from '../WearLatestSummaryTable';
import WireWearRecordDialog from '../WireWearRecordDialog';

const columns = [
  { tensionLength: '28', track: 'Siding' as const, fromM: 10, toM: 20, intervalCount: 2, intervals: [{ track: 'UP' as const, fromM: 10, toM: 14 }, { track: 'DN' as const, fromM: 16, toM: 20 }] },
  { tensionLength: 'X2', track: 'UP' as const, fromM: 20, toM: 30, intervalCount: 1, intervals: [{ track: 'UP' as const, fromM: 20, toM: 30 }] },
];

describe('wire wear workbench tables', () => {
  it('keeps historical and latest tables in the same canonical TL order', () => {
    render(<>
      <WearHistoryPivotTable columns={columns} rows={[]} pendingChanges={[]} onAdd={vi.fn()} onEdit={vi.fn()} onDeleteCell={vi.fn()} onDeleteRow={vi.fn()} />
      <WearLatestSummaryTable columns={columns} rows={[]} />
    </>);
    expect(within(screen.getByTestId('history-header')).getAllByRole('columnheader').map(cell => cell.textContent)).toEqual(['Cycle Date', '28', 'X2']);
    expect(within(screen.getByTestId('latest-header')).getAllByRole('columnheader').map(cell => cell.textContent)).toEqual(['Metric', '28', 'X2']);
    expect(within(screen.getByTestId('history-header')).getByRole('columnheader', { name: 'Cycle Date' })).toHaveStyle({ width: '156px' });
  });

  it('windows wide matrices and highlights the selected tension length', () => {
    const wideColumns = Array.from({ length: 40 }, (_value, index) => ({
      tensionLength: `TL${String(index + 1).padStart(2, '0')}`,
      track: 'UP' as const,
      fromM: index * 10,
      toM: index * 10 + 10,
      intervalCount: 1,
      intervals: [{ track: 'UP' as const, fromM: index * 10, toM: index * 10 + 10 }],
    }));

    render(<WearHistoryPivotTable
      columns={wideColumns}
      rows={[{
        cycleDate: '2026-05-28',
        values: Object.fromEntries(wideColumns.map((column, index) => [column.tensionLength, 12 - index / 100])),
      }]}
      pendingChanges={[]}
      selectedTensionLength="TL35"
      onAdd={vi.fn()}
      onEdit={vi.fn()}
      onDeleteCell={vi.fn()}
      onDeleteRow={vi.fn()}
    />);

    const selectedHeader = screen.getByRole('columnheader', { name: 'TL35' });
    expect(selectedHeader).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByTestId('history-cell-2026-05-28-TL35')).toHaveAttribute('data-selected', 'true');
    expect(within(screen.getByTestId('history-header')).getAllByRole('columnheader')).toHaveLength(15);
    expect(screen.queryByRole('columnheader', { name: 'TL01' })).not.toBeInTheDocument();
  });

  it('activates empty and value cells from the keyboard and prevents scrolling', () => {
    const onAdd = vi.fn();
    const onEdit = vi.fn();
    render(<WearHistoryPivotTable
      columns={columns}
      rows={[{ cycleDate: '2026-05-28', values: { 28: 11.45, X2: null } }]}
      pendingChanges={[]}
      onAdd={onAdd}
      onEdit={onEdit}
      onDeleteCell={vi.fn()}
      onDeleteRow={vi.fn()}
    />);

    const emptyEvent = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true });
    screen.getByTestId('history-cell-2026-05-28-X2-empty').dispatchEvent(emptyEvent);
    expect(emptyEvent.defaultPrevented).toBe(true);
    expect(onAdd).toHaveBeenCalledWith('2026-05-28', 'X2');

    const valueEvent = new KeyboardEvent('keydown', { key: ' ', bubbles: true, cancelable: true });
    screen.getByTestId('history-cell-2026-05-28-28').dispatchEvent(valueEvent);
    expect(valueEvent.defaultPrevented).toBe(true);
    expect(onEdit).toHaveBeenCalledWith('2026-05-28', '28', 11.45);
    fireEvent.keyDown(screen.getByTestId('history-cell-2026-05-28-28'), { key: 'ArrowRight' });
    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  it('keeps one direct row delete action without a duplicate actions menu', () => {
    const onDeleteRow = vi.fn();
    render(<WearHistoryPivotTable
      columns={columns.slice(0, 1)}
      rows={[{ cycleDate: '2026-05-28', values: { 28: 11.45 } }]}
      pendingChanges={[]}
      onAdd={vi.fn()}
      onEdit={vi.fn()}
      onDeleteCell={vi.fn()}
      onDeleteRow={onDeleteRow}
    />);

    const deleteRow = screen.getByRole('button', { name: 'Delete row 2026-05-28' });
    expect(screen.queryByRole('button', { name: /row actions/i })).not.toBeInTheDocument();
    fireEvent.click(deleteRow);
    expect(onDeleteRow).toHaveBeenCalledWith('2026-05-28');
  });

  it('renders every latest-summary tension-length column with horizontal overflow', () => {
    const wideColumns = Array.from({ length: 20 }, (_value, index) => ({
      tensionLength: `TL${String(index + 1).padStart(2, '0')}`,
      track: 'UP' as const,
      fromM: index * 10,
      toM: index * 10 + 10,
      intervalCount: 1,
      intervals: [{ track: 'UP' as const, fromM: index * 10, toM: index * 10 + 10 }],
    }));

    render(<WearLatestSummaryTable columns={wideColumns} rows={[]} />);
    const headers = within(screen.getByTestId('latest-header')).getAllByRole('columnheader');
    expect(headers).toHaveLength(21);
    expect(headers[0]).toHaveStyle({ width: '176px' });
    expect(headers[1]).toHaveStyle({ width: '96px' });
    expect(screen.getByRole('columnheader', { name: 'TL20' })).toBeInTheDocument();
    expect(screen.queryByText('Tension lengths per page')).not.toBeInTheDocument();
  });

  it('highlights the selected tension length throughout Latest Summary', () => {
    const { container } = render(
      <WearLatestSummaryTable columns={columns} rows={[]} selectedTensionLength="X2" />,
    );
    expect(screen.getByRole('columnheader', { name: 'X2' })).toHaveAttribute('data-selected', 'true');
    expect(container.querySelectorAll('tbody td[data-selected="true"]')).toHaveLength(7);
  });

  it('calibrates pending warning surfaces for light and dark themes', () => {
    const backgrounds: string[] = [];
    for (const mode of ['light', 'dark'] as const) {
      const { unmount } = render(
        <ThemeProvider theme={createTheme({ palette: { mode } })}>
          <WearHistoryPivotTable
            columns={columns.slice(0, 1)}
            rows={[{ cycleDate: '2026-05-28', values: { 28: 11.45 } }]}
            pendingChanges={[{
              kind: 'edit',
              key: { lineGroup: 'EAL', cycleDate: '2026-05-28', tensionLength: '28' },
              avgWearMin: 11.2,
              expectedUpdatedAt: '2026-05-28T12:00:00Z',
            }]}
            onAdd={vi.fn()}
            onEdit={vi.fn()}
            onDeleteCell={vi.fn()}
            onDeleteRow={vi.fn()}
          />
        </ThemeProvider>,
      );
      const cell = screen.getByTestId('history-cell-2026-05-28-28');
      backgrounds.push(getComputedStyle(cell).backgroundColor);
      expect(cell).toHaveAttribute('data-pending', 'edit');
      unmount();
    }

    expect(backgrounds[0]).not.toBe('rgba(0, 0, 0, 0)');
    expect(backgrounds[1]).not.toBe('rgba(0, 0, 0, 0)');
    expect(backgrounds[0]).not.toBe(backgrounds[1]);
  });

  it('shows rounded wear percent while preserving the precise value in a tooltip', () => {
    render(<WearLatestSummaryTable columns={columns.slice(0, 1)} rows={[{
      tensionLength: '28', latestCycleDate: '2026-05-28', latestAvgWearMin: 11.45,
      latestWearPercentage: 12.4, historicalSd: 0.2, wearRateMmPerYear: 0.1,
      observationCount: 3, rSquared: 0.9, trendStatus: 'eligible',
    }]} />);
    expect(screen.getByText('12%')).toHaveAttribute('title', '12.4%');
  });

  it('clips long latest-summary values while exposing the full status', () => {
    render(<WearLatestSummaryTable columns={columns.slice(0, 1)} rows={[{
      tensionLength: '28', latestCycleDate: '2026-05-28', latestAvgWearMin: 11.45,
      latestWearPercentage: 12.4, historicalSd: 0.2, wearRateMmPerYear: 0.1,
      observationCount: 3, rSquared: 0.9, trendStatus: 'non_positive_rate',
    }]} />);
    expect(screen.getByText('non_positive_rate')).toHaveAttribute('title', 'non_positive_rate');
    expect(screen.getByText('non_positive_rate')).toHaveStyle({ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' });
  });

  it('limits the dialog to editable business fields and read-only metadata', () => {
    render(<WireWearRecordDialog open mode="add" lineGroup="EAL" initialValue={{ cycleDate: '2026-05-28', tensionLength: '28', avgWearMin: 11 }} catalog={columns.map(column => ({ ...column, lineGroup: 'EAL' as const }))} onClose={vi.fn()} onStage={vi.fn()} />);
    const dialog = screen.getByRole('dialog', { name: /add wire wear record/i });
    expect(within(dialog).getByLabelText('Line')).toBeEnabled();
    expect(within(dialog).getByLabelText('Cycle Date')).toBeEnabled();
    expect(within(dialog).getByLabelText('Tension Length')).toBeEnabled();
    expect(within(dialog).getByLabelText('Avg Wear Min')).toBeEnabled();
    for (const label of ['Track', 'From (m)', 'To (m)', 'Intervals', 'Physical Intervals', 'Wear %']) expect(within(dialog).getByLabelText(label)).toBeDisabled();
    expect(within(dialog).getByLabelText('Intervals')).toHaveValue('2');
    expect(within(dialog).getByLabelText('Physical Intervals')).toHaveValue('UP 10-14\nDN 16-20');
    expect(within(dialog).queryByLabelText(/Measurement SD|^SD$/i)).not.toBeInTheDocument();
  });
});
