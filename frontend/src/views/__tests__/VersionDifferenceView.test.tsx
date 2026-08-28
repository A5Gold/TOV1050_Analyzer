import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import VersionDifferenceView from '../VersionDifferenceView';
import { VERSION_DIFFERENCE_CYCLES } from '../../constants/versionDifferenceCycles';
import { useVersionDifferenceStore } from '../../store/useVersionDifferenceStore';

const { analyzeSpy, chartSpy } = vi.hoisted(() => ({ analyzeSpy: vi.fn(), chartSpy: vi.fn() }));

vi.mock('../../api/client', () => ({ analyzeVersionDifference: analyzeSpy }));
vi.mock('../../components/VersionDifference/VersionDifferenceChart', () => ({
  __esModule: true,
  default: (props: any) => { chartSpy(props); return <div data-testid="version-difference-chart" />; },
}));

const readyResponse = { status: 'ready', latest_file: 'latest.xlsx', comparisons: [] } as any;

describe('VersionDifferenceView', () => {
  beforeEach(() => {
    analyzeSpy.mockReset();
    chartSpy.mockClear();
    useVersionDifferenceStore.getState().reset();
  });

  it('renders five role-labelled upload slots with the shared cycle colors', () => {
    render(<VersionDifferenceView />);

    VERSION_DIFFERENCE_CYCLES.forEach(cycle => {
      const slot = screen.getByRole('group', { name: `${cycle.label} report upload` });
      expect(slot).toHaveStyle({ borderColor: cycle.color });
      expect(slot.querySelector('[data-cycle-swatch]')).toHaveStyle({ backgroundColor: cycle.color });
    });
    expect(screen.getAllByText('Required')).toHaveLength(2);
    expect(screen.getAllByText('Optional')).toHaveLength(3);
  });

  it('requires Latest and Previous 1 and posts reports in explicit roles', async () => {
    const user = userEvent.setup();
    analyzeSpy.mockResolvedValue(readyResponse);
    render(<VersionDifferenceView />);
    const compare = screen.getByRole('button', { name: 'Compare' });
    expect(compare).toBeDisabled();

    const latest = new File(['latest'], 'latest.xlsx');
    const previous1 = new File(['previous-1'], 'previous-1.xlsx');
    await user.upload(screen.getByLabelText('Select Latest report'), latest);
    await user.upload(screen.getByLabelText('Select Previous 1 report'), previous1);
    expect(compare).toBeEnabled();

    await user.click(compare);
    expect(analyzeSpy).toHaveBeenCalledWith(latest, previous1, null);
    expect(chartSpy.mock.calls.at(-1)?.[0].response).toBe(readyResponse);
  });

  it('includes optional Previous 2 and invalidates stale results when an input is removed', async () => {
    const user = userEvent.setup();
    analyzeSpy.mockResolvedValue(readyResponse);
    render(<VersionDifferenceView />);
    await user.upload(screen.getByLabelText('Select Latest report'), new File(['latest'], 'latest.xlsx'));
    await user.upload(screen.getByLabelText('Select Previous 1 report'), new File(['one'], 'previous-1.xlsx'));
    const previous2 = new File(['two'], 'previous-2.xlsx');
    await user.upload(screen.getByLabelText('Select Previous 2 report'), previous2);
    await user.click(screen.getByRole('button', { name: 'Compare' }));

    expect(analyzeSpy.mock.calls[0][2]).toBe(previous2);
    await user.click(screen.getByRole('button', { name: 'Remove Previous 2 report' }));
    expect(chartSpy.mock.calls.at(-1)?.[0].response).toBeUndefined();
  });

  it('keeps an optional gap when only Previous 4 is supplied', async () => {
    const user = userEvent.setup();
    analyzeSpy.mockResolvedValue(readyResponse);
    render(<VersionDifferenceView />);
    const latest = new File(['latest'], 'latest.xlsx');
    const previous1 = new File(['one'], 'previous-1.xlsx');
    const previous4 = new File(['four'], 'previous-4.xlsx');

    await user.upload(screen.getByLabelText('Select Latest report'), latest);
    await user.upload(screen.getByLabelText('Select Previous 1 report'), previous1);
    await user.upload(screen.getByLabelText('Select Previous 4 report'), previous4);
    await user.click(screen.getByRole('button', { name: 'Compare' }));

    expect(analyzeSpy).toHaveBeenCalledWith(latest, previous1, null, null, previous4);
  });

  it('rejects non-Excel input before calling the API', async () => {
    const user = userEvent.setup({ applyAccept: false });
    render(<VersionDifferenceView />);

    await user.upload(screen.getByLabelText('Select Latest report'), new File(['text'], 'latest.txt', { type: 'text/plain' }));

    expect(screen.getByText('Latest must be an Excel workbook.')).toBeInTheDocument();
    expect(analyzeSpy).not.toHaveBeenCalled();
  });

  it('keeps an in-flight comparison and its result when the view is remounted', async () => {
    const user = userEvent.setup();
    let resolveComparison: (value: typeof readyResponse) => void = () => undefined;
    analyzeSpy.mockImplementation(() => new Promise(resolve => { resolveComparison = resolve; }));

    const firstRender = render(<VersionDifferenceView />);
    await user.upload(screen.getByLabelText('Select Latest report'), new File(['latest'], 'latest.xlsx'));
    await user.upload(screen.getByLabelText('Select Previous 1 report'), new File(['one'], 'previous-1.xlsx'));
    await user.click(screen.getByRole('button', { name: 'Compare' }));
    expect(screen.getByRole('button', { name: 'Comparing...' })).toBeDisabled();

    firstRender.unmount();
    render(<VersionDifferenceView />);
    expect(screen.getByRole('button', { name: 'Comparing...' })).toBeDisabled();

    await act(async () => resolveComparison(readyResponse));
    expect(chartSpy.mock.calls.at(-1)?.[0].response).toBe(readyResponse);
  });

  it('adds independent comparison tabs up to the six-tab limit', async () => {
    const user = userEvent.setup();
    render(<VersionDifferenceView />);

    expect(screen.getByRole('tab', { name: /Comparison 1/ })).toHaveAttribute('aria-selected', 'true');
    const addTab = screen.getByRole('button', { name: 'Add comparison' });
    await user.click(addTab);
    expect(screen.getByRole('tab', { name: /Comparison 2/ })).toHaveAttribute('aria-selected', 'true');

    await user.upload(screen.getByLabelText('Select Latest report'), new File(['latest'], 'tab-2-latest.xlsx'));
    await user.click(screen.getByRole('tab', { name: /Comparison 1/ }));
    expect(screen.getAllByText('No file selected')).toHaveLength(5);

    await user.click(addTab);
    await user.click(addTab);
    await user.click(addTab);
    await user.click(addTab);
    expect(screen.getAllByRole('tab')).toHaveLength(6);
    expect(addTab).toBeDisabled();
  });
});
