/**
 * Repeated Record Table Component
 * =================================
 * DataGrid for Sub-module 2: Saved Repeated Exception Records & Follow-up Actions
 * 
 * Features:
 * - Display saved repeated exception records from database
 * - Editable workflow fields including Initial Check, Site Verification, Final Adjustment
 * - 9 new workflow columns: reoccurrence_id, verify_deadline, verify_date, verify_result, 
 *   verified_by, adjust_deadline, adjust_date, adjust_result, adjusted_by
 * - Column grouping matching ComparisonDataGrid structure
 * - Sorting, filtering, pagination
 * - Delete functionality
 * 
 * Version: 3.0
 * Date: 2026-02-06
 * 
 * Bug Fixes:
 * - Bug 10.6-1: Fixed DataGrid v8 crash when rowSelectionModel/rows undefined
 * - Bug 10.7-1: Fixed "currentSelection.ids is not iterable" error
 * - Bug 10.9-3: DISABLED native checkboxSelection to prevent MUI DataGrid v8 crash
 * - Phase 10.10-D: Added custom checkbox column for multi-select (replaces MUI
 *   checkboxSelection). Uses local Set<number> state with onSelectionChange callback.
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  Box,
  IconButton,
  Tooltip,
  Typography,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  CircularProgress,
  LinearProgress,
  Select,
  MenuItem,
  TextField,
  Divider,
  Snackbar,
  Alert,
  Checkbox,
} from '@mui/material';
import {
  DataGrid,
  GridColDef,
  GridColumnGroupingModel,
  GridRenderCellParams,
  GridRowParams,
  GridRenderEditCellParams,
  useGridApiContext,
  useGridApiRef,
  GridColumnVisibilityModel,
  GridOverlay,
  // BUG 10.9-3: GridRowSelectionModel removed - checkbox selection disabled
  GridFooterContainer,
  GridPagination,
} from '@mui/x-data-grid';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';

import { SavedRepeatedRecord, UpdateRepeatedRecordRequest } from '../../types/api';
import { useDatabaseStore } from '../../store/useDatabaseStore';
import { formatDateDisplay, formatDateTimeDisplay } from '../../utils/dateFormatter';
import { getActionStyle } from '../../utils/actionStyles';
import { getRowClassName as sharedGetRowClassName, rowStylesSx } from '../../utils/rowStyles';

// =============================================================================
// PROPS INTERFACE
// =============================================================================

interface RepeatedRecordTableProps {
  data: SavedRepeatedRecord[];
  loading: boolean;
  onRowClick?: (record: SavedRepeatedRecord) => void;
  /** Phase 10.10-D: Callback when custom checkbox selection changes */
  onSelectionChange?: (selectedIds: Set<number>) => void;
  /** D1 Bug 6: Column visibility model from parent */
  columnVisibility?: GridColumnVisibilityModel;
  /** D1 Bug 6: Column visibility change callback */
  onColumnVisibilityChange?: (model: GridColumnVisibilityModel) => void;
  /** C2-3 Bug 7: Pending change IDs for row highlighting */
  pendingIds?: Set<number>;
  /** C2-3 Bug 7: Selected row IDs for row highlighting */
  selectedRowIds?: Set<number>;
  /** D1 Bug 6: Auto-fit trigger counter */
  autoFitTrigger?: number;
}

// =============================================================================
// BUG 10.9-3 FIX: Checkbox selection DISABLED
// The MUI DataGrid v8 has internal race conditions in useGridRowSelection.js
// that cause "currentSelection.ids is not iterable" errors regardless of
// initialization strategy. All previous workarounds (isGridMounted, delayed
// checkboxSelection, controlled state) have proven unreliable.
// 
// DECISION: Disable checkboxSelection entirely for stability.
// Row actions (View, Edit) remain functional via the Actions column.
// =============================================================================

// =============================================================================
// BUG 10.6-1 FIX: Custom Footer to prevent GridFooter v8 crash
// The default GridFooter uses gridRowSelectionCountSelector which crashes when
// selection.ids is undefined. This custom footer avoids that selector.
// =============================================================================
const SafeCustomFooter = () => {
  return (
    <GridFooterContainer>
      <Box sx={{ flex: 1 }} />
      <GridPagination />
    </GridFooterContainer>
  );
};

// =============================================================================
// Helper: Safely ensure data is always an array
// =============================================================================
const ensureArray = <T,>(data: T[] | undefined | null): T[] => {
  if (!data) return [];
  if (!Array.isArray(data)) return [];
  return data;
};

