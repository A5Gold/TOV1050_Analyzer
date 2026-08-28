import React from 'react';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import CloseIcon from '@mui/icons-material/Close';
import DataObjectIcon from '@mui/icons-material/DataObject';
import UploadFileIcon from '@mui/icons-material/UploadFile';
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
  Paper,
  Stack,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';

import WireWearSyncPreviewTable, {
  type WireWearConflictChoice,
  type WireWearSyncLineIdentity,
  type WireWearSyncPreviewRow,
  type WireWearSyncStatusFilter,
} from './WireWearSyncPreviewTable';

export type WireWearSyncDialogPhase = 'select' | 'preview' | 'success';
export type WireWearSyncGuardState =
  | 'none'
  | 'pending_changes'
  | 'unsupported_package'
  | 'stale_preview'
  | 'backup_failure'
  | 'apply_failure';

export interface WireWearSyncPackageInfo {
  packageId: string;
  sourceWorkstation?: string | null;
  exportedAt?: string | null;
  schema?: string | null;
}

export interface WireWearSyncConflictDecision {
  key: WireWearSyncLineIdentity;
  choice: WireWearConflictChoice;
}

export interface WireWearSyncApplySummary {
  created: number;
  updated: number;
  deleted: number;
  keepLocal: number;
  noChange: number;
  conflictsResolved: number;
  backupPath?: string | null;
  dataVersion: number;
}

export interface WireWearSyncImportDialogProps {
  open: boolean;
  phase: WireWearSyncDialogPhase;
  fileName?: string | null;
  packageInfo?: WireWearSyncPackageInfo | null;
  rows: WireWearSyncPreviewRow[];
  filter: WireWearSyncStatusFilter;
  warnings?: string[];
  guardState?: WireWearSyncGuardState;
  guardMessage?: string | null;
  isPreviewing?: boolean;
  isApplying?: boolean;
  successSummary?: WireWearSyncApplySummary | null;
  onFileSelect: (file: File | null) => void;
  onPreview: () => void;
  onFilterChange: (filter: WireWearSyncStatusFilter) => void;
  onResolveConflict: (rowId: string, choice: WireWearConflictChoice) => void;
  onConfirmImport: (decisions: WireWearSyncConflictDecision[]) => void;
  onStartOver: () => void;
  onClose: () => void;
}

const guardPresentation: Record<Exclude<WireWearSyncGuardState, 'none'>, { severity: 'warning' | 'error'; message: string }> = {
  pending_changes: {
    severity: 'warning',
    message: 'Save or discard pending Wire Wear changes before importing a data package.',
  },
  unsupported_package: {
    severity: 'error',
    message: 'This package is not a supported wear-cycle-v1 data package.',
  },
  stale_preview: {
    severity: 'warning',
    message: 'Wire Wear data changed after preview. Preview the package again before importing.',
  },
  backup_failure: {
    severity: 'error',
    message: 'The SQLite backup could not be created. No database changes were applied.',
  },
  apply_failure: {
    severity: 'error',
    message: 'The package could not be applied. The database transaction was rolled back.',
  },
};

