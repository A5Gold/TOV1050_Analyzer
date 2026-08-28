import React from 'react';
import CloseIcon from '@mui/icons-material/Close';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  LinearProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';

import type { WearCandidatePreview, WireWearLineClass } from '../../types/api';
import BatchAddRecordsGrid, {
  type BatchAddPastedRow,
  type BatchAddRecordField,
  type BatchAddRecordRow,
} from './BatchAddRecordsGrid';

export interface BatchAddRecordsDialogProps {
  open: boolean;
  lineClass: WireWearLineClass;
  cycleDate: string;
  rows: BatchAddRecordRow[];
  preview: WearCandidatePreview | null;
  previewError?: string | null;
  isPreviewing?: boolean;
  isSubmitting?: boolean;
  onLineClassChange: (lineClass: WireWearLineClass) => void;
  onCycleDateChange: (cycleDate: string) => void;
  onCellChange: (rowId: string, field: BatchAddRecordField, value: string) => void;
  onInsertRow: (afterRowId?: string) => void;
  onDeleteRow: (rowId: string) => void;
  onPasteRows: (startRowId: string, rows: BatchAddPastedRow[]) => void;
  onStageAll: (preview: WearCandidatePreview) => void;
  onClose: () => void;
}

const emptyCounts = { new: 0, update: 0, no_change: 0, duplicate: 0, error: 0 };

export default function BatchAddRecordsDialog({
  open,
  lineClass,
  cycleDate,
  rows,
  preview,
  previewError = null,
  isPreviewing = false,
  isSubmitting = false,
  onLineClassChange,
  onCycleDateChange,
  onCellChange,
  onInsertRow,
  onDeleteRow,
  onPasteRows,
  onStageAll,
  onClose,
}: BatchAddRecordsDialogProps) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const counts = preview?.counts ?? emptyCounts;
  const hasBlockingError = preview?.candidates.some(candidate => candidate.status === 'error' && !candidate.excluded) ?? false;
  const stageableCount = counts.new + counts.update;
  const controlsDisabled = isPreviewing || isSubmitting;
  const stageDisabled = !preview || hasBlockingError || stageableCount === 0 || controlsDisabled;
  const contextIssues = preview?.candidates.flatMap(candidate => candidate.issues).filter(
    issue => issue.field === 'cycle_date' || issue.field === 'cycleDate' || issue.field === 'line_class' || issue.field === 'lineClass',
  ) ?? [];
  const cycleDateIssue = contextIssues.find(issue => issue.field === 'cycle_date' || issue.field === 'cycleDate');

  const handleClose = () => {
    if (!isSubmitting) onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="lg"
      fullWidth
      fullScreen={fullScreen}
      scroll="paper"
      aria-labelledby="batch-add-records-title"
      aria-busy={controlsDisabled}
      PaperProps={{
        sx: fullScreen ? undefined : { height: 'min(820px, calc(100dvh - 64px))' },
      }}
    >
      <DialogTitle
        id="batch-add-records-title"
        sx={{
          position: 'sticky',
          top: 0,
          zIndex: 2,
          bgcolor: 'background.paper',
          borderBottom: 1,
          borderColor: 'divider',
          py: 1.5,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography component="span" variant="h5">Add Wire Wear Records</Typography>
            <Typography variant="body2" color="text.secondary">
              One line and cycle date apply to every row.
            </Typography>
          </Box>
          <IconButton aria-label="Close Add Wire Wear Records" onClick={handleClose} disabled={isSubmitting} edge="end">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      {isPreviewing ? <LinearProgress aria-label="Validating records" /> : null}

      <DialogContent sx={{ p: { xs: 2, sm: 3 } }}>
        <Stack spacing={2.5}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField
              select
              fullWidth
              size="small"
              label="Line"
              value={lineClass}
              onChange={event => onLineClassChange(event.target.value as WireWearLineClass)}
              disabled={controlsDisabled}
            >
              <MenuItem value="EAL">EAL</MenuItem>
              <MenuItem value="LMC">LMC</MenuItem>
              <MenuItem value="TML">TML</MenuItem>
            </TextField>
            <TextField
              fullWidth
              size="small"
              label="Cycle Date"
              type="date"
              value={cycleDate}
              onChange={event => onCycleDateChange(event.target.value)}
              disabled={controlsDisabled}
              error={Boolean(cycleDateIssue)}
              helperText={cycleDateIssue?.message}
              InputLabelProps={{ shrink: true }}
            />
          </Stack>

          {previewError ? <Alert severity="error">{previewError}</Alert> : null}
          {contextIssues.filter(issue => issue !== cycleDateIssue).map(issue => (
            <Alert severity="error" key={`${issue.field}:${issue.code}:${issue.message}`}>{issue.message}</Alert>
          ))}

          <BatchAddRecordsGrid
            rows={rows}
            candidates={preview?.candidates}
            disabled={controlsDisabled}
            onCellChange={onCellChange}
            onInsertRow={onInsertRow}
            onDeleteRow={onDeleteRow}
            onPasteRows={onPasteRows}
          />
        </Stack>
      </DialogContent>

      <DialogActions
        sx={{
          position: 'sticky',
          bottom: 0,
          zIndex: 2,
          bgcolor: 'background.paper',
          borderTop: 1,
          borderColor: 'divider',
          px: { xs: 2, sm: 3 },
          py: 1.5,
          gap: 1,
          flexWrap: 'wrap',
        }}
      >
        <Stack
          direction="row"
          spacing={1}
          useFlexGap
          flexWrap="wrap"
          role="status"
          aria-live="polite"
          sx={{ mr: 'auto' }}
        >
          <Chip size="small" label={`Valid ${counts.new}`} color="success" variant="outlined" />
          <Chip size="small" label={`Update ${counts.update}`} color="warning" variant="outlined" />
          <Chip size="small" label={`Duplicate ${counts.duplicate}`} color="info" variant="outlined" />
          <Chip size="small" label={`Error ${counts.error}`} color="error" variant="outlined" />
        </Stack>
        <Button onClick={handleClose} disabled={isSubmitting}>Cancel</Button>
        <Button
          variant="contained"
          onClick={() => preview && onStageAll(preview)}
          disabled={stageDisabled}
          startIcon={isSubmitting ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          {isSubmitting ? 'Staging...' : `Stage All (${stageableCount})`}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
