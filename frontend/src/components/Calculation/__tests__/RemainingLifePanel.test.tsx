import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import RemainingLifePanel from '../RemainingLifePanel';
import { useWearRecordsStore } from '../../../store/useWearRecordsStore';

vi.mock('react-plotly.js', () => ({ default: ({ data }: { data: Array<{ name: string; line?: { color?: string } }> }) => <div role="img" aria-label="remaining life chart" data-traces={JSON.stringify(data)} /> }));

const row = (overrides: Record<string, unknown> = {}) => ({
  lineGroup: 'EAL' as const, lineClass: 'EAL' as const, tensionLength: 'E01', track: 'UP', fromM: 0, toM: 10,
  latestCycleDate: '2026-01-01', latestAvgWearMin: 11.2, latestWearPercentage: 14,
  wearRatePercentPerYear: 1, wearRateMmPerYear: 0.2, observationCount: 3, rSquared: 0.9,
  trendStatus: 'eligible', projectedCrossingDate: '2032-01-01', projectedYear: 2032,
  yearsToThreshold: 6, remainingDays: 2100, curve: [{ date: '2026-01-01', remaining_days: 2100 }], ...overrides,
});

describe('RemainingLifePanel', () => {
  const loadRemainingLife = vi.fn();
  beforeEach(() => {
    loadRemainingLife.mockReset();
    useWearRecordsStore.setState({
      remainingLife: { thresholdMm: 10.2, rows: [row(), row({ tensionLength: 'E02', trendStatus: 'insufficient_data', wearRateMmPerYear: null, remainingDays: null, projectedCrossingDate: null, curve: [] }), row({ lineGroup: 'TML', lineClass: 'TML', tensionLength: 'T01', trendStatus: 'already_at_threshold', remainingDays: null, projectedCrossingDate: null, curve: [] })], defaultRows: [row()] },
      wearThresholdMm: 10.2,
      isRemainingLifeLoading: false, remainingLifeError: null, loadRemainingLife,
    } as any);
  });

  it('shows life estimate, N/A and semantic statuses', () => {
    render(<RemainingLifePanel />);
    expect(screen.getByText(/5y 8m/)).toBeInTheDocument();
    expect(screen.getAllByText('N/A').length).toBeGreaterThan(0);
    expect(screen.getByText('Insufficient data')).toBeInTheDocument();
    expect(screen.getByText('Already at threshold')).toBeInTheDocument();
    expect(screen.getAllByRole('img', { name: 'remaining life chart' })).toHaveLength(1);
  });

  it('shows non-positive rates explicitly and can clear selected curves', () => {
    useWearRecordsStore.setState({
      remainingLife: { thresholdMm: 10.2, rows: [row({ trendStatus: 'non_positive_rate', wearRateMmPerYear: null, remainingDays: null, projectedCrossingDate: null, curve: [{ date: '2026-01-01', remaining_days: 1 }] })], defaultRows: [] },
    } as any);
    render(<RemainingLifePanel />);
    expect(screen.getByText('Non-positive rate')).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: /^Add$/i })[0]);
    fireEvent.click(screen.getByRole('button', { name: /clear curve/i }));
    expect(screen.getByRole('button', { name: /^Add$/i })).toBeInTheDocument();
  });

  it('loads the shared threshold and allows adding a TL to the curve', () => {
    render(<RemainingLifePanel />);
    expect(loadRemainingLife).toHaveBeenCalledWith(10.2);
    fireEvent.click(screen.getAllByRole('button', { name: /^Add$/i })[0]);
    expect(screen.getByRole('button', { name: /^Remove$/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '9.1 mm' }));
    expect(loadRemainingLife).toHaveBeenLastCalledWith(9.1);
  });

  it('splits EAL and TML curves and applies the requested colors', () => {
    const eal = row();
    const tml = row({ lineGroup: 'TML', lineClass: 'TML', tensionLength: 'T01' });
    useWearRecordsStore.setState({
      remainingLife: { thresholdMm: 10.2, rows: [eal, tml], defaultRows: [eal, tml] },
    } as any);

    render(<RemainingLifePanel />);
    expect(screen.getByText('EAL remaining life curve')).toBeInTheDocument();
    expect(screen.getByText('TML remaining life curve')).toBeInTheDocument();
    const charts = screen.getAllByRole('img', { name: 'remaining life chart' });
    expect(charts).toHaveLength(2);
    expect(charts[0]).toHaveAttribute('data-traces', expect.stringContaining('#64b5f6'));
    expect(charts[1]).toHaveAttribute('data-traces', expect.stringContaining('#8d6e63'));
  });

  it('classifies estimated life at the approved 10-year and 30-year boundaries', () => {
    useWearRecordsStore.setState({
      remainingLife: {
        thresholdMm: 10.2,
        rows: [
          row({ tensionLength: 'NPR', trendStatus: 'non_positive_rate', remainingDays: null, projectedCrossingDate: null }),
          row({ tensionLength: 'Y10', remainingDays: 10 * 365.25 }),
          row({ tensionLength: 'Y30', remainingDays: 30 * 365.25 }),
          row({ tensionLength: 'Y31', remainingDays: 31 * 365.25 }),
        ],
        defaultRows: [],
      },
    } as any);

    render(<RemainingLifePanel />);
    expect(screen.getByText('Non-positive rate').closest('td')).toHaveAttribute('data-life-tone', 'grey');
    expect(screen.getByText(/10y 0m/).closest('td')).toHaveAttribute('data-life-tone', 'red');
    expect(screen.getByText(/30y 0m/).closest('td')).toHaveAttribute('data-life-tone', 'yellow');
    expect(screen.getByText(/31y 0m/).closest('td')).toHaveAttribute('data-life-tone', 'green');
  });
});
