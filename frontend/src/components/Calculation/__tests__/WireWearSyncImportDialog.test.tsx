import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import WireWearSyncImportDialog, {
  type WireWearSyncImportDialogProps,
} from '../WireWearSyncImportDialog';

const conflictKey = {
  lineGroup: 'EAL', lineClass: 'LMC', cycleDate: '2026-08-01', tensionLength: 'TL-C',
};

const rows = [
  {
    id: 'new', status: 'new' as const,
    key: { lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-08-01', tensionLength: 'TL-N' },
    incoming: { avgWearMin: 11.1 },
  },
  {
    id: 'conflict', status: 'conflict' as const, key: conflictKey,
    local: { avgWearMin: 11.2, updatedAt: '2026-08-07T10:00:00Z' },
    incoming: { avgWearMin: 10.8, updatedAt: '2026-08-07T10:00:00Z' },
    resolution: null,
  },
  {
    id: 'delete', status: 'delete' as const,
    key: { lineGroup: 'TML', lineClass: 'TML', cycleDate: '2026-07-01', tensionLength: 'TL-D' },
    incoming: { deletedAt: '2026-08-07T12:00:00Z' },
  },
];

const baseProps = (): WireWearSyncImportDialogProps => ({
  open: true,
  phase: 'select',
  fileName: 'wear-cycle.json',
  packageInfo: {
    packageId: 'package-1', sourceWorkstation: 'Engineer-PC', exportedAt: '2026-08-07T09:00:00Z', schema: 'wear-cycle-v1',
  },
  rows,
  filter: 'all',
  onFileSelect: vi.fn(),
  onPreview: vi.fn(),
  onFilterChange: vi.fn(),
  onResolveConflict: vi.fn(),
  onConfirmImport: vi.fn(),
  onStartOver: vi.fn(),
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

describe('WireWearSyncImportDialog', () => {
  afterEach(() => vi.restoreAllMocks());

  it('selects a JSON package and starts the controlled preview', async () => {
    setViewportMatch(false);
    const props = baseProps();
    const user = userEvent.setup();
    render(<WireWearSyncImportDialog {...props} />);

    const file = new File(['{}'], 'incoming.json', { type: 'application/json' });
    fireEvent.change(screen.getByLabelText('Wire Wear data package file'), { target: { files: [file] } });
    expect(props.onFileSelect).toHaveBeenCalledWith(file);
    await user.click(screen.getByRole('button', { name: 'Preview Package' }));
    expect(props.onPreview).toHaveBeenCalledTimes(1);
  });

  it('blocks import while pending changes exist and explains unsupported packages', () => {
    setViewportMatch(false);
    const props = baseProps();
    const { rerender } = render(<WireWearSyncImportDialog {...props} guardState="pending_changes" />);
    expect(screen.getByText(/Save or discard pending Wire Wear changes/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Choose Another Package' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Preview Package' })).toBeDisabled();

    rerender(<WireWearSyncImportDialog {...props} guardState="unsupported_package" />);
    expect(screen.getByText(/not a supported wear-cycle-v1/)).toBeInTheDocument();
  });

  it('shows all preview counts and blocks unresolved conflicts', () => {
    setViewportMatch(false);
    const props = baseProps();
    props.phase = 'preview';
    render(<WireWearSyncImportDialog {...props} />);

    const status = screen.getByRole('status');
    expect(status).toHaveTextContent('Total 3');
    expect(status).toHaveTextContent('New 1');
    expect(status).toHaveTextContent('Conflict 1');
    expect(status).toHaveTextContent('Delete 1');
    expect(screen.getByText('Resolve all 1 conflicts before importing.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm Import' })).toBeDisabled();
  });

  it('sends complete conflict decisions and preserves Delete actions', async () => {
    setViewportMatch(false);
    const props = baseProps();
    props.phase = 'preview';
    props.rows = rows.map(row => row.id === 'conflict' ? { ...row, resolution: 'incoming' as const } : row);
    const user = userEvent.setup();
    render(<WireWearSyncImportDialog {...props} />);

    expect(screen.getByText('Incoming tombstone deletes the local record.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Confirm Import' }));
    expect(props.onConfirmImport).toHaveBeenCalledWith([{ key: conflictKey, choice: 'incoming' }]);
  });

  it('never treats Error rows as importable actions', () => {
    setViewportMatch(false);
    const props = baseProps();
    props.phase = 'preview';
    props.rows = [{
      id: 'error', status: 'error', key: conflictKey, detail: 'Invalid metadata fingerprint.',
    }];
    render(<WireWearSyncImportDialog {...props} />);
    expect(screen.getByText(/contains 1 blocking errors/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm Import' })).toBeDisabled();
  });

  it.each([
    ['stale_preview', 'Preview the package again'],
    ['backup_failure', 'backup could not be created'],
    ['apply_failure', 'transaction was rolled back'],
  ] as const)('renders the %s recovery state', (guardState, message) => {
    setViewportMatch(false);
    const props = baseProps();
    props.phase = 'preview';
    render(<WireWearSyncImportDialog {...props} guardState={guardState} />);
    expect(screen.getByText(new RegExp(message, 'i'))).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm Import' })).toBeDisabled();
  });

  it('prevents duplicate actions while previewing or applying', () => {
    setViewportMatch(false);
    const props = baseProps();
    const { rerender } = render(<WireWearSyncImportDialog {...props} isPreviewing />);
    expect(screen.getByRole('progressbar', { name: 'Previewing data package' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Previewing...' })).toBeDisabled();

    props.phase = 'preview';
    props.rows = rows.map(row => row.id === 'conflict' ? { ...row, resolution: 'local' as const } : row);
    rerender(<WireWearSyncImportDialog {...props} isApplying />);
    expect(screen.getByRole('progressbar', { name: 'Applying data package' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Importing...' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
  });

  it('renders the backup-aware success summary and completion actions', async () => {
    setViewportMatch(false);
    const props = baseProps();
    props.phase = 'success';
    props.successSummary = {
      created: 2, updated: 1, deleted: 1, keepLocal: 3, noChange: 4,
      conflictsResolved: 2, backupPath: 'C:\\backups\\wire-wear.db', dataVersion: 14,
    };
    const user = userEvent.setup();
    render(<WireWearSyncImportDialog {...props} />);
    const status = screen.getByRole('status');
    expect(status).toHaveTextContent('Created 2');
    expect(status).toHaveTextContent('Conflicts Resolved 2');
    expect(screen.getByText(/Backup created: C:\\backups\\wire-wear.db/)).toBeInTheDocument();
    expect(screen.getByText('Data version 14')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Import Another' }));
    expect(props.onStartOver).toHaveBeenCalledTimes(1);
  });

  it('uses a full-screen dialog on a narrow viewport with fixed primary actions', () => {
    setViewportMatch(true);
    const props = baseProps();
    props.phase = 'preview';
    render(<WireWearSyncImportDialog {...props} />);
    const dialog = screen.getByRole('dialog', { name: /Import Wire Wear Data Package/ });
    expect(dialog).toHaveClass('MuiDialog-paperFullScreen');
    expect(within(dialog).getByRole('button', { name: 'Confirm Import' })).toBeInTheDocument();
  });
});
