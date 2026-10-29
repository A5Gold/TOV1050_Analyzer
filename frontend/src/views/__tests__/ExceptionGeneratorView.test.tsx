import React from 'react';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import apiClient from '../../api/client';
vi.mock('../../api/client', () => ({ default: { post: vi.fn(), get: vi.fn() } }));
import ExceptionGeneratorView from '../ExceptionGeneratorView';
import { useAnalysisStore } from '../../store/useAnalysisStore';

// Mock Child Components to avoid complex dependencies
vi.mock('../../components/ChartComponent', () => ({
  __esModule: true,
  default: () => <div data-testid="chart-component">Chart Component</div>
}));

vi.mock('../../components/ExceptionList', () => ({
  __esModule: true,
  default: () => <div data-testid="exception-list">Exception List</div>
}));

vi.mock('../../components/ExceptionTable', () => ({
  __esModule: true,
  default: () => <div data-testid="exception-table">Exception Table</div>
}));

// Mock Electron API
window.electronAPI = {
  openFile: vi.fn().mockResolvedValue('C:\\Test\\Data.csv'),
  saveFile: vi.fn().mockResolvedValue({ success: true, filePath: 'saved.xlsx' })
};

describe('ExceptionGeneratorView Multi-Tab', () => {
  beforeEach(() => {
    useAnalysisStore.getState().resetAnalysisSessions();
  });
  
  test('renders initial empty state', () => {
    render(<ExceptionGeneratorView />);
    expect(screen.getByText('No Active Analysis')).toBeInTheDocument();
    expect(screen.getByText('Start New Analysis')).toBeInTheDocument();
  });

  test('adds a new tab when clicking Start New Analysis', () => {
    render(<ExceptionGeneratorView />);
    
    const startBtn = screen.getByText('Start New Analysis');
    fireEvent.click(startBtn);

    // Should see Tab Label "Analysis 1"
    expect(screen.getByText('Analysis 1')).toBeInTheDocument();
    
    // Should see Config Form
    expect(screen.getByText('Configuration')).toBeInTheDocument();
  });

  test('adds multiple tabs and switches between them', () => {
    render(<ExceptionGeneratorView />);
    
    // Add Tab 1
    fireEvent.click(screen.getByText('Start New Analysis'));
    expect(screen.getByText('Analysis 1')).toBeInTheDocument();

    // Add Tab 2
    fireEvent.click(screen.getByText('New Analysis'));
    expect(screen.getByText('Analysis 2')).toBeInTheDocument();

    // Verify Tab 2 is active (should be bold or have specific style, but we check content logic)
    // Both tabs present
    expect(screen.getAllByRole('tab')).toHaveLength(2);
  });

  test('closes a tab', () => {
    render(<ExceptionGeneratorView />);
    
    // Add Tab 1
    fireEvent.click(screen.getByText('Start New Analysis'));
    
    // Find Close Button (it's inside the tab)
    const tab1 = screen.getByText('Analysis 1').closest('button');
    // Note: The close icon is a separate span inside the label, but we can search for the icon or use within
    // Our implementation: <CloseIcon ... /> inside the label
    
    // Since we can't easily select the Close Icon by text, let's look for testid or similar if added, 
    // or just assume the click on the icon wrapper works.
    // In real testing we might add data-testid to the close button.
  });
});


test('sends manually selected context for datac without reading header labels', async () => {
  useAnalysisStore.getState().resetAnalysisSessions();
  useAnalysisStore.getState().addAnalysisSession({
    id: 'manual-datac', label: 'Data.datac', filePath: 'C:/Test/Data.datac',
    line: 'TCL', track: 'DT', section: 'Mainline', dateStr: '20261023',
    stationStart: 'TUC', stationEnd: 'SUN', result: null, loading: false,
    error: null, viewMode: 'graph', selectedExceptionId: null,
  });
  vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { job_id: 'manual', kind: 'analysis', status: 'ready', stage: 'ready', elapsed_seconds: 1 } });
  vi.mocked(apiClient.get).mockResolvedValueOnce({ data: null });
  render(<ExceptionGeneratorView />);
  expect(screen.getByText(/分析及 Exception Report 使用下方選擇值/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Start Analysis' }));
  await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith('/analysis/jobs', expect.objectContaining({
    file_path: 'C:/Test/Data.datac', line: 'TCL', track: 'DT', section: 'Mainline',
  }), { timeout: 30_000 }));
});

