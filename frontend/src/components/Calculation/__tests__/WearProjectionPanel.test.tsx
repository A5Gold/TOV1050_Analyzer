import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';

import WearProjectionPanel from '../WearProjectionPanel';
import { useWearRecordsStore } from '../../../store/useWearRecordsStore';

vi.mock('react-plotly.js', () => ({
  default: ({ data, layout }: { data: Array<{ marker?: { color?: string } }>; layout: { title?: { text?: string } } }) => (
    <div role="img" aria-label={layout.title?.text} data-marker-color={data[0]?.marker?.color} />
  ),
}));

const projectedRecord = {
  lineGroup: 'EAL' as const,
  tensionLength: 'E01',
  track: 'UP',
  fromM: 100,
  toM: 200,
  latestCycleDate: '2026-01-01',
  latestAvgWearMin: 11.4,
  latestWearPercentage: 13.64,
  wearRatePercentPerYear: 1.2,
  wearRateMmPerYear: 0.2,
  observationCount: 3,
  rSquared: 0.95,
  trendStatus: 'eligible',
  projectedCrossingDate: '2032-06-01',
  projectedYear: 2032,
  yearsToThreshold: 6.4,
};

describe('WearProjectionPanel', () => {
  const loadProjection = vi.fn();

  beforeEach(() => {
    loadProjection.mockReset();
    useWearRecordsStore.setState({
      projection: {
        thresholdMm: 10.2,
        thresholdPercentage: 22.6,
        horizonYears: 30,
        lineGroups: {
          EAL: {
            yearBuckets: [{ year: 2032, count: 1, records: [projectedRecord] }],
            alreadyAtThreshold: [{ ...projectedRecord, tensionLength: 'E02', trendStatus: 'already_at_threshold' }],
            insufficientData: [{ ...projectedRecord, tensionLength: 'E03', trendStatus: 'insufficient_data' }],
            nonPositiveRate: [],
          },
          TML: {
            yearBuckets: [{ year: 2032, count: 1, records: [{ ...projectedRecord, lineGroup: 'TML', tensionLength: 'T01' }] }],
            alreadyAtThreshold: [],
            insufficientData: [],
            nonPositiveRate: [{ ...projectedRecord, lineGroup: 'TML', tensionLength: 'T02', trendStatus: 'non_positive_rate' }],
          },
        },
      },
      wearThresholdMm: 10.2,
      loadProjection,
    });
  });

  it('uses one shared thickness threshold for separate EAL and TML charts', () => {
    render(<WearProjectionPanel />);

    expect(loadProjection).toHaveBeenCalledWith(10.2);
    expect(screen.getByLabelText(/threshold mm/i)).toHaveValue(10.2);
    expect(screen.getByText(/equivalent wear: 23%/i)).toBeInTheDocument();
    for (const value of ['10.2', '9.1', '8.9', '7.44', '7.24']) {
      expect(screen.getByRole('button', { name: `${value} mm` })).toBeInTheDocument();
    }
    expect(screen.getByRole('img', { name: /eal 30-year projection/i })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /tml 30-year projection/i })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /eal 30-year projection/i })).toHaveAttribute('data-marker-color', '#64b5f6');
    expect(screen.getByRole('img', { name: /tml 30-year projection/i })).toHaveAttribute('data-marker-color', '#8d6e63');
  });

  it('loads a selected preset and a custom positive millimetre value', async () => {
    render(<WearProjectionPanel />);
    fireEvent.click(screen.getByRole('button', { name: '9.1 mm' }));
    expect(loadProjection).toHaveBeenLastCalledWith(9.1);

    fireEvent.change(screen.getByLabelText(/threshold mm/i), { target: { value: '8.25' } });
    fireEvent.click(screen.getByRole('button', { name: /apply threshold/i }));
    await waitFor(() => expect(loadProjection).toHaveBeenLastCalledWith(8.25));
  });

  it.each([
    ['', /enter a thickness/i],
    ['0', /greater than 0/i],
    ['-1', /greater than 0/i],
    ['13.21', /13\.2 mm or less/i],
  ])('rejects invalid custom threshold %s without changing the active request', (value, message) => {
    render(<WearProjectionPanel />);
    loadProjection.mockClear();

    fireEvent.change(screen.getByLabelText(/threshold mm/i), { target: { value } });

    expect(screen.getByText(message)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /apply threshold/i })).toBeDisabled();
    expect(loadProjection).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: '10.2 mm' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('keeps a valid custom value as a draft until Apply updates the active threshold', () => {
    render(<WearProjectionPanel />);
    loadProjection.mockClear();

    fireEvent.change(screen.getByLabelText(/threshold mm/i), { target: { value: '8.25' } });
    expect(loadProjection).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: '10.2 mm' })).toHaveAttribute('aria-pressed', 'true');

    fireEvent.click(screen.getByRole('button', { name: /apply threshold/i }));
    expect(loadProjection).toHaveBeenCalledWith(8.25);
    expect(screen.getByRole('button', { name: '10.2 mm' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('shows combined expandable year detail and all projection status lists', () => {
    render(<WearProjectionPanel />);
    expect(screen.getByRole('columnheader', { name: 'Projected Year' })).toBeInTheDocument();
    expect(screen.getByText('E01, T01')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /expand 2032/i }));
    expect(screen.getAllByText('2032-06-01')).toHaveLength(2);
    expect(screen.getByText(/already at threshold/i)).toBeInTheDocument();
    expect(screen.getByText('EAL E02')).toBeInTheDocument();
    expect(screen.getByText(/insufficient data/i)).toBeInTheDocument();
    expect(screen.getByText('EAL E03')).toBeInTheDocument();
    expect(screen.getByText(/non-positive rate/i)).toBeInTheDocument();
    expect(screen.getByText('TML T02')).toBeInTheDocument();
  });
});
