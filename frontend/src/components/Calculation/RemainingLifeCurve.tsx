import React from 'react';
import { Alert, Box, Paper, Typography } from '@mui/material';
import Plot from 'react-plotly.js';
import type { WearRemainingLifeRow } from '../../types/api';

interface Props { rows: WearRemainingLifeRow[] }

const LINE_COLORS = { EAL: '#64b5f6', TML: '#8d6e63' } as const;

const chartRows = (rows: WearRemainingLifeRow[], lineGroup: 'EAL' | 'TML') => rows.filter(row => row.lineGroup === lineGroup && row.curve.length > 0);

const buildTraces = (rows: WearRemainingLifeRow[], lineGroup: 'EAL' | 'TML') => chartRows(rows, lineGroup).map(row => ({
  x: row.curve.map(point => point.date),
  y: row.curve.map(point => point.remaining_days == null ? null : point.remaining_days / 365.25),
  type: 'scatter' as const,
  mode: 'lines+markers' as const,
  name: `${row.lineGroup} ${row.tensionLength}`,
  line: { color: LINE_COLORS[lineGroup] },
  marker: { color: LINE_COLORS[lineGroup] },
}));

function LineChart({ lineGroup, rows }: { lineGroup: 'EAL' | 'TML'; rows: WearRemainingLifeRow[] }) {
  const traces = buildTraces(rows, lineGroup);
  return <Paper variant="outlined" sx={{ p: 2, minWidth: 0 }}>
    <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>{lineGroup} remaining life curve</Typography>
    {traces.length === 0 ? <Alert severity="info">Select an eligible {lineGroup} tension length to draw a remaining-life curve.</Alert> : (
      <Box sx={{ width: '100%', height: 320 }}>
        <Plot
          data={traces}
          layout={{ autosize: true, margin: { t: 20, r: 24, b: 60, l: 60 }, xaxis: { title: { text: 'Date' }, type: 'date' }, yaxis: { title: { text: 'Remaining life (years)' }, rangemode: 'tozero' }, legend: { orientation: 'h' } }}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler
          config={{ responsive: true, displaylogo: false }}
        />
      </Box>
    )}
  </Paper>;
}

export default function RemainingLifeCurve({ rows }: Props) {
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'repeat(2, minmax(0, 1fr))' }, gap: 2 }}>
      <LineChart lineGroup="EAL" rows={rows} />
      <LineChart lineGroup="TML" rows={rows} />
    </Box>
  );
}
