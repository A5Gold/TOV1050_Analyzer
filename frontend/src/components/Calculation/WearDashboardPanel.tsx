import React from 'react';
import {
  Box, Paper, Stack, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, ToggleButton, ToggleButtonGroup, Typography,
} from '@mui/material';

import { useWearRecordsStore } from '../../store/useWearRecordsStore';
import type { WireWearLineGroup, WireWearRateRow } from '../../types/api';

type LineFilter = 'All' | WireWearLineGroup;
type RankingKey = 'top_max_rate' | 'top_min_rate' | 'top_current_wear';

const rankings: Array<{ key: RankingKey; title: string }> = [
  { key: 'top_max_rate', title: 'Top 5 Max Wear Rate' },
  { key: 'top_min_rate', title: 'Top 5 Min Positive Wear Rate' },
  { key: 'top_current_wear', title: 'Top 5 Current Wear' },
];

const formatNumber = (value: number | null | undefined, digits: number, suffix = '') =>
  typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(digits)}${suffix}` : '-';

function RankingTable({ rankingKey, title, rows }: { rankingKey: RankingKey; title: string; rows: WireWearRateRow[] }) {
  const isCurrentWear = rankingKey === 'top_current_wear';
  return (
    <Box component="section" aria-label={title}>
      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>{title}</Typography>
      <TableContainer sx={{ border: 1, borderColor: 'divider', maxHeight: 310 }}>
        <Table size="small" stickyHeader aria-label={title}>
          <TableHead>
            <TableRow>
              <TableCell>Rank</TableCell><TableCell>Line</TableCell><TableCell>TL</TableCell>
              {isCurrentWear ? (
                <><TableCell>Latest Wear</TableCell><TableCell>Avg Wear Min</TableCell></>
              ) : (
                <><TableCell>%/year</TableCell><TableCell>mm/year</TableCell></>
              )}
              <TableCell>R²</TableCell><TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, index) => (
              <TableRow key={`${row.line_group}-${row.tension_length}-${index}`}>
                <TableCell>{index + 1}</TableCell><TableCell>{row.line_group}</TableCell><TableCell>{row.tension_length}</TableCell>
                {isCurrentWear ? (
                  <>
                    <TableCell>{formatNumber(row.latest_wear_percentage, 1, '%')}</TableCell>
                    <TableCell>{formatNumber(row.latest_avg_wear_min, 3)}</TableCell>
                  </>
                ) : (
                  <>
                    <TableCell>{formatNumber(row.wear_percent_per_year, 2)}</TableCell>
                    <TableCell>{formatNumber(row.wear_mm_per_year, 3)}</TableCell>
                  </>
                )}
                <TableCell>{formatNumber(row.r_squared, 3)}</TableCell><TableCell>{row.trend_status}</TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && <TableRow><TableCell colSpan={7}>No committed records</TableCell></TableRow>}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

const WearDashboardPanel: React.FC = () => {
  const dashboard = useWearRecordsStore(state => state.dashboard);
  const loadDashboard = useWearRecordsStore(state => state.loadDashboard);
  const [lineFilter, setLineFilter] = React.useState<LineFilter>('All');

  React.useEffect(() => { loadDashboard(); }, [loadDashboard]);

  const rowsFor = (key: RankingKey) => {
    const groups: WireWearLineGroup[] = lineFilter === 'All' ? ['EAL', 'TML'] : [lineFilter];
    const rows = groups.flatMap(group => dashboard?.line_groups[group]?.[key] ?? []);
    if (key === 'top_current_wear') {
      return rows.slice().sort((left, right) => right.latest_wear_percentage - left.latest_wear_percentage).slice(0, 5);
    }
    const positive = rows.filter(row => typeof row.wear_mm_per_year === 'number' && row.wear_mm_per_year > 0);
    return positive.sort((left, right) => key === 'top_max_rate'
      ? (right.wear_mm_per_year ?? 0) - (left.wear_mm_per_year ?? 0)
      : (left.wear_mm_per_year ?? 0) - (right.wear_mm_per_year ?? 0)).slice(0, 5);
  };

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={2}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap' }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Committed wear rankings</Typography>
          <ToggleButtonGroup exclusive size="small" value={lineFilter} onChange={(_, value) => value && setLineFilter(value)}>
            {(['All', 'EAL', 'TML'] as const).map(value => <ToggleButton key={value} value={value}>{value}</ToggleButton>)}
          </ToggleButtonGroup>
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: 'repeat(3, minmax(0, 1fr))' }, gap: 2 }}>
          {rankings.map(ranking => <RankingTable key={ranking.key} rankingKey={ranking.key} title={ranking.title} rows={rowsFor(ranking.key)} />)}
        </Box>
      </Stack>
    </Paper>
  );
};

export default WearDashboardPanel;
