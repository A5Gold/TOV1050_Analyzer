import React from 'react';
import { Box, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import type { WearLatestSummary, WearWorkbenchColumn } from '../../types/api';

interface Props {
  columns: WearWorkbenchColumn[]
  rows: WearLatestSummary[]
  selectedTensionLength?: string | null
}

const fmt = (value: number | null, digits = 3) => value == null ? '' : value.toFixed(digits);

export default function WearLatestSummaryTable({ columns, rows, selectedTensionLength = null }: Props) {
  const scrollRef = React.useRef<HTMLDivElement | null>(null);
  const byTl = new Map(rows.map(row => [row.tensionLength, row]));
  const metrics = [
    ['Latest Cycle Date', (row: WearLatestSummary) => row.latestCycleDate ?? ''],
    ['Latest Avg Wear Min', (row: WearLatestSummary) => fmt(row.latestAvgWearMin, 2)],
    ['Latest Wear %', (row: WearLatestSummary) => row.latestWearPercentage == null ? '' : <span title={`${row.latestWearPercentage}%`}>{Math.round(row.latestWearPercentage)}%</span>],
    ['Wear Rate (mm / year)', (row: WearLatestSummary) => row.wearRateMmPerYear == null ? 'N/A' : fmt(row.wearRateMmPerYear)],
    ['Historical SD', (row: WearLatestSummary) => fmt(row.historicalSd)],
    ['R-squared', (row: WearLatestSummary) => fmt(row.rSquared)],
    ['Trend Status', (row: WearLatestSummary) => row.trendStatus],
  ] as const;
  React.useEffect(() => {
    if (!selectedTensionLength || !scrollRef.current) return;
    const selectedIndex = columns.findIndex(column => column.tensionLength === selectedTensionLength);
    if (selectedIndex >= 0) scrollRef.current.scrollLeft = selectedIndex * 96;
  }, [columns, selectedTensionLength]);

  return <TableContainer component={Paper} variant="outlined" ref={scrollRef} sx={{ maxHeight: 360, overflowX: 'auto' }}>
    <Table stickyHeader size="small" sx={{ minWidth: 176 + columns.length * 96, width: 176 + columns.length * 96, tableLayout: 'fixed' }} aria-label="Latest wire wear summary">
      <TableHead data-testid="latest-header"><TableRow><TableCell sx={{ width: 176, minWidth: 176, position: 'sticky', left: 0, top: 0, zIndex: 5, bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider', fontWeight: 700 }}>Metric</TableCell>{columns.map(column => {
        const selected = column.tensionLength === selectedTensionLength;
        return <TableCell key={column.tensionLength} align="right" aria-selected={selected || undefined} data-selected={selected || undefined} sx={theme => ({ width: 96, minWidth: 96, px: 0.75, position: 'sticky', top: 0, zIndex: 3, bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider', fontWeight: 700, ...(selected ? { bgcolor: theme.palette.action.selected, boxShadow: `inset 0 -2px ${theme.palette.primary.main}` } : {}) })}>{column.tensionLength}</TableCell>;
      })}</TableRow></TableHead>
      <TableBody>{metrics.map(([label, render]) => <TableRow key={label}><TableCell sx={{ width: 176, minWidth: 176, position: 'sticky', left: 0, zIndex: 2, bgcolor: 'background.paper', whiteSpace: 'nowrap' }}>{label}</TableCell>{columns.map(column => {
        const value = byTl.has(column.tensionLength) ? render(byTl.get(column.tensionLength)!) : '';
        const selected = column.tensionLength === selectedTensionLength;
        return <TableCell key={column.tensionLength} align="right" aria-selected={selected || undefined} data-selected={selected || undefined} sx={{ width: 96, minWidth: 96, px: 0.75, overflow: 'hidden', ...(selected ? { bgcolor: 'action.selected' } : {}) }}>
          <Box component="span" title={typeof value === 'string' && value ? value : undefined} sx={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</Box>
        </TableCell>;
      })}</TableRow>)}</TableBody>
    </Table>
  </TableContainer>;
}
