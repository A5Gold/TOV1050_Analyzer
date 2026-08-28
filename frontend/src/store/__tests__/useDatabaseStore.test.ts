import { beforeEach, describe, expect, it, vi } from 'vitest';

const { getSpy } = vi.hoisted(() => ({ getSpy: vi.fn() }));

vi.mock('../../api/client', () => ({
  default: { get: getSpy },
}));

import { useDatabaseStore } from '../useDatabaseStore';

const sectionCounts = {
  all: 1826,
  mainline: 1584,
  rac: 132,
  low_s1: 16,
  lmc: 94,
  unknown: 0,
};

describe('useDatabaseStore repeated-record counts', () => {
  beforeEach(() => {
    getSpy.mockReset();
    useDatabaseStore.getState().reset();
  });

  it('stores complete totals and section aggregates independently of loaded rows', async () => {
    getSpy.mockResolvedValue({
      data: {
        status: 'success',
        total: 94,
        section_counts: sectionCounts,
        records: [{ record_id: 1, line: 'EAL', section: 'LMC' }],
      },
    });

    await useDatabaseStore.getState().fetchRepeatedRecords({
      line: 'EAL',
      section: 'LMC',
      limit: 1000,
    });

    expect(getSpy).toHaveBeenCalledWith(
      '/database/repeated-records?line=EAL&section=LMC&limit=1000',
    );
    const state = useDatabaseStore.getState();
    expect(state.repeatedRecords).toHaveLength(1);
    expect(state.repeatedRecordsTotal).toBe(94);
    expect(state.repeatedRecordSectionCounts).toEqual(sectionCounts);
  });

  it('does not retain successful section badges after a later request fails', async () => {
    getSpy.mockResolvedValueOnce({
      data: {
        status: 'success',
        total: 1826,
        section_counts: sectionCounts,
        records: [],
      },
    });
    await useDatabaseStore.getState().fetchRepeatedRecords({ line: 'EAL' });

    getSpy.mockRejectedValueOnce(new Error('count query failed'));
    await useDatabaseStore.getState().fetchRepeatedRecords({ line: 'EAL', section: 'RAC' });

    const state = useDatabaseStore.getState();
    expect(state.repeatedRecordsError).toBe('count query failed');
    expect(state.repeatedRecordSectionCounts).toEqual({
      all: 0,
      mainline: 0,
      rac: 0,
      low_s1: 0,
      lmc: 0,
      unknown: 0,
    });
  });
});
