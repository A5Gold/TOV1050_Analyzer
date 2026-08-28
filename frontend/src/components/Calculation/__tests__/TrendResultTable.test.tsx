import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import TrendResultTable from '../TrendResultTable';
import type { TrendResult } from '../../../types/api';

const { aoaToSheetMock, writeFileMock } = vi.hoisted(() => ({
  aoaToSheetMock: vi.fn(() => ({})),
  writeFileMock: vi.fn(),
}));

vi.mock('xlsx', () => ({
  utils: {
    aoa_to_sheet: aoaToSheetMock,
    book_new: vi.fn(() => ({})),
    book_append_sheet: vi.fn(),
  },
  writeFile: writeFileMock,
}));

vi.mock('@mui/x-data-grid', async () => {
  const actual = await vi.importActual('@mui/x-data-grid');
  return {
    ...actual,
    DataGrid: ({ rows, columns }: { rows: any[]; columns: any[] }) => (
      <div data-testid="mock-datagrid">
        <div data-testid="column-headers">
          {columns.map((col: any) => (
            <span key={col.field} data-testid={`col-${col.field}`}>
              {col.headerName}
            </span>
          ))}
        </div>
        {rows.map((row: any) => (
          <div key={row.id} data-testid={`row-${row.exception_id}`}>
            {columns.map((col: any) => {
              const value = row[col.field];
              if (col.renderCell) {
                const rendered = col.renderCell({ value, row });
                return (
                  <span key={col.field} data-testid={`cell-${row.exception_id}-${col.field}`}>
                    {rendered}
                  </span>
                );
              }
              return (
                <span key={col.field} data-testid={`cell-${row.exception_id}-${col.field}`}>
                  {String(value ?? '')}
                </span>
              );
            })}
          </div>
        ))}
      </div>
    ),
  };
});

const makeTrendResult = (overrides: Partial<TrendResult> = {}): TrendResult => ({
  exception_id: 'EXC-001',
  task_run_date: '2024-01-01',
  line: 'EAL',
  track: 'UP',
  section: 'S1',
  task_no: 'T001',
  station_start: 'A',
  station_end: 'B',
  tension_length: 'TL-A',
  from_m: 100,
  to_m: 120,
  max_value: 11.5,
  max_location: 105.5,
  level: 'L2',
  dates: ['2024-01-01', '2023-12-01'],
  record_points: [11.5, 11.8],
  trend_points: [12.0, 12.3],
  trend_next: 12.5,
  logic_1: true,
  logic_2: false,
  recommendation: 'confirmed valid L2',
  ...overrides,
});

describe('TrendResultTable', () => {
  beforeEach(() => {
    aoaToSheetMock.mockClear();
    writeFileMock.mockClear();
  });

  it('renders key result columns', () => {
    render(<TrendResultTable results={[makeTrendResult()]} onViewChart={vi.fn()} selectedId={null} />);

    expect(screen.getByTestId('col-exception_id')).toBeInTheDocument();
    expect(screen.getByTestId('col-max_location')).toBeInTheDocument();
    expect(screen.getByTestId('col-logic_1')).toBeInTheDocument();
    expect(screen.getByTestId('col-logic_2')).toBeInTheDocument();
    expect(screen.getByTestId('col-recommendation')).toBeInTheDocument();
  });

  it('places recommendation and logic columns near the left edge for quick review', () => {
    render(<TrendResultTable results={[makeTrendResult()]} onViewChart={vi.fn()} selectedId={null} />);

    const headers = Array.from(screen.getByTestId('column-headers').querySelectorAll('span'))
      .map((element) => element.textContent);

    expect(headers.slice(0, 5)).toEqual(['Chart', 'Recommendation', 'Logic 1', 'Logic 2', 'ID']);
  });

  it('disables export when there are no results', () => {
    render(<TrendResultTable results={[]} onViewChart={vi.fn()} selectedId={null} />);

    expect(screen.getByRole('button', { name: /export excel/i })).toBeDisabled();
  });

  it('exports trend results to excel with the expected filename', () => {
    render(<TrendResultTable results={[makeTrendResult()]} onViewChart={vi.fn()} selectedId={null} />);

    fireEvent.click(screen.getByRole('button', { name: /export excel/i }));

    expect(writeFileMock).toHaveBeenCalledTimes(1);
    expect(writeFileMock.mock.calls[0]?.[1]).toBe('20240101_EAL_T001_A-B_Wire_Wear_L2_Trend_Report.xlsx');
  });

  it('exports recommendation and logic columns near the left edge for quick review', () => {
    render(<TrendResultTable results={[makeTrendResult()]} onViewChart={vi.fn()} selectedId={null} />);

    fireEvent.click(screen.getByRole('button', { name: /export excel/i }));

    const [sheetRows] = aoaToSheetMock.mock.calls[0] ?? [];
    expect(sheetRows[0].slice(0, 11)).toEqual([
      'Chart',
      'Recommendation',
      'Logic 1',
      'Logic 2',
      'ID',
      'Task Run Date',
      'Line',
      'Track',
      'Section',
      'Task No',
      'Stn Start',
    ]);
  });

  it('renders recommendation chips', () => {
    render(
      <TrendResultTable
        results={[
          makeTrendResult({ exception_id: 'EXC-001', recommendation: 'confirmed valid L2' }),
          makeTrendResult({ exception_id: 'EXC-002', recommendation: 'verify on site' }),
          makeTrendResult({ exception_id: 'EXC-003', recommendation: 'no action required' }),
        ]}
        onViewChart={vi.fn()}
        selectedId={null}
      />
    );

    expect(screen.getByTestId('recommendation-chip-EXC-001')).toHaveTextContent('confirmed valid L2');
    expect(screen.getByTestId('recommendation-chip-EXC-002')).toHaveTextContent('verify on site');
    expect(screen.getByTestId('recommendation-chip-EXC-003')).toHaveTextContent('no action required');
  });
});
