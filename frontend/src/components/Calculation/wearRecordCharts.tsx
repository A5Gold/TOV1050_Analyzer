import { Box } from '@mui/material';
import Plot from 'react-plotly.js';
import type { WireWearSavedRecord } from '../../types/api';

export type WireWearChartMetric = 'wear_percentage' | 'avg_wear_min';

function getMetricConfig(metric: WireWearChartMetric) {
  return metric === 'avg_wear_min'
    ? { field: 'avg_wear_min' as const, title: 'Avg Wear Min', color: '#2e7d32' }
    : { field: 'wear_percentage' as const, title: 'Wear %', color: '#1976d2' };
}

export function CycleWearBarChart({ records }: { records: WireWearSavedRecord[] }) {
  const sorted = [...records].sort((a, b) => a.from_m - b.from_m);
  return (
    <Box sx={{ width: '100%', height: 300 }}>
      <Plot
        data={[{
          x: sorted.map(record => record.tension_length),
          y: sorted.map(record => record.wear_percentage),
          type: 'bar',
          marker: { color: sorted.map(record => record.wear_percentage >= 10 ? '#d32f2f' : '#1976d2') },
        }]}
        layout={{
          autosize: true,
          margin: { t: 20, r: 20, b: 80, l: 50 },
          xaxis: { title: { text: 'Tension Length' }, type: 'category', tickangle: -45 },
          yaxis: { title: { text: 'Wear %' }, rangemode: 'tozero' },
        }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
        config={{ responsive: true, displaylogo: false }}
      />
    </Box>
  );
}

export function TensionLengthTrendChart({
  records,
  metric = 'wear_percentage',
}: {
  records: WireWearSavedRecord[]
  metric?: WireWearChartMetric
}) {
  const sorted = [...records].sort((a, b) => a.cycle_date.localeCompare(b.cycle_date));
  const metricConfig = getMetricConfig(metric);
  return (
    <Box sx={{ width: '100%', height: 300 }}>
      <Plot
        data={[{
          x: sorted.map(record => record.cycle_date),
          y: sorted.map(record => record[metricConfig.field]),
          type: 'scatter',
          mode: 'lines+markers',
          line: { color: metricConfig.color },
        }]}
        layout={{
          autosize: true,
          margin: { t: 20, r: 20, b: 60, l: 50 },
          xaxis: { title: { text: 'Cycle Date' }, type: 'date', tickformat: '%Y-%m-%d' },
          yaxis: { title: { text: metricConfig.title }, rangemode: 'tozero' },
        }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
        config={{ responsive: true, displaylogo: false }}
      />
    </Box>
  );
}

export function AllTensionLengthOverviewChart({
  records,
  metric = 'wear_percentage',
}: {
  records: WireWearSavedRecord[]
  metric?: WireWearChartMetric
}) {
  const metricConfig = getMetricConfig(metric);
  const latestByTl = new Map<string, WireWearSavedRecord>();
  for (const record of records) {
    const current = latestByTl.get(record.tension_length);
    if (!current || record.cycle_date > current.cycle_date) {
      latestByTl.set(record.tension_length, record);
    }
  }
  const sorted = [...latestByTl.values()].sort((a, b) => a.from_m - b.from_m);

  return (
    <Box sx={{ width: '100%', height: 300 }}>
      <Plot
        data={[{
          x: sorted.map(record => record.tension_length),
          y: sorted.map(record => record[metricConfig.field]),
          type: 'bar',
          marker: { color: metricConfig.color },
        }]}
        layout={{
          autosize: true,
          margin: { t: 20, r: 20, b: 80, l: 50 },
          xaxis: { title: { text: 'Tension Length' }, type: 'category', tickangle: -45 },
          yaxis: { title: { text: metricConfig.title }, rangemode: 'tozero' },
        }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
        config={{ responsive: true, displaylogo: false }}
      />
    </Box>
  );
}

export function ProjectionBucketChart({
  buckets,
  title,
  color,
}: {
  buckets: Array<{ year: number; count: number }>
  title: string
  color: string
}) {
  return (
    <Box sx={{ width: '100%', height: 300 }}>
      <Plot
        data={[{
          x: buckets.map(bucket => bucket.year),
          y: buckets.map(bucket => bucket.count),
          type: 'bar',
          marker: { color },
        }]}
        layout={{
          title: { text: title },
          autosize: true,
          margin: { t: 50, r: 20, b: 50, l: 50 },
          xaxis: { title: { text: 'Projected Year' } },
          yaxis: { title: { text: 'TL count reaching threshold' }, rangemode: 'tozero', tickmode: 'linear', dtick: 1 },
        }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
        config={{ responsive: true, displaylogo: false }}
      />
    </Box>
  );
}
