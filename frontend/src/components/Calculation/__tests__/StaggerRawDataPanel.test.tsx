import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import * as XLSX from 'xlsx';

import StaggerRawDataPanel from '../StaggerRawDataPanel';
import type { StaggerResult } from '../../../types/api';

const plotSpy = vi.fn(() => <div data-testid="plotly-chart" />);

vi.mock('react-plotly.js', () => ({
  __esModule: true,
  default: (props: any) => plotSpy(props),
}));

vi.mock('xlsx', () => ({
  read: vi.fn(),
  utils: {
    sheet_to_json: vi.fn(),
  },
}));

const baseResult: StaggerResult = {
  id: 'SG-001',
  line: 'EAL',
  track: 'UP',
  exception_type: 'Stagger Left',
  max_location: 120,
  chi: 120,
  overall_result: 'pass',
  trace_available: true,
  from_m: 100,
  to_m: 140,
  remark: [],
};

const createWorkbookFile = () => {
  const file = new File([new Uint8Array([1, 2, 3])], 'raw-data.xlsx');
  Object.defineProperty(file, 'arrayBuffer', {
    value: vi.fn().mockResolvedValue(new ArrayBuffer(8)),
  });
  return file;
};

describe('StaggerRawDataPanel', () => {
  beforeEach(() => {
    plotSpy.mockClear();
    vi.clearAllMocks();
  });

  it('shows an empty state before a summary row is selected', () => {
    render(<StaggerRawDataPanel file={null} result={null} />);

    expect(screen.getByText('請先在摘要表選擇一筆結果，再查看對應的 Raw Data。')).toBeInTheDocument();
  });

  it('shows a no-data hint when the filtered chart window has no chart points', async () => {
    vi.mocked(XLSX.read).mockReturnValue({ Sheets: { ChartData: {} } } as any);
    vi.mocked(XLSX.utils.sheet_to_json).mockReturnValue([
      { Chainage: 10, stagger1: 1 },
      { Chainage: 20, stagger1: 2 },
    ] as any);

    const file = createWorkbookFile();
    render(<StaggerRawDataPanel file={file} result={baseResult} />);

    await waitFor(() => {
      expect(screen.getByText('在指定的 Chainage 範圍內找不到可繪圖的 stagger 資料。請確認 ChartData 工作表包含 chainage 與 stagger 欄位。')).toBeInTheDocument();
    });
  });

  it('renders the local chart helper text when chart data is available', async () => {
    vi.mocked(XLSX.read).mockReturnValue({ Sheets: { ChartData: {} } } as any);
    vi.mocked(XLSX.utils.sheet_to_json).mockReturnValue([
      { Chainage: 100, stagger1: 1.1, stagger2: 1.2 },
      { Chainage: 120, stagger1: 1.3, stagger2: 1.4 },
      { Chainage: 140, stagger1: 1.5, stagger2: 1.6 },
    ] as any);

    const file = createWorkbookFile();
    render(<StaggerRawDataPanel file={file} result={baseResult} />);

    await waitFor(() => {
      expect(screen.getByText('目前顯示 50m 到 190m 的區間，紅色區塊代表 alarm range，虛線代表 MaxLocation。')).toBeInTheDocument();
    });

    expect(screen.getByTestId('plotly-chart')).toBeInTheDocument();
    const props = plotSpy.mock.calls.at(-1)?.[0];
    expect(props.data).toHaveLength(4);
    expect(props.layout.title.text).toBe('SG-001 - Stagger vs Chainage');
  });
});
