import { describe, expect, it } from 'vitest';
import {
  buildHistoricalWearMatrix,
  sortTensionLengthLabels,
} from '../wearTensionLengthOrder';
import type { WearWorkbenchColumn } from '../../../types/api';

describe('wear tension-length ordering', () => {
  it('sorts H-prefixed and numeric labels naturally', () => {
    expect(sortTensionLengthLabels(['H02', 'H04', 'H01', 'H03', 'H06', 'H08', 'H05', '4', '3', '6', '5', '8', '7', '10']))
      .toEqual(['H01', 'H02', 'H03', 'H04', 'H05', 'H06', 'H08', '3', '4', '5', '6', '7', '8', '10']);
  });

  it('sorts known metadata prefixes before unknown labels', () => {
    expect(sortTensionLengthLabels(['L10', 'X2', 'T1', 'D3', 'M4', 'L2', 'X01', 'other']))
      .toEqual(['X01', 'X2', 'T1', 'D3', 'M4', 'L2', 'L10', 'other']);
  });

  it('keeps matrix rows complete while applying the requested column order', () => {
    const columns: WearWorkbenchColumn[] = [
      { tensionLength: 'H02' },
      { tensionLength: 'H01' },
    ];
    expect(buildHistoricalWearMatrix(columns, [
      { cycleDate: '2026-05-28', values: { H01: 11.2, H02: null } },
    ])).toEqual([
      ['Cycle Date', 'H02', 'H01'],
      ['2026-05-28', null, 11.2],
    ]);
  });
});
