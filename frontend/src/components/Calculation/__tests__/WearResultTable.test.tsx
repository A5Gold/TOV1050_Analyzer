import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom';
import WearResultTable from '../WearResultTable';
import type { WearCycleRecord } from '../../../types/api';

const gridSpy = vi.hoisted(() => vi.fn());
vi.mock('@mui/x-data-grid', () => ({ DataGrid: ({ rows, columns }: any) => { gridSpy({ rows, columns }); const intervalColumn = columns.find((column: any) => column.field === 'intervalCount'); return <div><div data-testid="column-headers">{columns.map((column: any) => <span key={column.field}>{column.headerName}</span>)}</div>{rows.map((row: any) => <div key={row.id} data-testid={`row-${row.id}`}>{row.tensionLength}{intervalColumn?.renderCell && <span data-testid={`interval-${row.tensionLength}`}>{intervalColumn.renderCell({ row, value: row.intervalCount })}</span>}</div>)}</div>; } }));

const record = (tensionLength: string, fromM: number, overrides: Partial<WearCycleRecord> = {}): WearCycleRecord => ({
  key: { lineGroup: 'EAL', cycleDate: '2026-05-28', tensionLength }, track: 'Siding', fromM, toM: fromM + 10,
  avgWearMin: 10.4, wearPercentage: 18.49, measurementSd: 0.2, hasDataConflict: true, conflictIds: ['c1'], updatedAt: null,
  intervalCount: 1, intervals: [{ track: 'Siding', fromM, toM: fromM + 10 }], ...overrides,
});

describe('WearResultTable', () => {
  it('renders approved complete-cycle columns in backend canonical order', () => {
    render(<WearResultTable rows={[record('28', 20)]} />);
    expect(screen.getByTestId('column-headers').textContent).toBe('Cycle DateLineTrackTension LengthFrom (m)To (m)IntervalsAvg Wear MinWear %Measurement SD');
  });

  it('defaults to canonical From ascending order', () => {
    gridSpy.mockClear();
    render(<WearResultTable rows={[record('10', 100), record('2', 20), record('1', 10), record('101', 1010)]} />);
    expect(gridSpy.mock.calls[0][0].rows.map((row: WearCycleRecord) => row.key.tensionLength)).toEqual(['1', '2', '10', '101']);
  });

  it('shows the interval count with ordered physical details without changing bounding values', () => {
    render(<WearResultTable rows={[record('28', 10, {
      toM: 30,
      intervalCount: 2,
      intervals: [
        { track: 'UP', fromM: 10, toM: 14 },
        { track: 'DN', fromM: 20, toM: 30 },
      ],
    })]} />);

    const cell = screen.getByTestId('interval-28');
    expect(cell).toHaveTextContent('2');
    expect(cell.querySelector('[aria-label]')).toHaveAttribute(
      'aria-label',
      'UP 10-14\nDN 20-30',
    );
    expect(gridSpy.mock.calls.at(-1)?.[0].rows[0]).toMatchObject({ fromM: 10, toM: 30 });
  });

  it('wires natural tension length sorting into the DataGrid column', () => {
    gridSpy.mockClear();
    render(<WearResultTable rows={[record('1', 1)]} />);
    const column = gridSpy.mock.calls[0][0].columns.find((item: any) => item.field === 'tensionLength');
    expect(['10', '2', '101', '1'].sort(column.sortComparator)).toEqual(['1', '2', '10', '101']);
  });
});