// =============================================================================
// CONSTANTS
// =============================================================================

// Action options matching ComparisonDataGrid
const ACTION_OPTIONS = [
  'Keep monitoring',
  'Calculation',
  'Verify on site',
  'Verify by next 1st line PM cycle',
  'No action required (Overshoot)',
  'No action required (Verified within 1 year)',
  'No action required (Overlapping area)',
  'Pending',
];

const repeatedRecordBaseColumns: GridColDef[] = [
  { field: 'track', headerName: 'Track', width: 72, minWidth: 64 },
  { field: 'section', headerName: 'Section', width: 96, minWidth: 88 },
  { field: 'exception_id', headerName: 'ID', width: 86, minWidth: 78 },
  { field: 'from_m', headerName: 'FromM', width: 88, minWidth: 80, type: 'number' },
  { field: 'to_m', headerName: 'ToM', width: 88, minWidth: 80, type: 'number' },
  { field: 'length', headerName: 'Length', width: 78, minWidth: 72, type: 'number' },
  { field: 'track_type', headerName: 'Track Type', width: 96, minWidth: 88 },
  { field: 'level', headerName: 'Level', width: 68, minWidth: 64 },
];

export const __TEST_ONLY__ = {
  baseColumns: repeatedRecordBaseColumns,
};

// Phase 12 Bug 2.3: RESULT options unified — see utils/resultEditCell.tsx

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

const getLevelColor = (level: string): 'error' | 'warning' | 'info' | 'default' => {
  switch (level) {
    case 'L1':
      return 'error';
    case 'L2':
      return 'warning';
    case 'L3':
      return 'info';
    default:
      return 'default';
  }
};

// getActionColor removed — using shared getActionStyle from utils/actionStyles.ts (Phase 12 Bug 2.1);

// formatDate is now imported from dateFormatter utility

// =============================================================================
// CUSTOM EDIT COMPONENTS
// =============================================================================

export const RepeatedRecordLoadingOverlay: React.FC = () => (
  <GridOverlay>
    <Box sx={{ width: '100%' }}>
      <LinearProgress data-testid="repeated-record-loading-overlay" />
    </Box>
  </GridOverlay>
);

const ActionEditCell: React.FC<GridRenderEditCellParams> = (props) => {
  const { id, value, field } = props;
  const apiRef = useGridApiContext();

  const handleChange = (newValue: string) => {
    apiRef.current.setEditCellValue({ id, field, value: newValue });
    apiRef.current.stopCellEditMode({ id, field });
  };

  return (
    <Select
      value={value || ''}
      onChange={(e) => handleChange(e.target.value)}
      size="small"
      fullWidth
      autoFocus
    >
      {ACTION_OPTIONS.map((option) => (
        <MenuItem key={option} value={option}>
          {option}
        </MenuItem>
      ))}
    </Select>
  );
};

// Phase 12 Bug 2.3: CalcResultEditCell, VerifyResultEditCell, AdjustResultEditCell
// replaced by shared ResultEditCell from utils/resultEditCell.tsx

const DateEditCell: React.FC<GridRenderEditCellParams> = (props) => {
  const { id, value, field } = props;
  const apiRef = useGridApiContext();

  const handleChange = (newValue: string) => {
    apiRef.current.setEditCellValue({ id, field, value: newValue });
    apiRef.current.stopCellEditMode({ id, field });
  };

  return (
    <TextField
      type="date"
      value={value || ''}
      onChange={(e) => handleChange(e.target.value)}
      size="small"
      fullWidth
      autoFocus
      InputLabelProps={{ shrink: true }}
    />
  );
};

// =============================================================================
// COMPONENT
// =============================================================================

