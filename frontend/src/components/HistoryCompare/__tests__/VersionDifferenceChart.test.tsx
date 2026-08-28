import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import VersionDifferenceChart from '../VersionDifferenceChart';
import { AlignedComparison, AlignedMetricResult } from '../../../types/api';

const { plotSpy } = vi.hoisted(() => ({ plotSpy: vi.fn() }));

vi.mock('react-plotly.js', () => ({
  __esModule: true,
  default: (props: any) => {
    plotSpy(props);
    return (
      <button type="button" aria-label={`plot-${props.layout.title.text}`} onClick={() => props.onRelayout({ 'xaxis.range[0]': 10, 'xaxis.range[1]': 20 })}>
        Plot
      </button>
    );
  },
}));

const readyMetric = (offset = 0): AlignedMetricResult => ({
  status: 'ready',
  reason: null,
  shift_m: 1.25,
  rmse: 2,
  normalized_rmse: 0.125,
  overlap_from: 0,
  overlap_to: 1,
  overlap_length: 1,
  valid_points: 16,
  chainage: [0, 0.25, 0.5, 0.75, 1],
  latest: Array.from({ length: 4 }, (_, channel) => [1, 2, null, 4, 5].map(value => value == null ? null : value + channel + offset)),
  previous: Array.from({ length: 4 }, (_, channel) => [0, 1, null, 3, 4].map(value => value == null ? null : value + channel + offset)),
  difference: Array.from({ length: 4 }, () => [1, 1, null, 1, 1]),
});

const comparison = (): AlignedComparison => ({
  status: 'ready',
  reason: null,
  latest_file: 'latest.xlsx',
  previous_file: 'previous.xlsx',
  step_m: 0.25,
  max_shift_m: 50,
  metrics: {
    height: readyMetric(),
    stagger: readyMetric(100),
    wear: { ...readyMetric(), status: 'unavailable', reason: 'Wear channels missing', chainage: [] },
  },
});

describe('VersionDifferenceChart', () => {
  beforeEach(() => plotSpy.mockClear());

  it('renders raw cycle traces and four difference traces with channel line styles', () => {
    render(<VersionDifferenceChart alignedComparison={comparison()} sessionId="s1" />);

    const raw = plotSpy.mock.calls[0][0].data;
    const difference = plotSpy.mock.calls[1][0].data;
    expect(raw).toHaveLength(8);
    expect(difference).toHaveLength(4);
    expect(raw.slice(0, 4).map((trace: any) => trace.line.color)).toEqual(Array(4).fill('#b3261e'));
    expect(raw.slice(4, 8).map((trace: any) => trace.line.color)).toEqual(Array(4).fill('#1769aa'));
    expect(difference.map((trace: any) => trace.line.dash)).toEqual(['solid', 'dash', 'dot', 'dashdot']);
    expect(difference[0].connectgaps).toBe(false);
  });

  it('switches metric traces', async () => {
    const user = userEvent.setup();
    render(<VersionDifferenceChart alignedComparison={comparison()} sessionId="s1" />);

    await user.click(screen.getByRole('button', { name: 'Stagger' }));

    const latestRawCall = plotSpy.mock.calls.at(-2)?.[0];
    expect(latestRawCall.layout.title.text).toBe('Stagger raw overlay');
    expect(latestRawCall.data[0].y[0]).toBe(101);
  });

  it('synchronizes plot zoom and resets to the route range', async () => {
    const user = userEvent.setup();
    render(<VersionDifferenceChart alignedComparison={comparison()} sessionId="s1" />);

    fireEvent.click(screen.getByRole('button', { name: /plot-Height raw overlay/i }));
    expect(plotSpy.mock.calls.at(-1)?.[0].layout.xaxis.range).toEqual([10, 20]);
    expect(plotSpy.mock.calls.at(-2)?.[0].layout.xaxis.range).toEqual([10, 20]);

    await user.click(screen.getByRole('button', { name: /Reset Zoom/i }));
    expect(plotSpy.mock.calls.at(-1)?.[0].layout.xaxis.range).toEqual([0, 1]);
  });

  it('renders loading, empty, unavailable, and error states', () => {
    const { rerender } = render(<VersionDifferenceChart loading sessionId="s1" />);
    expect(screen.getByLabelText('Version Difference loading')).toBeInTheDocument();

    rerender(<VersionDifferenceChart sessionId="s1" />);
    expect(screen.getByText('No Version Difference Result')).toBeInTheDocument();

    rerender(<VersionDifferenceChart error="Request failed" sessionId="s1" />);
    expect(screen.getByText('Request failed')).toBeInTheDocument();

    rerender(<VersionDifferenceChart alignedComparison={{ status: 'unavailable', reason: 'ChartData missing', step_m: 0.25, max_shift_m: 50, metrics: {} }} sessionId="s1" />);
    expect(screen.getByText('ChartData missing')).toBeInTheDocument();
  });

  it('disables unavailable metrics without hiding available metrics', () => {
    render(<VersionDifferenceChart alignedComparison={comparison()} sessionId="s1" />);
    expect(screen.getByRole('button', { name: 'Wear' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Height' })).toBeEnabled();
  });
});
