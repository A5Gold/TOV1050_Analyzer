import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { describe, expect, it, vi } from 'vitest';

import ExcelWearImportPreviewTable, {
  type ExcelImportPreviewRow,
} from '../ExcelWearImportPreviewTable';

const rows: ExcelImportPreviewRow[] = [
  {
    id: 'new-1', status: 'new', sheet: 'EAL', cell: 'C4', track: 'UP', tensionLength: 'TL01',
    cycleDate: '2026-01-01', importedValue: 11.125,
  },
  {
    id: 'update-1', status: 'update', sheet: 'TML', cell: 'D7', track: 'DOWN', tensionLength: 'TL02',
    cycleDate: '2026-02-01', importedValue: 10.875, existingValue: 11.25,
  },
  {
    id: 'same-1', status: 'no_change', sheet: 'LMC', cell: 'E8', tensionLength: 'TL03',
    cycleDate: '2026-03-01', importedValue: 10.5,
  },
  {
    id: 'error-1', status: 'error', sheet: 'EAL', cell: 'F9', tensionLength: 'TL04',
    originalValue: 'not-a-number', reason: 'Enter a numeric wear value.', importedValue: null, excluded: false,
  },
];

const baseProps = () => ({
  rows,
  filter: 'all' as const,
  onFilterChange: vi.fn(),
  onExcludeError: vi.fn(),
  onDownloadErrorReport: vi.fn(),
});

describe('ExcelWearImportPreviewTable', () => {
  it('renders stable operational columns and all preview statuses', () => {
    render(<ExcelWearImportPreviewTable {...baseProps()} />);

    const table = screen.getByRole('table', { name: 'Excel import preview' });
    expect(within(table).getAllByRole('columnheader').map(cell => cell.textContent)).toEqual([
      'Status', 'Sheet', 'Cell', 'Track', 'Tension Length', 'Cycle Date', 'Existing', 'Imported', 'Source / Reason', 'Exclude',
    ]);
    expect(screen.getByText('New')).toBeInTheDocument();
    expect(screen.getByText('Update')).toBeInTheDocument();
    expect(screen.getByText('No Change')).toBeInTheDocument();
    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('11.250')).toBeInTheDocument();
    expect(screen.getByText('10.875')).toBeInTheDocument();
  });

  it('emits controlled filter and error report actions', async () => {
    const props = baseProps();
    const user = userEvent.setup();
    render(<ExcelWearImportPreviewTable {...props} />);

    await user.click(screen.getByRole('button', { name: 'Show Update rows' }));
    expect(props.onFilterChange).toHaveBeenCalledWith('update');
    await user.click(screen.getByRole('button', { name: 'Download Error Report' }));
    expect(props.onDownloadErrorReport).toHaveBeenCalledTimes(1);
  });

  it('shows exact source diagnostics and explicitly excludes an error', async () => {
    const props = baseProps();
    const user = userEvent.setup();
    render(<ExcelWearImportPreviewTable {...props} filter="error" />);

    expect(screen.getByText('EAL')).toBeInTheDocument();
    expect(screen.getByText('F9')).toBeInTheDocument();
    expect(screen.getByText('Original: not-a-number')).toBeInTheDocument();
    expect(screen.getByText('Enter a numeric wear value.')).toBeInTheDocument();
    await user.click(screen.getByRole('checkbox', { name: 'Exclude error EAL F9' }));
    expect(props.onExcludeError).toHaveBeenCalledWith('error-1', true);
  });

  it('renders a filter-specific empty state', () => {
    render(<ExcelWearImportPreviewTable {...baseProps()} filter="error" rows={rows.slice(0, 3)} />);
    expect(screen.getByText('No Error rows.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Download Error Report' })).toBeDisabled();
  });

  it('keeps a large preview available while bounding rendered DOM rows', () => {
    const largeRows = Array.from({ length: 1000 }, (_, index): ExcelImportPreviewRow => ({
      id: `row-${index}`,
      status: 'new',
      sheet: 'EAL',
      cell: `C${index + 2}`,
      tensionLength: `TL${index + 1}`,
      importedValue: 11 - index / 100,
    }));
    render(<ExcelWearImportPreviewTable {...baseProps()} rows={largeRows} />);

    expect(screen.getAllByRole('row')).toHaveLength(101);
    expect(screen.getByText('TL100')).toBeInTheDocument();
    expect(screen.queryByText('TL101')).not.toBeInTheDocument();
    expect(screen.getByText('1-100 of 1000 filtered rows (1000 total)')).toBeInTheDocument();
    expect(screen.getAllByRole('columnheader')).toHaveLength(10);
  });
});
