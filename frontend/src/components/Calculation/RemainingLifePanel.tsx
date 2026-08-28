import React from 'react';
import {
  Alert, Autocomplete, Box, Button, Paper, Skeleton, Stack, Table, TableBody,
  TableCell, TableContainer, TableHead, TablePagination, TableRow, TextField, Typography,
} from '@mui/material';
import { createFilterOptions } from '@mui/material/Autocomplete';
import { useWearRecordsStore } from '../../store/useWearRecordsStore';
import type { WearRemainingLifeRow } from '../../types/api';
import RemainingLifeCurve from './RemainingLifeCurve';

const PRESETS = [10.2, 9.1, 8.9, 7.44, 7.24] as const;
const EMPTY_ROWS: WearRemainingLifeRow[] = [];
const formatRate = (value: number | null) => value == null || !Number.isFinite(value) ? 'N/A' : `${value.toFixed(2)} mm/year`;
const formatLife = (row: WearRemainingLifeRow) => {
  if (row.trendStatus === 'already_at_threshold') return 'Already at threshold';
  if (row.trendStatus === 'non_positive_rate') return 'Non-positive rate';
  if (row.remainingDays == null || row.projectedCrossingDate == null) return 'Insufficient data';
  const years = Math.floor(row.remainingDays / 365.25);
  const months = Math.floor((row.remainingDays - years * 365.25) / 30.4375);
  return `${years}y ${months}m (${row.projectedCrossingDate})`;
};
const lifeTone = (row: WearRemainingLifeRow): 'neutral' | 'grey' | 'red' | 'yellow' | 'green' => {
  if (row.trendStatus === 'non_positive_rate') return 'grey';
  if (row.remainingDays == null || !Number.isFinite(row.remainingDays)) return 'neutral';
  const years = row.remainingDays / 365.25;
  if (years <= 10) return 'red';
  if (years <= 30) return 'yellow';
  return 'green';
};
const LIFE_TONE_STYLES = {
  neutral: {},
  grey: { bgcolor: 'action.disabledBackground', color: 'text.secondary' },
  red: { bgcolor: 'error.light', color: 'error.contrastText' },
  yellow: { bgcolor: 'warning.light', color: 'warning.contrastText' },
  green: { bgcolor: 'success.light', color: 'success.contrastText' },
} as const;
const filterRows = createFilterOptions<WearRemainingLifeRow>({ limit: 100, stringify: row => `${row.lineGroup} ${row.tensionLength}` });

export default function RemainingLifePanel() {
  const remainingLife = useWearRecordsStore(state => state.remainingLife);
  const loading = useWearRecordsStore(state => state.isRemainingLifeLoading);
  const error = useWearRecordsStore(state => state.remainingLifeError);
  const loadRemainingLife = useWearRecordsStore(state => state.loadRemainingLife);
  const threshold = useWearRecordsStore(state => state.wearThresholdMm ?? 10.2);
  const setWearThresholdMm = useWearRecordsStore(state => state.setWearThresholdMm);
  const [selected, setSelected] = React.useState<WearRemainingLifeRow[]>([]);
  const [page, setPage] = React.useState(0);
  React.useEffect(() => { void loadRemainingLife(threshold); }, [loadRemainingLife, threshold]);
  React.useEffect(() => { setSelected([]); setPage(0); }, [threshold]);

  const rows = remainingLife?.rows ?? EMPTY_ROWS;
  const defaults = remainingLife?.defaultRows ?? EMPTY_ROWS;
  const curveRows = React.useMemo(() => {
    const byKey = new Map<string, WearRemainingLifeRow>();
    [...defaults, ...selected].forEach(row => byKey.set(`${row.lineGroup}:${row.tensionLength}`, row));
    return [...byKey.values()];
  }, [defaults, selected]);
  const visibleRows = rows.slice(page * 50, page * 50 + 50);
  const selectedKeys = new Set(selected.map(row => `${row.lineGroup}:${row.tensionLength}`));
  const toggleRow = (row: WearRemainingLifeRow) => {
    const key = `${row.lineGroup}:${row.tensionLength}`;
    setSelected(current => selectedKeys.has(key) ? current.filter(item => `${item.lineGroup}:${item.tensionLength}` !== key) : [...current, row]);
  };

  return <Stack spacing={2}>
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'center' }} flexWrap="wrap" useFlexGap>
        <Box sx={{ flex: 1 }}><Typography variant="h6" sx={{ fontWeight: 700 }}>Remaining Life Cycle</Typography><Typography variant="body2" color="text.secondary">Worst eligible tension length is selected for each line by default.</Typography></Box>
        {PRESETS.map(value => <Button key={value} size="small" variant={threshold === value ? 'contained' : 'outlined'} aria-pressed={threshold === value} onClick={() => setWearThresholdMm(value)}>{value} mm</Button>)}
      </Stack>
    </Paper>
    {error && <Alert severity="error" action={<Button color="inherit" size="small" onClick={() => void loadRemainingLife(threshold)}>Retry</Button>}>Remaining-life data could not be loaded. {error}</Alert>}
    {loading && !remainingLife && <Skeleton variant="rectangular" height={360} />}
    {remainingLife && <>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'flex-start' }}>
        <Autocomplete
          multiple
          size="small"
          options={rows}
          value={selected}
          filterOptions={filterRows}
          getOptionLabel={row => `${row.lineGroup} ${row.tensionLength}`}
          isOptionEqualToValue={(a, b) => a.lineGroup === b.lineGroup && a.tensionLength === b.tensionLength}
          onChange={(_event, value) => setSelected(value)}
          renderInput={params => <TextField {...params} label="Add tension lengths to curve" placeholder="Search TL" />}
          sx={{ flex: 1, minWidth: 0 }}
        />
        <Button size="small" variant="outlined" disabled={selected.length === 0} onClick={() => setSelected([])}>Clear curve</Button>
      </Stack>
      <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 440 }}>
        <Table stickyHeader size="small" aria-label="Remaining life table">
          <TableHead><TableRow><TableCell>Line / TL</TableCell><TableCell>Latest thickness</TableCell><TableCell>Wear rate</TableCell><TableCell>Estimated life</TableCell><TableCell>Curve</TableCell></TableRow></TableHead>
          <TableBody>{visibleRows.map(row => {
            const tone = lifeTone(row);
            return <TableRow key={`${row.lineGroup}-${row.tensionLength}`}><TableCell>{row.lineGroup} {row.tensionLength}</TableCell><TableCell>{row.latestAvgWearMin == null ? 'N/A' : `${row.latestAvgWearMin.toFixed(2)} mm`}</TableCell><TableCell>{formatRate(row.wearRateMmPerYear)}</TableCell><TableCell data-life-tone={tone} sx={{ ...LIFE_TONE_STYLES[tone], fontWeight: 600 }}>{formatLife(row)}</TableCell><TableCell><Button size="small" onClick={() => toggleRow(row)} disabled={row.curve.length === 0}>{selectedKeys.has(`${row.lineGroup}:${row.tensionLength}`) ? 'Remove' : 'Add'}</Button></TableCell></TableRow>;
          })}</TableBody>
        </Table>
        <TablePagination component="div" count={rows.length} page={page} rowsPerPage={50} rowsPerPageOptions={[50]} onPageChange={(_event, next) => setPage(next)} />
      </TableContainer>
      <RemainingLifeCurve rows={curveRows} />
    </>}
  </Stack>;
}
