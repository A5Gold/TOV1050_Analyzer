import React from 'react';
import {
  Alert, Box, Button, Collapse, IconButton, Paper, Skeleton, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, TextField, Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

import { useWearRecordsStore } from '../../store/useWearRecordsStore';
import type { WearProjectionRecord } from '../../types/api';
import { ProjectionBucketChart } from './wearRecordCharts';

const PRESETS = [10.2, 9.1, 8.9, 7.44, 7.24] as const;
const PROJECTION_COLORS = { EAL: '#64b5f6', TML: '#8d6e63' } as const;

const WearProjectionPanel: React.FC = () => {
  const projection = useWearRecordsStore(state => state.projection);
  const loadProjection = useWearRecordsStore(state => state.loadProjection);
  const sharedThresholdMm = useWearRecordsStore(state => state.wearThresholdMm ?? 10.2);
  const setWearThresholdMm = useWearRecordsStore(state => state.setWearThresholdMm);
  const isProjectionLoading = useWearRecordsStore(state => state.isProjectionLoading);
  const projectionError = useWearRecordsStore(state => state.projectionError);
  const [thresholdDraft, setThresholdDraft] = React.useState(String(sharedThresholdMm));
  const [expandedYear, setExpandedYear] = React.useState<number | null>(null);

  React.useEffect(() => { setThresholdDraft(String(sharedThresholdMm)); }, [sharedThresholdMm]);
  React.useEffect(() => { void loadProjection(sharedThresholdMm); }, [loadProjection, sharedThresholdMm]);

  const applyThreshold = (value: number) => {
    if (!Number.isFinite(value) || value <= 0 || value > 13.2) return;
    setWearThresholdMm(value);
    setThresholdDraft(String(value));
  };

  const draftValue = thresholdDraft.trim() === '' ? Number.NaN : Number(thresholdDraft);
  const thresholdError = thresholdDraft.trim() === ''
    ? 'Enter a thickness.'
    : !Number.isFinite(draftValue) || draftValue <= 0
      ? 'Threshold must be greater than 0 mm.'
      : draftValue > 13.2
        ? 'Threshold must be 13.2 mm or less.'
        : null;

  const buckets = (['EAL', 'TML'] as const).flatMap(line =>
    (projection?.lineGroups[line].yearBuckets ?? []).map(bucket => ({ line, ...bucket })),
  );
  const years = [...new Set(buckets.filter(bucket => bucket.count > 0).map(bucket => bucket.year))].sort((a, b) => a - b);
  const rowsForYear = (year: number) => buckets.filter(bucket => bucket.year === year).flatMap(bucket => bucket.records);

  return (
    <Stack spacing={2}>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ md: 'center' }} justifyContent="space-between">
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>30-Year Thickness Projection</Typography>
            <Typography variant="body2" color="text.secondary">
              Equivalent wear: {Math.round(projection?.thresholdPercentage ?? 0)}%
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            {PRESETS.map(value => (
              <Button
                key={value}
                size="small"
                variant={sharedThresholdMm === value ? 'contained' : 'outlined'}
                aria-pressed={sharedThresholdMm === value}
                onClick={() => applyThreshold(value)}
              >
                {value} mm
              </Button>
            ))}
            <TextField
              size="small"
              type="number"
              label="Threshold mm"
              value={thresholdDraft}
              onChange={event => setThresholdDraft(event.target.value)}
              error={thresholdError != null}
              helperText={thresholdError ?? 'Valid range: greater than 0 to 13.2 mm'}
              inputProps={{ min: 0.01, max: 13.2, step: 0.01 }}
              sx={{ width: 132 }}
            />
            <Button variant="outlined" disabled={thresholdError != null} onClick={() => applyThreshold(draftValue)}>Apply threshold</Button>
          </Stack>
        </Stack>
      </Paper>

      {projectionError && (
        <Alert
          severity="error"
          action={<Button color="inherit" size="small" onClick={() => void loadProjection(sharedThresholdMm)}>Retry</Button>}
        >
          Projection data could not be loaded. {projectionError}
        </Alert>
      )}

      {isProjectionLoading && !projection && (
        <Box aria-label="Loading projection" sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' }, gap: 2 }}>
          <Skeleton variant="rectangular" height={300} />
          <Skeleton variant="rectangular" height={300} />
        </Box>
      )}

      {projection && <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' }, gap: 2 }} aria-busy={isProjectionLoading}>
        {(['EAL', 'TML'] as const).map(line => (
          <Paper key={line} variant="outlined" sx={{ p: 1 }}>
            <ProjectionBucketChart
              title={`${line} 30-year projection`}
              buckets={projection?.lineGroups[line].yearBuckets ?? []}
              color={PROJECTION_COLORS[line]}
            />
          </Paper>
        ))}
      </Box>}

      <Paper variant="outlined" sx={{ p: 2, overflowX: 'auto' }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>Combined projected year detail</Typography>
        <Table size="small" aria-label="Combined projected year detail">
          <TableHead><TableRow><TableCell width={44} /><TableCell>Projected Year</TableCell><TableCell>Count</TableCell><TableCell>Tension Lengths</TableCell></TableRow></TableHead>
          <TableBody>{years.map(year => {
            const rows = rowsForYear(year);
            const open = expandedYear === year;
            return <React.Fragment key={year}>
              <TableRow hover>
                <TableCell><IconButton size="small" aria-label={`Expand ${year}`} onClick={() => setExpandedYear(open ? null : year)}><ExpandMoreIcon /></IconButton></TableCell>
                <TableCell>{year}</TableCell><TableCell>{rows.length}</TableCell><TableCell>{rows.map(row => row.tensionLength).join(', ')}</TableCell>
              </TableRow>
              <TableRow><TableCell colSpan={4} sx={{ py: 0, border: 0 }}><Collapse in={open}>
                <Table size="small" aria-label={`${year} projection records`} sx={{ my: 1 }}>
                  <TableHead><TableRow><TableCell>Line / TL</TableCell><TableCell>Latest thickness / date</TableCell><TableCell>mm/year</TableCell><TableCell>Crossing date</TableCell><TableCell>R-squared</TableCell><TableCell>Status</TableCell></TableRow></TableHead>
                  <TableBody>{rows.map(row => <TableRow key={`${row.lineGroup}-${row.tensionLength}`}>
                    <TableCell>{row.lineGroup} {row.tensionLength}</TableCell><TableCell>{row.latestAvgWearMin} mm / {row.latestCycleDate}</TableCell>
                    <TableCell>{formatNumber(row.wearRateMmPerYear)}</TableCell><TableCell>{row.projectedCrossingDate ?? '-'}</TableCell>
                    <TableCell>{formatNumber(row.rSquared)}</TableCell><TableCell>{row.trendStatus}</TableCell>
                  </TableRow>)}</TableBody>
                </Table>
              </Collapse></TableCell></TableRow>
            </React.Fragment>;
          })}</TableBody>
        </Table>
      </Paper>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, gap: 2 }}>
        <StatusList title="Already at threshold" records={statusRecords(projection, 'alreadyAtThreshold')} />
        <StatusList title="Insufficient data" records={statusRecords(projection, 'insufficientData')} />
        <StatusList title="Non-positive rate" records={statusRecords(projection, 'nonPositiveRate')} />
      </Box>
    </Stack>
  );
};

const formatNumber = (value: number | null) => value == null ? 'N/A' : value.toFixed(2);

function statusRecords(projection: ReturnType<typeof useWearRecordsStore.getState>['projection'], key: 'alreadyAtThreshold' | 'insufficientData' | 'nonPositiveRate') {
  return (['EAL', 'TML'] as const).flatMap(line => projection?.lineGroups[line][key] ?? []);
}

function StatusList({ title, records }: { title: string; records: WearProjectionRecord[] }) {
  return <Paper variant="outlined" sx={{ p: 2 }}>
    <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{title}</Typography>
    <Typography variant="body2" color="text.secondary">{records.length ? records.map(record => `${record.lineGroup} ${record.tensionLength}`).join(', ') : 'None'}</Typography>
  </Paper>;
}

export default WearProjectionPanel;
