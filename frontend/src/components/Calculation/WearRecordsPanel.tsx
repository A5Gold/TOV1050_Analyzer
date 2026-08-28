import React from 'react';
import * as XLSX from 'xlsx';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import DownloadIcon from '@mui/icons-material/Download';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import StorageIcon from '@mui/icons-material/Storage';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import {
  alpha,
  Alert,
  Autocomplete,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Menu,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
  createFilterOptions,
} from '@mui/material';

import { useWearRecordsStore } from '../../store/useWearRecordsStore';
import type {
  WearCandidatePreview,
  WearCycleRecord,
  WearCycleWorkbenchResponse,
  WireWearLineClass,
} from '../../types/api';
import BatchAddRecordsDialog from './BatchAddRecordsDialog';
import type {
  BatchAddPastedRow,
  BatchAddRecordField,
  BatchAddRecordRow,
} from './BatchAddRecordsGrid';
import ExcelWearImportDialog, {
  type ExcelImportPhase,
  type WorkbookSheetOption,
} from './ExcelWearImportDialog';
import type {
  ExcelImportPreviewRow,
  ExcelImportStatusFilter,
} from './ExcelWearImportPreviewTable';
import WearHistoryPivotTable from './WearHistoryPivotTable';
import WearLatestSummaryTable from './WearLatestSummaryTable';
import {
  buildHistoricalWearMatrix,
  sortWearWorkbenchColumns,
} from './wearTensionLengthOrder';
import WireWearRecordDialog from './WireWearRecordDialog';
import WireWearSyncImportDialog, {
  type WireWearSyncDialogPhase,
} from './WireWearSyncImportDialog';
import type {
  WireWearSyncPreviewRow,
  WireWearSyncStatusFilter,
} from './WireWearSyncPreviewTable';

type DialogState = {
  mode: 'add' | 'edit'
  cycleDate: string
  tensionLength: string
  avgWearMin: number
} | null;
type DeleteState =
  | { kind: 'cell'; cycleDate: string; tensionLength: string }
  | { kind: 'row'; cycleDate: string }
  | null;

let nextBatchRowId = 1;
const newBatchRow = (): BatchAddRecordRow => ({
  rowId: `batch-${nextBatchRowId++}`,
  tensionLength: '',
  avgWearMin: '',
});

const lineGroupForClass = (lineClass: WireWearLineClass) => (
  lineClass === 'TML' ? 'TML' : 'EAL'
);

const filterTensionLengths = createFilterOptions<WearCycleWorkbenchResponse['catalog'][number]>({
  limit: 100,
  stringify: option => option.tensionLength,
});

const csvCell = (value: unknown) => {
  const text = value == null ? '' : String(value);
  return `"${text.replace(/"/g, '""')}"`;
};