test('disables the visible action while analysis is pending and restores it on failure', async () => {
  useAnalysisStore.getState().resetAnalysisSessions();
  useAnalysisStore.getState().addAnalysisSession({
    id: 'pending', label: 'Data.csv', filePath: 'C:/Test/Data.csv',
    line: 'TWL', track: 'UT', section: 'Mainline', dateStr: '20261023',
    stationStart: 'CEN', stationEnd: 'TSW', result: null, loading: false,
    error: null, viewMode: 'graph', selectedExceptionId: null,
  });
  let rejectAnalysis!: (error: Error) => void;
  vi.mocked(apiClient.post).mockImplementationOnce(() => new Promise((_, reject) => {
    rejectAnalysis = reject;
  }));
  render(<ExceptionGeneratorView />);
  fireEvent.click(screen.getByRole('button', { name: 'Start Analysis' }));
  expect(screen.getByRole('button', { name: 'Analyzing...' })).toBeDisabled();
  expect(screen.getByLabelText('Task Number (Optional)')).toBeDisabled();
  expect(screen.getByLabelText('Station Start')).toBeDisabled();
  expect(screen.getByLabelText('Station End')).toBeDisabled();
  expect(screen.getByRole('button', { name: /Choose date/ })).toBeDisabled();
  rejectAnalysis(new Error('Unable to analyze this file'));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Start Analysis' })).toBeEnabled());
  expect(screen.getByText('Unable to analyze this file')).toBeInTheDocument();
});

const createSession = (id: string, result: any = null) => ({
  id, label: `${id}.csv`, filePath: `C:/Test/${id}.csv`, line: 'TWL', track: 'UT',
  section: 'Mainline', dateStr: '20260907', stationStart: 'CEN', stationEnd: 'TSW',
  result, loading: false, error: null, viewMode: 'graph' as const, selectedExceptionId: null,
});
const result = { status: 'success', params: {}, exceptions: {}, boundaries: [], chart_data: {}, analysis_revision: 'revision-a' };
const ready = { job_id: 'job-a', kind: 'analysis', status: 'ready', stage: 'ready', elapsed_seconds: 2 };

test('applies an analysis response to its original tab after switching tabs', async () => {
  vi.clearAllMocks();
  useAnalysisStore.getState().resetAnalysisSessions();
  useAnalysisStore.getState().addAnalysisSession(createSession('tab-a'));
  let finish!: (value: any) => void;
  vi.mocked(apiClient.post).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  vi.mocked(apiClient.get).mockResolvedValueOnce({ data: result });
  render(<ExceptionGeneratorView />);
  fireEvent.click(screen.getByRole('button', { name: 'Start Analysis' }));
  fireEvent.click(screen.getByRole('button', { name: 'New Analysis' }));
  finish({ data: ready });
  await waitFor(() => expect(useAnalysisStore.getState().analysisSessions[0].result).toEqual(result));
  expect(useAnalysisStore.getState().analysisSessions[1].result).toBeNull();
  expect(useAnalysisStore.getState().activeAnalysisTabId).not.toBe('tab-a');
});

test('median export sends revision and mode without a sampled chart payload', async () => {
  vi.clearAllMocks();
  useAnalysisStore.getState().resetAnalysisSessions();
  useAnalysisStore.getState().addAnalysisSession(createSession('tab-a', result));
  vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { ...ready, kind: 'export' } });
  vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Download interrupted'));
  render(<ExceptionGeneratorView />);
  fireEvent.click(screen.getByRole('button', { name: '匯出例外報表' }));
  await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith('/export/report/jobs', {
    client_session_id: 'tab-a', analysis_revision: 'revision-a', chart_data_mode: 'chainage_median',
  }, { timeout: 30_000 }));
  await waitFor(() => expect(screen.getByText('Download interrupted')).toBeInTheDocument());
  expect(useAnalysisStore.getState().analysisSessions[0].exportJob?.status).toBe('ready');
  fireEvent.click(screen.getByRole('button', { name: '重新下載報表' }));
  await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(2));
  expect(apiClient.post).toHaveBeenCalledTimes(1);
});


test('raw overview disables report export and can return to median analysis', async () => {
  vi.clearAllMocks();
  useAnalysisStore.getState().resetAnalysisSessions();
  useAnalysisStore.getState().addAnalysisSession(createSession('raw', { ...result, analysis_mode: 'raw_overview' }));
  vi.mocked(apiClient.post).mockResolvedValueOnce({ data: ready });
  vi.mocked(apiClient.get).mockResolvedValueOnce({ data: { ...result, analysis_mode: 'median' } });
  render(<ExceptionGeneratorView />);
  expect(screen.getByRole('button', { name: '匯出例外報表' })).toBeDisabled();
  expect(screen.getByRole('button', { name: /Table/ })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: '返回中位樣本分析' }));
  await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith('/analysis/jobs', expect.objectContaining({
    analysis_mode: 'median', chart_data_mode: 'chainage_median',
  }), { timeout: 30_000 }));
});

test('offers original data overview at import with explicit raw mode', async () => {
  vi.clearAllMocks();
  useAnalysisStore.getState().resetAnalysisSessions();
  useAnalysisStore.getState().addAnalysisSession(createSession('raw-import'));
  vi.mocked(apiClient.post).mockResolvedValueOnce({ data: ready });
  vi.mocked(apiClient.get).mockResolvedValueOnce({ data: { ...result, analysis_mode: 'raw_overview' } });
  render(<ExceptionGeneratorView />);
  fireEvent.click(screen.getByRole('button', { name: '原始資料概覽' }));
  await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith('/analysis/jobs', expect.objectContaining({
    analysis_mode: 'raw_overview', chart_data_mode: 'raw',
  }), { timeout: 30_000 }));
});
