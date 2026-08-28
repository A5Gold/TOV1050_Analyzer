import React from 'react';
import CloseIcon from '@mui/icons-material/Close';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  IconButton,
  LinearProgress,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';

import ExcelWearImportPreviewTable, {
  type ExcelImportPreviewRow,
  type ExcelImportStatusFilter,
} from './ExcelWearImportPreviewTable';

export type ExcelImportPhase = 'select' | 'preview' | 'confirm';
export type WorkbookSheetSupport = 'supported' | 'reserved' | 'ignored';

export interface WorkbookSheetOption {
  name: string;
  support: WorkbookSheetSupport;
  selected: boolean;
  enabled: boolean;
  reason?: string | null;
}

export interface WorkbookSheetSummary {
  sheetName: string;
  skipped: number;
  new: number;
  update: number;
  noChange: number;
  duplicate?: number;
  error: number;
  total: number;
}

export interface ExcelWearImportDialogProps {
  open: boolean;
  phase: ExcelImportPhase;
  fileName?: string | null;
  sheets: WorkbookSheetOption[];
  sheetSummaries: WorkbookSheetSummary[];
  rows: ExcelImportPreviewRow[];
  filter: ExcelImportStatusFilter;
  error?: string | null;
  isLoading?: boolean;
  isSubmitting?: boolean;
  onFileSelect: (file: File | null) => void;
  onSheetToggle: (sheetName: string, selected: boolean) => void;
  onPreview: () => void;
  onPhaseChange: (phase: ExcelImportPhase) => void;
  onFilterChange: (filter: ExcelImportStatusFilter) => void;
  onExcludeError: (rowId: string, excluded: boolean) => void;
  onDownloadErrorReport: () => void;
  onConfirmAndStage: (rows: ExcelImportPreviewRow[]) => void;
  onClose: () => void;
}

const phaseIndex: Record<ExcelImportPhase, number> = { select: 0, preview: 1, confirm: 2 };
const phaseLabels = ['Select', 'Preview', 'Confirm & Stage'];

const supportLabel = (sheet: WorkbookSheetOption) => {
  if (sheet.support === 'reserved') return sheet.reason || 'Reserved for future support';
  if (sheet.support === 'ignored') return sheet.reason || 'Ignored';
  return 'Supported';
};

