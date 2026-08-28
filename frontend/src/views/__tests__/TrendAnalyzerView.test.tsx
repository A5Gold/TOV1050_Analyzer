import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import TrendAnalyzerView from '../TrendAnalyzerView';
import { useTrendStore, type TrendTab } from '../../store/useTrendStore';

vi.mock('../../components/Calculation/TrendChart', () => ({
  default: () => <div data-testid="trend-chart">Trend Chart</div>,
}));

vi.mock('../../components/Calculation/TrendResultTable', () => ({
  default: ({ results }: { results: unknown[] }) => <div data-testid="trend-result-table">{results.length}</div>,
}));

vi.mock('../../components/Calculation/TrendAlgorithmDialog', () => ({
  default: () => null,
}));

function makeTab(overrides: Partial<TrendTab> = {}): TrendTab {
  return {
    id: 'tab-1',
    label: 'Tab 1',
    uploadedFiles: [],
    repeatedFile: null,
    isLoading: false,
    error: null,
    trendResults: [],
    selectedResult: null,
    hasAnalyzed: false,
    ...overrides,
  };
}

describe('TrendAnalyzerView', () => {
  beforeEach(() => {
    useTrendStore.setState({
      tabs: [makeTab()],
      activeTabId: 'tab-1',
    });
  });

  test('shows a dedicated empty-result success message after analysis completes with zero results', () => {
    useTrendStore.setState({
      tabs: [
        makeTab({
          uploadedFiles: [new File(['exception'], 'exception-report.xlsx')],
          repeatedFile: new File(['repeated'], 'n_repeated.xlsx'),
          hasAnalyzed: true,
          trendResults: [],
        }),
      ],
      activeTabId: 'tab-1',
    });

    render(<TrendAnalyzerView />);

    expect(
      screen.getByText(/No matching L2 Wire Wear alarms found in the uploaded n_Repeated Exception Report after filter\./i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/The analysis completed successfully with 0 result\./i)
    ).toBeInTheDocument();
  });

  test('shows the latest exception report empty-result message when no repeated report is uploaded', () => {
    useTrendStore.setState({
      tabs: [
        makeTab({
          uploadedFiles: [new File(['exception'], 'exception-report.xlsx')],
          repeatedFile: null,
          hasAnalyzed: true,
          trendResults: [],
        }),
      ],
      activeTabId: 'tab-1',
    });

    render(<TrendAnalyzerView />);

    expect(
      screen.getByText(/No matching L2 Wire Wear alarms found in the latest uploaded Exception Report after filter\./i)
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/uploaded n_Repeated Exception Report after filter/i)
    ).not.toBeInTheDocument();
  });

  test('resets only the active tab from the tab action area', () => {
    useTrendStore.setState({
      tabs: [
        makeTab({
          id: 'tab-1',
          label: 'Tab 1',
          uploadedFiles: [new File(['a'], 'tab-1.xlsx')],
        }),
        makeTab({
          id: 'tab-2',
          label: 'Tab 2',
          uploadedFiles: [new File(['b'], 'tab-2.xlsx')],
          repeatedFile: new File(['r'], 'tab-2-repeated.xlsx'),
          error: 'Needs reset',
          trendResults: [
            {
              exception_id: 'EX-1',
            } as TrendTab['trendResults'][number],
          ],
          selectedResult: {
            exception_id: 'EX-1',
          } as TrendTab['selectedResult'],
          hasAnalyzed: true,
        }),
      ],
      activeTabId: 'tab-2',
    });

    render(<TrendAnalyzerView />);

    fireEvent.click(screen.getByRole('button', { name: /reset current tab/i }));

    const { tabs, activeTabId } = useTrendStore.getState();
    expect(activeTabId).toBe('tab-2');
    expect(tabs[0].uploadedFiles.map((file) => file.name)).toEqual(['tab-1.xlsx']);
    expect(tabs[1].uploadedFiles).toHaveLength(0);
    expect(tabs[1].repeatedFile).toBeNull();
    expect(tabs[1].error).toBeNull();
    expect(tabs[1].trendResults).toHaveLength(0);
    expect(tabs[1].selectedResult).toBeNull();
    expect(tabs[1].hasAnalyzed).toBe(false);
  });
});
