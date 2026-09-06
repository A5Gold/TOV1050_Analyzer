import { Box, LinearProgress, Paper, Skeleton, Stack, Typography } from '@mui/material';

export type TaskStage = 'queued' | 'reading' | 'cleaning' | 'metadata_mapping' | 'detecting' | 'preparing_chart' | 'exporting';

const STAGE_LABELS: Record<TaskStage, string> = {
  queued: 'Queued',
  reading: 'Reading source data',
  cleaning: 'Cleaning measurements',
  metadata_mapping: 'Mapping metadata',
  detecting: 'Detecting exceptions',
  preparing_chart: 'Preparing chart',
  exporting: 'Writing workbook',
};

interface TaskLoadingStateProps {
  stage: TaskStage;
  exportMode?: boolean;
}

const TaskLoadingState = ({ stage, exportMode = false }: TaskLoadingStateProps) => (
  <Paper elevation={0} variant="outlined" sx={{ p: 2, width: '100%', maxWidth: 680 }} aria-live="polite">
    <Stack spacing={1.25}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 2 }}>
        <Typography variant="subtitle2">{exportMode ? 'Preparing export' : 'Analysis in progress'}</Typography>
        <Typography variant="caption" color="text.secondary">{STAGE_LABELS[stage]}</Typography>
      </Box>
      <Skeleton variant="rounded" height={12} animation="wave" />
      <Skeleton variant="rounded" height={12} width="72%" animation="wave" />
      <LinearProgress aria-label={STAGE_LABELS[stage]} />
      <Typography variant="caption" color="text.secondary">
        The detector is processing the complete data set. The chart will use a compact overview after completion.
      </Typography>
    </Stack>
  </Paper>
);

export default TaskLoadingState;
