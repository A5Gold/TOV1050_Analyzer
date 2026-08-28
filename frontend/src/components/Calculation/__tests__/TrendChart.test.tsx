import React from 'react';
import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import TrendChart from '../TrendChart';

const plotSpy = vi.fn(() => <div data-testid="plotly-chart" />);

vi.mock('react-plotly.js', () => ({
  __esModule: true,
  default: (props: any) => plotSpy(props),
}));

describe('TrendChart', () => {
  it('limits x-axis categories to dates with actual record or trend data', () => {
    render(
      <TrendChart
        result={{
          exception_id: 'EX-001',
          task_run_date: '2026-03-01',
          line: 'EAL',
          track: 'UP',
          section: 'Mainline',
          task_no: 'T01',
          station_start: 'A',
          station_end: 'B',
          tension_length: 'T3',
          from_m: 1000,
          to_m: 1100,
          level: 'L2',
          dates: ['2026-03-01', '2026-02-01', '2026-01-01', '2025-12-01'],
          record_points: [10.3, 10.2, null, null],
          trend_points: [10.1, 10.0, null as any, null as any],
          trend_next: 10.1,
          logic_1: true,
          logic_2: false,
          recommendation: 'confirmed valid L2',
          max_value: 10.3,
          max_location: 1010,
        }}
      />
    );

    const props = plotSpy.mock.calls.at(-1)?.[0];
    expect(props.data[0].x).toEqual(['2026-02-01', '2026-03-01']);
    expect(props.data[1].x).toEqual(['2026-02-01', '2026-03-01']);
  });

  it('uses a date axis and renders the regression trend as one straight endpoint line', () => {
    render(
      <TrendChart
        result={{
          exception_id: 'EX-002',
          task_run_date: '2026-06-11',
          line: 'EAL',
          track: 'UP',
          section: 'Mainline',
          task_no: 'U2',
          station_start: 'FOT',
          station_end: 'TAP',
          tension_length: '39',
          from_m: 113000,
          to_m: 113100,
          level: 'L2',
          dates: ['2026-06-11', '2026-05-21', '2026-04-12', '2026-02-05', '2026-01-15', '2025-12-28'],
          record_points: [9.61, 9.77, 9.8, 10.16, 10.27, 10.39],
          trend_points: [9.62, 9.71, 9.88, 10.16, 10.27, 10.37],
          trend_next: 9.62,
          logic_1: true,
          logic_2: false,
          recommendation: 'confirmed valid L2',
          max_value: 9.61,
          max_location: 113050,
        }}
      />
    );

    const props = plotSpy.mock.calls.at(-1)?.[0];
    expect(props.layout.xaxis.type).toBe('date');
    expect(props.data[1].mode).toBe('lines');
    expect(props.data[1].x).toEqual(['2025-12-28', '2026-06-11']);
    expect(props.data[1].y).toEqual([10.37, 9.62]);
  });

  it('renders a clean title with only ID and task run date', () => {
    render(
      <TrendChart
        result={{
          exception_id: '20260130_TML_UP_W2',
          task_run_date: '2026-01-20',
          line: 'TML',
          track: 'UP',
          section: 'Mainline',
          task_no: 'W2',
          station_start: 'A',
          station_end: 'B',
          tension_length: 'T3',
          from_m: 1000,
          to_m: 1100,
          level: 'L2',
          dates: ['2026-01-20'],
          record_points: [10.3],
          trend_points: [10.1],
          trend_next: 10.1,
          logic_1: true,
          logic_2: false,
          recommendation: 'confirmed valid L2',
          max_value: 10.3,
          max_location: 1010,
        }}
      />
    );

    const props = plotSpy.mock.calls.at(-1)?.[0];
    expect(props.layout.title.text).toBe('20260130_TML_UP_W2 - 2026-01-20');
    expect(props.layout.title.text).not.toContain('??');
  });
});
