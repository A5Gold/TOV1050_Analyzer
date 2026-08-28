import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { describe, expect, it, vi } from 'vitest';

import BatchAddRecordsGrid, { type BatchAddRecordRow } from '../BatchAddRecordsGrid';

const rows: BatchAddRecordRow[] = [
  { rowId: 'row-1', tensionLength: 'TL1', avgWearMin: '11.2' },
  { rowId: 'row-2', tensionLength: 'TL2', avgWearMin: '10.9' },
];

const baseProps = () => ({
  rows,
  onCellChange: vi.fn(),
  onInsertRow: vi.fn(),
  onDeleteRow: vi.fn(),
  onPasteRows: vi.fn(),
});

describe('BatchAddRecordsGrid', () => {
  it('renders stable spreadsheet columns and controlled row commands', async () => {
    const props = baseProps();
    const user = userEvent.setup();
    const ControlledGrid = () => {
      const [controlledRows, setControlledRows] = React.useState(rows);
      return (
        <BatchAddRecordsGrid
          {...props}
          rows={controlledRows}
          onCellChange={(rowId, field, value) => {
            props.onCellChange(rowId, field, value);
            setControlledRows(current => current.map(row => (
              row.rowId === rowId ? { ...row, [field]: value } : row
            )));
          }}
        />
      );
    };
    render(<ControlledGrid />);

    const grid = screen.getByRole('table', { name: 'Batch Add Records grid' });
    expect(within(grid).getAllByRole('columnheader').map(cell => cell.textContent)).toEqual([
      '#', 'Tension Length', 'Avg Wear Min', 'Status', 'Delete',
    ]);
    await user.clear(screen.getByLabelText('Row 1 Tension Length'));
    await user.type(screen.getByLabelText('Row 1 Tension Length'), 'TL9');
    expect(props.onCellChange).toHaveBeenLastCalledWith('row-1', 'tensionLength', 'TL9');

    await user.click(screen.getByRole('button', { name: 'Add Row' }));
    expect(props.onInsertRow).toHaveBeenCalledWith('row-2');
    await user.click(screen.getByRole('button', { name: 'Delete row 2' }));
    expect(props.onDeleteRow).toHaveBeenCalledWith('row-2');
  });

  it('parses an Excel two-column paste into one callback payload', () => {
    const props = baseProps();
    render(<BatchAddRecordsGrid {...props} />);

    fireEvent.paste(screen.getByLabelText('Row 1 Tension Length'), {
      clipboardData: { getData: () => 'TL7\t11.125\r\nTL8\t10.875\r\n' },
    });

    expect(props.onPasteRows).toHaveBeenCalledWith('row-1', [
      { tensionLength: 'TL7', avgWearMin: '11.125' },
      { tensionLength: 'TL8', avgWearMin: '10.875' },
    ]);
  });

  it('supports predictable vertical keyboard navigation and row insertion', async () => {
    const props = baseProps();
    const user = userEvent.setup();
    render(<BatchAddRecordsGrid {...props} />);

    const firstWear = screen.getByLabelText('Row 1 Avg Wear Min');
    const secondWear = screen.getByLabelText('Row 2 Avg Wear Min');
    await user.click(firstWear);
    await user.keyboard('{ArrowDown}');
    expect(secondWear).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(props.onInsertRow).toHaveBeenCalledWith('row-2');
  });

  it('attaches exact candidate errors and statuses to their row cells', () => {
    const props = baseProps();
    render(
      <BatchAddRecordsGrid
        {...props}
        candidates={[
          {
            status: 'error', key: null, avgWearMin: null, track: null,
            existingAvgWearMin: null, expectedUpdatedAt: null,
            sourceType: 'manual', sourceSheet: null, sourceRow: 1, sourceCell: 'B1',
            originalValue: 'bad', excluded: false, rowId: 'row-1',
            issues: [{ code: 'invalid_number', message: 'Enter a finite wear value.', field: 'avg_wear_min', cell: 'B1' }],
          },
          {
            status: 'update', key: { lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-08-01', tensionLength: 'TL2' },
            avgWearMin: 10.9, track: 'UP', existingAvgWearMin: 11.1, expectedUpdatedAt: 'v1',
            sourceType: 'manual', sourceSheet: null, sourceRow: 2, sourceCell: 'B2',
            originalValue: 10.9, excluded: false, rowId: 'row-2', issues: [],
          },
        ]}
      />,
    );

    expect(screen.getByLabelText('Row 1 Avg Wear Min')).toHaveAccessibleDescription('Enter a finite wear value.');
    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('Update')).toBeInTheDocument();
    expect(screen.getByText('Existing 11.100')).toBeInTheDocument();
  });

  it('keeps a large controlled batch available without changing the column structure', () => {
    const props = baseProps();
    const largeRows = Array.from({ length: 50 }, (_, index) => ({
      rowId: `row-${index + 1}`,
      tensionLength: `TL${index + 1}`,
      avgWearMin: `${11 - index / 100}`,
    }));
    render(<BatchAddRecordsGrid {...props} rows={largeRows} />);

    expect(screen.getAllByRole('row')).toHaveLength(51);
    expect(screen.getByLabelText('Row 50 Avg Wear Min')).toHaveValue('10.51');
    expect(screen.getAllByRole('columnheader')).toHaveLength(5);
  });
});
