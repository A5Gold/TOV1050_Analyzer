import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import WearAnalysisCharts from '../WearAnalysisCharts';
import type { WearCycleRecord, WearTrack } from '../../../types/api';

vi.mock('react-plotly.js', () => ({
  default: ({ data }: { data: Array<{ x?: string[] }> }) => (
    <div data-testid="plot">{JSON.stringify(data[0]?.x ?? [])}</div>
  ),
}));

const record = (
  tensionLength: string,
  track: WearTrack,
  intervalTracks: WearTrack[],
): WearCycleRecord => ({
  key: { lineGroup: 'EAL', cycleDate: '2026-06-17', tensionLength },
  track,
  fromM: Number(tensionLength),
  toM: Number(tensionLength) + 1,
  intervalCount: intervalTracks.length,
  intervals: intervalTracks.map((intervalTrack, index) => ({
    track: intervalTrack,
    fromM: Number(tensionLength) + index,
    toM: Number(tensionLength) + index + 1,
  })),
  avgWearMin: 10,
  wearPercentage: 5,
  measurementSd: null,
  hasDataConflict: false,
  conflictIds: [],
  updatedAt: null,
});

describe('WearAnalysisCharts', () => {
  it('offers only physical directions and keeps mixed-direction mainline rows', () => {
    render(<WearAnalysisCharts rows={[
      record('1', 'UP', ['UP']),
      record('2', 'DN', ['DN']),
      record('3', 'Siding', ['UP', 'DN']),
    ]} />);

    expect(screen.getByRole('checkbox', { name: 'UP' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'DN' })).toBeChecked();
    expect(screen.queryByRole('checkbox', { name: 'Siding' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('checkbox', { name: 'UP' }));

    for (const plot of screen.getAllByTestId('plot')) {
      expect(plot).toHaveTextContent('["2","3"]');
    }
  });
});
