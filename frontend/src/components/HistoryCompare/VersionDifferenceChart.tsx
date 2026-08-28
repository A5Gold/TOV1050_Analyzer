import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Plot from 'react-plotly.js';
import {
  Alert,
  Box,
  Button,
  Divider,
  Grid,
  Skeleton,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { AlignedComparison, AlignedMetricResult } from '../../types/api';

type Metric = 'height' | 'stagger' | 'wear';
type AxisRange = [number, number];

const METRICS: Array<{ value: Metric; label: string }> = [
  { value: 'height', label: 'Height' },
  { value: 'stagger', label: 'Stagger' },
  { value: 'wear', label: 'Wear' },
];
const CHANNEL_DASH: Array<'solid' | 'dash' | 'dot' | 'dashdot'> = ['solid', 'dash', 'dot', 'dashdot'];
const CYCLE_COLORS = { latest: '#b3261e', previous: '#1769aa', difference: '#455a64' };

interface VersionDifferenceChartProps {
  alignedComparison?: AlignedComparison;
  loading?: boolean;
  error?: string | null;
  sessionId: string;
}

const formatNumber = (value: number | null | undefined, digits = 2) => (
  value == null || !Number.isFinite(value) ? 'Unavailable' : value.toFixed(digits)
);

const metricLabel = (metric: Metric) => METRICS.find(item => item.value === metric)?.label ?? metric;

const buildTraces = (result: AlignedMetricResult, metric: Metric): Plotly.Data[] => {
  const traces: Plotly.Data[] = [];
  const chainage = result.chainage ?? [];
  const channelNames = Array.from({ length: 4 }, (_, index) => `${metricLabel(metric)} channel ${index + 1}`);
  [
    { key: 'latest' as const, label: 'Latest', color: CYCLE_COLORS.latest, axis: 'y' },
    { key: 'previous' as const, label: 'Prev 1 (shifted)', color: CYCLE_COLORS.previous, axis: 'y' },
  ].forEach(cycle => {
    const values = result[cycle.key] ?? [];
    values.forEach((channel, index) => {
      traces.push({
        type: 'scattergl',
        mode: 'lines',
        x: chainage,
        y: channel,
        name: `${cycle.label} ${channelNames[index]}`,
        xaxis: 'x',
        yaxis: cycle.axis,
        connectgaps: false,
        line: { color: cycle.color, width: 1.4, dash: CHANNEL_DASH[index] },
        hovertemplate: `Chainage %{x:.2f} m<br>${cycle.label}, channel ${index + 1}: %{y}<extra></extra>`,
      });
    });
  });
  (result.difference ?? []).forEach((channel, index) => {
    traces.push({
      type: 'scattergl',
      mode: 'lines',
      x: chainage,
      y: channel,
      customdata: chainage.map((_, pointIndex) => [result.latest?.[index]?.[pointIndex], result.previous?.[index]?.[pointIndex]]),
      name: `Difference channel ${index + 1}`,
      xaxis: 'x2',
      yaxis: 'y2',
      connectgaps: false,
      line: { color: CYCLE_COLORS.difference, width: 1.6, dash: CHANNEL_DASH[index] },
      hovertemplate: `Chainage %{x:.2f} m<br>channel ${index + 1}<br>Latest: %{customdata[0]}<br>Prev 1: %{customdata[1]}<br>Difference: %{y}<extra></extra>`,
    });
  });
  return traces;
};

const VersionDifferenceChart = ({ alignedComparison, loading, error, sessionId }: VersionDifferenceChartProps) => {
  const [metric, setMetric] = useState<Metric>('height');
  const [xRange, setXRange] = useState<[number, number] | null>(null);
  const [yRanges, setYRanges] = useState<Record<'raw' | 'difference', AxisRange | undefined>>({
    raw: undefined,
    difference: undefined,
  });
  const previousComparison = useRef(alignedComparison);
  const previousSession = useRef(sessionId);

  useEffect(() => {
    if (previousComparison.current === alignedComparison && previousSession.current === sessionId) return;
    previousComparison.current = alignedComparison;
    previousSession.current = sessionId;
    setXRange(null);
    setYRanges({ raw: undefined, difference: undefined });
  }, [alignedComparison, sessionId]);

  const handleRelayout = useCallback((plotId: 'raw' | 'difference', event: Readonly<Record<string, unknown>>) => {
    if (event['xaxis.autorange'] === true || event['xaxis2.autorange'] === true) {
      setXRange(null);
    } else {
      const start = Number(event['xaxis.range[0]'] ?? event['xaxis2.range[0]']);
      const end = Number(event['xaxis.range[1]'] ?? event['xaxis2.range[1]']);
      if (Number.isFinite(start) && Number.isFinite(end)) setXRange([start, end]);
    }

    const yAxis = plotId === 'raw' ? 'yaxis' : 'yaxis2';
    if (event[`${yAxis}.autorange`] === true) {
      setYRanges(current => ({ ...current, [plotId]: undefined }));
      return;
    }
    const start = Number(event[`${yAxis}.range[0]`]);
    const end = Number(event[`${yAxis}.range[1]`]);
    if (Number.isFinite(start) && Number.isFinite(end)) {
      setYRanges(current => ({ ...current, [plotId]: [start, end] }));
    }
  }, []);

  const result = alignedComparison?.metrics?.[metric];
  const traces = useMemo(() => (result?.chainage?.length ? buildTraces(result, metric) : []), [result, metric]);
  const defaultRange = result?.chainage?.length
    ? [result.chainage[0], result.chainage[result.chainage.length - 1]] as [number, number]
    : undefined;
  const range = xRange ?? defaultRange;

  if (loading) {
    return (
      <Stack spacing={1.5} sx={{ p: 1 }} aria-label="Version Difference loading">
        <Skeleton variant="rectangular" height={42} />
        <Skeleton variant="rectangular" height={300} />
        <Skeleton variant="rectangular" height={300} />
      </Stack>
    );
  }

  if (error && !alignedComparison) {
    return <Alert severity="error" sx={{ m: 2 }}>{error}</Alert>;
  }

  if (!alignedComparison) {
    return (
      <Box sx={{ p: 4, minHeight: 360, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
        <InfoOutlinedIcon color="disabled" sx={{ fontSize: 40, mb: 1 }} />
        <Typography variant="h6">No Version Difference Result</Typography>
        <Typography variant="body2" color="text.secondary">Run Compare with two reports containing ChartData.</Typography>
      </Box>
    );
  }

  if (alignedComparison.status === 'unavailable' && !result?.chainage?.length) {
    return <Alert severity="info" icon={<InfoOutlinedIcon />} sx={{ m: 2 }}>{alignedComparison.reason ?? 'Version Difference is unavailable.'}</Alert>;
  }

  return (
    <Box sx={{ width: '100%', minHeight: 0 }}>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ xs: 'stretch', md: 'center' }} sx={{ p: 1, flexWrap: 'wrap' }}>
        <ToggleButtonGroup
          exclusive
          size="small"
          value={metric}
          onChange={(_, next: Metric | null) => {
            if (next) {
              setMetric(next);
              setXRange(null);
              setYRanges({ raw: undefined, difference: undefined });
            }
          }}
          aria-label="Version Difference metric"
        >
          {METRICS.map(item => {
            const metricResult = alignedComparison.metrics?.[item.value];
            return (
              <ToggleButton key={item.value} value={item.value} disabled={!metricResult || (metricResult.status === 'unavailable' && !metricResult.chainage.length)}>
                {item.label}
              </ToggleButton>
            );
          })}
        </ToggleButtonGroup>
        <Button size="small" startIcon={<RestartAltIcon />} onClick={() => { setXRange(null); setYRanges({ raw: undefined, difference: undefined }); }} disabled={!defaultRange}>
          Reset Zoom
        </Button>
        {result?.status === 'unavailable' && <Typography variant="body2" color="text.secondary">{result.reason ?? `${metricLabel(metric)} is unavailable.`}</Typography>}
      </Stack>
      {result?.chainage?.length ? (
        <>
          {result.status === 'unavailable' && <Alert severity="info" sx={{ mx: 1, mb: 1 }}>{result.reason}</Alert>}
          {result.status === 'ready' && <Grid container spacing={1} sx={{ px: 1, pb: 1 }}>
            <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Best shift</Typography><Typography variant="body2" fontWeight={600}>{formatNumber(result.shift_m)} m</Typography></Grid>
            <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Normalized RMSE</Typography><Typography variant="body2" fontWeight={600}>{formatNumber(result.normalized_rmse, 4)}</Typography></Grid>
            <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Valid points</Typography><Typography variant="body2" fontWeight={600}>{result.valid_points.toLocaleString()}</Typography></Grid>
            <Grid item xs={6} sm={3}><Typography variant="caption" color="text.secondary">Overlap length</Typography><Typography variant="body2" fontWeight={600}>{formatNumber(result.overlap_length)} m</Typography></Grid>
          </Grid>}
          <Divider />
          {result.status === 'ready' && <Box sx={{ minHeight: 330, height: { xs: 360, md: 430 }, width: '100%' }}>
            <Plot
              data={traces.slice(0, 8)}
              layout={{
                autosize: true,
                margin: { t: 34, r: 24, b: 42, l: 62 },
                title: { text: `${metricLabel(metric)} raw overlay`, font: { size: 14 } },
                showlegend: true,
                legend: { orientation: 'h', y: 1.08, x: 0 },
                uirevision: `${sessionId}-${metric}`,
                xaxis: { title: { text: 'Chainage (m)' }, range, uirevision: `${sessionId}-${metric}` },
                yaxis: { title: { text: metricLabel(metric) }, range: yRanges.raw, uirevision: `${sessionId}-${metric}` },
                hovermode: 'x unified',
              }}
              useResizeHandler
              style={{ width: '100%', height: '100%' }}
              config={{ responsive: true, scrollZoom: true, displaylogo: false }}
              onRelayout={event => handleRelayout('raw', event)}
            />
          </Box>}
          <Box sx={{ minHeight: 330, height: { xs: 360, md: 430 }, width: '100%' }}>
            <Plot
              data={traces.slice(8)}
              layout={{
                autosize: true,
                margin: { t: 34, r: 24, b: 42, l: 62 },
                title: { text: `${metricLabel(metric)} difference`, font: { size: 14 } },
                showlegend: true,
                legend: { orientation: 'h', y: 1.08, x: 0 },
                uirevision: `${sessionId}-${metric}`,
                xaxis: { title: { text: 'Chainage (m)' }, range, matches: 'x', uirevision: `${sessionId}-${metric}` },
                yaxis: { title: { text: 'Latest - shifted Prev 1' }, range: yRanges.difference, uirevision: `${sessionId}-${metric}` },
                hovermode: 'x unified',
              }}
              useResizeHandler
              style={{ width: '100%', height: '100%' }}
              config={{ responsive: true, scrollZoom: true, displaylogo: false }}
              onRelayout={event => handleRelayout('difference', event)}
            />
          </Box>
        </>
      ) : (
        <Alert severity="info" sx={{ m: 1 }}>{result?.reason ?? `${metricLabel(metric)} is unavailable.`}</Alert>
      )}
    </Box>
  );
};

export default VersionDifferenceChart;
