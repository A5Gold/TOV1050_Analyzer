import React, { useCallback, useEffect, useState, useMemo, useRef } from 'react';
import Plotly from 'plotly.js';
import Plot from 'react-plotly.js';
import { Alert, Box, Typography, Paper, FormGroup, FormControlLabel, Checkbox, Button, Chip, CircularProgress } from '@mui/material';
import ClearIcon from '@mui/icons-material/Clear';
import { AnalysisResponse, ExceptionRecord } from '../types/api';
import apiClient from '../api/client';

const LEVEL_COLORS: Record<string, string> = {
  'L1': '#d32f2f', // Red
  'L2': '#ed6c02', // Orange
  'L3': '#0288d1', // Blue
};

interface ChartComponentProps {
  result: AnalysisResponse | null;
  selectedExceptionId: string | null;
  onSelectException: (id: string | null) => void;
  sessionId: string;
}

type ChartDomain = { from_m: number; to_m: number };
type ChartWindow = { from: number; to: number; empty?: boolean };
type ThresholdSegment = ChartDomain & {
  metric: 'height' | 'stagger' | 'wear';
  exception_type: string;
  level: string;
  value: number;
};
type ChartExtras = { chart_domain?: ChartDomain | null; threshold_segments?: ThresholdSegment[] };
type DetailResponse = ChartExtras & Pick<AnalysisResponse, 'chart_data' | 'chart_resolution'>;

// Clamp only overlapping windows. A valid window wholly outside the data is
// empty, rather than a zero-width request at the nearest endpoint.
const normalizeWindow = (start: number, end: number, domain: ChartDomain | null): ChartWindow | null => {
  if (!Number.isFinite(start) || !Number.isFinite(end) || start === end) return null;
  const from = Math.min(start, end), to = Math.max(start, end);
  if (!domain) return { from, to };
  if (to < domain.from_m || from > domain.to_m) return { from, to, empty: true };
  return { from: Math.max(from, domain.from_m), to: Math.min(to, domain.to_m) };
};

const detailErrorMessage = (error: any): string => {
  const detail = error?.response?.data?.detail;
  const message = typeof detail === 'string' ? detail : Array.isArray(detail)
    ? detail.map(item => `${item.loc?.join('.') || '參數'}: ${item.msg || '無效值'}`).join('；') : detail?.message || '';
  if ([409, 410].includes(error?.response?.status)) return `${message || '分析快照已失效。'} 請重新匯入或重新分析。`;
  if (error?.response?.status === 422) return `圖表範圍驗證失敗：${message || '請檢查里程範圍。'}`;
  if (error?.code === 'ECONNABORTED' || error?.code === 'ETIMEDOUT') return '載入圖表細節逾時，請重試此範圍。';
  return message || '無法載入圖表細節，請重試此範圍。';
};

