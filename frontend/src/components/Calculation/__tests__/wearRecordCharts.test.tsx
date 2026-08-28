import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import '@testing-library/jest-dom';

import {
  AllTensionLengthOverviewChart,
  TensionLengthTrendChart,
} from '../wearRecordCharts';
import type { WireWearSavedRecord } from '../../../types/api';

const plotSpy = vi.hoisted(() => vi.fn());

vi.mock('react-plotly.js', () => ({
  default: (props: any) => {
    plotSpy(props);
    return <div data-testid="plot" />;
  },
}));

const record = (overrides: Partial<WireWearSavedRecord> = {}): WireWearSavedRecord => ({
  record_id: 1,
  line_group: 'EAL',
  line_class: 'EAL',
  track: 'UP',
  section: 'Mainline',
  cycle_date: '2026-01-01',
  tension_length: 'TL1',
  from_m: 0,
  to_m: 10,
  avg_wear_min: 10.5,
  sd: 0.1,
  wear_percentage: 8,
  source_file_names: [],
  saved_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
  saved_by: 'tester',
  ...overrides,
});

describe('wearRecordCharts', () => {
  it('is not rendered by the staged records workbench', async () => {
    const source = await import('../WearRecordsPanel?raw').then(module => String(module.default));
    expect(source).not.toContain('TensionLengthTrendChart');
    expect(source).not.toContain('AllTensionLengthOverviewChart');
  });
  it('renders trend by Avg Wear Min with date-only x-axis formatting', () => {
    plotSpy.mockClear();

    render(
      <TensionLengthTrendChart
        records={[
          record({ record_id: 2, cycle_date: '2026-03-31', avg_wear_min: 9.8, wear_percentage: 16 }),
          record({ record_id: 1, cycle_date: '2026-01-01', avg_wear_min: 10.5, wear_percentage: 8 }),
        ]}
        metric="avg_wear_min"
      />,
    );

    const props = plotSpy.mock.calls[0][0];
    expect(props.data[0].y).toEqual([10.5, 9.8]);
    expect(props.layout.xaxis.type).toBe('date');
    expect(props.layout.xaxis.tickformat).toBe('%Y-%m-%d');
    expect(props.layout.yaxis.title.text).toBe('Avg Wear Min');
  });

  it('renders all tension lengths by selected metric', () => {
    plotSpy.mockClear();

    render(
      <AllTensionLengthOverviewChart
        records={[
          record({ tension_length: 'TL2', from_m: 20, avg_wear_min: 9.5, wear_percentage: 20 }),
          record({ tension_length: 'TL1', from_m: 0, avg_wear_min: 10.5, wear_percentage: 8 }),
        ]}
        metric="wear_percentage"
      />,
    );

    expect(screen.getByTestId('plot')).toBeInTheDocument();
    const props = plotSpy.mock.calls[0][0];
    expect(props.data[0].x).toEqual(['TL1', 'TL2']);
    expect(props.data[0].y).toEqual([8, 20]);
    expect(props.layout.yaxis.title.text).toBe('Wear %');
  });
});
