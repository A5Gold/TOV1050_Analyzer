/**
 * Database Record View
 * =====================
 * Main view for Database Record Module - Repeated Exception & Follow-up Action
 * 
 * NOTE: Sub-module 1 (Exception Records) has been REMOVED as of 2026-01-31.
 * This view now only shows Sub-module 2 (Repeated Exception Records).
 * 
 * Architecture (Phase 10.10-C):
 * - Tab architecture: Split by TOV1050 line via LineTabPanel
 * - Section sub-tabs inside LineTabPanel (Mainline, PL, TKS)
 * - FilterPanel inside LineTabPanel (collapsible, independent state per tab)
 * - Header bar with Export, Import, Batch Edit, Save buttons
 * - DataGrid with editable workflow fields (38 columns supported)
 * 
 * Version: 3.0
 * Date: 2026-02-06
 * 
 * Changes:
 * - Phase 10.10-C: Moved filter panel into LineTabPanel/FilterPanel for
 *   independent filter state per tab. Removed filter state from this view.
 */

import React, { useState, useRef, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Stack,
  TextField,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Snackbar,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Checkbox,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import FileUploadIcon from '@mui/icons-material/FileUpload';
import StorageIcon from '@mui/icons-material/Storage';
import SaveIcon from '@mui/icons-material/Save';
import UndoIcon from '@mui/icons-material/Undo';

import { useDatabaseStore } from '../store/useDatabaseStore';
import RepeatedRecordTable from '../components/DatabaseRecord/RepeatedRecordTable';
import LineTabPanel from '../components/DatabaseRecord/LineTabPanel';
import ColumnManagementMenu from '../components/DatabaseRecord/ColumnManagementMenu';
// BUG 10.7-1 FIX: ErrorBoundary to gracefully handle DataGrid crashes
import ErrorBoundary, { DataGridErrorFallback } from '../components/common/ErrorBoundary';
import { SavedRepeatedRecord } from '../types/api';
import { GridColumnVisibilityModel } from '@mui/x-data-grid';
import * as XLSX from 'xlsx';
import { fillDataRegionSx, scrollablePageSx } from '../utils/pageLayout';

// =============================================================================
// CONSTANTS
// =============================================================================

// Batch edit dropdown options
const ACTION_OPTIONS = [
  'Pending',
  'Keep monitoring',
  'Calculation',
  'Verify on site',
  'Verify by next 1st line PM cycle',
  'No action required (Overshoot)',
  'No action required (Verified within 1 year)',
  'No action required (Overlapping area)',
];

// =============================================================================
// COMPONENT
// =============================================================================

const DatabaseRecordView: React.FC = () => {
  // Store
  const {
    repeatedRecords,
    repeatedRecordsLoading,
    repeatedRecordsTotal,
    repeatedRecordsError,
    exportRepeatedRecords,
    importRepeatedRecords,
    isImporting,
    // Feature-002: Batch save state and actions
    hasPendingChanges,
    pendingChanges,
    batchSaveChanges,
    discardChanges,
    isBatchSaving,
    queueChange,
  } = useDatabaseStore();
  
  // File input ref for import
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Phase 10.10-C: Filter state moved to FilterPanel (independent per tab).
  // DatabaseRecordView no longer manages filter state directly.

  // Toast state
  const [toast, setToast] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({ open: false, message: '', severity: 'info' });

  // Export loading state
  const [exporting, setExporting] = useState(false);

  // Column visibility model (for ColumnManagementMenu)
  const [columnVisibility, setColumnVisibility] = useState<GridColumnVisibilityModel>({});

  // Bug 6: Auto-fit trigger counter
  const [autoFitTrigger, setAutoFitTrigger] = useState(0);

  // Selected rows (for batch operations) — updated by RepeatedRecordTable's custom checkbox
  const [selectedRows, setSelectedRows] = useState<SavedRepeatedRecord[]>([]);

  // Feature-002: Save confirmation dialog state
  const [saveConfirmOpen, setSaveConfirmOpen] = useState(false);

  // Batch Edit Dialog State
  const [batchEditDialogOpen, setBatchEditDialogOpen] = useState(false);
  const [batchEditValues, setBatchEditValues] = useState<{
    action: string | null;
    check_date: string | null;
    checked_by: string | null;
    check_result: string | null;
    remarks: string | null;
    verify_deadline: string | null;
    verify_date: string | null;
    verify_result: string | null;
    verified_by: string | null;
    adjust_deadline: string | null;
    adjust_date: string | null;
    adjust_result: string | null;
    adjusted_by: string | null;
    reoccurrence_id: string | null;
  }>({
    action: null,
    check_date: null,
    checked_by: null,
    check_result: null,
    remarks: null,
    verify_deadline: null,
    verify_date: null,
    verify_result: null,
    verified_by: null,
    adjust_deadline: null,
    adjust_date: null,
    adjust_result: null,
    adjusted_by: null,
    reoccurrence_id: null,
  });
  
  // Track which fields are selected for update
  const [batchEditFields, setBatchEditFields] = useState<Set<string>>(new Set());

  // =========================================================================
  // EFFECTS
  // =========================================================================

  // Phase 10.10-C: Initial data load moved to FilterPanel (triggers on mount).
  // DatabaseRecordView no longer calls fetchRepeatedRecords on mount.

  // =========================================================================
  // HANDLERS
  // =========================================================================

  // Feature-002: Batch save handlers
  const handleSaveEditClick = () => {
    if (pendingChanges.size > 0) {
      setSaveConfirmOpen(true);
    } else {
      setToast({ open: true, message: 'No pending changes to save', severity: 'info' });
    }
  };

  const handleConfirmSave = async () => {
    setSaveConfirmOpen(false);
    const result = await batchSaveChanges();
    setToast({
      open: true,
      message: result.message,
      severity: result.success ? 'success' : 'error',
    });
  };

  const handleDiscardChanges = () => {
    if (pendingChanges.size > 0) {
      if (window.confirm(`Discard ${pendingChanges.size} pending changes?`)) {
        discardChanges();
        setToast({ open: true, message: 'Changes discarded', severity: 'info' });
      }
    }
  };

  // Phase 10.10-C: handleClearFilters and handleLineTabChange removed.
  // Filter state and fetching are now managed by FilterPanel inside LineTabPanel.

  // Phase 10.10-D: Custom checkbox selection handler from RepeatedRecordTable
  const handleSelectionChange = useCallback((newSelectedIds: Set<number>) => {
    const selected = repeatedRecords.filter((r) => newSelectedIds.has(r.record_id));
    setSelectedRows(selected);
  }, [repeatedRecords]);

  // Handler for batch delete (ColumnManagementMenu)
  const handleBatchDelete = useCallback(async (recordIds: number[]) => {
    const { deleteRepeatedRecord, fetchRepeatedRecords } = useDatabaseStore.getState();
    for (const id of recordIds) {
      await deleteRepeatedRecord(id);
    }
    // Refresh after deletion using current store filters
    await fetchRepeatedRecords();
    setSelectedRows([]);
    setToast({ open: true, message: `Deleted ${recordIds.length} records`, severity: 'success' });
  }, []);

  // Batch Edit Handlers
  const handleOpenBatchEdit = () => {
    setBatchEditValues({
      action: null,
      check_date: null,
      checked_by: null,
      check_result: null,
      remarks: null,
      verify_deadline: null,
      verify_date: null,
      verify_result: null,
      verified_by: null,
      adjust_deadline: null,
      adjust_date: null,
      adjust_result: null,
      adjusted_by: null,
      reoccurrence_id: null,
    });
    setBatchEditFields(new Set());
    setBatchEditDialogOpen(true);
  };

  const handleBatchEditFieldToggle = (field: string) => {
    setBatchEditFields((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(field)) {
        newSet.delete(field);
      } else {
        newSet.add(field);
      }
      return newSet;
    });
  };

  const handleBatchEditValueChange = (field: string, value: string | null) => {
    setBatchEditValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleConfirmBatchEdit = () => {
    if (batchEditFields.size === 0) {
      // Note: Toast severity type may not include 'warning', use 'info' as fallback
      setToast({ open: true, message: 'No fields selected for update', severity: 'info' });
      return;
    }

    const updates: any = {};
    batchEditFields.forEach((field) => {
      updates[field] = (batchEditValues as any)[field];
    });

    // Queue changes for all selected rows
    selectedRows.forEach((row) => {
      queueChange(row.record_id, updates);
    });

    setBatchEditDialogOpen(false);
    setToast({ 
      open: true, 
      message: `Queued updates for ${selectedRows.length} records. Click "Save Edit" to commit.`, 
      severity: 'info' 
    });
    
    // Clear selection after batch edit? Maybe keep it for further actions.
    // setRowSelectionModel([]);
    // setSelectedRows([]);
  };

  // Handler for export selected records (ColumnManagementMenu)
  const handleExportSelected = useCallback((records: SavedRepeatedRecord[]) => {
    // Create a simple CSV/Excel export
    import('xlsx').then((XLSX) => {
      const worksheet = XLSX.utils.json_to_sheet(records);
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, 'Exported Records');
      XLSX.writeFile(workbook, `exported_records_${new Date().toISOString().slice(0, 10)}.xlsx`);
      setToast({ open: true, message: `Exported ${records.length} records`, severity: 'success' });
    });
  }, []);

  // Handler for auto-fit columns (placeholder - DataGrid handles this)
  const handleAutoFitColumns = useCallback(() => {
    setAutoFitTrigger((prev) => prev + 1);
    setToast({ open: true, message: 'Column widths auto-adjusted', severity: 'info' });
  }, []);

  const handleExport = async () => {
    setExporting(true);
    setToast({ open: true, message: 'Generating export file...', severity: 'info' });

    try {
      // Phase 10.10-C: Use store's current repeatedFilters (set by FilterPanel)
      const { repeatedFilters } = useDatabaseStore.getState();
      await exportRepeatedRecords(repeatedFilters);
      setToast({ open: true, message: 'Follow-up action list exported successfully!', severity: 'success' });
    } catch (error) {
      console.error('Export failed:', error);
      setToast({ open: true, message: 'Export failed. Please try again.', severity: 'error' });
    } finally {
      setExporting(false);
    }
  };

  // Import handler
  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleImportFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setToast({ open: true, message: 'Parsing Excel file...', severity: 'info' });

    try {
      // Read Excel file
      const data = await file.arrayBuffer();
      const workbook = XLSX.read(data);
      const sheetName = workbook.SheetNames[0];
      const worksheet = workbook.Sheets[sheetName];
      const jsonData = XLSX.utils.sheet_to_json(worksheet) as Record<string, unknown>[];

      if (jsonData.length === 0) {
        setToast({ open: true, message: 'No data found in Excel file', severity: 'error' });
        return;
      }

      // Use first record to determine line/track/date or use defaults
      const firstRecord = jsonData[0];
      const defaultLine = (firstRecord.line as string) || 'AEL';
      const defaultTrack = (firstRecord.track as string) || 'UT';
      const defaultDate = (firstRecord.date_str as string) || new Date().toISOString().slice(0, 10).replace(/-/g, '');

      setToast({ open: true, message: 'Importing records...', severity: 'info' });

      // Call import API
      const result = await importRepeatedRecords({
        records: jsonData as Record<string, any>[],
        line: defaultLine,
        track: defaultTrack,
        date_str: defaultDate,
      });

      setToast({
        open: true,
        message: `Import complete: ${result.created_count} created, ${result.updated_count} updated`,
        severity: 'success'
      });

      // Refresh data using current store filters
      const { fetchRepeatedRecords } = useDatabaseStore.getState();
      await fetchRepeatedRecords();
    } catch (error: any) {
      console.error('Import failed:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Import failed';
      setToast({ open: true, message: errorMsg, severity: 'error' });
    } finally {
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleCloseToast = () => {
    setToast((prev) => ({ ...prev, open: false }));
  };

  // =========================================================================
  // COMPUTED VALUES
  // =========================================================================

  const currentLoading = repeatedRecordsLoading || isImporting;
  const currentTotal = repeatedRecordsTotal;
  const currentError = repeatedRecordsError;
  const loadedCount = repeatedRecords.length;
  const countLabel = currentTotal > loadedCount
    ? `${currentTotal.toLocaleString('en-US')} total · ${loadedCount.toLocaleString('en-US')} loaded`
    : `${currentTotal.toLocaleString('en-US')} records`;

  // =========================================================================
  // RENDER
  // =========================================================================

  return (
    <Box sx={{
      ...scrollablePageSx,
      height: 'auto',
      minHeight: '100%',
      overflow: 'visible',
    }}>
      {/* Hidden file input for import */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        accept=".xlsx,.xls"
        onChange={handleImportFile}
      />

      {/* Header */}
      <Paper sx={{ p: 1.5, flexShrink: 0 }}>
        <Stack
          direction={{ xs: 'column', lg: 'row' }}
          alignItems={{ xs: 'stretch', lg: 'center' }}
          justifyContent="space-between"
          gap={2}
        >
          <Stack direction="row" alignItems="center" spacing={0} gap={2} flexWrap="wrap">
            <StorageIcon color="primary" />
            <Typography variant="h6" fontWeight="600">
              Database Record
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Repeated Exception & Follow-up Action
            </Typography>
            <Chip
              label={countLabel}
              size="small"
              color={currentTotal > 0 ? 'primary' : 'default'}
              variant="outlined"
            />
          </Stack>
          <Stack
            direction="row"
            spacing={0}
            gap={1}
            flexWrap="wrap"
            justifyContent={{ xs: 'flex-start', lg: 'flex-end' }}
          >
            <ColumnManagementMenu
              selectedRows={selectedRows}
              allRecords={repeatedRecords}
              columnVisibility={columnVisibility}
              onColumnVisibilityChange={setColumnVisibility}
              onDeleteRecords={handleBatchDelete}
              onExportRecords={handleExportSelected}
              onAutoFitColumns={handleAutoFitColumns}
              loading={currentLoading}
            />
            
            {/* Batch Edit Button - Selection based (only shown when rows selected) */}
            {selectedRows.length > 0 && (
              <Button
                size="small"
                variant="outlined"
                color="primary"
                startIcon={<EditIcon />}
                onClick={handleOpenBatchEdit}
                disabled={isBatchSaving}
              >
                Batch Edit ({selectedRows.length})
              </Button>
            )}
            
            {/* Bug 10.9.1-5 FIX: Batch Edit by Filter - Alternative to row selection */}
            {/* Always visible when there are filtered records */}
            {repeatedRecords.length > 0 && (
              <Button
                size="small"
                variant="outlined"
                color="secondary"
                startIcon={<EditIcon />}
                onClick={() => {
                  // Use all currently displayed (filtered) records for batch edit
                  setSelectedRows(repeatedRecords);
                  handleOpenBatchEdit();
                }}
                disabled={isBatchSaving}
                title={`Batch edit the ${repeatedRecords.length} records currently loaded in the table`}
              >
                Batch Edit Loaded ({repeatedRecords.length})
              </Button>
            )}

            {/* Feature-002: Save Edit button (replaces immediate save) */}
            <Button
              size="small"
              variant="contained"
              color="success"
              startIcon={isBatchSaving ? <CircularProgress size={16} color="inherit" /> : <SaveIcon />}
              onClick={handleSaveEditClick}
              disabled={isBatchSaving || !hasPendingChanges}
            >
              Save Edit {hasPendingChanges && `(${pendingChanges.size})`}
            </Button>
            {/* Feature-002: Discard Changes button */}
            {hasPendingChanges && (
              <Button
                size="small"
                variant="outlined"
                color="warning"
                startIcon={<UndoIcon />}
                onClick={handleDiscardChanges}
                disabled={isBatchSaving}
              >
                Discard
              </Button>
            )}
            <Button
              size="small"
              variant="outlined"
              color="secondary"
              startIcon={isImporting ? <CircularProgress size={16} /> : <FileUploadIcon />}
              onClick={handleImportClick}
              disabled={isImporting || currentLoading || hasPendingChanges}
            >
              Import
            </Button>
            <Button
              size="small"
              variant="contained"
              startIcon={exporting ? <CircularProgress size={16} color="inherit" /> : <FileDownloadIcon />}
              onClick={handleExport}
              disabled={exporting || currentLoading || currentTotal === 0}
            >
              Export Follow-up List
            </Button>
          </Stack>
        </Stack>
      </Paper>

      {/* Phase 10.10-C: Filter panel moved into LineTabPanel/FilterPanel */}

      {/* Error Alert */}
      {currentError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {currentError}
        </Alert>
      )}

      {/* Data Table with Line Tabs */}
      {/* BUG 10.7-1 FIX: Wrap with ErrorBoundary to gracefully handle DataGrid crashes */}
      {/* BUG 10.9.1-2 FIX: Add minHeight to prevent "empty height" warning on window resize */}
      <Box sx={{
        ...fillDataRegionSx,
        flex: '0 0 auto',
        overflow: 'visible',
      }}>
        <ErrorBoundary 
          FallbackComponent={DataGridErrorFallback}
          resetKeys={[repeatedRecords.length, repeatedRecordsLoading]}
          onError={(error, errorInfo) => {
            console.error('[DatabaseRecordView] DataGrid error:', error);
            console.error('[DatabaseRecordView] Component stack:', errorInfo.componentStack);
          }}
        >
          <LineTabPanel
            records={repeatedRecords}
            loading={repeatedRecordsLoading}
          >
            {(filteredRecords: SavedRepeatedRecord[]) => (
              <Paper sx={{ height: { xs: 520, sm: 'calc(100vh - 220px)' }, minHeight: 520, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <RepeatedRecordTable
                  data={filteredRecords}
                  loading={repeatedRecordsLoading}
                  onSelectionChange={handleSelectionChange}
                  columnVisibility={columnVisibility}
                  onColumnVisibilityChange={setColumnVisibility}
                  autoFitTrigger={autoFitTrigger}
                  pendingIds={new Set(pendingChanges.keys())}
                  selectedRowIds={new Set(selectedRows.map((r) => r.record_id))}
                />
              </Paper>
            )}
          </LineTabPanel>
        </ErrorBoundary>
      </Box>

      {/* Batch Edit Dialog */}
      <Dialog open={batchEditDialogOpen} onClose={() => setBatchEditDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Batch Edit {selectedRows.length} Records</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Select fields to update and provide new values. Only selected fields will be updated.
          </DialogContentText>
          <Grid container spacing={2}>
            {/* Action */}
            <Grid item xs={12} sm={6}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('action')} 
                  onChange={() => handleBatchEditFieldToggle('action')} 
                />
                <FormControl fullWidth size="small" disabled={!batchEditFields.has('action')}>
                  <InputLabel>Action</InputLabel>
                  <Select
                    value={batchEditValues.action || ''}
                    label="Action"
                    onChange={(e) => handleBatchEditValueChange('action', e.target.value)}
                  >
                    {ACTION_OPTIONS.map((opt) => (
                      <MenuItem key={opt} value={opt}>{opt}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Stack>
            </Grid>
            {/* Check Date */}
            <Grid item xs={12} sm={6}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('check_date')} 
                  onChange={() => handleBatchEditFieldToggle('check_date')} 
                />
                <TextField
                  fullWidth
                  size="small"
                  label="Check Date"
                  type="date"
                  InputLabelProps={{ shrink: true }}
                  value={batchEditValues.check_date || ''}
                  onChange={(e) => handleBatchEditValueChange('check_date', e.target.value)}
                  disabled={!batchEditFields.has('check_date')}
                />
              </Stack>
            </Grid>
            {/* Checked By */}
            <Grid item xs={12} sm={6}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('checked_by')} 
                  onChange={() => handleBatchEditFieldToggle('checked_by')} 
                />
                <TextField
                  fullWidth
                  size="small"
                  label="Checked By"
                  value={batchEditValues.checked_by || ''}
                  onChange={(e) => handleBatchEditValueChange('checked_by', e.target.value)}
                  disabled={!batchEditFields.has('checked_by')}
                />
              </Stack>
            </Grid>
            {/* Check Result */}
            <Grid item xs={12} sm={6}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('check_result')} 
                  onChange={() => handleBatchEditFieldToggle('check_result')} 
                />
                <TextField
                  fullWidth
                  size="small"
                  label="Check Result"
                  value={batchEditValues.check_result || ''}
                  onChange={(e) => handleBatchEditValueChange('check_result', e.target.value)}
                  disabled={!batchEditFields.has('check_result')}
                />
              </Stack>
            </Grid>
            {/* Verify Deadline */}
            <Grid item xs={12} sm={6}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('verify_deadline')} 
                  onChange={() => handleBatchEditFieldToggle('verify_deadline')} 
                />
                <TextField
                  fullWidth
                  size="small"
                  label="Verify Deadline"
                  type="date"
                  InputLabelProps={{ shrink: true }}
                  value={batchEditValues.verify_deadline || ''}
                  onChange={(e) => handleBatchEditValueChange('verify_deadline', e.target.value)}
                  disabled={!batchEditFields.has('verify_deadline')}
                />
              </Stack>
            </Grid>
            {/* Verify Date */}
            <Grid item xs={12} sm={6}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('verify_date')} 
                  onChange={() => handleBatchEditFieldToggle('verify_date')} 
                />
                <TextField
                  fullWidth
                  size="small"
                  label="Verify Date"
                  type="date"
                  InputLabelProps={{ shrink: true }}
                  value={batchEditValues.verify_date || ''}
                  onChange={(e) => handleBatchEditValueChange('verify_date', e.target.value)}
                  disabled={!batchEditFields.has('verify_date')}
                />
              </Stack>
            </Grid>
            {/* Verify Result */}
            <Grid item xs={12} sm={6}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('verify_result')} 
                  onChange={() => handleBatchEditFieldToggle('verify_result')} 
                />
                <TextField
                  fullWidth
                  size="small"
                  label="Verify Result"
                  value={batchEditValues.verify_result || ''}
                  onChange={(e) => handleBatchEditValueChange('verify_result', e.target.value)}
                  disabled={!batchEditFields.has('verify_result')}
                />
              </Stack>
            </Grid>
            {/* Verified By */}
            <Grid item xs={12} sm={6}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('verified_by')} 
                  onChange={() => handleBatchEditFieldToggle('verified_by')} 
                />
                <TextField
                  fullWidth
                  size="small"
                  label="Verified By"
                  value={batchEditValues.verified_by || ''}
                  onChange={(e) => handleBatchEditValueChange('verified_by', e.target.value)}
                  disabled={!batchEditFields.has('verified_by')}
                />
              </Stack>
            </Grid>
            {/* Adjust Deadline */}
            <Grid item xs={12} sm={6}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('adjust_deadline')} 
                  onChange={() => handleBatchEditFieldToggle('adjust_deadline')} 
                />
                <TextField
                  fullWidth
                  size="small"
                  label="Adjust Deadline"
                  type="date"
                  InputLabelProps={{ shrink: true }}
                  value={batchEditValues.adjust_deadline || ''}
                  onChange={(e) => handleBatchEditValueChange('adjust_deadline', e.target.value)}
                  disabled={!batchEditFields.has('adjust_deadline')}
                />
              </Stack>
            </Grid>
            {/* Adjust Date */}
            <Grid item xs={12} sm={6}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('adjust_date')} 
                  onChange={() => handleBatchEditFieldToggle('adjust_date')} 
                />
                <TextField
                  fullWidth
                  size="small"
                  label="Adjust Date"
                  type="date"
                  InputLabelProps={{ shrink: true }}
                  value={batchEditValues.adjust_date || ''}
                  onChange={(e) => handleBatchEditValueChange('adjust_date', e.target.value)}
                  disabled={!batchEditFields.has('adjust_date')}
                />
              </Stack>
            </Grid>
            {/* Adjust Result */}
            <Grid item xs={12} sm={6}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('adjust_result')} 
                  onChange={() => handleBatchEditFieldToggle('adjust_result')} 
                />
                <TextField
                  fullWidth
                  size="small"
                  label="Adjust Result"
                  value={batchEditValues.adjust_result || ''}
                  onChange={(e) => handleBatchEditValueChange('adjust_result', e.target.value)}
                  disabled={!batchEditFields.has('adjust_result')}
                />
              </Stack>
            </Grid>
            {/* Adjusted By */}
            <Grid item xs={12} sm={6}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('adjusted_by')} 
                  onChange={() => handleBatchEditFieldToggle('adjusted_by')} 
                />
                <TextField
                  fullWidth
                  size="small"
                  label="Adjusted By"
                  value={batchEditValues.adjusted_by || ''}
                  onChange={(e) => handleBatchEditValueChange('adjusted_by', e.target.value)}
                  disabled={!batchEditFields.has('adjusted_by')}
                />
              </Stack>
            </Grid>
            {/* Remarks */}
            <Grid item xs={12}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Checkbox 
                  checked={batchEditFields.has('remarks')} 
                  onChange={() => handleBatchEditFieldToggle('remarks')} 
                />
                <TextField
                  fullWidth
                  size="small"
                  label="Remarks"
                  value={batchEditValues.remarks || ''}
                  onChange={(e) => handleBatchEditValueChange('remarks', e.target.value)}
                  disabled={!batchEditFields.has('remarks')}
                />
              </Stack>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBatchEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleConfirmBatchEdit} variant="contained" color="primary">
            Apply Updates
          </Button>
        </DialogActions>
      </Dialog>

      {/* Toast Notification */}
      {/* Feature-002: Save Confirmation Dialog */}
      <Dialog
        open={saveConfirmOpen}
        onClose={() => setSaveConfirmOpen(false)}
      >
        <DialogTitle>Confirm Save</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Save {pendingChanges.size} pending changes to the database?
            This will update the <strong>last_updated</strong> timestamp for all modified records.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveConfirmOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleConfirmSave} 
            variant="contained" 
            color="success"
            startIcon={isBatchSaving ? <CircularProgress size={16} /> : <SaveIcon />}
            disabled={isBatchSaving}
          >
            {isBatchSaving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={toast.open}
        autoHideDuration={6000}
        onClose={handleCloseToast}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseToast} severity={toast.severity} sx={{ width: '100%' }}>
          {toast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default DatabaseRecordView;
