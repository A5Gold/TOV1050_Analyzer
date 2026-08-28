import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import HistoryCompareView from '../HistoryCompareView';
import { useAnalysisStore, type CompareSession } from '../../store/useAnalysisStore';
import { useDatabaseStore } from '../../store/useDatabaseStore';

const comparisonDataGridSpy = vi.fn();

vi.mock('../../components/HistoryCompare/ComparisonDataGrid', () => ({
  __esModule: true,
  default: (props: any) => {
    comparisonDataGridSpy(props);
    return (
      <div data-testid="comparison-data-grid">
        Grid rows: {props.data.length}
      </div>
    );
  },
}));

vi.mock('../../components/HistoryCompare/ComparisonFilterPanel', () => ({
  __esModule: true,
  default: ({ onFilteredDataChange }: { onFilteredDataChange: (rows: any[]) => void }) => (
    <div data-testid="comparison-filter-panel">
      <button type="button" onClick={() => onFilteredDataChange([])}>
        Apply empty filter
      </button>
    </div>
  ),
}));

vi.mock('../../components/HistoryCompare/ComparisonChart', () => ({
  __esModule: true,
  default: () => <div data-testid="comparison-chart">Comparison Chart</div>,
}));

vi.mock('../../components/HistoryCompare/AlgorithmTutorialDialog', () => ({
  __esModule: true,
  default: () => null,
}));

vi.mock('../../components/HistoryCompare/SaveToDBDialog', () => ({
  __esModule: true,
  default: () => null,
}));

vi.mock('../../components/HistoryCompare/Check1YearDialog', () => ({
  __esModule: true,
  default: () => null,
}));

vi.mock('../../components/HistoryCompare/BatchEditDialog', () => ({
  __esModule: true,
  default: () => null,
}));

const buildCompareSession = (): CompareSession => ({
  id: 'compare-1',
  label: 'Comparison 1',
  latestFile: new File(['latest'], '20260101_EAL_UP_TAP-HUH_U1A.xlsx'),
  closestPreviousFile: new File(['closest'], '20251201_EAL_UP_TAP-HUH_U1A.xlsx'),
  olderPreviousFiles: [],
  repeatedData: [
    {
      id: 'EX-001',
      exception_id: 'EX-001',
      line: 'EAL',
      track: 'UP',
      section: 'Mainline',
      level: 'L1',
      exception_type: 'Wear',
      max_location: 123,
      from_m: 100,
      to_m: 150,
      action: '',
      check_result: '',
      task_run_date: '20260101',
    } as any,
  ],
  latestFileName: '20260101_EAL_UP_TAP-HUH_U1A.xlsx',
  chartData: [],
  loading: false,
  error: null,
  tabIndex: 0,
});

describe('HistoryCompareView result toolbar', () => {
  beforeEach(() => {
    comparisonDataGridSpy.mockClear();
    useAnalysisStore.getState().resetCompareSessions();
    useAnalysisStore.setState({
      compareSessions: [buildCompareSession()],
      activeCompareTabId: 'compare-1',
    });
    useDatabaseStore.getState().reset();
  });

  it('shows grouped result toolbar actions when comparison results exist', () => {
    render(<HistoryCompareView />);

    expect(screen.getByRole('tab', { name: /Repeated Table/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Comparison Chart/i })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /Version Difference/i })).not.toBeInTheDocument();

    const toolbar = screen.getByLabelText('comparison result toolbar');
    expect(within(toolbar).getByText('1 Match')).toBeInTheDocument();

    const editGroup = within(toolbar).getByLabelText('edit actions');
    expect(within(editGroup).getByRole('button', { name: /Batch Edit/i })).toBeVisible();
    expect(within(editGroup).getByRole('button', { name: /Save Edit/i })).toBeVisible();
    expect(within(editGroup).getByRole('button', { name: /Discard/i })).toBeVisible();

    const followUpGroup = within(toolbar).getByLabelText('follow-up actions');
    expect(within(followUpGroup).getByRole('button', { name: /Check 1 Year Record/i })).toBeVisible();
    expect(within(followUpGroup).getByRole('button', { name: /Export/i })).toBeVisible();
    expect(within(followUpGroup).getByRole('button', { name: /Save to DB/i })).toBeVisible();
  });

  it('preserves disabled state for edit actions without selection or pending changes', () => {
    render(<HistoryCompareView />);

    const toolbar = screen.getByLabelText('comparison result toolbar');
    const editGroup = within(toolbar).getByLabelText('edit actions');

    expect(within(editGroup).getByRole('button', { name: /Batch Edit/i })).toBeDisabled();
    expect(within(editGroup).getByRole('button', { name: /Save Edit/i })).toBeDisabled();
    expect(within(editGroup).getByRole('button', { name: /Discard/i })).toBeDisabled();

    const followUpGroup = within(toolbar).getByLabelText('follow-up actions');
    expect(within(followUpGroup).getByRole('button', { name: /Check 1 Year Record/i })).toBeEnabled();
    expect(within(followUpGroup).getByRole('button', { name: /Save to DB/i })).toBeEnabled();
  });

  it('keeps an empty filter result empty instead of falling back to all rows', async () => {
    const user = userEvent.setup();

    render(<HistoryCompareView />);

    expect(screen.getByText('Grid rows: 1')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Apply empty filter/i }));

    expect(await screen.findByText('Grid rows: 0')).toBeInTheDocument();
    expect(comparisonDataGridSpy.mock.calls.at(-1)?.[0]?.data).toEqual([]);
  });
});
