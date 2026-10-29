import { Box, LinearProgress, Paper, Stack, Typography } from '@mui/material';
import { BackgroundJob } from '../types/api';

export type TaskStage = 'queued' | 'reading' | 'cleaning' | 'metadata_mapping' | 'detecting' | 'preparing_chart' | 'exporting' | 'finalizing';

const STAGE_LABELS: Record<TaskStage, string> = {
  queued: 'Queued',
  reading: 'Reading source data',
  cleaning: 'Cleaning measurements',
  metadata_mapping: 'Mapping metadata',
  detecting: 'Detecting exceptions',
  preparing_chart: 'Preparing chart',
  exporting: 'Writing workbook',
  finalizing: 'Finalizing workbook',
};

interface TaskLoadingStateProps {
  stage: TaskStage;
  exportMode?: boolean;
  progress?: BackgroundJob | null;
}

const TaskLoadingState = ({ stage, exportMode = false, progress }: TaskLoadingStateProps) => {
  const currentStage = progress?.stage || stage;
  const label = currentStage.startsWith('exporting_') ? `Writing ${currentStage.slice(10)}`
    : currentStage === 'aggregating_chainage' ? 'Calculating chainage means'
    : STAGE_LABELS[currentStage as TaskStage] || currentStage;
  const total = progress?.total;
  const processed = progress?.processed;
  const percent = typeof total === 'number' && total > 0 && typeof processed === 'number'
    ? Math.max(0, Math.min(100, processed / total * 100)) : null;
  const elapsed = Math.floor(progress?.elapsed_seconds || 0);
  return (
  <Paper elevation={0} variant="outlined" sx={{ p: 2, width: '100%', maxWidth: 680 }} aria-live="polite">
    <Stack spacing={1.25}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 2 }}>
        <Typography variant="subtitle2">{exportMode ? 'Preparing export' : 'Analysis in progress'}</Typography>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
      </Box>
      <LinearProgress aria-label={label} variant={percent === null ? 'indeterminate' : 'determinate'} value={percent ?? undefined} />
      {progress && <Typography variant="body2">
        {progress.status === 'cancelling' ? '正在取消，等待安全停止點 · ' : ''}
        {percent !== null ? `${processed!.toLocaleString()} / ${total!.toLocaleString()} ${progress.unit || ''}（本階段 ${percent.toFixed(1)}%） · ` : '處理中 · '}
        已用 {Math.floor(elapsed / 60).toString().padStart(2, '0')}:{(elapsed % 60).toString().padStart(2, '0')}
      </Typography>}
      <Typography variant="caption" color="text.secondary">
        {exportMode ? '工作完成後才開始下載；寫入列數完成後仍需封存 Excel。' : '例外偵測使用完整資料；圖表可顯示同里程平均值及原始極值。'}
      </Typography>
    </Stack>
  </Paper>
  );
};

export default TaskLoadingState;