export default function ExcelWearImportDialog({
  open,
  phase,
  fileName = null,
  sheets,
  sheetSummaries,
  rows,
  filter,
  error = null,
  isLoading = false,
  isSubmitting = false,
  onFileSelect,
  onSheetToggle,
  onPreview,
  onPhaseChange,
  onFilterChange,
  onExcludeError,
  onDownloadErrorReport,
  onConfirmAndStage,
  onClose,
}: ExcelWearImportDialogProps) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const controlsDisabled = isLoading || isSubmitting;
  const selectedSupportedCount = sheets.filter(sheet => sheet.support === 'supported' && sheet.enabled && sheet.selected).length;
  const unresolvedErrors = rows.filter(row => row.status === 'error' && !row.excluded).length;
  const stageableRows = rows.filter(row => row.status === 'new' || row.status === 'update');
  const previewDisabled = !fileName || selectedSupportedCount === 0 || controlsDisabled;
  const confirmDisabled = unresolvedErrors > 0 || stageableRows.length === 0 || controlsDisabled;
  const totals = React.useMemo(() => sheetSummaries.reduce((result, summary) => ({
    total: result.total + summary.total,
    new: result.new + summary.new,
    update: result.update + summary.update,
    noChange: result.noChange + summary.noChange,
    error: result.error + summary.error,
  }), { total: 0, new: 0, update: 0, noChange: 0, error: 0 }), [sheetSummaries]);

  const handleClose = () => {
    if (!isSubmitting) onClose();
  };

  const handleReviewStage = () => {
    onFilterChange('all');
    onPhaseChange('confirm');
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="xl"
      fullWidth
      fullScreen={fullScreen}
      scroll="paper"
      aria-labelledby="excel-wear-import-title"
      aria-busy={controlsDisabled}
      PaperProps={{ sx: fullScreen ? undefined : { height: 'min(880px, calc(100dvh - 48px))' } }}
    >
      <DialogTitle
        id="excel-wear-import-title"
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
          <UploadFileIcon color="primary" />
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography component="span" variant="h5">Import Wire Wear Excel</Typography>
            <Typography variant="body2" color="text.secondary" noWrap>
              {fileName || 'Select a historical .xlsx workbook'}
            </Typography>
          </Box>
          <IconButton aria-label="Close Import Wire Wear Excel" onClick={handleClose} disabled={isSubmitting} edge="end">
            <CloseIcon />
          </IconButton>
        </Box>
        <Stepper activeStep={phaseIndex[phase]} sx={{ mt: 1.5 }} alternativeLabel={fullScreen}>
          {phaseLabels.map(label => <Step key={label}><StepLabel>{label}</StepLabel></Step>)}
        </Stepper>
      </DialogTitle>

      {isLoading ? <LinearProgress aria-label="Loading Excel import" /> : null}

      <DialogContent sx={{ p: { xs: 2, sm: 3 } }}>
        <Stack spacing={2.5}>
          {error ? <Alert severity="error">{error}</Alert> : null}

          {phase === 'select' ? (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                hidden
                onChange={event => onFileSelect(event.target.files?.[0] ?? null)}
                disabled={controlsDisabled}
                aria-label="Historical workbook file"
              />
              <Paper variant="outlined" sx={{ p: 2.5 }}>
                <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ sm: 'center' }} spacing={2}>
                  <DescriptionOutlinedIcon color={fileName ? 'primary' : 'disabled'} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography fontWeight={700}>{fileName || 'No workbook selected'}</Typography>
                    <Typography variant="body2" color="text.secondary">Excel workbooks must use the .xlsx format.</Typography>
                  </Box>
                  <Button
                    variant={fileName ? 'outlined' : 'contained'}
                    startIcon={<UploadFileIcon />}
                    onClick={() => fileInputRef.current?.click()}
                    disabled={controlsDisabled}
                  >
                    {fileName ? 'Choose Another File' : 'Choose Excel File'}
                  </Button>
                </Stack>
              </Paper>

              {fileName ? (
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>Worksheets</Typography>
                  <Stack divider={<Divider flexItem />} sx={{ border: 1, borderColor: 'divider', borderRadius: 1 }}>
                    {sheets.length === 0 ? (
                      <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>No worksheets discovered.</Typography>
                    ) : sheets.map(sheet => (
                      <Box key={sheet.name} sx={{ display: 'flex', alignItems: 'center', gap: 1.5, px: 2, py: 1.25 }}>
                        <FormControlLabel
                          sx={{ m: 0, flex: 1, minWidth: 0 }}
                          control={(
                            <Checkbox
                              checked={sheet.selected}
                              disabled={!sheet.enabled || controlsDisabled}
                              onChange={event => onSheetToggle(sheet.name, event.target.checked)}
                              inputProps={{ 'aria-label': `Select worksheet ${sheet.name}` }}
                            />
                          )}
                          label={<Typography noWrap>{sheet.name}</Typography>}
                        />
                        <Chip
                          size="small"
                          label={supportLabel(sheet)}
                          color={sheet.support === 'supported' ? 'success' : 'default'}
                          variant="outlined"
                        />
                      </Box>
                    ))}
                  </Stack>
                </Box>
              ) : null}
            </>
          ) : (
            <>
              <Box>
                <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" role="status" aria-live="polite">
                  <Chip label={`Total ${totals.total}`} />
                  <Chip label={`New ${totals.new}`} color="success" variant="outlined" />
                  <Chip label={`Update ${totals.update}`} color="warning" variant="outlined" />
                  <Chip label={`No Change ${totals.noChange}`} variant="outlined" />
                  <Chip label={`Error ${totals.error}`} color="error" variant="outlined" />
                </Stack>
                {sheetSummaries.length ? (
                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1 }} aria-label="Worksheet summaries">
                    {sheetSummaries.map(summary => (
                      <Chip
                        key={summary.sheetName}
                        size="small"
                        label={`${summary.sheetName} ${summary.total} rows, ${summary.error} errors`}
                        variant="outlined"
                      />
                    ))}
                  </Stack>
                ) : null}
              </Box>

              {phase === 'confirm' ? (
                <Alert severity={unresolvedErrors ? 'error' : 'info'}>
                  {unresolvedErrors
                    ? `${unresolvedErrors} error rows must be corrected or explicitly excluded.`
                    : `${stageableRows.length} New or Update rows will enter the existing staged-change workflow. No Change rows will not be staged.`}
                </Alert>
              ) : null}

              <ExcelWearImportPreviewTable
                rows={rows}
                filter={filter}
                disabled={controlsDisabled}
                onFilterChange={onFilterChange}
                onExcludeError={onExcludeError}
                onDownloadErrorReport={onDownloadErrorReport}
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
        {phase !== 'select' ? (
          <Button onClick={() => onPhaseChange(phase === 'confirm' ? 'preview' : 'select')} disabled={controlsDisabled}>
            Back
          </Button>
        ) : null}
        <Box sx={{ flex: 1 }} />
        <Button onClick={handleClose} disabled={isSubmitting}>Cancel</Button>
        {phase === 'select' ? (
          <Button variant="contained" onClick={onPreview} disabled={previewDisabled}>
            {isLoading ? 'Loading...' : 'Preview'}
          </Button>
        ) : phase === 'preview' ? (
          <Button variant="contained" onClick={handleReviewStage} disabled={controlsDisabled || rows.length === 0}>
            Review Stage
          </Button>
        ) : (
          <Button
            variant="contained"
            onClick={() => onConfirmAndStage(stageableRows)}
            disabled={confirmDisabled}
            startIcon={isSubmitting ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            {isSubmitting ? 'Staging...' : `Confirm & Stage (${stageableRows.length})`}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