const RepeatedRecordTable: React.FC<RepeatedRecordTableProps> = ({
  data,
  loading,
  onRowClick,
  onSelectionChange,
  columnVisibility,
  onColumnVisibilityChange,
  pendingIds,
  selectedRowIds,
  autoFitTrigger,
}) => {
  const apiRef = useGridApiRef();
  const { 
    deleteRepeatedRecord, 
    // Feature-002: Batch save functions
    queueChange,
    batchSaveChanges,
    discardChanges,
    hasPendingChanges,
    pendingChanges,
    isBatchSaving,
  } = useDatabaseStore();
  
  // Delete confirmation dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [recordToDelete, setRecordToDelete] = useState<SavedRepeatedRecord | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Detail dialog state
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<SavedRepeatedRecord | null>(null);
  
  // Feature-002: Save confirmation dialog state
  const [saveConfirmOpen, setSaveConfirmOpen] = useState(false);
  
  // Phase 10.10-D: Custom checkbox selection state (replaces MUI checkboxSelection)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  
  // Toast notification state for edit errors
  const [toast, setToast] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({ open: false, message: '', severity: 'info' });
  
  const handleCloseToast = () => {
    setToast((prev) => ({ ...prev, open: false }));
  };

  // =========================================================================
  // PHASE 10.10-D: CUSTOM CHECKBOX SELECTION HANDLERS
  // =========================================================================

  /** Toggle selection for a single row */
  const handleToggleSelect = useCallback((recordId: number) => {
    setSelectedIds((prev) => {
      const updated = new Set(prev);
      if (updated.has(recordId)) {
        updated.delete(recordId);
      } else {
        updated.add(recordId);
      }
      onSelectionChange?.(updated);
      return updated;
    });
  }, [onSelectionChange]);

  /** Select or deselect all currently visible rows */
  const handleSelectAll = useCallback(() => {
    setSelectedIds((prev) => {
      const safeRows = ensureArray(data);
      const allIds = safeRows.map((r) => r.record_id);
      const allSelected = allIds.length > 0 && allIds.every((id) => prev.has(id));

      const updated = allSelected ? new Set<number>() : new Set(allIds);
      onSelectionChange?.(updated);
      return updated;
    });
  }, [data, onSelectionChange]);

  /** Clear selection when data changes (avoid stale selections) */
  useEffect(() => {
    setSelectedIds(new Set());
    onSelectionChange?.(new Set());
  }, [data, onSelectionChange]);

  /** D1 Bug 6: Auto-fit columns when trigger changes */
  useEffect(() => {
    if (autoFitTrigger && autoFitTrigger > 0) {
      try {
        apiRef.current?.autosizeColumns({ includeHeaders: true, includeOutliers: true });
      } catch (e) {
        // DataGrid may not be ready
      }
    }
  }, [autoFitTrigger, apiRef]);

  // =========================================================================
  // HANDLERS
  // =========================================================================

  const handleDeleteClick = (record: SavedRepeatedRecord, e: React.MouseEvent) => {
    e.stopPropagation();
    setRecordToDelete(record);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!recordToDelete) return;
    
    setDeleting(true);
    const success = await deleteRepeatedRecord(recordToDelete.record_id);
    setDeleting(false);
    
    if (success) {
      setDeleteDialogOpen(false);
      setRecordToDelete(null);
    }
  };

  const handleViewClick = (record: SavedRepeatedRecord, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedRecord(record);
    setDetailDialogOpen(true);
  };

  const handleRowClick = (params: GridRowParams) => {
    if (onRowClick) {
      onRowClick(params.row as SavedRepeatedRecord);
    }
  };

  const handleProcessRowUpdate = useCallback(
    async (newRow: SavedRepeatedRecord, oldRow: SavedRepeatedRecord) => {
      // Determine which fields changed
      // Note: We use null coalescing to handle the case where the user clears a field
      // Empty string "" should be sent to clear the field, not undefined
      const updates: UpdateRepeatedRecordRequest = {};
      
      // Helper to normalize value: null/undefined -> undefined, "" -> "" (keep empty string)
      const normalizeValue = (value: string | null | undefined): string | undefined => {
        if (value === null || value === undefined) return undefined;
        return value; // Keep empty string as-is
      };
      
      // Helper to check if values are different (treating null and undefined as same)
      const hasChanged = (newVal: string | null | undefined, oldVal: string | null | undefined): boolean => {
        const normalizedNew = newVal ?? null;
        const normalizedOld = oldVal ?? null;
        return normalizedNew !== normalizedOld;
      };
      
      // Initial Check fields
      if (hasChanged(newRow.action, oldRow.action)) {
        updates.action = normalizeValue(newRow.action);
      }
      if (hasChanged(newRow.check_date, oldRow.check_date)) {
        updates.check_date = normalizeValue(newRow.check_date);
      }
      if (hasChanged(newRow.checked_by, oldRow.checked_by)) {
        updates.checked_by = normalizeValue(newRow.checked_by);
      }
      if (hasChanged(newRow.check_result, oldRow.check_result)) {
        updates.check_result = normalizeValue(newRow.check_result);
      }
      if (hasChanged(newRow.remarks, oldRow.remarks)) {
        updates.remarks = normalizeValue(newRow.remarks);
      }

      // Reoccurrence ID
      if (hasChanged(newRow.reoccurrence_id, oldRow.reoccurrence_id)) {
        updates.reoccurrence_id = normalizeValue(newRow.reoccurrence_id);
      }

      // Site Verification fields
      if (hasChanged(newRow.verify_deadline, oldRow.verify_deadline)) {
        updates.verify_deadline = normalizeValue(newRow.verify_deadline);
      }
      if (hasChanged(newRow.verify_date, oldRow.verify_date)) {
        updates.verify_date = normalizeValue(newRow.verify_date);
      }
      if (hasChanged(newRow.verify_result, oldRow.verify_result)) {
        updates.verify_result = normalizeValue(newRow.verify_result);
      }
      if (hasChanged(newRow.verified_by, oldRow.verified_by)) {
        updates.verified_by = normalizeValue(newRow.verified_by);
      }

      // Final Adjustment fields
      if (hasChanged(newRow.adjust_deadline, oldRow.adjust_deadline)) {
        updates.adjust_deadline = normalizeValue(newRow.adjust_deadline);
      }
      if (hasChanged(newRow.adjust_date, oldRow.adjust_date)) {
        updates.adjust_date = normalizeValue(newRow.adjust_date);
      }
      if (hasChanged(newRow.adjust_result, oldRow.adjust_result)) {
        updates.adjust_result = normalizeValue(newRow.adjust_result);
      }
      if (hasChanged(newRow.adjusted_by, oldRow.adjusted_by)) {
        updates.adjusted_by = normalizeValue(newRow.adjusted_by);
      }

      // Only update if there are actual changes (filter out undefined values)
      const filteredUpdates = Object.fromEntries(
        Object.entries(updates).filter(([_, v]) => v !== undefined)
      ) as UpdateRepeatedRecordRequest;
      
      // Feature-002: Queue change for batch save instead of immediate save
      if (Object.keys(filteredUpdates).length > 0) {
        queueChange(newRow.record_id, filteredUpdates);
        // No toast here - changes are queued, not saved yet
      }

      return newRow;
    },
    [queueChange]
  );

  // Feature-002: Handle batch save with confirmation
  const handleSaveEditClick = () => {
    if (pendingChanges.size > 0) {
      setSaveConfirmOpen(true);
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
        setToast({
          open: true,
          message: 'Changes discarded',
          severity: 'info',
        });
      }
    }
  };

  // =========================================================================
  // COLUMN DEFINITIONS
  // =========================================================================

  // Phase 10.10-D: Compute allSelected for header checkbox
  const safeDataForSelection = useMemo(() => ensureArray(data), [data]);
  const allSelected = useMemo(
    () => safeDataForSelection.length > 0 && safeDataForSelection.every((r) => selectedIds.has(r.record_id)),
    [safeDataForSelection, selectedIds],
  );
  const someSelected = useMemo(
    () => safeDataForSelection.some((r) => selectedIds.has(r.record_id)) && !allSelected,
    [safeDataForSelection, selectedIds, allSelected],
  );

  const columns: GridColDef[] = useMemo(() => [
    // Phase 10.10-D: Custom checkbox selection column (replaces MUI checkboxSelection)
    {
      field: '__selection__',
      headerName: '',
      width: 50,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
      renderHeader: () => (
        <Checkbox
          checked={allSelected}
          indeterminate={someSelected}
          onChange={handleSelectAll}
          size="small"
          sx={{ p: 0 }}
        />
      ),
      renderCell: (params: GridRenderCellParams<SavedRepeatedRecord>) => (
        <Checkbox
          checked={selectedIds.has(params.row.record_id)}
          onChange={() => handleToggleSelect(params.row.record_id)}
          size="small"
          sx={{ p: 0 }}
          onClick={(e) => e.stopPropagation()}
        />
      ),
    },
    // Actions column
    {
      field: 'actions',
      headerName: '',
      width: 50,
      sortable: false,
      filterable: false,
      renderCell: (params: GridRenderCellParams<SavedRepeatedRecord>) => (
        <Tooltip title="View Details">
          <IconButton
            size="small"
            onClick={(e) => handleViewClick(params.row, e)}
          >
            <VisibilityIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      ),
    },
    
    // =========================================================================
    // Group 1: TASK RUN DATA (7 columns) - Phase 10.10-E: Reordered per spec 12.6
    // =========================================================================
    {
      field: 'task_run_date',
      headerName: 'Run Date',
      width: 110,
      valueFormatter: (value: string) => formatDateDisplay(value),
    },
    {
      field: 'line',
      headerName: 'Line',
      width: 60,
    },
    {
      ...repeatedRecordBaseColumns.find((column) => column.field === 'track')!,
    },
    {
      ...repeatedRecordBaseColumns.find((column) => column.field === 'section')!,
    },
    {
      field: 'task_no',
      headerName: 'Task Number',
      width: 100,
    },
    {
      field: 'station_start',
      headerName: 'Station Start',
      width: 100,
    },
    {
      field: 'station_end',
      headerName: 'Station End',
      width: 100,
    },
    
    // =========================================================================
    // Group 2: EXCEPTION DETAILS (16 columns)
    // =========================================================================
    {
      ...repeatedRecordBaseColumns.find((column) => column.field === 'exception_id')!,
    },
    {
      ...repeatedRecordBaseColumns.find((column) => column.field === 'from_m')!,
      valueFormatter: (value: number) => value?.toFixed(2) ?? '-',
    },
    {
      ...repeatedRecordBaseColumns.find((column) => column.field === 'to_m')!,
      valueFormatter: (value: number) => value?.toFixed(2) ?? '-',
    },
    {
      ...repeatedRecordBaseColumns.find((column) => column.field === 'length')!,
      valueFormatter: (value: number) => value?.toFixed(2) ?? '-',
    },
    {
      field: 'exception_type',
      headerName: 'Exception Type',
      width: 120,
    },
    {
      field: 'max_value',
      headerName: 'MaxValue',
      width: 90,
      type: 'number',
      valueFormatter: (value: number) => value?.toFixed(2) ?? '-',
    },
    {
      field: 'max_location',
      headerName: 'MaxLocation',
      width: 100,
      type: 'number',
      valueFormatter: (value: number) => value?.toFixed(2) ?? '-',
    },
    {
      field: 'overlap',
      headerName: 'Overlap',
      width: 90,
    },
    {
      field: 'tension_length',
      headerName: 'Tension Length',
      width: 110,
    },
    {
      ...repeatedRecordBaseColumns.find((column) => column.field === 'track_type')!,
    },
    {
      ...repeatedRecordBaseColumns.find((column) => column.field === 'level')!,
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value}
          color={getLevelColor(params.value)}
          size="small"
          sx={{ fontWeight: 600 }}
        />
      ),
    },
    // Feature-005: repeat_count column removed from UI
    {
      field: 'previous_1',
      headerName: 'Previous 1',
      width: 100,
      renderCell: (params: GridRenderCellParams) => (
        params.value ? <Chip label={params.value} size="small" variant="outlined" /> : '-'
      ),
    },
    {
      field: 'previous_2',
      headerName: 'Previous 2',
      width: 100,
      renderCell: (params: GridRenderCellParams) => (
        params.value ? <Chip label={params.value} size="small" variant="outlined" /> : '-'
      ),
    },
    {
      field: 'reoccurrence_id',
      headerName: 'Reoccurrence ID',
      width: 130,
      editable: true,
      renderCell: (params: GridRenderCellParams) => (
        params.value ? <Chip label={params.value} size="small" color="info" variant="outlined" /> : '-'
      ),
    },
    {
      field: 'remarks',
      headerName: 'Remarks',
      width: 150,
      editable: true,
    },
    
    // =========================================================================
    // Group 3: INITIAL CHECK (4 columns)
    // =========================================================================
    {
      field: 'action',
      headerName: 'ACTION',
      width: 200,
      editable: true,
      renderCell: (params: GridRenderCellParams) => (
        params.value ? (
          <Chip
            label={params.value}
            size="small"
            sx={{ ...getActionStyle(params.value), borderRadius: 1 }}
          />
        ) : (
          <Typography variant="body2" color="text.secondary">-</Typography>
        )
      ),
      renderEditCell: (params) => <ActionEditCell {...params} />,
    },
    {
      field: 'check_date',
      headerName: 'CHECK DATE',
      width: 130,
      editable: true,
      type: 'string',
      valueFormatter: (value: string) => formatDateDisplay(value),
      renderEditCell: (params) => <DateEditCell {...params} />,
    },
    {
      field: 'checked_by',
      headerName: 'CHECK BY',
      width: 100,
      editable: true,
    },
    {
      field: 'check_result',
      headerName: 'CHECK RESULT',
      width: 110,
      editable: true,
      renderCell: (params: GridRenderCellParams) => {
        const value = params.value;
        if (!value) return <Typography variant="body2" color="text.secondary">-</Typography>;
        return (
          <Chip
            label={value}
            color={value === 'Pass' ? 'success' : value === 'Fail' ? 'error' : 'default'}
            size="small"
          />
        );
      },
    },

    // =========================================================================
    // Group 4: SITE VERIFICATION (4 columns)
    // =========================================================================
    {
      field: 'verify_deadline',
      headerName: 'VERIFY DEADLINE',
      width: 120,
      editable: true,
      type: 'string',
      valueFormatter: (value: string) => formatDateDisplay(value),
      renderEditCell: (params) => <DateEditCell {...params} />, // Bug 10.9.1-5 FIX: Add Date Selector
    },
    {
      field: 'verify_date',
      headerName: 'VERIFY DATE',
      width: 130,
      editable: true,
      type: 'string',
      valueFormatter: (value: string) => formatDateDisplay(value),
      renderEditCell: (params) => <DateEditCell {...params} />,
    },
    {
      field: 'verify_result',
      headerName: 'VERIFY RESULT',
      width: 110,
      editable: true,
      renderCell: (params: GridRenderCellParams) => {
        const value = params.value;
        if (!value) return <Typography variant="body2" color="text.secondary">-</Typography>;
        return (
          <Chip
            label={value}
            color={value === 'Pass' ? 'success' : value === 'Fail' ? 'error' : value === 'Pending' ? 'warning' : 'default'}
            size="small"
          />
        );
      },
    },
    {
      field: 'verified_by',
      headerName: 'VERIFIED BY',
      width: 100,
      editable: true,
    },
    
    // =========================================================================
    // Group 5: FINAL ADJUSTMENT (4 columns)
    // =========================================================================
    {
      field: 'adjust_deadline',
      headerName: 'ADJUST DEADLINE',
      width: 130,
      editable: true,
      type: 'string',
      valueFormatter: (value: string) => formatDateDisplay(value),
      renderEditCell: (params) => <DateEditCell {...params} />, // Bug 10.9.1-5 FIX: Add Date Selector
    },
    {
      field: 'adjust_date',
      headerName: 'ADJUST DATE',
      width: 130,
      editable: true,
      type: 'string',
      valueFormatter: (value: string) => formatDateDisplay(value),
      renderEditCell: (params) => <DateEditCell {...params} />,
    },
    {
      field: 'adjust_result',
      headerName: 'ADJUST RESULT',
      width: 120,
      editable: true,
      renderCell: (params: GridRenderCellParams) => {
        const value = params.value;
        if (!value) return <Typography variant="body2" color="text.secondary">-</Typography>;
        return (
          <Chip
            label={value}
            color={value === 'Completed' ? 'success' : value === 'Pending' ? 'warning' : 'default'}
            size="small"
          />
        );
      },
    },
    {
      field: 'adjusted_by',
      headerName: 'ADJUSTED BY',
      width: 110,
      editable: true,
    },
    
    // =========================================================================
    // Group 6: DATABASE (3 columns)
    // =========================================================================
    {
      field: 'saved_at',
      headerName: 'saved_at',
      width: 160,
      valueFormatter: (value: string) => formatDateTimeDisplay(value),
    },
    {
      field: 'last_updated',
      headerName: 'last_updated',
      width: 160,
      valueFormatter: (value: string) => formatDateTimeDisplay(value),
    },
    // Feature-005: saved_by column removed from UI
  ], [selectedIds, allSelected, someSelected, handleSelectAll, handleToggleSelect]);

  // =========================================================================
  // COLUMN GROUPING
  // =========================================================================

  const columnGroupingModel: GridColumnGroupingModel = useMemo(() => [
    // Group 1: Task Run Data (7 fields) - Phase 10.10-E: Reordered per spec 12.6
    {
      groupId: 'task_run_data',
      headerName: 'TASK RUN DATA',
      children: [
        { field: 'task_run_date' },
        { field: 'line' },
        { field: 'track' },
        { field: 'section' },
        { field: 'task_no' },
        { field: 'station_start' },
        { field: 'station_end' },
      ],
    },
    // Group 2: Exception Details (16 fields)
    {
      groupId: 'exception_details',
      headerName: 'EXCEPTION DETAILS',
      children: [
        { field: 'exception_id' },
        { field: 'from_m' },
        { field: 'to_m' },
        { field: 'length' },
        { field: 'exception_type' },
        { field: 'max_value' },
        { field: 'max_location' },
        { field: 'overlap' },
        { field: 'tension_length' },
        { field: 'track_type' },
        { field: 'level' },
        // Feature-005: repeat_count removed
        { field: 'previous_1' },
        { field: 'previous_2' },
        { field: 'reoccurrence_id' },
        { field: 'remarks' },
      ],
    },
    // Group 3: Initial Check (4 fields)
    {
      groupId: 'initial_check',
      headerName: 'INITIAL CHECK',
      children: [
        { field: 'action' },
        { field: 'check_date' },
        { field: 'checked_by' },
        { field: 'check_result' },
      ],
    },
    // Group 4: Site Verification (4 fields)
    {
      groupId: 'site_verification',
      headerName: 'SITE VERIFICATION (IF ANY)',
      children: [
        { field: 'verify_deadline' },
        { field: 'verify_date' },
        { field: 'verify_result' },
        { field: 'verified_by' },
      ],
    },
    // Group 5: Final Adjustment (4 fields)
    {
      groupId: 'final_adjustment',
      headerName: 'FINAL ADJUSTMENT (IF ANY)',
      children: [
        { field: 'adjust_deadline' },
        { field: 'adjust_date' },
        { field: 'adjust_result' },
        { field: 'adjusted_by' },
      ],
    },
    // Group 6: Database (2 fields) - Feature-005: saved_by removed
    {
      groupId: 'database',
      headerName: 'DATABASE',
      children: [
        { field: 'saved_at' },
        { field: 'last_updated' },
      ],
    },
  ], []);

  // =========================================================================
  // BUG 10.7-1 FIX: Safe data handling with useMemo
  // Ensure data is always a valid array to prevent DataGrid v8 crashes
  // =========================================================================
  const safeData = useMemo(() => ensureArray(data), [data]);
  
  // BUG 10.9-3: Selection-related state removed to prevent MUI DataGrid v8 crashes

  // =========================================================================
  // RENDER
  // =========================================================================

  // BUG 10.9-3: isGridMounted state removed - checkboxSelection disabled entirely

  // BUG 10.7-1 FIX: Enhanced check - ensure data is defined AND is an array
  // This check must happen AFTER all hooks but BEFORE any DataGrid rendering
  // to prevent MUI's internal hooks from crashing with invalid data.
  if (!data || !Array.isArray(data)) {
    // Debug logging for troubleshooting
    if (process.env.NODE_ENV === 'development') {
      console.debug('[RepeatedRecordTable] Data not ready:', { data, type: typeof data });
    }
    return (
      <Box sx={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }
  
  // BUG 10.7-1 FIX: Additional safety check for loading state
  // If loading is true and data is empty, show loading indicator
  if (loading && safeData.length === 0) {
    return (
      <Box sx={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box 
      sx={{ 
        // Bug-003 Fix: Ensure proper height and overflow for scrollbar visibility
        height: '100%', 
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',  // Prevent content from pushing scrollbars out of view
        position: 'relative',
      }}
    >
      <DataGrid
        apiRef={apiRef}
        rows={safeData}
        columns={columns}
        columnGroupingModel={columnGroupingModel}
        columnVisibilityModel={columnVisibility}
        onColumnVisibilityModelChange={onColumnVisibilityChange}
        loading={loading}
        autosizeOnMount
        autosizeOptions={{ includeHeaders: true, includeOutliers: true }}
        // BUG 10.6-1 FIX: Use custom footer to avoid GridFooter v8 crash
        slots={{ 
          loadingOverlay: RepeatedRecordLoadingOverlay,
          footer: SafeCustomFooter,
        }}
        getRowId={(row) => row.record_id}
        pageSizeOptions={[25, 50, 100]}
        initialState={{
          pagination: { paginationModel: { pageSize: 50 } },
          sorting: { sortModel: [{ field: 'saved_at', sort: 'desc' }] },
        }}
        onRowClick={handleRowClick}
        processRowUpdate={handleProcessRowUpdate}
        onProcessRowUpdateError={(error) => console.error('Row update error:', error)}
        disableColumnResize={loading}
        disableRowSelectionOnClick
        // BUG 10.9-3 FIX: checkboxSelection DISABLED
        // MUI DataGrid v8 has internal race conditions in selection hooks that cannot
        // be reliably worked around. All row operations available via Actions column.
        checkboxSelection={false}
        density="compact"
        getRowClassName={(params) => sharedGetRowClassName(params, {
            pendingIds: pendingIds,
            selectedIds: selectedRowIds,
        })}
        sx={{
          border: 'none',
          height: '100%',
          flex: 1,
          minHeight: 0,
          ...rowStylesSx,
          '& .MuiDataGrid-main': {
            overflow: 'hidden',
          },
          '& .MuiDataGrid-virtualScroller': {
            overflow: 'auto !important',
          },
          '& .MuiDataGrid-cell:focus': {
            outline: 'none',
          },
          '& .MuiDataGrid-row:hover': {
            cursor: 'pointer',
            bgcolor: 'action.hover',
          },
          '& .MuiDataGrid-cell--editable': {
            bgcolor: 'action.hover',
            '&:hover': {
              bgcolor: 'action.selected',
            },
          },
        }}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this repeated exception record?
          </Typography>
          {recordToDelete && (
            <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="body2">
                <strong>ID:</strong> {recordToDelete.exception_id}
              </Typography>
              <Typography variant="body2">
                <strong>Type:</strong> {recordToDelete.exception_type}
              </Typography>
              {/* Feature-005: repeat_count removed */}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleting}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmDelete}
            color="error"
            variant="contained"
            disabled={deleting}
            startIcon={deleting ? <CircularProgress size={16} /> : null}
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Detail View Dialog */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>Repeated Exception Record Details</DialogTitle>
        <DialogContent>
          {selectedRecord && (
            <Box sx={{ mt: 1 }}>
              {/* Exception Details */}
              <Typography variant="subtitle2" color="primary" sx={{ mb: 1 }}>
                Exception Details
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 2, mb: 2 }}>
                <Typography variant="body2">
                  <strong>Exception ID:</strong> {selectedRecord.exception_id}
                </Typography>
                <Typography variant="body2">
                  <strong>Level:</strong> {selectedRecord.level}
                </Typography>
                <Typography variant="body2">
                  <strong>Type:</strong> {selectedRecord.exception_type}
                </Typography>
                {/* Feature-005: repeat_count removed */}
                <Typography variant="body2">
                  <strong>From:</strong> {selectedRecord.from_m?.toFixed(2)} m
                </Typography>
                <Typography variant="body2">
                  <strong>To:</strong> {selectedRecord.to_m?.toFixed(2)} m
                </Typography>
                <Typography variant="body2">
                  <strong>Max Value:</strong> {selectedRecord.max_value?.toFixed(2) || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Reoccurrence ID:</strong> {selectedRecord.reoccurrence_id || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Previous 1:</strong> {selectedRecord.previous_1 || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Previous 2:</strong> {selectedRecord.previous_2 || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Line:</strong> {selectedRecord.line}
                </Typography>
                <Typography variant="body2">
                  <strong>Track:</strong> {selectedRecord.track}
                </Typography>
                <Typography variant="body2">
                  <strong>Date:</strong> {formatDateDisplay(selectedRecord.date_str)}
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Initial Check */}
              <Typography variant="subtitle2" color="secondary" sx={{ mb: 1 }}>
                Initial Check
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 2, mb: 2 }}>
                <Typography variant="body2">
                  <strong>Action:</strong> {selectedRecord.action || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Check Date:</strong> {selectedRecord.check_date || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Checked By:</strong> {selectedRecord.checked_by || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Calc Result:</strong> {selectedRecord.check_result || '-'}
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Site Verification */}
              <Typography variant="subtitle2" color="warning.main" sx={{ mb: 1 }}>
                Site Verification (If Any)
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 2, mb: 2 }}>
                <Typography variant="body2">
                  <strong>Deadline:</strong> {selectedRecord.verify_deadline || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Date:</strong> {selectedRecord.verify_date || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Result:</strong> {selectedRecord.verify_result || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Verified By:</strong> {selectedRecord.verified_by || '-'}
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Final Adjustment */}
              <Typography variant="subtitle2" color="success.main" sx={{ mb: 1 }}>
                Final Adjustment (If Any)
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 2, mb: 2 }}>
                <Typography variant="body2">
                  <strong>Deadline:</strong> {selectedRecord.adjust_deadline || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Date:</strong> {selectedRecord.adjust_date || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Result:</strong> {selectedRecord.adjust_result || '-'}
                </Typography>
                <Typography variant="body2">
                  <strong>Adjusted By:</strong> {selectedRecord.adjusted_by || '-'}
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Remarks and Metadata */}
              <Typography variant="body2" sx={{ mb: 1 }}>
                <strong>Remarks:</strong> {selectedRecord.remarks || '-'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                <strong>Last Updated:</strong> {formatDateTimeDisplay(selectedRecord.last_updated)}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Toast Notification for Edit Results */}
      <Snackbar
        open={toast.open}
        autoHideDuration={4000}
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

export default RepeatedRecordTable;
