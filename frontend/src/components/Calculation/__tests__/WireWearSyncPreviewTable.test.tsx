import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { describe, expect, it, vi } from 'vitest';

import WireWearSyncPreviewTable, {
  type WireWearSyncPreviewRow,
} from '../WireWearSyncPreviewTable';

const key = (suffix: string) => ({
  lineGroup: 'EAL',
  lineClass: suffix === 'LMC' ? 'LMC' : 'EAL',
  cycleDate: '2026-08-01',
  tensionLength: `TL-${suffix}`,
});

const rows: WireWearSyncPreviewRow[] = [
  { id: 'new', status: 'new', key: key('NEW'), incoming: { avgWearMin: 11.1, updatedAt: '2026-08-07T10:00:00Z' } },
  { id: 'update', status: 'update', key: key('UPDATE'), local: { avgWearMin: 11.3 }, incoming: { avgWearMin: 11.0 } },
  { id: 'local', status: 'keep_local', key: key('LOCAL'), detail: 'Local change is newer.' },
  { id: 'same', status: 'no_change', key: key('SAME') },
  {
    id: 'conflict', status: 'conflict', key: key('LMC'),
    local: { avgWearMin: 11.2, track: 'UP', updatedAt: '2026-08-07T11:00:00Z', source: 'Local PC' },
    incoming: { avgWearMin: 10.8, track: 'DOWN', updatedAt: '2026-08-07T11:00:00Z', source: 'Remote PC' },
  },
  { id: 'error', status: 'error', key: key('ERROR'), detail: 'Incoming record has invalid metadata.' },
  {
    id: 'delete', status: 'delete', key: key('DELETE'),
    local: { avgWearMin: 10.7, updatedAt: '2026-08-01T09:00:00Z' },
    incoming: { deletedAt: '2026-08-07T12:00:00Z', source: 'Remote PC' },
  },
];

const baseProps = () => ({
  rows,
  filter: 'all' as const,
  onFilterChange: vi.fn(),
  onResolveConflict: vi.fn(),
});

describe('WireWearSyncPreviewTable', () => {
  it('renders every sync action and stable full-identity columns', () => {
    render(<WireWearSyncPreviewTable {...baseProps()} />);
    const table = screen.getByRole('table', { name: 'Wire Wear sync preview' });
    expect(within(table).getAllByRole('columnheader').map(cell => cell.textContent)).toEqual([
      'Action', 'Line', 'Class', 'Cycle Date', 'Tension Length', 'Local', 'Incoming', 'Decision / Detail',
    ]);
    ['New', 'Update', 'Keep Local', 'No Change', 'Conflict', 'Error', 'Delete'].forEach(label => {
      expect(screen.getAllByText(label)).not.toHaveLength(0);
    });
    expect(screen.getByText('LMC')).toBeInTheDocument();
    expect(screen.getByText('TL-LMC')).toBeInTheDocument();
  });

  it('emits all controlled status filters with accurate counts', async () => {
    const props = baseProps();
    const user = userEvent.setup();
    render(<WireWearSyncPreviewTable {...props} />);

    expect(screen.getByRole('button', { name: 'Show All actions' })).toHaveTextContent('All 7');
    expect(screen.getByRole('button', { name: 'Show Delete actions' })).toHaveTextContent('Delete 1');
    await user.click(screen.getByRole('button', { name: 'Show Keep Local actions' }));
    expect(props.onFilterChange).toHaveBeenCalledWith('keep_local');
  });

  it('shows local and incoming conflict values and emits an explicit resolution', async () => {
    const props = baseProps();
    const user = userEvent.setup();
    render(<WireWearSyncPreviewTable {...props} filter="conflict" />);

    expect(screen.getByText('Wear 11.200')).toBeInTheDocument();
    expect(screen.getByText('Wear 10.800')).toBeInTheDocument();
    expect(screen.getByText('Local PC')).toBeInTheDocument();
    expect(screen.getByText('Remote PC')).toBeInTheDocument();
    const group = screen.getByRole('radiogroup', { name: /Resolve conflict EAL LMC 2026-08-01 TL-LMC/ });
    await user.click(within(group).getByRole('radio', { name: 'Use Incoming' }));
    expect(props.onResolveConflict).toHaveBeenCalledWith('conflict', 'incoming');
  });

  it('keeps Delete and Error semantics visible without decision controls', () => {
    const props = baseProps();
    const { rerender } = render(<WireWearSyncPreviewTable {...props} filter="delete" />);
    expect(screen.getByText('Incoming tombstone deletes the local record.')).toBeInTheDocument();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();

    rerender(<WireWearSyncPreviewTable {...props} filter="error" />);
    expect(screen.getByText('Incoming record has invalid metadata.')).toBeInTheDocument();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
  });

  it('keeps a large result scrollable without changing its table structure', () => {
    const largeRows = Array.from({ length: 60 }, (_, index): WireWearSyncPreviewRow => ({
      id: `row-${index}`,
      status: index % 2 ? 'update' : 'new',
      key: { ...key(`${index}`), tensionLength: `TL-${index + 1}` },
      incoming: { avgWearMin: 11 - index / 100 },
    }));
    render(<WireWearSyncPreviewTable {...baseProps()} rows={largeRows} />);
    expect(screen.getAllByRole('row')).toHaveLength(61);
    expect(screen.getByText('TL-60')).toBeInTheDocument();
    expect(screen.getAllByRole('columnheader')).toHaveLength(8);
  });
});
