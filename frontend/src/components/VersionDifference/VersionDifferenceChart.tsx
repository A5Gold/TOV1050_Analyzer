import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Plot from 'react-plotly.js';
import {
  Alert,
  Box,
  Checkbox,
  Divider,
  Grid,
  IconButton,
  Paper,
  Popover,
  Skeleton,
  Slider,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from '@mui/material';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import TuneIcon from '@mui/icons-material/Tune';
import type {
  AlignedMetricResult,
  VersionDifferenceComparison,
  VersionDifferenceResponse,
} from '../../types/api';
import {
  VERSION_DIFFERENCE_CYCLES,
  type VersionDifferenceComparisonKey,
} from '../../constants/versionDifferenceCycles';

type Metric = 'height' | 'stagger' | 'wear';
type AxisRange = [number, number];

interface SeriesTrace {
  id: string;
  groupId: string;
  groupLabel: string;
  shortLabel: string;
  color: string;
  data: Plotly.Data;
}

interface TraceSetting {
  visible: boolean;
  opacity: number;
}

interface ControlledPlotProps {
  plotId: string;
  title: string;
  ariaLabel: string;
  traces: SeriesTrace[];
  range?: [number, number];
  yRange?: AxisRange;
  yTitle: string;
  uirevision: string;
  onRelayout: (plotId: string, event: Readonly<Record<string, unknown>>) => void;
}

const METRICS: Array<{ value: Metric; label: string }> = [
  { value: 'height', label: 'Height' },
  { value: 'stagger', label: 'Stagger' },
  { value: 'wear', label: 'Wear' },
];

const CHANNEL_DASH: Array<'solid' | 'dash' | 'dot' | 'dashdot'> = ['solid', 'dash', 'dot', 'dashdot'];
const LATEST_CYCLE = VERSION_DIFFERENCE_CYCLES[0];
const cycleForComparison = (key: VersionDifferenceComparisonKey) => VERSION_DIFFERENCE_CYCLES.find(cycle => cycle.comparisonKey === key);
const cycleColor = (key: VersionDifferenceComparisonKey) => cycleForComparison(key)?.color ?? '#687589';
const cycleLabel = (key: VersionDifferenceComparisonKey) => cycleForComparison(key)?.label ?? key;

const metricLabel = (metric: Metric) => METRICS.find(item => item.value === metric)?.label ?? metric;

const formatNumber = (value: number | null | undefined, digits = 2) => (
  value == null || !Number.isFinite(value) ? 'Unavailable' : value.toFixed(digits)
);

const moveItem = <T,>(items: T[], index: number, direction: -1 | 1): T[] => {
  const target = index + direction;
  if (target < 0 || target >= items.length) return items;
  const next = [...items];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
};

const ControlledPlot = ({ plotId, title, ariaLabel, traces, range, yRange, yTitle, uirevision, onRelayout }: ControlledPlotProps) => {
  const groups = useMemo(() => Array.from(new Map(traces.map(trace => [trace.groupId, trace.groupLabel])).entries()), [traces]);
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [groupOrder, setGroupOrder] = useState(() => groups.map(([groupId]) => groupId));
  const [traceOrder, setTraceOrder] = useState<Record<string, string[]>>(() => Object.fromEntries(
    groups.map(([groupId]) => [groupId, traces.filter(trace => trace.groupId === groupId).map(trace => trace.id)]),
  ));
  const [settings, setSettings] = useState<Record<string, TraceSetting>>(() => Object.fromEntries(
    traces.map(trace => [trace.id, { visible: true, opacity: 0.9 }]),
  ));

  const traceById = useMemo(() => new Map(traces.map(trace => [trace.id, trace])), [traces]);
  const orderedTraces = useMemo(() => groupOrder.flatMap(groupId => (
    traceOrder[groupId] ?? []
  )).map(id => traceById.get(id)).filter((trace): trace is SeriesTrace => Boolean(trace)), [groupOrder, traceOrder, traceById]);

  const plotData = useMemo(() => orderedTraces.map(trace => ({
    ...trace.data,
    visible: settings[trace.id]?.visible ?? true,
    opacity: settings[trace.id]?.opacity ?? 0.9,
  } as Plotly.Data)), [orderedTraces, settings]);

  const setTraceVisible = (id: string, visible: boolean) => {
    setSettings(current => ({ ...current, [id]: { ...current[id], visible } }));
  };

  const setTraceOpacity = (id: string, opacity: number) => {
    setSettings(current => ({ ...current, [id]: { ...current[id], opacity } }));
  };

  const setGroupVisible = (groupId: string, visible: boolean) => {
    const ids = traceOrder[groupId] ?? [];
    setSettings(current => {
      const next = { ...current };
      ids.forEach(id => { next[id] = { ...next[id], visible }; });
      return next;
    });
  };

  const setGroupOpacity = (groupId: string, opacity: number) => {
    const ids = traceOrder[groupId] ?? [];
    setSettings(current => {
      const next = { ...current };
      ids.forEach(id => { next[id] = { ...next[id], opacity }; });
      return next;
    });
  };

  return (
    <Paper variant="outlined" sx={{ overflow: 'hidden', minWidth: 0 }}>
      <Box sx={{ minHeight: 44, px: 1.5, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="subtitle2" fontWeight={750}>{title}</Typography>
        <Tooltip title="Series controls">
          <IconButton aria-label={`Configure ${ariaLabel} series`} size="small" onClick={event => setAnchorEl(event.currentTarget)}>
            <TuneIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <Box sx={{ height: { xs: 340, md: 420 }, minHeight: 340, width: '100%' }}>
        <Plot
          data={plotData}
          layout={{
            autosize: true,
            margin: { t: 18, r: 24, b: 52, l: 64 },
            showlegend: false,
            uirevision,
            xaxis: { title: { text: 'Chainage (m)' }, range, uirevision },
            yaxis: { title: { text: yTitle }, fixedrange: false, range: yRange, uirevision },
            hovermode: 'x unified',
            paper_bgcolor: '#ffffff',
            plot_bgcolor: '#ffffff',
          }}
          useResizeHandler
          style={{ width: '100%', height: '100%' }}
          config={{ responsive: true, scrollZoom: true, displaylogo: false }}
          onRelayout={event => onRelayout(plotId, event)}
        />
      </Box>

      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        slotProps={{ paper: { sx: { width: 356, maxWidth: 'calc(100vw - 24px)', maxHeight: 'min(560px, calc(100vh - 96px))', overflowY: 'auto' } } }}
      >
        <Box sx={{ p: 1.5 }}>
          <Typography variant="subtitle2" fontWeight={750}>Series</Typography>
          <Typography variant="caption" color="text.secondary">Later layers are drawn in front.</Typography>
        </Box>
        <Divider />
        <Stack divider={<Divider flexItem />}>
          {groupOrder.map((groupId, groupIndex) => {
            const groupLabel = groups.find(([id]) => id === groupId)?.[1] ?? groupId;
            const ids = traceOrder[groupId] ?? [];
            const visibleCount = ids.filter(id => settings[id]?.visible).length;
            const groupOpacity = ids.length ? ids.reduce((sum, id) => sum + (settings[id]?.opacity ?? 0.9), 0) / ids.length : 0.9;
            return (
              <Box key={groupId} sx={{ p: 1.25 }}>
                <Box sx={{ display: 'grid', gridTemplateColumns: 'auto minmax(0, 1fr) auto auto', alignItems: 'center', gap: 0.5 }}>
                  <Checkbox
                    size="small"
                    checked={visibleCount === ids.length && ids.length > 0}
                    indeterminate={visibleCount > 0 && visibleCount < ids.length}
                    onChange={event => setGroupVisible(groupId, event.target.checked)}
                    inputProps={{ 'aria-label': `Toggle ${groupLabel} group` }}
                  />
                  <Typography variant="body2" fontWeight={700} noWrap>{groupLabel}</Typography>
                  <Tooltip title="Send group backward"><span><IconButton aria-label={`Send ${groupLabel} group backward`} size="small" disabled={groupIndex === 0} onClick={() => setGroupOrder(current => moveItem(current, groupIndex, -1))}><ArrowDownwardIcon sx={{ fontSize: 17 }} /></IconButton></span></Tooltip>
                  <Tooltip title="Bring group forward"><span><IconButton aria-label={`Bring ${groupLabel} group forward`} size="small" disabled={groupIndex === groupOrder.length - 1} onClick={() => setGroupOrder(current => moveItem(current, groupIndex, 1))}><ArrowUpwardIcon sx={{ fontSize: 17 }} /></IconButton></span></Tooltip>
                </Box>
                <Box sx={{ px: 1, pb: 0.75, display: 'grid', gridTemplateColumns: '52px minmax(0, 1fr) 42px', alignItems: 'center', gap: 1 }}>
                  <Typography variant="caption" color="text.secondary">Opacity</Typography>
                  <Slider size="small" min={0.1} max={1} step={0.1} value={Number(groupOpacity.toFixed(1))} onChange={(_, value) => setGroupOpacity(groupId, value as number)} aria-label={`${groupLabel} opacity`} />
                  <Typography variant="caption" color="text.secondary" textAlign="right">{Math.round(groupOpacity * 100)}%</Typography>
                </Box>
                <Stack spacing={0.25}>
                  {ids.map((id, traceIndex) => {
                    const trace = traceById.get(id);
                    if (!trace) return null;
                    const setting = settings[id] ?? { visible: true, opacity: 0.9 };
                    return (
                      <Box key={id} sx={{ display: 'grid', gridTemplateColumns: 'auto 28px 58px minmax(64px, 1fr) 38px auto auto', gap: 0.5, alignItems: 'center' }}>
                        <Checkbox size="small" checked={setting.visible} onChange={event => setTraceVisible(id, event.target.checked)} inputProps={{ 'aria-label': `Toggle ${groupLabel} ${trace.shortLabel}` }} />
                        <Box aria-hidden="true" sx={{ width: 22, borderTop: `2px solid ${trace.color}` }} />
                        <Typography variant="caption" noWrap>{trace.shortLabel}</Typography>
                        <Slider size="small" min={0.1} max={1} step={0.1} value={setting.opacity} onChange={(_, value) => setTraceOpacity(id, value as number)} aria-label={`${groupLabel} ${trace.shortLabel} opacity`} />
                        <Typography variant="caption" color="text.secondary" textAlign="right">{Math.round(setting.opacity * 100)}%</Typography>
                        <Tooltip title="Send backward"><span><IconButton aria-label={`Send ${groupLabel} ${trace.shortLabel} backward`} size="small" disabled={traceIndex === 0} onClick={() => setTraceOrder(current => ({ ...current, [groupId]: moveItem(current[groupId] ?? [], traceIndex, -1) }))}><ArrowDownwardIcon sx={{ fontSize: 16 }} /></IconButton></span></Tooltip>
                        <Tooltip title="Bring forward"><span><IconButton aria-label={`Bring ${groupLabel} ${trace.shortLabel} forward`} size="small" disabled={traceIndex === ids.length - 1} onClick={() => setTraceOrder(current => ({ ...current, [groupId]: moveItem(current[groupId] ?? [], traceIndex, 1) }))}><ArrowUpwardIcon sx={{ fontSize: 16 }} /></IconButton></span></Tooltip>
                      </Box>
                    );
                  })}
                </Stack>
              </Box>
            );
          })}
        </Stack>
      </Popover>
    </Paper>
  );
};

const channelTraces = (
  result: AlignedMetricResult,
  metric: Metric,
  valueKey: 'latest' | 'previous' | 'difference',
  groupId: string,
  groupLabel: string,
  color: string,
  idPrefix: string,
): SeriesTrace[] => (result[valueKey] ?? []).map((values, index) => ({
  id: `${idPrefix}-${index + 1}`,
  groupId,
  groupLabel,
  shortLabel: `Channel ${index + 1}`,
  color,
  data: {
    type: 'scattergl',
    mode: 'lines',
    x: result.chainage,
    y: values,
    name: `${groupLabel} ${metricLabel(metric)} channel ${index + 1}`,
    connectgaps: false,
    line: { color, width: valueKey === 'difference' ? 1.6 : 1.35, dash: CHANNEL_DASH[index] },
    customdata: valueKey === 'difference'
      ? result.chainage.map((_, pointIndex) => [result.latest?.[index]?.[pointIndex], result.previous?.[index]?.[pointIndex]])
      : undefined,
    hovertemplate: valueKey === 'difference'
      ? `Chainage %{x:.2f} m<br>Channel ${index + 1}<br>Latest: %{customdata[0]}<br>Previous: %{customdata[1]}<br>Difference: %{y}<extra></extra>`
      : `Chainage %{x:.2f} m<br>${groupLabel}, channel ${index + 1}: %{y}<extra></extra>`,
  },
}));

const buildRawTraces = (comparisons: VersionDifferenceComparison[], metric: Metric): SeriesTrace[] => {
  const latestSource = comparisons.map(comparison => comparison.metrics?.[metric]).find(result => result?.chainage?.length);
  if (!latestSource) return [];
  const traces = channelTraces(latestSource, metric, 'latest', 'latest', LATEST_CYCLE.label, LATEST_CYCLE.color, 'latest');
  comparisons.forEach(comparison => {
    const result = comparison.metrics?.[metric];
    if (!result?.chainage?.length) return;
    const label = cycleLabel(comparison.key);
    traces.push(...channelTraces(result, metric, 'previous', comparison.key, label, cycleColor(comparison.key), comparison.key));
  });
  return traces;
};

const comparisonLabel = (comparison: VersionDifferenceComparison) => (
  `Latest - ${cycleLabel(comparison.key)}`
);

const ComparisonSummary = ({ comparison, result }: { comparison: VersionDifferenceComparison; result: AlignedMetricResult }) => (
  <Box sx={{ px: 1.5, py: 1.25, border: 1, borderColor: 'divider', borderBottom: 0, borderRadius: '8px 8px 0 0', bgcolor: 'background.paper' }}>
    <Typography variant="subtitle2" fontWeight={750} sx={{ mb: 1 }}>{comparisonLabel(comparison)}</Typography>
    <Grid container spacing={1}>
      <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Best shift</Typography><Typography variant="body2" fontWeight={700}>{formatNumber(result.shift_m)} m</Typography></Grid>
      <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Normalized RMSE</Typography><Typography variant="body2" fontWeight={700}>{formatNumber(result.normalized_rmse, 4)}</Typography></Grid>
      <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Valid points</Typography><Typography variant="body2" fontWeight={700}>{result.valid_points.toLocaleString()}</Typography></Grid>
      <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Overlap length</Typography><Typography variant="body2" fontWeight={700}>{formatNumber(result.overlap_length)} m</Typography></Grid>
    </Grid>
  </Box>
);

interface VersionDifferenceChartProps {
  response?: VersionDifferenceResponse;
  loading?: boolean;
  error?: string | null;
}

const VersionDifferenceChart = ({ response, loading, error }: VersionDifferenceChartProps) => {
  const availableMetrics = useMemo(() => new Set(METRICS.filter(item => response?.comparisons.some(comparison => (
    comparison.metrics?.[item.value]?.chainage?.length
  ))).map(item => item.value)), [response]);
  const initialMetric = METRICS.find(item => availableMetrics.has(item.value))?.value ?? 'height';
  const [metric, setMetric] = useState<Metric>(initialMetric);
  const selectedMetric = availableMetrics.has(metric) ? metric : initialMetric;
  const [xRange, setXRange] = useState<[number, number] | null>(null);
  const [yRanges, setYRanges] = useState<Record<string, AxisRange>>({});
  const previousResponse = useRef(response);

  useEffect(() => {
    if (previousResponse.current === response) return;
    previousResponse.current = response;
    setXRange(null);
    setYRanges({});
  }, [response]);

  const handleRelayout = useCallback((plotId: string, event: Readonly<Record<string, unknown>>) => {
    if (event['xaxis.autorange'] === true || event['xaxis2.autorange'] === true) {
      setXRange(null);
    } else {
      const start = Number(event['xaxis.range[0]'] ?? event['xaxis2.range[0]']);
      const end = Number(event['xaxis.range[1]'] ?? event['xaxis2.range[1]']);
      if (Number.isFinite(start) && Number.isFinite(end)) setXRange([start, end]);
    }

    const yAxis = plotId === 'raw' ? 'yaxis' : `yaxis${plotId === 'difference' ? '2' : ''}`;
    if (event[`${yAxis}.autorange`] === true || event['yaxis.autorange'] === true) {
      setYRanges(current => {
        if (!(plotId in current)) return current;
        const next = { ...current };
        delete next[plotId];
        return next;
      });
      return;
    }
    const start = Number(event[`${yAxis}.range[0]`] ?? event['yaxis.range[0]']);
    const end = Number(event[`${yAxis}.range[1]`] ?? event['yaxis.range[1]']);
    if (Number.isFinite(start) && Number.isFinite(end)) {
      setYRanges(current => ({ ...current, [plotId]: [start, end] }));
    }
  }, []);

  const rawTraces = useMemo(() => response ? buildRawTraces(response.comparisons, selectedMetric) : [], [response, selectedMetric]);
  const defaultRange = useMemo(() => {
    let minimum = Number.POSITIVE_INFINITY;
    let maximum = Number.NEGATIVE_INFINITY;
    rawTraces.forEach(trace => {
      ((((trace.data as any).x) as number[] | undefined) ?? []).forEach(value => {
        if (!Number.isFinite(value)) return;
        minimum = Math.min(minimum, value);
        maximum = Math.max(maximum, value);
      });
    });
    return Number.isFinite(minimum) && Number.isFinite(maximum) ? [minimum, maximum] as [number, number] : undefined;
  }, [rawTraces]);
  const range = xRange ?? defaultRange;
  const responseKey = response ? `${response.latest_file}-${response.comparisons.map(item => item.previous_file).join('-')}` : 'empty';

  if (loading) {
    return (
      <Stack spacing={1.5} aria-label="Version Difference loading">
        <Skeleton variant="rectangular" height={48} />
        <Skeleton variant="rectangular" height={420} />
        <Skeleton variant="rectangular" height={420} />
      </Stack>
    );
  }

  if (error && !response) return <Alert severity="error">{error}</Alert>;

  if (!response) {
    return (
      <Box sx={{ minHeight: 360, display: 'grid', placeItems: 'center', textAlign: 'center' }}>
        <Box>
          <InfoOutlinedIcon color="disabled" sx={{ fontSize: 40, mb: 1 }} />
          <Typography variant="h6">No comparison result</Typography>
          <Typography variant="body2" color="text.secondary">Select Latest and Previous 1 reports, then run Compare.</Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Stack spacing={1.5}>
      {error && <Alert severity="error">{error}</Alert>}
      <Box sx={{ display: 'flex', alignItems: { xs: 'stretch', sm: 'center' }, justifyContent: 'space-between', flexDirection: { xs: 'column', sm: 'row' }, gap: 1 }}>
        <ToggleButtonGroup
          exclusive
          size="small"
          value={selectedMetric}
          onChange={(_, next: Metric | null) => {
            if (next) {
              setMetric(next);
              setXRange(null);
              setYRanges({});
            }
          }}
          aria-label="Version Difference metric"
        >
          {METRICS.map(item => <ToggleButton key={item.value} value={item.value} disabled={!availableMetrics.has(item.value)}>{item.label}</ToggleButton>)}
        </ToggleButtonGroup>
        <Tooltip title="Reset synchronized zoom">
          <span><IconButton aria-label="Reset zoom" onClick={() => { setXRange(null); setYRanges({}); }} disabled={!defaultRange}><RestartAltIcon /></IconButton></span>
        </Tooltip>
      </Box>

      {rawTraces.length > 0 ? (
        <ControlledPlot
          plotId="raw"
          key={`${responseKey}-${selectedMetric}-raw`}
          title={`${metricLabel(selectedMetric)} raw overlay`}
          ariaLabel="raw overlay"
          traces={rawTraces}
          range={range}
          yRange={yRanges.raw}
          yTitle={metricLabel(selectedMetric)}
          uirevision={`${responseKey}-${selectedMetric}`}
          onRelayout={handleRelayout}
        />
      ) : <Alert severity="info">No usable {metricLabel(selectedMetric)} data is available.</Alert>}

      {response.comparisons.map(comparison => {
        const result = comparison.metrics?.[selectedMetric];
        if (!result || result.status !== 'ready') {
          return <Alert key={comparison.key} severity="info"><strong>{comparisonLabel(comparison)}:</strong> {result?.reason ?? comparison.reason ?? 'Difference is unavailable.'}</Alert>;
        }
        const label = comparisonLabel(comparison);
        const traces = channelTraces(result, selectedMetric, 'difference', comparison.key, label, cycleColor(comparison.key), `${comparison.key}-difference`);
        return (
          <Box key={comparison.key}>
            <ComparisonSummary comparison={comparison} result={result} />
            <Box sx={{ '& > .MuiPaper-root': { borderTopLeftRadius: 0, borderTopRightRadius: 0 } }}>
              <ControlledPlot
                plotId={comparison.key}
                key={`${responseKey}-${selectedMetric}-${comparison.key}`}
                title={`${metricLabel(selectedMetric)} difference`}
                ariaLabel={`${label} difference`}
                traces={traces}
                range={range}
                yRange={yRanges[comparison.key]}
                yTitle={label}
                uirevision={`${responseKey}-${selectedMetric}`}
                onRelayout={handleRelayout}
              />
            </Box>
          </Box>
        );
      })}
    </Stack>
  );
};

export default VersionDifferenceChart;