const WearRecordsPanel: React.FC = () => {
  const store = useWearRecordsStore();
  const {
    cycleWorkbench,
    committedSnapshot,
    pendingChanges,
    changeSummary,
    commitErrors,
    selectedLineGroup,
    selectedLineClass,
    selectedTensionLength,
    isLoading,
    isSaving,
    hasPendingChanges,
    candidatePreview,
    historicalDiscovery,
    historicalPreview,
    historicalExcludedDiagnosticIds,
    isPreviewingCandidates,
    previewError,
    syncPreview,
    syncConflictDecisions,
    syncApplySummary,
    syncGuardState,
    syncGuardMessage,
    isPreviewingSync,
    isApplyingSync,
    loadCycleWorkbench,
    setSelectedLineClass,
    setSelectedTensionLength,
    stageAdd,
    stageEdit,
    stageDeleteCell,
    stageDeleteRow,
    previewCandidateRows,
    discoverHistoricalWorkbook,
    previewHistoricalWorkbook,
    setHistoricalErrorExcluded,
    clearImportPreviews,
    stageBatch,
    stageHistoricalPreview,
    saveChanges,
    discardChanges,
    exportSyncPackage,
    previewSyncPackage,
    resolveSyncConflict,
    applySyncPreview,
    clearSyncImport,
    error,
  } = store;
  const [dialog, setDialog] = React.useState<DialogState>(null);
  const [deleting, setDeleting] = React.useState<DeleteState>(null);
  const [batchOpen, setBatchOpen] = React.useState(false);
  const activeLineClass = selectedLineClass ?? selectedLineGroup;
  const [batchLineClass, setBatchLineClass] = React.useState<WireWearLineClass>(activeLineClass);
  const [batchCycleDate, setBatchCycleDate] = React.useState('');
  const [batchRows, setBatchRows] = React.useState<BatchAddRecordRow[]>([newBatchRow()]);
  const [importOpen, setImportOpen] = React.useState(false);
  const [importPhase, setImportPhase] = React.useState<ExcelImportPhase>('select');
  const [importFile, setImportFile] = React.useState<File | null>(null);
  const [selectedSheets, setSelectedSheets] = React.useState<string[]>([]);
  const [importFilter, setImportFilter] = React.useState<ExcelImportStatusFilter>('all');
  const [databaseAnchor, setDatabaseAnchor] = React.useState<HTMLElement | null>(null);
  const [syncOpen, setSyncOpen] = React.useState(false);
  const [syncPhase, setSyncPhase] = React.useState<WireWearSyncDialogPhase>('select');
  const [syncFile, setSyncFile] = React.useState<File | null>(null);
  const [syncFilter, setSyncFilter] = React.useState<WireWearSyncStatusFilter>('all');
  const errorRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    if (!cycleWorkbench) {
      loadCycleWorkbench({ lineGroup: selectedLineGroup, lineClass: activeLineClass, summaryOnly: false });
    }
  }, [activeLineClass, cycleWorkbench, loadCycleWorkbench, selectedLineGroup]);

  React.useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => {
      if (hasPendingChanges) {
        event.preventDefault();
        event.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', guard);
    return () => window.removeEventListener('beforeunload', guard);
  }, [hasPendingChanges]);

  React.useEffect(() => {
    if (commitErrors.length) errorRef.current?.focus();
  }, [commitErrors]);

  React.useEffect(() => {
    if (!batchOpen || !batchCycleDate) return undefined;
    if (!batchRows.some(row => row.tensionLength.trim() || String(row.avgWearMin ?? '').trim())) {
      return undefined;
    }
    const timer = window.setTimeout(() => {
      previewCandidateRows({
        lineClass: batchLineClass,
        cycleDate: batchCycleDate,
        rows: batchRows.map((row, index) => ({
          ...row,
          tensionLengthCell: `A${index + 1}`,
          avgWearMinCell: `B${index + 1}`,
        })),
      });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [batchCycleDate, batchLineClass, batchOpen, batchRows, previewCandidateRows]);

  const columns = React.useMemo(
    () => sortWearWorkbenchColumns(cycleWorkbench?.summaryOnly ? [] : cycleWorkbench?.columns ?? []),
    [cycleWorkbench?.columns, cycleWorkbench?.summaryOnly],
  );
  const records = cycleWorkbench?.records ?? [];
  const catalog = React.useMemo(() => cycleWorkbench?.catalog ?? [], [cycleWorkbench?.catalog]);
  const selectedCatalogItem = React.useMemo(
    () => catalog.find(item => item.tensionLength === selectedTensionLength) ?? null,
    [catalog, selectedTensionLength],
  );
  const rows = React.useMemo(() => {
    const result = (committedSnapshot?.matrixRows ?? []).map(row => ({
      cycleDate: row.cycleDate,
      values: { ...row.values },
    }));
    for (const change of pendingChanges) {
      if (change.kind === 'delete_cell' || change.kind === 'delete_row') continue;
      let row = result.find(item => item.cycleDate === change.key.cycleDate);
      if (!row) {
        row = { cycleDate: change.key.cycleDate, values: {} };
        result.push(row);
      }
      row.values[change.key.tensionLength] = change.avgWearMin;
    }
    return result.sort((a, b) => b.cycleDate.localeCompare(a.cycleDate));
  }, [committedSnapshot, pendingChanges]);
  const newCycleDates = React.useMemo(() => {
    const committedDates = new Set((committedSnapshot?.matrixRows ?? []).map(row => row.cycleDate));
    return new Set(
      pendingChanges
        .filter(change => change.kind === 'add' && !committedDates.has(change.key.cycleDate))
        .map(change => change.kind === 'add' ? change.key.cycleDate : ''),
    );
  }, [committedSnapshot, pendingChanges]);

  const importRows = React.useMemo<ExcelImportPreviewRow[]>(() => {
    if (!historicalPreview) return [];
    const candidateRows = historicalPreview.candidates.map((candidate, index) => ({
      id: candidate.rowId || `candidate:${index}`,
      status: candidate.status,
      sheet: candidate.sourceSheet || '-',
      cell: candidate.sourceCell,
      track: candidate.track,
      tensionLength: candidate.key?.tensionLength ?? null,
      cycleDate: candidate.key?.cycleDate ?? null,
      importedValue: candidate.avgWearMin,
      existingValue: candidate.existingAvgWearMin,
      originalValue: candidate.originalValue,
      reason: candidate.issues.map(issue => issue.message).join('; ') || null,
      excluded: candidate.excluded,
    }));
    const diagnosticRows = historicalPreview.diagnostics.map((diagnostic, index) => ({
      id: `diagnostic:${index}`,
      status: 'error' as const,
      sheet: diagnostic.sheet,
      cell: diagnostic.cell,
      originalValue: diagnostic.originalValue,
      reason: diagnostic.message,
      excluded: historicalExcludedDiagnosticIds.includes(`diagnostic:${index}`),
    }));
    return [...candidateRows, ...diagnosticRows];
  }, [historicalExcludedDiagnosticIds, historicalPreview]);

  const sheetOptions = React.useMemo<WorkbookSheetOption[]>(() => (
    historicalDiscovery?.sheets.map(sheet => ({
      name: sheet.name,
      support: sheet.support,
      enabled: sheet.enabled,
      selected: selectedSheets.includes(sheet.name),
      reason: sheet.support === 'reserved'
        ? 'Reserved for future support'
        : sheet.support === 'ignored' ? 'Ignored' : null,
    })) ?? []
  ), [historicalDiscovery, selectedSheets]);
  const syncRows = React.useMemo<WireWearSyncPreviewRow[]>(() => (
    syncPreview?.rows.map(row => ({
      ...row,
      resolution: syncConflictDecisions[row.id] ?? null,
    })) ?? []
  ), [syncConflictDecisions, syncPreview]);

  const findRecord = (cycleDate: string, tensionLength: string): WearCycleRecord | undefined => (
    records.find(record => (
      record.key.cycleDate === cycleDate && record.key.tensionLength === tensionLength
    ))
  );
  const openAdd = (cycleDate = '', tensionLength = '') => {
    setDialog({ mode: 'add', cycleDate, tensionLength, avgWearMin: 0 });
  };
  const openEdit = (cycleDate: string, tensionLength: string, avgWearMin: number) => {
    setDialog({ mode: 'edit', cycleDate, tensionLength, avgWearMin });
  };

  const confirmDelete = () => {
    if (!deleting) return;
    if (deleting.kind === 'row') {
      stageDeleteRow(selectedLineGroup, deleting.cycleDate, activeLineClass);
    } else {
      const record = findRecord(deleting.cycleDate, deleting.tensionLength);
      stageDeleteCell({
        lineGroup: selectedLineGroup,
        lineClass: activeLineClass,
        cycleDate: deleting.cycleDate,
        tensionLength: deleting.tensionLength,
      }, record?.updatedAt ?? '');
    }
    setDeleting(null);
  };

  const closeBatch = () => {
    window.requestAnimationFrame(() => setBatchOpen(false));
    clearImportPreviews();
  };
  const openBatch = () => {
    setBatchLineClass(activeLineClass);
    setBatchCycleDate('');
    setBatchRows([newBatchRow()]);
    clearImportPreviews();
    setBatchOpen(true);
  };
  const updateBatchCell = (rowId: string, field: BatchAddRecordField, value: string) => {
    setBatchRows(current => current.map(row => (
      row.rowId === rowId ? { ...row, [field]: value } : row
    )));
  };
  const insertBatchRow = (afterRowId?: string) => {
    setBatchRows(current => {
      const next = [...current];
      const index = afterRowId ? next.findIndex(row => row.rowId === afterRowId) + 1 : next.length;
      next.splice(index < 0 ? next.length : index, 0, newBatchRow());
      return next;
    });
  };
  const pasteBatchRows = (startRowId: string, pasted: BatchAddPastedRow[]) => {
    setBatchRows(current => {
      const next = [...current];
      const startIndex = Math.max(0, next.findIndex(row => row.rowId === startRowId));
      pasted.forEach((value, offset) => {
        const index = startIndex + offset;
        if (!next[index]) next[index] = newBatchRow();
        next[index] = { ...next[index], ...value };
      });
      return next;
    });
  };
  const stageManualBatch = (preview: WearCandidatePreview) => {
    if (stageBatch(preview, 'manual')) closeBatch();
  };

  const closeImport = () => {
    window.requestAnimationFrame(() => setImportOpen(false));
    setImportPhase('select');
    setImportFile(null);
    setSelectedSheets([]);
    setImportFilter('all');
    clearImportPreviews();
  };
  const handleImportFile = async (file: File | null) => {
    setImportFile(file);
    setImportPhase('select');
    setImportFilter('all');
    if (!file) {
      setSelectedSheets([]);
      clearImportPreviews();
      return;
    }
    const discovery = await discoverHistoricalWorkbook(file);
    setSelectedSheets(
      discovery?.sheets
        .filter(sheet => sheet.enabled && sheet.selectedByDefault)
        .map(sheet => sheet.name) ?? [],
    );
  };
  const runImportPreview = async () => {
    if (!importFile) return;
    const preview = await previewHistoricalWorkbook(importFile, selectedSheets);
    if (preview) setImportPhase('preview');
  };
  const confirmHistoricalStage = () => {
    if (stageHistoricalPreview()) closeImport();
  };
  const downloadErrorReport = () => {
    const errorRows = importRows.filter(row => row.status === 'error');
    if (!errorRows.length) return;
    const csv = [
      ['Sheet', 'Cell', 'Original Value', 'Reason', 'Excluded'],
      ...errorRows.map(row => [
        row.sheet,
        row.cell ?? '',
        row.originalValue ?? '',
        row.reason ?? '',
        row.excluded ? 'Yes' : 'No',
      ]),
    ].map(row => row.map(csvCell).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'wire-wear-import-errors.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  };
  const exportDataPackage = async () => {
    setDatabaseAnchor(null);
    const blob = await exportSyncPackage();
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'wire-wear-data-package.json';
    anchor.click();
    URL.revokeObjectURL(url);
  };
  const exportHistoricalWearExcel = () => {
    if (!columns.length || !rows.length) return;
    const exportRows = rows
      .filter(row => !pendingChanges.some(change => (
        change.kind === 'delete_row' && change.cycleDate === row.cycleDate
      )))
      .map(row => {
        const values = { ...row.values };
        pendingChanges.forEach(change => {
          if (change.kind === 'delete_cell' && change.key.cycleDate === row.cycleDate) {
            values[change.key.tensionLength] = null;
          }
        });
        return { ...row, values };
      });
    const worksheet = XLSX.utils.aoa_to_sheet(buildHistoricalWearMatrix(columns, exportRows));
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Historical Avg Wear Min');
    XLSX.writeFile(workbook, `${activeLineClass}_Historical_Avg_Wear_Min.xlsx`);
  };
  const openSyncImport = () => {
    setDatabaseAnchor(null);
    setSyncPhase('select');
    setSyncFile(null);
    setSyncFilter('all');
    clearSyncImport();
    setSyncOpen(true);
  };
  const closeSyncImport = () => {
    setSyncOpen(false);
    setSyncPhase('select');
    setSyncFile(null);
    setSyncFilter('all');
    clearSyncImport();
  };
  const previewDataPackage = async () => {
    if (!syncFile) return;
    const preview = await previewSyncPackage(syncFile);
    if (preview) setSyncPhase('preview');
  };
  const confirmDataPackage = async () => {
    const summary = await applySyncPreview();
    if (summary) setSyncPhase('success');
  };

  return <Stack spacing={2}>
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack direction="row" spacing={1.25} alignItems="center" flexWrap="wrap">
        <TextField
          select
          size="small"
          label="Line"
          value={activeLineClass}
          disabled={hasPendingChanges}
          onChange={event => {
            const lineClass = event.target.value as WireWearLineClass;
            const lineGroup = lineGroupForClass(lineClass);
            setSelectedLineClass(lineClass);
            setSelectedTensionLength(null);
            loadCycleWorkbench({ lineGroup, lineClass, summaryOnly: false });
          }}
        >
          <MenuItem value="EAL">EAL</MenuItem>
          <MenuItem value="LMC">LMC</MenuItem>
          <MenuItem value="TML">TML</MenuItem>
        </TextField>
        <Autocomplete
          size="small"
          options={catalog}
          value={selectedCatalogItem}
          filterOptions={filterTensionLengths}
          getOptionLabel={option => option.tensionLength}
          isOptionEqualToValue={(option, value) => option.tensionLength === value.tensionLength}
          onChange={(_event, value) => {
            const tensionLength = value?.tensionLength ?? null;
            setSelectedTensionLength(tensionLength);
            void loadCycleWorkbench({
              lineGroup: selectedLineGroup,
              lineClass: activeLineClass,
              summaryOnly: false,
            });
          }}
          renderInput={params => (
            <TextField
              {...params}
              label="Tension Length"
              placeholder="Search catalog"
              helperText={selectedTensionLength ? 'Selected column highlighted' : `${catalog.length.toLocaleString()} tension lengths available`}
            />
          )}
          sx={{ width: { xs: '100%', sm: 280 } }}
        />
        <Button variant="contained" startIcon={<AddIcon />} onClick={openBatch} disabled={isLoading}>
          Add Records
        </Button>
        <Button variant="outlined" startIcon={<UploadFileIcon />} onClick={() => setImportOpen(true)} disabled={isLoading}>
          Import Excel
        </Button>
        <Box sx={{ flex: 1 }} />
        <Button
          variant="outlined"
          startIcon={<StorageIcon />}
          onClick={event => setDatabaseAnchor(event.currentTarget)}
          aria-haspopup="menu"
          aria-expanded={Boolean(databaseAnchor)}
        >
          Database
        </Button>
        <Menu anchorEl={databaseAnchor} open={Boolean(databaseAnchor)} onClose={() => setDatabaseAnchor(null)}>
          <MenuItem onClick={exportDataPackage}>Export Data Package</MenuItem>
          <MenuItem onClick={openSyncImport}>Import Data Package</MenuItem>
        </Menu>
        <Button variant="contained" onClick={saveChanges} disabled={!hasPendingChanges || isSaving}>
          Save Changes
        </Button>
      </Stack>
    </Paper>

    {error && !commitErrors.length && <Alert severity="error">{error}</Alert>}
    <Box>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'center' }} sx={{ mb: 1 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Historical Avg Wear Min</Typography>
        <Stack direction="row" spacing={1.25} useFlexGap flexWrap="wrap" aria-label="Pending change legend" sx={{ color: 'warning.dark' }}>
          <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}><AddCircleOutlineIcon sx={{ fontSize: 16 }} /><Typography variant="caption" sx={{ fontWeight: 700 }}>Add</Typography></Box>
          <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}><EditOutlinedIcon sx={{ fontSize: 16 }} /><Typography variant="caption" sx={{ fontWeight: 700 }}>Edit</Typography></Box>
          <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}><DeleteOutlineIcon sx={{ fontSize: 16 }} /><Typography variant="caption" sx={{ fontWeight: 700 }}>Delete</Typography></Box>
        </Stack>
        <Button
          size="small"
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={exportHistoricalWearExcel}
          disabled={!columns.length || !rows.length}
          sx={{ ml: { sm: 'auto' } }}
        >
          Export Excel
        </Button>
      </Stack>
      <WearHistoryPivotTable
        columns={columns}
        rows={rows}
        selectedTensionLength={selectedTensionLength}
        pendingChanges={pendingChanges}
        newCycleDates={newCycleDates}
        onAdd={openAdd}
        onEdit={openEdit}
        onDeleteCell={(cycleDate, tensionLength) => setDeleting({ kind: 'cell', cycleDate, tensionLength })}
        onDeleteRow={cycleDate => setDeleting({ kind: 'row', cycleDate })}
      />
    </Box>
    <Box>
      <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>Latest Summary</Typography>
      <WearLatestSummaryTable
        columns={columns}
        rows={cycleWorkbench?.latestSummary ?? []}
        selectedTensionLength={selectedTensionLength}
      />
    </Box>

    {hasPendingChanges && (
      <Paper variant="outlined" sx={theme => ({
        p: 1.5,
        borderColor: 'warning.main',
        bgcolor: alpha(theme.palette.warning.main, theme.palette.mode === 'dark' ? 0.2 : 0.1),
      })}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'center' }}>
          <Typography role="status" aria-live="polite" variant="body2" sx={{ flex: 1, fontWeight: 700 }}>
            待處理：新增 {changeSummary.added}、更新 {changeSummary.edited}、刪除儲存格 {changeSummary.deletedCells}、刪除整列 {changeSummary.deletedRows}
          </Typography>
          <Button onClick={discardChanges}>Discard Changes</Button>
        </Stack>
      </Paper>
    )}
    {commitErrors.length > 0 && (
      <Alert ref={errorRef} tabIndex={-1} severity="error" role="alert">
        {commitErrors.join('. ')}
      </Alert>
    )}

    <BatchAddRecordsDialog
      open={batchOpen}
      lineClass={batchLineClass}
      cycleDate={batchCycleDate}
      rows={batchRows}
      preview={candidatePreview}
      previewError={previewError}
      isPreviewing={isPreviewingCandidates}
      isSubmitting={false}
      onLineClassChange={setBatchLineClass}
      onCycleDateChange={setBatchCycleDate}
      onCellChange={updateBatchCell}
      onInsertRow={insertBatchRow}
      onDeleteRow={rowId => setBatchRows(current => (
        current.length === 1 ? [newBatchRow()] : current.filter(row => row.rowId !== rowId)
      ))}
      onPasteRows={pasteBatchRows}
      onStageAll={stageManualBatch}
      onClose={closeBatch}
    />

    <ExcelWearImportDialog
      open={importOpen}
      phase={importPhase}
      fileName={importFile?.name ?? null}
      sheets={sheetOptions}
      sheetSummaries={historicalPreview?.sheetSummaries ?? []}
      rows={importRows}
      filter={importFilter}
      error={previewError}
      isLoading={isPreviewingCandidates}
      isSubmitting={false}
      onFileSelect={handleImportFile}
      onSheetToggle={(sheetName, selected) => setSelectedSheets(current => (
        selected ? [...new Set([...current, sheetName])] : current.filter(name => name !== sheetName)
      ))}
      onPreview={runImportPreview}
      onPhaseChange={setImportPhase}
      onFilterChange={setImportFilter}
      onExcludeError={setHistoricalErrorExcluded}
      onDownloadErrorReport={downloadErrorReport}
      onConfirmAndStage={confirmHistoricalStage}
      onClose={closeImport}
    />

    <WireWearSyncImportDialog
      open={syncOpen}
      phase={syncPhase}
      fileName={syncFile?.name ?? null}
      packageInfo={syncPreview?.packageInfo ?? null}
      rows={syncRows}
      filter={syncFilter}
      warnings={syncPreview?.warnings ?? []}
      guardState={hasPendingChanges ? 'pending_changes' : syncGuardState}
      guardMessage={hasPendingChanges ? null : syncGuardMessage}
      isPreviewing={isPreviewingSync}
      isApplying={isApplyingSync}
      successSummary={syncApplySummary}
      onFileSelect={file => {
        setSyncFile(file);
        setSyncPhase('select');
        setSyncFilter('all');
        clearSyncImport();
      }}
      onPreview={previewDataPackage}
      onFilterChange={setSyncFilter}
      onResolveConflict={resolveSyncConflict}
      onConfirmImport={confirmDataPackage}
      onStartOver={() => {
        setSyncFile(null);
        setSyncPhase('select');
        setSyncFilter('all');
        clearSyncImport();
      }}
      onClose={closeSyncImport}
    />

    {dialog && (
      <WireWearRecordDialog
        open
        mode={dialog.mode}
        lineGroup={selectedLineGroup}
        initialValue={dialog}
        catalog={cycleWorkbench?.catalog ?? []}
        onClose={() => setDialog(null)}
        onStage={value => {
          const key = {
            lineGroup: value.lineGroup,
            lineClass: activeLineClass,
            cycleDate: value.cycleDate,
            tensionLength: value.tensionLength,
          };
          if (dialog.mode === 'add') stageAdd(key, value.avgWearMin);
          else stageEdit(key, value.avgWearMin, findRecord(value.cycleDate, value.tensionLength)?.updatedAt ?? '');
          setDialog(null);
        }}
      />
    )}
    <Dialog
      open={Boolean(deleting)}
      onClose={() => setDeleting(null)}
      TransitionProps={{ timeout: 0 }}
      aria-labelledby="delete-wear-record-title"
    >
      <DialogTitle id="delete-wear-record-title">Confirm deletion</DialogTitle>
      <DialogContent>
        <Typography>
          {deleting?.kind === 'row'
            ? `Delete all records for ${deleting.cycleDate}?`
            : `Delete ${deleting?.tensionLength} on ${deleting?.cycleDate}?`}
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setDeleting(null)}>Cancel</Button>
        <Button color="error" variant="contained" onClick={confirmDelete}>Confirm</Button>
      </DialogActions>
    </Dialog>
  </Stack>;
};

export default WearRecordsPanel;
