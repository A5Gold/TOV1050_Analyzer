import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { MockedFunction } from 'vitest';

vi.mock('../../api/client', () => ({
  uploadTrendFiles: vi.fn(),
}));

import { uploadTrendFiles } from '../../api/client';
import { useTrendStore } from '../useTrendStore';

const mockedUploadTrendFiles = uploadTrendFiles as MockedFunction<typeof uploadTrendFiles>;

describe('useTrendStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useTrendStore.getState().resetTab();
  });

  it('marks the tab as analyzed when trend analysis returns an empty result set', async () => {
    mockedUploadTrendFiles.mockResolvedValueOnce({ trend_results: [] });

    const file = new File(['exception'], 'exception-report.xlsx');
    useTrendStore.getState().addFile(file);

    await useTrendStore.getState().analyze();

    const state = useTrendStore.getState();
    const activeTab = state.tabs.find((tab) => tab.id === state.activeTabId)!;

    expect(activeTab.hasAnalyzed).toBe(true);
    expect(activeTab.trendResults).toEqual([]);
    expect(activeTab.selectedResult).toBeNull();
  });

  it('clears the analyzed state when uploaded files change after an empty-result success', async () => {
    mockedUploadTrendFiles.mockResolvedValueOnce({ trend_results: [] });

    useTrendStore.getState().addFile(new File(['a'], 'report-a.xlsx'));
    await useTrendStore.getState().analyze();

    useTrendStore.getState().addFile(new File(['b'], 'report-b.xlsx'));

    const state = useTrendStore.getState();
    const activeTab = state.tabs.find((tab) => tab.id === state.activeTabId)!;

    expect(activeTab.hasAnalyzed).toBe(false);
    expect(activeTab.trendResults).toEqual([]);
    expect(activeTab.selectedResult).toBeNull();
    expect(activeTab.error).toBeNull();
  });

  it('infers the uploaded line from TML filenames and passes it to the trend API', async () => {
    mockedUploadTrendFiles.mockResolvedValueOnce({ trend_results: [] });

    const reportA = new File(['a'], '20260130_TML_U2_TAW-HUH_Exception_Report.xlsx');
    const reportB = new File(['b'], '20251104_TML_U2_TAW-HUH_Exception_Report.xlsx');
    const repeated = new File(['r'], '20260130_TML_U2_TAW-HUH_Exception_Report_2_Repeated.xlsx');
    useTrendStore.getState().addFile(reportA);
    useTrendStore.getState().addFile(reportB);
    useTrendStore.getState().setRepeatedFile(repeated);

    await useTrendStore.getState().analyze();

    expect(mockedUploadTrendFiles).toHaveBeenCalledWith([reportA, reportB], repeated, 'TML');
  });
});
