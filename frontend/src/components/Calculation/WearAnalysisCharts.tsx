import React, { useMemo, useState } from 'react';
import { Box, Checkbox, FormControlLabel, MenuItem, Select, Stack, Typography } from '@mui/material';
import Plot from 'react-plotly.js';
import type { WearCycleRecord } from '../../types/api';
import { chartAxisRange, visibleAnalysisRows, type AnalysisChartSort, type AnalysisDirection } from './wearAnalysisPresentation';

export default function WearAnalysisCharts({ rows }: { rows: WearCycleRecord[] }) {
  const [directions, setDirections] = useState<AnalysisDirection[]>(['UP', 'DN']);
  const [sort, setSort] = useState<AnalysisChartSort>({ field: 'fromM', direction: 'asc' });
  const visible = useMemo(() => visibleAnalysisRows(rows, directions, sort), [rows, directions, sort]);
  const toggle = (direction: AnalysisDirection) => setDirections(current => current.includes(direction) ? current.filter(item => item !== direction) : [...current, direction]);
  return <Box>
    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
      {(['UP', 'DN'] as AnalysisDirection[]).map(direction => <FormControlLabel key={direction} control={<Checkbox size="small" checked={directions.includes(direction)} onChange={() => toggle(direction)} />} label={direction} />)}
      <Select size="small" aria-label="Chart sort" value={`${sort.field}:${sort.direction}`} onChange={event => { const [field, direction] = event.target.value.split(':'); setSort({ field: field as AnalysisChartSort['field'], direction: direction as AnalysisChartSort['direction'] }); }}>
        <MenuItem value="fromM:asc">From ascending</MenuItem><MenuItem value="fromM:desc">From descending</MenuItem>
        <MenuItem value="wearPercentage:asc">Wear % ascending</MenuItem><MenuItem value="wearPercentage:desc">Wear % descending</MenuItem>
        <MenuItem value="avgWearMin:asc">Avg Wear Min ascending</MenuItem><MenuItem value="avgWearMin:desc">Avg Wear Min descending</MenuItem>
      </Select>
    </Stack>
    {!visible.length ? <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>No analysis rows match the selected tracks.</Typography> : (['wearPercentage', 'avgWearMin'] as const).map(metric => {
      const values = visible.map(row => row[metric]);
      return <Box key={metric} sx={{ height: 260, width: '100%' }}><Plot data={[{ type: 'bar', x: visible.map(row => row.key.tensionLength), y: values }]} layout={{ autosize: true, margin: { t: 32, r: 16, b: 60, l: 58 }, xaxis: { type: 'category', title: { text: 'Tension Length' } }, yaxis: { range: chartAxisRange(values), title: { text: metric === 'wearPercentage' ? 'Wear %' : 'Avg Wear Min' } } }} style={{ width: '100%', height: '100%' }} useResizeHandler config={{ responsive: true, displaylogo: false }} /></Box>;
    })}
  </Box>;
}