const ChartComponent = ({ result, selectedExceptionId, onSelectException, sessionId }: ChartComponentProps) => {
  
  const [showMarkers, setShowMarkers] = useState(true);
  const [showThresholds, setShowThresholds] = useState(true);
  const [showLegend, setShowLegend] = useState(true);
  const [layoutState, setLayoutState] = useState<Partial<Plotly.Layout>>({});
  const [chartData, setChartData] = useState<AnalysisResponse['chart_data']>({});
  const [chartResolution, setChartResolution] = useState<AnalysisResponse['chart_resolution']>();
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailCancelled, setDetailCancelled] = useState(false);
  const [detailWindow, setDetailWindow] = useState<ChartWindow | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);
  const [thresholdSegments, setThresholdSegments] = useState<ThresholdSegment[]>([]);
  const [loadedIdentity, setLoadedIdentity] = useState('');
  const chartRef = useRef<any>(null); // Ref to hold the Plotly chart instance
  const detailController = useRef<AbortController | null>(null);
  const requestGeneration = useRef(0);
  const focusGeneration = useRef(0);
  const requestedWindow = useRef<ChartWindow | null>(null);
  const isRaw = result?.analysis_mode === 'raw_overview' || result?.chart_view === 'raw';
  const dataMode = isRaw ? 'raw' : 'chainage_median';
  const identity = `${sessionId}:${result?.analysis_revision || ''}:${dataMode}`;
  const domain = useMemo(() => {
    const provided = (result as (AnalysisResponse & ChartExtras) | null)?.chart_domain;
    if (provided && Number.isFinite(provided.from_m) && Number.isFinite(provided.to_m) && provided.from_m <= provided.to_m) return provided;
    let min = Infinity, max = -Infinity;
    for (const value of result?.chart_data.Chainage || []) {
      if (typeof value === 'number' && Number.isFinite(value)) { min = Math.min(min, value); max = Math.max(max, value); }
    }
    return Number.isFinite(min) ? { from_m: min, to_m: max } : null;
  }, [result]);
  const setWindow = useCallback((start: number, end: number) => {
    const next = normalizeWindow(start, end, domain);
    if (!next) return;
    const previous = requestedWindow.current;
    if (previous?.from !== next.from || previous?.to !== next.to || !!previous?.empty !== !!next.empty) {
      // Invalidate synchronously, before the next effect cleanup can run.
      requestGeneration.current += 1;
      detailController.current?.abort();
      requestedWindow.current = next;
      setDetailWindow(next);
    }
    setLayoutState(previous => previous.xaxis?.range?.[0] === next.from && previous.xaxis?.range?.[1] === next.to && previous.xaxis?.autorange === false
      ? previous : { ...previous, xaxis: { ...previous.xaxis, range: [next.from, next.to], autorange: false } });
  }, [domain]);
  const focusException = useCallback((exception: ExceptionRecord, markerX = exception.maxLocation) => {
    if (!Number.isFinite(markerX)) return;
    setWindow(markerX - 100, markerX + 100);
    setLayoutState(previous => ({ ...previous, uirevision: `${identity}:focus:${++focusGeneration.current}` }));
  }, [identity, setWindow]);

  // Keep the initial overview resident: reset never needs a full-data request.
  const resetOverview = () => {
    requestGeneration.current += 1;
    detailController.current?.abort();
    setChartData(result?.chart_data || {});
    setChartResolution(result?.chart_resolution);
    setThresholdSegments((result as (AnalysisResponse & ChartExtras) | null)?.threshold_segments || []);
    setLoadedIdentity(identity);
    requestedWindow.current = null;
    setDetailWindow(null);
    setDetailLoading(false);
    setDetailError(null);
    setDetailCancelled(false);
    setLayoutState({ xaxis: { autorange: true, anchor: 'y3' },
      yaxis: { autorange: true, domain: [0.70, 1], anchor: 'x' },
      yaxis2: { autorange: true, domain: [0.35, 0.65], anchor: 'x' },
      yaxis3: { autorange: true, domain: [0, 0.30], anchor: 'x' } });
    onSelectException(null);
  };

  const selectedException = useMemo(() => {
    if (!result || !selectedExceptionId) return null;
    for (const list of Object.values(result.exceptions)) {
      const found = list.find(e => e.id === selectedExceptionId);
      if (found) return found;
    }
    return null;
  }, [result, selectedExceptionId]);

  useEffect(() => {
    requestGeneration.current += 1;
    detailController.current?.abort();
    setChartData(result?.chart_data || {});
    setChartResolution(result?.chart_resolution);
    setThresholdSegments((result as (AnalysisResponse & ChartExtras) | null)?.threshold_segments || []);
    setLoadedIdentity(identity);
    requestedWindow.current = null;
    setDetailWindow(null);
    setLayoutState({});
    setDetailError(null);
    setDetailCancelled(false);
    setDetailLoading(false);
  }, [result, identity]);

  // A new window/mode cancels both the debounce and any in-flight request.
  // Never apply detail from another session or successful analysis revision.
  useEffect(() => {
    if (!result) return;
    if (!detailWindow) {
      setChartData(result?.chart_data || {});
      setChartResolution(result?.chart_resolution);
      setLoadedIdentity(identity);
      setDetailLoading(false);
      return;
    }
    if (detailWindow.empty) {
      setChartData(Object.fromEntries(Object.keys(result.chart_data).map(key => [key, []])));
      setChartResolution({ source_points: 0, returned_points: 0, strategy: 'empty', from_m: detailWindow.from, to_m: detailWindow.to });
      setLoadedIdentity(identity);
      setDetailLoading(false);
      setDetailError(null);
      setDetailCancelled(false);
      return;
    }
    let cancelled = false;
    const controller = new AbortController();
    detailController.current = controller;
    const generation = ++requestGeneration.current;
    const isCurrent = () => !cancelled && !controller.signal.aborted && generation === requestGeneration.current;
    setDetailLoading(true);
    setDetailError(null);
    setDetailCancelled(false);
    const timer = window.setTimeout(() => {
      if (!isCurrent()) return;
      apiClient.get<DetailResponse>(
      '/analyze/chart-data',
      {
        signal: controller.signal,
        // Raw cache expiry requires a full source read; measured cold loads
        // exceed 30 seconds. Median detail keeps its normal response budget.
        timeout: isRaw ? 120000 : 30000,
        params: {
          from_m: detailWindow?.from,
          to_m: detailWindow?.to,
          max_points: 12000,
          file_path: result?.params.file_path,
          line: result?.params.line,
          client_session_id: sessionId,
          analysis_revision: result.analysis_revision,
          chart_data_mode: dataMode,
        },
      },
    ).then(({ data }) => {
      if (isCurrent()) {
        setChartData(data.chart_data);
        setChartResolution(data.chart_resolution);
        if (data.threshold_segments) setThresholdSegments(data.threshold_segments);
        setLoadedIdentity(identity);
      }
    }).catch((error) => {
      if (isCurrent() && error?.code !== 'ERR_CANCELED' && error?.response?.data?.detail?.code !== 'CHART_REQUEST_SUPERSEDED') {
        setDetailError(detailErrorMessage(error));
      }
    }).finally(() => {
      if (isCurrent()) setDetailLoading(false);
    });
    }, 250);
    return () => { cancelled = true; controller.abort(); window.clearTimeout(timer); };
  }, [detailWindow, retryNonce, dataMode, isRaw, result, sessionId, identity]);

  // Handle Chart Zoom based on Selection
  useEffect(() => {
    if (selectedException) focusException(selectedException);
  }, [selectedException, focusException]);

  useEffect(() => {
    if (!isRaw || !result?.analysis_revision) return;
    const revision = result.analysis_revision;
    return () => {
      // Releasing a raw view only drops its bounded detail cache. The resident
      // overview remains usable, and later visits can prepare detail again.
      void apiClient.post('/analyze/chart-cache/release', {
        client_session_id: sessionId, analysis_revision: revision,
      }).catch(() => { /* TTL also releases caches if the backend has exited. */ });
    };
  }, [isRaw, result?.analysis_revision, sessionId]);

  // Clean up plot on unmount
  useEffect(() => {
    return () => {
      // Explicitly purge the plot
      if (chartRef.current && chartRef.current.el) {
        try {
            Plotly.purge(chartRef.current.el);
        } catch (e) {
            console.warn('Failed to purge plot:', e);
        }
      }
    };
  }, []);

  if (!result) {
    return <Typography>No data loaded.</Typography>;
  }

  const displayedData = loadedIdentity === identity ? chartData : result.chart_data;
  const resolution = loadedIdentity === identity ? chartResolution : result.chart_resolution;
  const chainage = displayedData['Chainage'] || [];
  const traces: Plotly.Data[] = [];
  const channelColors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd'];

    const addLineTrace = (name: string, yCol: string, row: number) => {
    if (displayedData[yCol]) {
      const color = channelColors[(Number(yCol.slice(-1)) - 1) % 4];
      const x: (number | null)[] = [], y: (number | null)[] = [];
      const customdata: (number | string)[][] = [];
      chainage.forEach((value, i) => {
        // Acquisition passes and context segments must never be joined.
        const keys = ['segment_id', 'pass_id', 'context_id'];
        if (i > 0 && keys.some(key => displayedData[key]?.[i] !== displayedData[key]?.[i - 1])) {
          x.push(null); y.push(null); customdata.push(['—', '—', '—', '—']);
        }
        x.push(value); y.push(displayedData[yCol][i]);
        customdata.push([
          displayedData[`${yCol}_source_row`]?.[i] ?? displayedData.source_row_number?.[i] ?? '未提供',
          displayedData[`${yCol}_sample_counter`]?.[i] ?? displayedData.SampleCount?.[i] ?? '未提供',
          displayedData[`${yCol}_valid_count`]?.[i] ?? 1,
          displayedData.sample_count?.[i] ?? 1,
        ]);
      });
      traces.push({
        x,
        y,
        type: 'scattergl',
        mode: 'lines',
        connectgaps: false,
        name,
        customdata: customdata as any,
        hovertemplate: `Chainage: %{x:.4f} m<br>實測值: %{y:.4f} mm<br>來源列: %{customdata[0]}<br>SampleCount: %{customdata[1]}<br>有效樣本: %{customdata[2]} / %{customdata[3]}<extra>%{fullData.name}</extra>`,
        xaxis: 'x',
        yaxis: row === 1 ? 'y' : `y${row}`,
        marker: { size: 3, color },
        line: { width: 1, color }
      });
    }
  };

  ['height1', 'height2', 'height3', 'height4'].forEach(c => addLineTrace(c, c, 1));
  ['stagger1', 'stagger2', 'stagger3', 'stagger4'].forEach(c => addLineTrace(c, c, 2));
  ['wear1', 'wear2', 'wear3', 'wear4'].forEach(c => addLineTrace(c, c, 3));

  if (showMarkers) {
    const rowMap: Record<string, number> = {
      'Low Height': 1, 'High Height': 1,
      'Stagger Left': 2, 'Stagger Right': 2,
      'Wire Wear': 3
    };

    Object.entries(result.exceptions).forEach(([type, items]) => {
        if (!items.length) return;
        const targetRow = rowMap[type] || 1;
        const x: number[] = [];
        const y: number[] = [];
        const colors: string[] = [];
        const ids: string[] = [];

        items.forEach(item => {
            x.push(item.maxLocation);
            y.push(item.maxValue);
            colors.push(LEVEL_COLORS[item.level] || 'grey');
            ids.push(item.id);
        });

        traces.push({
            x: x,
            y: y,
            mode: 'markers',
            type: 'scattergl',
            name: `${type} Dots`,
            text: ids,
            customdata: ids.map(id => ({ kind: 'exception-marker', id })) as any,
            xaxis: 'x',
            yaxis: targetRow === 1 ? 'y' : `y${targetRow}`,
            marker: {
                size: 8, 
                color: colors,
                symbol: 'circle',
                line: { color: 'white', width: 1 }
            },
            hoverinfo: 'text', // Only show ID on hover
            hovertemplate: '<b>ID: %{text}</b><br>Loc: %{x:.2f}m<br>Val: %{y:.2f}<extra></extra>',
        });
    });
  }

  // Shapes Construction
  const shapes: Partial<Plotly.Shape>[] = [];

  // Values are already signed and resolved by the detector's same-revision
  // metadata rules. Never invent absent levels or mirror stagger thresholds.
  const activeThresholds = loadedIdentity === identity ? thresholdSegments : (result as AnalysisResponse & ChartExtras).threshold_segments || [];
  if (showThresholds && !isRaw) {
    for (const segment of activeThresholds) {
      if (![segment.from_m, segment.to_m, segment.value].every(Number.isFinite)) continue;
      shapes.push({
        type: 'line', x0: segment.from_m, x1: segment.to_m,
        y0: segment.value, y1: segment.value, xref: 'x',
        yref: ({ height: 'y', stagger: 'y2', wear: 'y3' } as const)[segment.metric],
        line: { color: LEVEL_COLORS[segment.level] || '#687589', width: 1, dash: 'dash' },
        opacity: 0.8,
      });
    }
  }

  if (selectedException) {
    const center = selectedException.maxLocation;
    const type = selectedException['exception type'];
    const rowMap: Record<string, string> = {
      'Low Height': 'y', 'High Height': 'y',
      'Stagger Left': 'y2', 'Stagger Right': 'y2',
      'Wire Wear': 'y3'
    };
    const yRef = rowMap[type] || 'y';

    // Define domains for paper coordinates to match baseLayout
    // This prevents the highlight rect from stretching the Y-axis range
    const domainMap: Record<string, [number, number]> = {
      'y': [0.70, 1],
      'y2': [0.35, 0.65],
      'y3': [0, 0.30]
    };
    const [domainMin, domainMax] = domainMap[yRef] || [0, 1];

    // 1. Highlight Area (Specific Subplot)
    shapes.push({
      type: 'rect',
      x0: selectedException.FromM,
      x1: selectedException.ToM,
      y0: domainMin, 
      y1: domainMax,
      xref: 'x',
      yref: 'paper',
      fillcolor: 'rgba(200, 200, 200, 0.3)', // Lighter Gray
      line: { width: 0 },
      layer: 'below' // Draw behind data traces
    });
    
    // 2. Vertical Line (At Peak)
    if (showMarkers) {
      shapes.push({
        type: 'line',
        x0: center, x1: center,
        y0: 0, y1: 1,
        xref: 'x', yref: 'paper',
        line: { 
          color: LEVEL_COLORS[selectedException.level] || 'red', 
          width: 2, 
          dash: 'dot' 
        }
      });
    }

  }

  const baseLayout: Partial<Plotly.Layout> = {
    uirevision: identity,
    // All measurement panels share one canonical chainage axis. Session
    // isolation belongs to uirevision, not Plotly axis IDs (x, x2, ...).
    margin: { t: 30, r: 20, b: 40, l: 60 },
    // Removed fixed height to allow flexbox resizing
    autosize: true,
    showlegend: showLegend,
    shapes: shapes,
    xaxis: {  
      title: { text: 'Chainage (m)' }, 
      anchor: 'y3' as any, 
      showticklabels: true 
    },
    yaxis: { title: { text: 'Height (mm)' }, domain: [0.70, 1], anchor: 'x', showgrid: true },
    yaxis2: { title: { text: 'Stagger (mm)' }, domain: [0.35, 0.65], anchor: 'x', showgrid: true },
    yaxis3: { title: { text: 'Wear (mm)' }, domain: [0, 0.30], anchor: 'x', showgrid: true },
  };

  const finalLayout = { 
    ...baseLayout, 
    ...layoutState,
    xaxis: { ...baseLayout.xaxis, ...layoutState.xaxis },
    yaxis: { ...baseLayout.yaxis, ...layoutState.yaxis },
    yaxis2: { ...baseLayout.yaxis2, ...layoutState.yaxis2 },
    yaxis3: { ...baseLayout.yaxis3, ...layoutState.yaxis3 },
    shapes: shapes 
  };

  const chartTitle = `${result.params.date_str}_${result.params.line}_${result.params.section}_${result.params.track}`;

  return (
    <Box sx={{ width: '100%', height: '100%', p: 1, display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'space-between', alignItems: 'center', mb: 1, px: 1 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1, minWidth: 0 }}>
          <Typography variant="h6" color="primary" noWrap>{chartTitle}</Typography>
          {resolution && <Chip size="small" variant="outlined" label={`${isRaw ? '原始資料概覽' : '同 Km 中位實測樣本'}${resolution.strategy === 'min_max_envelope' ? ' · 概覽取樣' : ''} · ${resolution.returned_points.toLocaleString()} / ${resolution.source_points.toLocaleString()} 點`} />}
          {detailLoading && <CircularProgress size={16} aria-label="Loading chart detail" />}
        </Box>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
          <FormGroup row>
            <FormControlLabel 
              control={<Checkbox checked={showMarkers} onChange={(e) => setShowMarkers(e.target.checked)} size="small" />} 
              label="Markers" 
            />
            <FormControlLabel 
              control={<Checkbox checked={showThresholds} onChange={(e) => setShowThresholds(e.target.checked)} size="small" />} 
              label="門檻線"
            />
            <FormControlLabel 
              control={<Checkbox checked={showLegend} onChange={(e) => setShowLegend(e.target.checked)} size="small" />} 
              label="Legend" 
            />
          </FormGroup>
          <Button 
            variant="outlined" 
            size="small" 
            startIcon={<ClearIcon />}
            onClick={resetOverview}
            disabled={!selectedExceptionId && !detailWindow}
          >
            Clear Selection
          </Button>
        </Box>
      </Box>
      {detailLoading && <Box role="status" aria-live="polite" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, px: 1 }}>
        <Typography variant="body2" sx={{ flex: 1 }}>{isRaw
          ? '載入原始資料明細；快取過期時需重新讀取來源檔。保留目前圖表資料。'
          : '載入圖表明細；保留目前圖表資料。'}</Typography>
        <Button size="small" onClick={() => {
          requestGeneration.current += 1;
          detailController.current?.abort();
          setDetailLoading(false);
          setDetailCancelled(true);
        }}>取消載入</Button>
      </Box>}
      {(detailError || detailCancelled) && <Alert severity={detailCancelled ? 'info' : 'warning'} sx={{ mb: 1 }} action={
        <Button color="inherit" size="small" disabled={detailLoading} onClick={() => setRetryNonce(value => value + 1)}>重試此範圍</Button>
      }>{detailCancelled ? '已取消載入圖表明細。' : detailError} 保留目前圖表資料。</Alert>}
      {!detailLoading && resolution?.strategy === 'empty' && <Alert severity="info" sx={{ mb: 1 }}>此範圍沒有資料。</Alert>}
      {isRaw && <Typography variant="caption" sx={{ mb: 1, px: 1 }}>原始量測依採集次序連線；概覽可能取樣，放大後載入該範圍細節。此模式不進行例外分析。</Typography>}

      <Paper variant="outlined" sx={{ p: 1, flex: '1 0 540px', minHeight: 540, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Plot
          ref={chartRef}
          data={traces}
          layout={finalLayout}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler={true}
          config={{ 
            responsive: true,
            modeBarButtonsToRemove: ['select2d', 'lasso2d'],
            displaylogo: false,
            scrollZoom: true // Enable scroll zoom
          }}
          onClick={(data) => {
            for (const point of (data.points || []) as any[]) {
              const marker = point.customdata?.kind === 'exception-marker' ? point.customdata : point.data?.customdata?.[point.pointIndex];
              if (marker?.kind !== 'exception-marker') continue;
              const id = marker.id;
              const exception = Object.values(result.exceptions).flat().find(item => item.id === id);
              if (exception) {
                focusException(exception, typeof point.x === 'number' ? point.x : exception.maxLocation);
                onSelectException(exception.id);
                break;
              }
            }
          }}
          onDoubleClick={() => { resetOverview(); }}
          onRelayout={(event) => {
            const changes = event as Record<string, any>;
            if (Object.keys(changes).some(key => /^xaxis\d*\.autorange$/.test(key) && changes[key])) {
              resetOverview();
              return;
            }
            const axis = Object.keys(changes).find(key => /^xaxis\d*\.range(?:\[0\])?$/.test(key));
            if (!axis) return;
            const prefix = axis.replace(/\.range.*$/, '');
            const range = changes[`${prefix}.range`] || [changes[`${prefix}.range[0]`], changes[`${prefix}.range[1]`]];
            const start = Number(range[0]), end = Number(range[1]);
            if (!Number.isFinite(start) || !Number.isFinite(end) || start === end) return;
            setWindow(start, end);
          }}
        />
      </Paper>
    </Box>
  );
};

export default ChartComponent;
