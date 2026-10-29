import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ChartComponent from '../ChartComponent';
import type { AnalysisResponse } from '../../types/api';

const mocks = vi.hoisted(() => ({ props: {} as any, get: vi.fn(), post: vi.fn() }));
vi.mock('../../api/client', () => ({ default: { get: mocks.get, post: mocks.post } }));
vi.mock('plotly.js', () => ({ default: { purge: vi.fn() } }));
vi.mock('react-plotly.js', async () => {
  const React = await import('react');
  return { default: React.forwardRef((props: any, _ref) => { mocks.props = props; return <div data-testid="plot" />; }) };
});

const result = (revision = 'r1') => ({
  status: 'success', analysis_revision: revision, analysis_mode: 'median', chart_view: 'chainage_median',
  params: { file_path: 'TWL.csv', line: 'TWL', section: 'Mainline', track: 'UT', date_str: '20260907' },
  chart_domain: { from_m: 0, to_m: 1000 },
  chart_data: { Chainage: [100, 101], height1: [10, 12], height1_min: [8, 11], height1_max: [30, 13],
    height1_valid_count: [3, 2], height1_source_row: [4, 6], height1_sample_counter: [1002, 1004], sample_count: [4, 2], source_row_first: [2, 6], source_row_last: [5, 7], SampleCount_first: [1000, 1004], SampleCount_last: [1003, 1005] },
  chart_resolution: { source_points: 2, returned_points: 2, strategy: 'raw', aggregation: 'chainage_median', raw_points: 6, grouped_points: 2 },
  exceptions: { 'High Height': [{ id: 'E1', 'exception type': 'High Height', level: 'L1', FromM: 100, ToM: 100,
    length: 0, maxLocation: 100, maxValue: 30, 'Threshold Value': 20 }] }, boundaries: [],
} as unknown as AnalysisResponse);

const detail = (height = 99) => ({ data: {
  chart_data: { Chainage: [100], height1: [height], source_row_number: [22] },
  chart_resolution: { source_points: 1, returned_points: 1, strategy: 'raw', aggregation: 'raw' },
} });

