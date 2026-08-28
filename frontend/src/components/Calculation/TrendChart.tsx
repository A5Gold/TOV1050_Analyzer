import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { Box, Typography } from '@mui/material';
import { TrendResult } from '../../types/api';

interface TrendChartProps {
  result: TrendResult;
}

const L2_THRESHOLD = 10.2;

const TrendChart = ({ result }: TrendChartProps) => {
  const { chartDates, chartRecords, chartTrend } = useMemo(() => {
    const filteredPoints = result.dates
      .map((date, index) => ({
        date,
        record: result.record_points[index],
        trend: result.trend_points[index],
      }))
      .filter((point) => point.record != null || point.trend != null)
      .reverse();

    return {
      chartDates: filteredPoints.map((point) => point.date),
      chartRecords: filteredPoints.map((point) => point.record),
      chartTrend: filteredPoints.map((point) => point.trend),
    };
  }, [result]);

  const trendLine = useMemo(() => {
    const points = chartDates
      .map((date, index) => ({ date, trend: chartTrend[index] }))
      .filter((point) => point.trend != null && Number.isFinite(Number(point.trend)));
    if (points.length <= 2) {
      return points;
    }
    return [points[0], points[points.length - 1]];
  }, [chartDates, chartTrend]);

  const traces = useMemo<Plotly.Data[]>(() => [
    {
      x: chartDates,
      y: chartRecords,
      type: 'scatter',
      mode: 'lines+markers',
      name: `${result.tension_length} (record)`,
      line: { color: '#1f77b4', dash: 'solid', width: 2 },
      marker: { color: '#1f77b4', size: 8 },
    },
    {
      x: trendLine.map((point) => point.date),
      y: trendLine.map((point) => point.trend),
      type: 'scatter',
      mode: 'lines',
      name: `${result.tension_length} (trend)`,
      line: { color: '#ff7f0e', dash: 'dash', width: 1.5 },
    },
  ], [chartDates, chartRecords, trendLine, result.tension_length]);

  const shapes: Partial<Plotly.Shape>[] = [
    {
      type: 'line',
      x0: 0, x1: 1, xref: 'paper',
      y0: L2_THRESHOLD, y1: L2_THRESHOLD, yref: 'y',
      line: { color: 'red', dash: 'dash', width: 1.5 },
    },
  ];

  const annotations: Partial<Plotly.Annotations>[] = [
    {
      x: 1, xref: 'paper',
      y: L2_THRESHOLD, yref: 'y',
      text: 'L2 threshold',
      showarrow: false,
      xanchor: 'right', yanchor: 'bottom',
      font: { color: 'red', size: 11 },
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    title: {
      text: `${result.exception_id || result.tension_length} - ${result.task_run_date}`,
      font: { size: 13 },
    },
    margin: { t: 40, r: 20, b: 60, l: 60 },
    autosize: true,
    xaxis: { title: { text: 'Date' }, type: 'date' },
    yaxis: { title: { text: 'avg_wear_min (mm)' } },
    legend: { orientation: 'h', x: 0.5, xanchor: 'center', y: -0.2 },
    shapes,
    annotations,
  };

  if (!result.dates.length) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          No trend data available.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%', height: 400 }}>
      <Plot
        data={traces}
        layout={layout}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
        config={{ responsive: true, displaylogo: false }}
      />
    </Box>
  );
};

export default TrendChart;
