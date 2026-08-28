import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import VersionDifferenceChart from '../VersionDifferenceChart';
import { VERSION_DIFFERENCE_CYCLES } from '../../../constants/versionDifferenceCycles';
import type { AlignedMetricResult, VersionDifferenceResponse } from '../../../types/api';

const { plotSpy } = vi.hoisted(() => ({ plotSpy: vi.fn() }));

vi.mock('react-plotly.js', () => ({
  __esModule: true,
  default: (props: any) => {
    plotSpy(props);
    return <button type="button" aria-label={`plot-${props.data.length}`} onClick={() => props.onRelayout({ 'xaxis.range[0]': 10, 'xaxis.range[1]': 20 })}>Plot</button>;
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
  latest: Array.from({ length: 4 }, (_, channel) => [1, 2, null, 4, 5].map(value => value == null ? null : value + channel)),
  previous: Array.from({ length: 4 }, (_, channel) => [0, 1, null, 3, 4].map(value => value == null ? null : value + channel + offset)),
  difference: Array.from({ length: 4 }, () => [1, 1, null, 1, 1]),
});

const response = (): VersionDifferenceResponse => ({
  status: 'ready',
  latest_file: 'latest.xlsx',
  comparisons: [
    { key: 'previous_1', previous_file: 'previous-1.xlsx', status: 'ready', step_m: 0.25, max_shift_m: 50, metrics: { height: readyMetric(), stagger: readyMetric(10), wear: readyMetric(20) } },
    { key: 'previous_2', previous_file: 'previous-2.xlsx', status: 'ready', step_m: 0.25, max_shift_m: 50, metrics: { height: readyMetric(30), stagger: readyMetric(40), wear: readyMetric(50) } },
  ],
});

const fiveCycleResponse = (): VersionDifferenceResponse => {
  const base = response();
  return {
    ...base,
    comparisons: [
      ...base.comparisons,
      { key: 'previous_3', previous_file: 'previous-3.xlsx', status: 'ready', step_m: 0.25, max_shift_m: 50, metrics: { height: readyMetric(60), stagger: readyMetric(70), wear: readyMetric(80) } },
      { key: 'previous_4', previous_file: 'previous-4.xlsx', status: 'ready', step_m: 0.25, max_shift_m: 50, metrics: { height: readyMetric(90), stagger: readyMetric(100), wear: readyMetric(110) } },
    ],
  };
};

describe('VersionDifferenceChart', () => {
  beforeEach(() => plotSpy.mockClear());

  it('renders three-cycle raw data and two Latest-based difference plots without Plotly legends', () => {
    render(<VersionDifferenceChart response={response()} />);

    expect(plotSpy).toHaveBeenCalledTimes(3);
    expect(plotSpy.mock.calls[0][0].data).toHaveLength(12);
    expect(plotSpy.mock.calls[1][0].data).toHaveLength(4);
    expect(plotSpy.mock.calls[2][0].data).toHaveLength(4);
    expect(plotSpy.mock.calls.every(call => call[0].layout.showlegend === false)).toBe(true);
    expect(screen.getByText('Latest - Previous 1')).toBeInTheDocument();
    expect(screen.getByText('Latest - Previous 2')).toBeInTheDocument();
  });

  it('renders five-cycle colors as 20 raw traces and four Latest-based differences', () => {
    render(<VersionDifferenceChart response={fiveCycleResponse()} />);

    expect(plotSpy).toHaveBeenCalledTimes(5);
    expect(plotSpy.mock.calls[0][0].data).toHaveLength(20);
    expect(plotSpy.mock.calls.slice(1, 5).every(call => call[0].data.length === 4)).toBe(true);

    VERSION_DIFFERENCE_CYCLES.forEach((cycle, index) => {
      const rawCycleTraces = plotSpy.mock.calls[0][0].data.slice(index * 4, (index + 1) * 4);
      expect(rawCycleTraces.every((trace: Plotly.Data) => trace.line?.color === cycle.color)).toBe(true);
      if (cycle.comparisonKey) {
        expect(screen.getByText(`Latest - ${cycle.label}`)).toBeInTheDocument();
        expect(plotSpy.mock.calls[index][0].data.every((trace: Plotly.Data) => trace.line?.color === cycle.color)).toBe(true);
      }
    });
  });

  it('preserves comparison labels when Previous 2 is absent and Previous 3 is present', () => {
    const withGap = fiveCycleResponse();
    withGap.comparisons = withGap.comparisons.filter(comparison => (
      comparison.key === 'previous_1' || comparison.key === 'previous_3'
    ));

    render(<VersionDifferenceChart response={withGap} />);

    expect(plotSpy).toHaveBeenCalledTimes(3);
    expect(plotSpy.mock.calls[0][0].data).toHaveLength(12);
    expect(screen.queryByText('Latest - Previous 2')).not.toBeInTheDocument();
    expect(screen.getByText('Latest - Previous 3')).toBeInTheDocument();
  });

  it('controls visibility, opacity, and layer order within the selected plot', async () => {
    const user = userEvent.setup();
    render(<VersionDifferenceChart response={response()} />);
    await user.click(screen.getByRole('button', { name: 'Configure raw overlay series' }));

    await user.click(screen.getByRole('checkbox', { name: 'Toggle Latest Channel 1' }));
    let rawCall = [...plotSpy.mock.calls].reverse().find(call => call[0].data.length === 12)?.[0];
    expect(rawCall.data[0].visible).toBe(false);

    fireEvent.change(screen.getByRole('slider', { name: 'Latest Channel 2 opacity' }), { target: { value: '0.4' } });
    rawCall = [...plotSpy.mock.calls].reverse().find(call => call[0].data.length === 12)?.[0];
    expect(rawCall.data[1].opacity).toBe(0.4);

    await user.click(screen.getByRole('button', { name: 'Bring Latest Channel 1 forward' }));
    rawCall = [...plotSpy.mock.calls].reverse().find(call => call[0].data.length === 12)?.[0];
    expect(rawCall.data[0].name).toContain('channel 2');
    expect(rawCall.data[1].name).toContain('channel 1');
  });

  it('synchronizes chainage zoom across visible plots and resets it', async () => {
    const user = userEvent.setup();
    render(<VersionDifferenceChart response={response()} />);

    fireEvent.click(screen.getByRole('button', { name: 'plot-12' }));
    const latestCalls = plotSpy.mock.calls.slice(-3).map(call => call[0]);
    expect(latestCalls.every(call => call.layout.xaxis.range[0] === 10 && call.layout.xaxis.range[1] === 20)).toBe(true);

    await user.click(screen.getByRole('button', { name: 'Reset zoom' }));
    expect(plotSpy.mock.calls.at(-1)?.[0].layout.xaxis.range).toEqual([0, 1]);
  });

  it('renders loading, empty, and partial unavailable states', () => {
    const { rerender } = render(<VersionDifferenceChart loading />);
    expect(screen.getByLabelText('Version Difference loading')).toBeInTheDocument();

    rerender(<VersionDifferenceChart />);
    expect(screen.getByText('No comparison result')).toBeInTheDocument();

    const partial = response();
    partial.comparisons[1].metrics.height = { ...readyMetric(), status: 'unavailable', reason: 'Insufficient overlap' };
    rerender(<VersionDifferenceChart response={partial} />);
    expect(screen.getByText(/Insufficient overlap/)).toBeInTheDocument();
  });
});