async function advance(ms = 250) { await act(async () => { vi.advanceTimersByTime(ms); }); }
function zoom(from = 90, to = 110) { act(() => mocks.props.onRelayout({ 'xaxis.range[0]': from, 'xaxis.range[1]': to })); }
describe('ChartComponent median/raw detail', () => {
  beforeEach(() => { vi.useFakeTimers(); mocks.get.mockReset(); mocks.post.mockReset().mockResolvedValue({ data: {} }); });
  afterEach(() => { cleanup(); vi.useRealTimers(); });

  it('draws measured sample lines with channel provenance and only selects exception markers', () => {
    const select = vi.fn();
    render(<ChartComponent result={result()} selectedExceptionId={null} onSelectException={select} sessionId="A" />);
    const traces = mocks.props.data;
    const line = traces.find((t: any) => t.name === 'height1');
    expect(line).toMatchObject({ mode: 'lines', y: [10, 12], connectgaps: false });
    expect(line.customdata[0]).toEqual([4, 1002, 3, 4]);
    expect(line.customdata.flat().every((value: any) => value != null)).toBe(true);
    expect(traces.every((trace: any) => trace.xaxis === 'x')).toBe(true);
    expect(mocks.props.layout.xaxis).toMatchObject({ anchor: 'y3' });
    for (const axis of ['yaxis', 'yaxis2', 'yaxis3']) expect(mocks.props.layout[axis].anchor).toBe('x');
    act(() => mocks.props.onClick({ points: [{ data: line, text: 'E1', pointIndex: 0 }] }));
    expect(select).not.toHaveBeenCalled();
    act(() => mocks.props.onClick({ points: [{ data: traces.find((t: any) => t.name === 'High Height Dots'), text: 'E1', pointIndex: 0 }] }));
    expect(select).toHaveBeenCalledWith('E1');
  });

  it('debounces arbitrary zooms and sends the session/revision and median mode', async () => {
    mocks.get.mockResolvedValue(detail());
    render(<ChartComponent result={result()} selectedExceptionId={null} onSelectException={vi.fn()} sessionId="A" />);
    zoom(); await advance(200); zoom(95, 105); await advance(249);
    expect(mocks.get).not.toHaveBeenCalled();
    await advance(1);
    expect(mocks.get).toHaveBeenCalledTimes(1);
    expect(mocks.get.mock.calls[0][1]).toMatchObject({ timeout: 30000, params: {
      from_m: 95, to_m: 105, client_session_id: 'A', analysis_revision: 'r1', chart_data_mode: 'chainage_median', max_points: 12000,
    } });
  });

  it('draws raw overview lines, separates segments, and labels missing provenance', () => {
    const raw = result();
    raw.analysis_mode = 'raw_overview'; raw.chart_view = 'raw'; raw.exceptions = {};
    raw.chart_data = { Chainage: [100, 101, 100], height1: [10, 12, 14], segment_id: [0, 0, 1] };
    render(<ChartComponent result={raw} selectedExceptionId={null} onSelectException={vi.fn()} sessionId="A" />);
    const trace = mocks.props.data.find((t: any) => t.name === 'height1');
    expect(trace).toMatchObject({ mode: 'lines', x: [100, 101, null, 100], y: [10, 12, null, 14] });
    expect(trace.customdata[0]).toEqual(['未提供', '未提供', 1, 1]);
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(mocks.get).not.toHaveBeenCalled();
  });

  it('cancels old windows and ignores late responses after a session/revision change', async () => {
    let resolveOld: (value: any) => void = () => {};
    mocks.get.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }));
    const view = render(<ChartComponent result={result()} selectedExceptionId={null} onSelectException={vi.fn()} sessionId="A" />);
    zoom(); await advance();
    const oldSignal = mocks.get.mock.calls[0][1].signal;
    view.rerender(<ChartComponent result={result('r2')} selectedExceptionId={null} onSelectException={vi.fn()} sessionId="B" />);
    expect(oldSignal.aborted).toBe(true);
    await act(async () => resolveOld(detail(999)));
    expect(mocks.props.data.find((t: any) => t.name === 'height1').y).toEqual([10, 12]);
  });

  it('shows detail failures and keeps the displayed data and precision label', async () => {
    mocks.get.mockRejectedValue({ response: { data: { detail: 'Analysis has expired. Re-analyze the source file.' } } });
    render(<ChartComponent result={result()} selectedExceptionId={null} onSelectException={vi.fn()} sessionId="A" />);
    zoom(); await advance();
    expect(screen.getByRole('alert')).toHaveTextContent('Analysis has expired');
    expect(mocks.props.data.find((t: any) => t.name === 'height1').y).toEqual([10, 12]);
  });

  it('loads selected exception detail and resets to overview on autorange', async () => {
    mocks.get.mockResolvedValue(detail());
    render(<ChartComponent result={result()} selectedExceptionId="E1" onSelectException={vi.fn()} sessionId="A" />);
    await advance();
    expect(mocks.get.mock.calls[0][1].params).toMatchObject({ from_m: 0, to_m: 200 });
    expect(mocks.props.layout.xaxis).toMatchObject({ range: [0, 200], anchor: 'y3' });
    expect(mocks.props.layout.xaxis.matches).toBeUndefined();
    act(() => mocks.props.onRelayout({ 'xaxis.autorange': true }));
    expect(mocks.props.data.find((t: any) => t.name === 'height1').y).toEqual([10, 12]);
    expect(mocks.props.layout.xaxis).toMatchObject({ autorange: true, title: { text: 'Chainage (m)' } });
  });
  it('double-click immediately restores resident overview and ignores pending raw detail', async () => {
    let finish!: (value: any) => void;
    mocks.get.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    const raw = result(); raw.analysis_mode = 'raw_overview'; raw.chart_view = 'raw';
    render(<ChartComponent result={raw} selectedExceptionId={null} onSelectException={vi.fn()} sessionId="A" />);
    zoom(); await advance();
    expect(mocks.get.mock.calls[0][1].params.chart_data_mode).toBe('raw');
    expect(mocks.get.mock.calls[0][1].timeout).toBe(120000);
    act(() => mocks.props.onDoubleClick());
    expect(mocks.get.mock.calls[0][1].signal.aborted).toBe(true);
    expect(mocks.props.data[0].y).toEqual([10, 12]);
    await act(async () => finish(detail(999)));
    await advance();
    expect(mocks.props.data[0].y).toEqual([10, 12]);
    expect(mocks.get).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });

  it('explains a raw cold reload and cancels it while keeping the chart, then retries', async () => {
    let finish!: (value: any) => void;
    mocks.get.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    mocks.get.mockResolvedValueOnce(detail(55));
    const raw = { ...result(), analysis_mode: 'raw_overview' as const, chart_view: 'raw' as const };
    render(<ChartComponent result={raw} selectedExceptionId={null} onSelectException={vi.fn()} sessionId="A" />);
    zoom(); await advance();
    expect(screen.getByRole('status')).toHaveTextContent('載入原始資料明細；快取過期時需重新讀取來源檔');
    expect(mocks.get.mock.lastCall?.[1].timeout).toBe(120000);
    const signal = mocks.get.mock.lastCall?.[1].signal;
    fireEvent.click(screen.getByRole('button', { name: '取消載入' }));
    expect(signal.aborted).toBe(true);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('已取消載入');
    await act(async () => finish(detail(999)));
    expect(mocks.props.data[0].y).toEqual([10, 12]);
    fireEvent.click(screen.getByRole('button', { name: '重試此範圍' }));
    await advance();
    expect(mocks.props.data[0].y).toEqual([55]);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows only configured signed threshold segments without selecting an exception', () => {
    const overview = { ...result(), threshold_segments: [
      { from_m: 0, to_m: 500, metric: 'stagger', exception_type: 'Stagger Right', level: 'L2', value: -240 },
      { from_m: 500, to_m: 1000, metric: 'wear', exception_type: 'Wire Wear', level: 'L1', value: 9.5 },
    ] };
    render(<ChartComponent result={overview} selectedExceptionId={null} onSelectException={vi.fn()} sessionId="A" />);
    expect(mocks.props.layout.shapes).toHaveLength(2);
    expect(mocks.props.layout.shapes[0]).toMatchObject({ x0: 0, x1: 500, y0: -240, y1: -240, yref: 'y2' });
    fireEvent.click(screen.getByRole('checkbox', { name: '門檻線' }));
    expect(mocks.props.layout.shapes).toHaveLength(0);
    expect(mocks.get).not.toHaveBeenCalled();
  });

  it('focuses the actual marker among overlapping line points and refocuses the same dot after panning', async () => {
    mocks.get.mockResolvedValue(detail());
    const select = vi.fn();
    render(<ChartComponent result={result()} selectedExceptionId="E1" onSelectException={select} sessionId="A" />);
    await advance();
    zoom(400, 600); await advance();
    const dots = mocks.props.data.find((trace: any) => trace.name === 'High Height Dots');
    act(() => mocks.props.onClick({ points: [
      { data: mocks.props.data[0], text: 'E1', x: 100 },
      { data: dots, customdata: 'E1', x: 100, pointIndex: 0 },
    ] }));
    expect(select).toHaveBeenCalledWith('E1');
    expect(mocks.props.layout.xaxis.range).toEqual([0, 200]);
    await advance();
    expect(mocks.get.mock.lastCall?.[1].params).toMatchObject({ from_m: 0, to_m: 200 });
  });

  it('clamps negative padding, sorts reverse ranges, and handles wholly outside windows locally', async () => {
    mocks.get.mockResolvedValue(detail());
    render(<ChartComponent result={result()} selectedExceptionId={null} onSelectException={vi.fn()} sessionId="A" />);
    zoom(200, -919.16); await advance();
    expect(mocks.get.mock.lastCall?.[1].params).toMatchObject({ from_m: 0, to_m: 200 });
    expect(mocks.props.layout.xaxis.range).toEqual([0, 200]);
    zoom(-300, -100); await advance();
    expect(mocks.get).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('alert')).toHaveTextContent('此範圍沒有資料');
    expect(mocks.props.data.find((trace: any) => trace.name === 'height1').y).toEqual([]);
    zoom(NaN, 100); zoom(10, 10); await advance();
    expect(mocks.get).toHaveBeenCalledTimes(1);
  });

  it('does not cancel an in-flight request for a duplicate relayout and retries the same failed window', async () => {
    mocks.get.mockRejectedValueOnce({ response: { status: 422, data: { detail: [{ loc: ['query', 'from_m'], msg: 'invalid range' }] } } });
    mocks.get.mockResolvedValueOnce(detail(44));
    render(<ChartComponent result={result()} selectedExceptionId={null} onSelectException={vi.fn()} sessionId="A" />);
    zoom(); await advance();
    expect(screen.getByRole('alert')).toHaveTextContent('query.from_m: invalid range');
    fireEvent.click(screen.getByRole('button', { name: '重試此範圍' }));
    await advance();
    expect(mocks.get).toHaveBeenCalledTimes(2);
    expect(mocks.props.data.find((trace: any) => trace.name === 'height1').y).toEqual([44]);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    let finish!: (value: any) => void;
    mocks.get.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    zoom(300, 500); await advance();
    const signal = mocks.get.mock.lastCall?.[1].signal;
    zoom(300, 500); await advance();
    expect(signal.aborted).toBe(false);
    expect(mocks.get).toHaveBeenCalledTimes(3);
    await act(async () => finish(detail(55)));
    expect(mocks.props.data.find((trace: any) => trace.name === 'height1').y).toEqual([55]);
  });

  it('releases a raw detail cache on revision changes and unmount, without treating superseded requests as failures', async () => {
    mocks.get.mockRejectedValue({ response: { status: 409, data: { detail: { code: 'CHART_REQUEST_SUPERSEDED', message: 'Replaced' } } } });
    const raw = { ...result(), analysis_mode: 'raw_overview' as const, chart_view: 'raw' as const };
    const view = render(<ChartComponent result={raw} selectedExceptionId={null} onSelectException={vi.fn()} sessionId="A" />);
    zoom(); await advance();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    view.rerender(<ChartComponent result={{ ...raw, analysis_revision: 'r2' }} selectedExceptionId={null} onSelectException={vi.fn()} sessionId="A" />);
    expect(mocks.post).toHaveBeenCalledWith('/analyze/chart-cache/release', { client_session_id: 'A', analysis_revision: 'r1' });
    view.unmount();
    expect(mocks.post).toHaveBeenCalledWith('/analyze/chart-cache/release', { client_session_id: 'A', analysis_revision: 'r2' });
  });

});