export default function WireWearSyncImportDialog({
  open,
  phase,
  fileName = null,
  packageInfo = null,
  rows,
  filter,
  warnings = [],
  guardState = 'none',
  guardMessage = null,
  isPreviewing = false,
  isApplying = false,
  successSummary = null,
  onFileSelect,
  onPreview,
  onFilterChange,
  onResolveConflict,
  onConfirmImport,
  onStartOver,
  onClose,
}: WireWearSyncImportDialogProps) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const controlsDisabled = isPreviewing || isApplying;
  const blockingGuard = guardState !== 'none';
  const unresolvedConflicts = rows.filter(row => row.status === 'conflict' && !row.resolution);
  const errorRows = rows.filter(row => row.status === 'error');
  const decisions = rows.flatMap<WireWearSyncConflictDecision>(row => (
    row.status === 'conflict' && row.resolution ? [{ key: row.key, choice: row.resolution }] : []
  ));
  const confirmDisabled = controlsDisabled || blockingGuard || unresolvedConflicts.length > 0 || errorRows.length > 0 || rows.length === 0;
  const counts = React.useMemo(() => rows.reduce<Record<string, number>>((result, row) => {
    result[row.status] = (result[row.status] || 0) + 1;
    return result;
  }, {}), [rows]);
  const guard = guardState === 'none' ? null : guardPresentation[guardState];

  const handleClose = () => {
    if (!isApplying) onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="xl"
      fullWidth
      fullScreen={fullScreen}
      scroll="paper"
      aria-labelledby="wire-wear-sync-import-title"
      aria-busy={controlsDisabled}
      PaperProps={{ sx: fullScreen ? undefined : { height: 'min(880px, calc(100dvh - 48px))' } }}
    >
      <DialogTitle
        id="wire-wear-sync-import-title"
        sx={{
          position: 'sticky',
          top: 0,
          zIndex: 3,
          bgcolor: 'background.paper',
          borderBottom: 1,
          borderColor: 'divider',
          py: 1.5,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <DataObjectIcon color="primary" />
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography component="span" variant="h5">Import Wire Wear Data Package</Typography>
            <Typography variant="body2" color="text.secondary" noWrap>
              {phase === 'success' ? 'Import completed' : fileName || 'Select a wear-cycle-v1 JSON package'}
            </Typography>
          </Box>
          <IconButton aria-label="Close Import Wire Wear Data Package" onClick={handleClose} disabled={isApplying} edge="end">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      {controlsDisabled ? <LinearProgress aria-label={isApplying ? 'Applying data package' : 'Previewing data package'} /> : null}

      <DialogContent sx={{ p: { xs: 2, sm: 3 } }}>
        <Stack spacing={2.5}>
          {guard ? <Alert severity={guard.severity}>{guardMessage || guard.message}</Alert> : null}
          {warnings.map(warning => <Alert severity="warning" key={warning}>{warning}</Alert>)}

          {phase === 'select' ? (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                hidden
                aria-label="Wire Wear data package file"
                disabled={controlsDisabled || guardState === 'pending_changes'}
                onChange={event => onFileSelect(event.target.files?.[0] ?? null)}
              />
              <Paper variant="outlined" sx={{ p: 2.5 }}>
                <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ sm: 'center' }} spacing={2}>
                  <DataObjectIcon color={fileName ? 'primary' : 'disabled'} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography fontWeight={700}>{fileName || 'No data package selected'}</Typography>
                    <Typography variant="body2" color="text.secondary">Only normalized wear-cycle-v1 JSON packages are supported.</Typography>
                  </Box>
                  <Button
                    variant={fileName ? 'outlined' : 'contained'}
                    startIcon={<UploadFileIcon />}
                    onClick={() => fileInputRef.current?.click()}
                    disabled={controlsDisabled || guardState === 'pending_changes'}
                  >
                    {fileName ? 'Choose Another Package' : 'Choose Data Package'}
                  </Button>
                </Stack>
              </Paper>
            </>
          ) : phase === 'success' && successSummary ? (
            <Box sx={{ maxWidth: 760, mx: 'auto', width: '100%', py: 3 }}>
              <Stack alignItems="center" spacing={2}>
                <CheckCircleOutlineIcon color="success" sx={{ fontSize: 52 }} />
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h5">Wire Wear data package imported</Typography>
                  <Typography variant="body2" color="text.secondary">Data version {successSummary.dataVersion}</Typography>
                </Box>
                <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" justifyContent="center" role="status">
                  <Chip label={`Created ${successSummary.created}`} color="success" variant="outlined" />
                  <Chip label={`Updated ${successSummary.updated}`} color="warning" variant="outlined" />
                  <Chip label={`Deleted ${successSummary.deleted}`} color="error" variant="outlined" />
                  <Chip label={`Keep Local ${successSummary.keepLocal}`} color="info" variant="outlined" />
                  <Chip label={`No Change ${successSummary.noChange}`} variant="outlined" />
                  <Chip label={`Conflicts Resolved ${successSummary.conflictsResolved}`} color="secondary" variant="outlined" />
                </Stack>
                {successSummary.backupPath ? (
                  <Alert severity="success" sx={{ width: '100%', overflowWrap: 'anywhere' }}>
                    Backup created: {successSummary.backupPath}
                  </Alert>
                ) : null}
              </Stack>
            </Box>
          ) : (
            <>
              {packageInfo ? (
                <Paper variant="outlined" sx={{ p: 1.5 }}>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={{ xs: 0.5, sm: 3 }}>
                    <Typography variant="body2"><strong>Package:</strong> {packageInfo.packageId}</Typography>
                    <Typography variant="body2"><strong>Source:</strong> {packageInfo.sourceWorkstation || '-'}</Typography>
                    <Typography variant="body2"><strong>Exported:</strong> {packageInfo.exportedAt || '-'}</Typography>
                    <Typography variant="body2"><strong>Schema:</strong> {packageInfo.schema || 'wear-cycle-v1'}</Typography>
                  </Stack>
                </Paper>
              ) : null}
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" role="status" aria-live="polite">
                <Chip label={`Total ${rows.length}`} />
                <Chip label={`New ${counts.new || 0}`} color="success" variant="outlined" />
                <Chip label={`Update ${counts.update || 0}`} color="warning" variant="outlined" />
                <Chip label={`Keep Local ${counts.keep_local || 0}`} color="info" variant="outlined" />
                <Chip label={`No Change ${counts.no_change || 0}`} variant="outlined" />
                <Chip label={`Conflict ${counts.conflict || 0}`} color="secondary" variant="outlined" />
                <Chip label={`Error ${counts.error || 0}`} color="error" variant="outlined" />
                <Chip label={`Delete ${counts.delete || 0}`} color="error" variant="outlined" />
              </Stack>
              {unresolvedConflicts.length > 0 ? (
                <Alert severity="warning">Resolve all {unresolvedConflicts.length} conflicts before importing.</Alert>
              ) : null}
              {errorRows.length > 0 ? (
                <Alert severity="error">This preview contains {errorRows.length} blocking errors. Error actions cannot be imported.</Alert>
              ) : null}
              <WireWearSyncPreviewTable
                rows={rows}
                filter={filter}
                disabled={controlsDisabled}
                onFilterChange={onFilterChange}
                onResolveConflict={onResolveConflict}
              />
            </>
          )}
        </Stack>
      </DialogContent>

      <DialogActions
        sx={{
          position: 'sticky',
          bottom: 0,
          zIndex: 3,
          bgcolor: 'background.paper',
          borderTop: 1,
          borderColor: 'divider',
          px: { xs: 2, sm: 3 },
          py: 1.5,
          gap: 1,
        }}
      >
        {phase === 'success' ? (
          <>
            <Button onClick={onStartOver}>Import Another</Button>
            <Box sx={{ flex: 1 }} />
            <Button variant="contained" onClick={handleClose}>Done</Button>
          </>
        ) : (
          <>
            {phase === 'preview' ? <Button onClick={onStartOver} disabled={controlsDisabled}>Back</Button> : null}
            <Box sx={{ flex: 1 }} />
            <Button onClick={handleClose} disabled={isApplying}>Cancel</Button>
            {phase === 'select' ? (
              <Button
                variant="contained"
                onClick={onPreview}
                disabled={!fileName || controlsDisabled || blockingGuard}
              >
                {isPreviewing ? 'Previewing...' : 'Preview Package'}
              </Button>
            ) : (
              <Button
                variant="contained"
                onClick={() => onConfirmImport(decisions)}
                disabled={confirmDisabled}
                startIcon={isApplying ? <CircularProgress size={16} color="inherit" /> : undefined}
              >
                {isApplying ? 'Importing...' : 'Confirm Import'}
              </Button>
            )}
          </>
        )}
      </DialogActions>
    </Dialog>
  );
}
