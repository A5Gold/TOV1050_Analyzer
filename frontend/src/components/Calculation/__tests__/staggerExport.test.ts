import { describe, expect, it, vi, beforeEach } from 'vitest';

const {
  aoaToSheetMock,
  bookNewMock,
  bookAppendSheetMock,
  writeFileMock,
} = vi.hoisted(() => ({
  aoaToSheetMock: vi.fn(() => ({})),
  bookNewMock: vi.fn(() => ({})),
  bookAppendSheetMock: vi.fn(),
  writeFileMock: vi.fn(),
}));

vi.mock('xlsx', () => ({
  utils: {
    aoa_to_sheet: aoaToSheetMock,
    book_new: bookNewMock,
    book_append_sheet: bookAppendSheetMock,
  },
  writeFile: writeFileMock,
}));

import { exportStaggerResults } from '../staggerExport';

describe('exportStaggerResults', () => {
  beforeEach(() => {
    aoaToSheetMock.mockClear();
    bookNewMock.mockClear();
    bookAppendSheetMock.mockClear();
    writeFileMock.mockClear();
  });

  it('exports the stagger summary workbook with the expected filename', () => {
    exportStaggerResults([
      {
        id: 'SG-001',
        run_date: '2026-03-01',
        line: 'EAL',
        track: 'UP',
        section: 'Mainline',
        task_no: 'U2',
        station_start: 'FOT',
        station_end: 'TAP',
        from_m: 113498,
        to_m: 113500,
        length: 2,
        tension_length: 'H01',
        overlap: null,
        track_type: 'Tangent',
        level: 'L1',
        landmark: null,
        asset_class: 'Stagger',
        threshold_value: 45,
        exception_type: 'Stagger Left',
        max_value: 122,
        max_location: 113498.5,
        chi: 113498.5,
        spt_a: 113490,
        spt_i: 113498.5,
        spt_b: 113510,
        span_ai: 8.5,
        span_ib: 11.5,
        k_eq: 1.235,
        overall_result: 'pass',
        trace_available: true,
        trace_status: 'complete',
        chi_source: 'maxLocation',
        remark: ['Case A'],
      },
    ]);

    expect(aoaToSheetMock).toHaveBeenCalledTimes(1);
    expect(bookNewMock).toHaveBeenCalledTimes(1);
    expect(bookAppendSheetMock).toHaveBeenCalledTimes(1);
    expect(writeFileMock).toHaveBeenCalledTimes(1);
    expect(writeFileMock.mock.calls[0]?.[1]).toBe('20260301_EAL_U2_FOT-TAP_Stagger_Report.xlsx');
  });

  it('exports span calculation values and pass/fail criteria statements', () => {
    exportStaggerResults([
      {
        id: 'SG-002',
        run_date: '2026-06-11',
        line: 'EAL',
        track: 'up',
        section: 'Mainline',
        task_no: 'U2',
        station_start: 'FOT',
        station_end: 'TAP',
        from_m: 113568,
        to_m: 113574.25,
        length: 6.25,
        tension_length: '31, 33',
        overlap: null,
        track_type: 'Tangent',
        level: 'L2',
        landmark: null,
        asset_class: 'EAL',
        threshold_value: 280,
        exception_type: 'Stagger Left',
        max_value: 306.99,
        max_location: 113569,
        chi: 113569,
        spt_a: 113527,
        spt_i: 113568,
        spt_b: 113613,
        span_ai: 41,
        span_ib: 45,
        k_eq: 0.94,
        overall_result: 'pass',
        trace_available: true,
        trace_status: 'complete',
        chi_source: 'n_repeated',
        remark: ['Case B'],
        span_results: {
          ai: { b: 27.7, s: 514.96, p: 49.51, allowable: -121.11, result: 'pass_short_circuit' },
          ib: { b: 33.36, s: 482.97, p: 65.51, allowable: 34.68, result: 'pass_short_circuit' },
        },
      } as any,
    ]);

    const [sheetRows] = aoaToSheetMock.mock.calls[0] ?? [];
    expect(sheetRows[0]).toEqual(expect.arrayContaining([
      '4B_AI',
      'S_AI',
      'S_AI >= 4B',
      'P_AI',
      'Allowable_AI',
      'P_AI <= Allowable_AI',
      '4B_IB',
      'S_IB',
      'S_IB >= 4B',
      'P_IB',
      'Allowable_IB',
      'P_IB <= Allowable_IB',
      'P <= Allowable',
    ]));
    expect(sheetRows[1]).toEqual(expect.arrayContaining([
      '514.96 >= 110.80: Pass',
      '49.51 <= -121.11: Fail',
      '482.97 >= 133.44: Pass',
      '65.51 <= 34.68: Fail',
      'AI Fail; IB Fail',
    ]));
  });
});
