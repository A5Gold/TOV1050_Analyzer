import { render, screen, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';

import WearDashboardPanel from '../WearDashboardPanel';
import { useWearRecordsStore } from '../../../store/useWearRecordsStore';

describe('WearDashboardPanel', () => {
  beforeEach(() => {
    useWearRecordsStore.setState({
      dashboard: {
        line_groups: {
          EAL: { top_max_rate: [], top_min_rate: [], top_current_wear: [] },
          TML: { top_max_rate: [], top_min_rate: [], top_current_wear: [] },
        },
      },
      loadDashboard: vi.fn(),
    } as any);
  });

  it('renders exactly three rankings and filters them by line group', () => {
    render(<WearDashboardPanel />);

    expect(screen.getByRole('button', { name: 'All' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'EAL' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'TML' })).toBeInTheDocument();
    expect(screen.getAllByRole('table')).toHaveLength(3);
    expect(screen.getByText('Top 5 Max Wear Rate')).toBeInTheDocument();
    expect(screen.getByText('Top 5 Min Positive Wear Rate')).toBeInTheDocument();
    expect(screen.getByText('Top 5 Current Wear')).toBeInTheDocument();
  });

  it('renders nullable trend values without crashing and includes the approved quality fields', () => {
    useWearRecordsStore.setState({
      dashboard: {
        line_groups: {
          EAL: {
            top_max_rate: [],
            top_min_rate: [],
            top_current_wear: [{
              line_group: 'EAL', tension_length: '28', latest_cycle_date: '2026-05-28',
              latest_wear_percentage: 22.73, latest_avg_wear_min: 10.2,
              wear_percent_per_year: null, wear_mm_per_year: null,
              r_squared: null, trend_status: 'insufficient_data', record_count: 1,
            }],
          },
          TML: { top_max_rate: [], top_min_rate: [], top_current_wear: [] },
        },
      },
    } as any);

    render(<WearDashboardPanel />);

    const current = screen.getByRole('table', { name: 'Top 5 Current Wear' });
    expect(within(current).getByText('10.200')).toBeInTheDocument();
    expect(within(current).getByText('insufficient_data')).toBeInTheDocument();
    expect(within(current).getAllByText('-').length).toBeGreaterThan(0);
    expect(within(current).getByRole('columnheader', { name: 'R²' })).toBeInTheDocument();
  });

  it('globally sorts and caps All rankings across EAL and TML', () => {
    const row = (line: 'EAL' | 'TML', tensionLength: string, mmRate: number, wear: number) => ({
      line_group: line, tension_length: tensionLength, latest_cycle_date: '2026-05-28',
      latest_wear_percentage: wear, latest_avg_wear_min: 13.2 - wear / 10,
      wear_percent_per_year: mmRate * 10, wear_mm_per_year: mmRate,
      r_squared: 0.91, trend_status: 'eligible', record_count: 3,
    });
    useWearRecordsStore.setState({
      dashboard: {
        line_groups: {
          EAL: {
            top_max_rate: [row('EAL', 'E1', 9, 10), row('EAL', 'E2', 8, 20), row('EAL', 'E3', 7, 30)],
            top_min_rate: [row('EAL', 'E3', 7, 30), row('EAL', 'E2', 8, 20), row('EAL', 'E1', 9, 10)],
            top_current_wear: [row('EAL', 'E3', 7, 30), row('EAL', 'E2', 8, 20), row('EAL', 'E1', 9, 10)],
          },
          TML: {
            top_max_rate: [row('TML', 'T1', 12, 60), row('TML', 'T2', 11, 50), row('TML', 'T3', 10, 40)],
            top_min_rate: [row('TML', 'T3', 10, 40), row('TML', 'T2', 11, 50), row('TML', 'T1', 12, 60)],
            top_current_wear: [row('TML', 'T1', 12, 60), row('TML', 'T2', 11, 50), row('TML', 'T3', 10, 40)],
          },
        },
      },
    } as any);

    render(<WearDashboardPanel />);

    const cells = (name: string) => within(screen.getByRole('table', { name })).getAllByRole('row')
      .slice(1).map(tableRow => within(tableRow).getAllByRole('cell')[2].textContent);
    expect(cells('Top 5 Max Wear Rate')).toEqual(['T1', 'T2', 'T3', 'E1', 'E2']);
    expect(cells('Top 5 Min Positive Wear Rate')).toEqual(['E3', 'E2', 'E1', 'T3', 'T2']);
    expect(cells('Top 5 Current Wear')).toEqual(['T1', 'T2', 'T3', 'E3', 'E2']);
  });
});
