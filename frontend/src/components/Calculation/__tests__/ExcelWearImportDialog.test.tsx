import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import ExcelWearImportDialog, {
  type ExcelWearImportDialogProps,
} from '../ExcelWearImportDialog';

const sheets = [
  { name: 'EAL', support: 'supported' as const, selected: true, enabled: true },
  { name: 'TML', support: 'supported' as const, selected: true, enabled: true },
  { name: 'LMC', support: 'supported' as const, selected: true, enabled: true },
  { name: 'LRL', support: 'reserved' as const, selected: false, enabled: false, reason: 'Reserved for future support' },
  { name: 'Notes', support: 'ignored' as const, selected: false, enabled: false, reason: 'Ignored' },
];

const sheetSummaries = [
  { sheetName: 'EAL', skipped: 2, new: 1, update: 1, noChange: 1, duplicate: 0, error: 1, total: 4 },
  { sheetName: 'TML', skipped: 0, new: 1, update: 0, noChange: 0, duplicate: 0, error: 0, total: 1 },
];

const rows = [
  { id: 'new-1', status: 'new' as const, sheet: 'EAL', cell: 'C4', importedValue: 11.1 },
  { id: 'update-1', status: 'update' as const, sheet: 'EAL', cell: 'D4', importedValue: 10.9, existingValue: 11.2 },
  { id: 'same-1', status: 'no_change' as const, sheet: 'TML', cell: 'E5', importedValue: 10.5 },
  { id: 'error-1', status: 'error' as const, sheet: 'EAL', cell: 'F6', originalValue: 'bad', reason: 'Invalid number.', excluded: false },
];

const baseProps = (): ExcelWearImportDialogProps => ({
  open: true,
  phase: 'select',
  fileName: 'historical.xlsx',
  sheets,
  sheetSummaries,
  rows,
  filter: 'all',
  onFileSelect: vi.fn(),
  onSheetToggle: vi.fn(),
  onPreview: vi.fn(),
  onPhaseChange: vi.fn(),
  onFilterChange: vi.fn(),
  onExcludeError: vi.fn(),
  onDownloadErrorReport: vi.fn(),
  onConfirmAndStage: vi.fn(),
  onClose: vi.fn(),
});

const setViewportMatch = (matches: boolean) => {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation(() => ({
      matches,
      media: '(max-width:599.95px)',
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
};

describe('ExcelWearImportDialog', () => {
  afterEach(() => vi.restoreAllMocks());

  it('discovers supported, reserved, and ignored worksheets without hiding them', async () => {
    setViewportMatch(false);
    const props = baseProps();
    const user = userEvent.setup();
    render(<ExcelWearImportDialog {...props} />);

    expect(screen.getByRole('dialog', { name: /Import Wire Wear Excel/ })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Select worksheet EAL' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Select worksheet LRL' })).toBeDisabled();
    expect(screen.getByText('Reserved for future support')).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Select worksheet Notes' })).toBeDisabled();
    expect(screen.getByText('Ignored')).toBeInTheDocument();

    await user.click(screen.getByRole('checkbox', { name: 'Select worksheet EAL' }));
    expect(props.onSheetToggle).toHaveBeenCalledWith('EAL', false);
    await user.click(screen.getByRole('button', { name: 'Preview' }));
    expect(props.onPreview).toHaveBeenCalledTimes(1);
  });

  it('emits the selected xlsx file and requires one supported sheet', () => {
    setViewportMatch(false);
    const props = baseProps();
    props.fileName = null;
    props.sheets = sheets.map(sheet => ({ ...sheet, selected: false }));
    const { rerender } = render(<ExcelWearImportDialog {...props} />);

    expect(screen.getByRole('button', { name: 'Preview' })).toBeDisabled();
    const file = new File(['workbook'], 'wear.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    fireEvent.change(screen.getByLabelText('Historical workbook file'), { target: { files: [file] } });
    expect(props.onFileSelect).toHaveBeenCalledWith(file);

    rerender(<ExcelWearImportDialog {...props} fileName="wear.xlsx" />);
    expect(screen.getByRole('button', { name: 'Preview' })).toBeDisabled();
  });

  it('shows per-sheet and total preview counts and advances to confirmation', async () => {
    setViewportMatch(false);
    const props = baseProps();
    props.phase = 'preview';
    const user = userEvent.setup();
    render(<ExcelWearImportDialog {...props} />);

    const status = screen.getByRole('status');
    expect(status).toHaveTextContent('Total 5');
    expect(status).toHaveTextContent('New 2');
    expect(status).toHaveTextContent('Update 1');
    expect(status).toHaveTextContent('No Change 1');
    expect(status).toHaveTextContent('Error 1');
    expect(screen.getByLabelText('Worksheet summaries')).toHaveTextContent('EAL 4 rows, 1 errors');
    expect(screen.getByLabelText('Worksheet summaries')).toHaveTextContent('TML 1 rows, 0 errors');

    await user.click(screen.getByRole('button', { name: 'Show Update rows' }));
    expect(props.onFilterChange).toHaveBeenCalledWith('update');
    await user.click(screen.getByRole('button', { name: 'Review Stage' }));
    expect(props.onFilterChange).toHaveBeenCalledWith('all');
    expect(props.onPhaseChange).toHaveBeenCalledWith('confirm');
  });

  it('blocks unresolved errors and stages only New and Update rows after exclusion', async () => {
    setViewportMatch(false);
    const props = baseProps();
    props.phase = 'confirm';
    const user = userEvent.setup();
    const { rerender } = render(<ExcelWearImportDialog {...props} />);

    expect(screen.getByText('1 error rows must be corrected or explicitly excluded.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm & Stage (2)' })).toBeDisabled();

    const excludedRows = rows.map(row => row.id === 'error-1' ? { ...row, excluded: true } : row);
    rerender(<ExcelWearImportDialog {...props} rows={excludedRows} />);
    expect(screen.getByText(/2 New or Update rows will enter/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Confirm & Stage (2)' }));
    expect(props.onConfirmAndStage).toHaveBeenCalledWith([excludedRows[0], excludedRows[1]]);
  });

  it('prevents duplicate actions while loading or staging', () => {
    setViewportMatch(false);
    const loadingProps = baseProps();
    loadingProps.isLoading = true;
    const { rerender } = render(<ExcelWearImportDialog {...loadingProps} />);
    expect(screen.getByRole('progressbar', { name: 'Loading Excel import' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Loading...' })).toBeDisabled();

    const submittingProps = baseProps();
    submittingProps.phase = 'confirm';
    submittingProps.rows = rows.map(row => row.id === 'error-1' ? { ...row, excluded: true } : row);
    submittingProps.isSubmitting = true;
    rerender(<ExcelWearImportDialog {...submittingProps} />);
    expect(screen.getByRole('button', { name: 'Staging...' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Close Import Wire Wear Excel' })).toBeDisabled();
  });

  it('uses a full-screen dialog on a narrow viewport and exposes all three phases', () => {
    setViewportMatch(true);
    render(<ExcelWearImportDialog {...baseProps()} />);
    const dialog = screen.getByRole('dialog', { name: /Import Wire Wear Excel/ });
    expect(dialog).toHaveClass('MuiDialog-paperFullScreen');
    expect(within(dialog).getByText('Select')).toBeInTheDocument();
    expect(within(dialog).getAllByText('Preview')).not.toHaveLength(0);
    expect(within(dialog).getByText('Confirm & Stage')).toBeInTheDocument();
  });
});
