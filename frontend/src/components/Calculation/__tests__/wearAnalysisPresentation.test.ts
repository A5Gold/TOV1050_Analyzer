import { describe, it, expect } from 'vitest';
import {
  chartAxisRange,
  visibleAnalysisRows,
  buildWearAnalysisChartSpec,
  getAvgWearMinStatusColor,
  getAvgWearMinStatusStyle,
} from '../wearAnalysisPresentation';
import type { WearCycleRecord } from '../../../types/api';
import type { WearResult } from '../../../types/api';

const makeResult = (overrides: Partial<WearResult> = {}): WearResult => ({
  line: 'EAL',
  track: 'UP',
  tension_length: '4',
  from_m: 1000,
  to_m: 1200,
  avg_wear_min: 10.5,
  sd: 0.3,
  wear_percentage: 3.0,
  dates: ['2026-01-01'],
  record_points: [10.5],
  ...overrides,
});

describe('wear analysis presentation helpers', () => {
  const cycleRecord = (tensionLength: string, fromM: number, track: 'UP' | 'DN' | 'Siding' = 'UP'): WearCycleRecord => ({
    key: { lineGroup: 'EAL', cycleDate: '2026-05-28', tensionLength }, track, fromM, toM: fromM + 10,
    intervalCount: 1, intervals: [{ track, fromM, toM: fromM + 10 }], avgWearMin: 10,
    wearPercentage: fromM, measurementSd: null, hasDataConflict: false, conflictIds: [], updatedAt: null,
  });

  it('filters physical directions and sorts chart rows without mutating the source', () => {
    const mixed = {
      ...cycleRecord('1', 1, 'Siding'),
      intervalCount: 2,
      intervals: [
        { track: 'UP' as const, fromM: 1, toM: 5 },
        { track: 'DN' as const, fromM: 6, toM: 11 },
      ],
    };
    const rows = [cycleRecord('10', 10, 'DN'), cycleRecord('2', 2), mixed];
    expect(visibleAnalysisRows(rows, ['UP'], { field: 'fromM', direction: 'asc' }).map(r => r.key.tensionLength)).toEqual(['1', '2']);
    expect(visibleAnalysisRows(rows, ['DN'], { field: 'fromM', direction: 'asc' }).map(r => r.key.tensionLength)).toEqual(['1', '10']);
    expect(rows.map(r => r.key.tensionLength)).toEqual(['10', '2', '1']);
  });

  it('pads the y axis around actual values', () => {
    expect(chartAxisRange([10, 12])).toEqual([9.84, 12.16]);
    expect(chartAxisRange([10])).toEqual([9.9, 10.1]);
  });
  it('classifies Avg Wear Min thresholds', () => {
    expect(getAvgWearMinStatusStyle(10.3).backgroundColor).toBe('#d4edda');
    expect(getAvgWearMinStatusStyle(10.2).backgroundColor).toBe('#fff3cd');
    expect(getAvgWearMinStatusStyle(9.1).backgroundColor).toBe('#fff3cd');
    expect(getAvgWearMinStatusStyle(9.0).backgroundColor).toBe('#ffcccc');
  });

  it('colors Wear % bars from the matching Avg Wear Min status', () => {
    const spec = buildWearAnalysisChartSpec('wear_percentage', [
      makeResult({ tension_length: 'G', avg_wear_min: 10.4, wear_percentage: 4 }),
      makeResult({ tension_length: 'Y', avg_wear_min: 9.7, wear_percentage: 12 }),
      makeResult({ tension_length: 'R', avg_wear_min: 8.9, wear_percentage: 32 }),
    ]);

    expect(spec.data[0].marker?.color).toEqual([
      getAvgWearMinStatusColor(10.4),
      getAvgWearMinStatusColor(9.7),
      getAvgWearMinStatusColor(8.9),
    ]);
  });

  it('adds 10.2 and 9.1 threshold lines to the Avg Wear Min chart', () => {
    const spec = buildWearAnalysisChartSpec('avg_wear_min', [
      makeResult({ tension_length: '4', avg_wear_min: 10.4 }),
    ]);

    expect(spec.layout.yaxis?.title?.text).toBe('Avg Wear Min');
    expect(spec.layout.shapes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ y0: 10.2, y1: 10.2 }),
        expect.objectContaining({ y0: 9.1, y1: 9.1 }),
      ]),
    );
  });
});
