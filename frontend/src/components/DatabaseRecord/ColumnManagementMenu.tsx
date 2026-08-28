/**
 * Column Management Menu Component
 * =================================
 * Provides a toolbar menu for managing DataGrid columns and batch operations.
 * 
 * Features:
 * - Batch deletion based on various criteria
 * - Column visibility toggle
 * - Column width auto-adjustment
 * - Column pinning/freezing
 * - Export selected rows
 * 
 * Version: 1.0
 * Date: 2026-02-01
 */

import React, { useState } from 'react';
import {
  Box,
  Button,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Typography,
  Chip,
  Alert,
  CircularProgress,
  TextField,
  Stack,
} from '@mui/material';
import ViewColumnIcon from '@mui/icons-material/ViewColumn';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import PushPinIcon from '@mui/icons-material/PushPin';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import WarningIcon from '@mui/icons-material/Warning';
import { GridColumnVisibilityModel } from '@mui/x-data-grid';
import { SavedRepeatedRecord } from '../../types/api';
import { TOV1050_LINES, TOV1050_SECTION_OPTIONS } from '../../config/tov1050';

// =============================================================================
// TYPES
// =============================================================================

interface ColumnManagementMenuProps {
  /** Currently selected rows */
  selectedRows: SavedRepeatedRecord[];
  /** All records */
  allRecords: SavedRepeatedRecord[];
  /** Column visibility model */
  columnVisibility: GridColumnVisibilityModel;
  /** Callback to update column visibility */
  onColumnVisibilityChange: (model: GridColumnVisibilityModel) => void;
  /** Callback to delete records */
  onDeleteRecords: (recordIds: number[]) => Promise<void>;
  /** Callback to export records */
  onExportRecords: (records: SavedRepeatedRecord[]) => void;
  /** Callback to auto-fit columns */
  onAutoFitColumns: () => void;
  /** Loading state */
  loading?: boolean;
}

// Feature-007: Enhanced batch delete criteria
interface BatchDeleteCriteria {
  selectedOnly: boolean;
  byAction: string | null;
  byLevel: string | null;
  byLine: string | null;
  bySection: string | null;
  dateFrom: string;
  dateTo: string;
}

// =============================================================================
// CONSTANTS
// =============================================================================

const COLUMN_GROUPS = {
  'Task Run Data': ['line', 'track', 'section', 'task_no', 'station_start', 'station_end', 'task_run_date'],
  'Exception Details': ['exception_id', 'from_m', 'to_m', 'length', 'exception_type', 'max_value', 'max_location', 'overlap', 'tension_length', 'track_type', 'level', 'repeat_count', 'previous_1', 'previous_2', 'reoccurrence_id', 'remarks'],
  'Initial Check': ['action', 'check_date', 'checked_by', 'check_result'],
  'Site Verification': ['verify_deadline', 'verify_date', 'verify_result', 'verified_by'],
  'Final Adjustment': ['adjust_deadline', 'adjust_date', 'adjusted_by', 'adjust_result'],
  'Database': ['saved_at', 'last_updated', 'saved_by'],
};

const ACTION_OPTIONS = ['Pending', 'Keep monitoring', 'Calculation', 'Verify on site', 'Adjustment required', 'Completed'];
const LEVEL_OPTIONS = ['L1', 'L2', 'L3'];
const LINE_OPTIONS = [...TOV1050_LINES];
// Feature-007: Section options for batch delete
const SECTION_OPTIONS = [...TOV1050_SECTION_OPTIONS];

// =============================================================================
// MAIN COMPONENT
// =============================================================================

const ColumnManagementMenu: React.FC<ColumnManagementMenuProps> = ({
  selectedRows,
  allRecords,
  columnVisibility,
  onColumnVisibilityChange,
  onDeleteRecords,
  onExportRecords,
  onAutoFitColumns,
  loading = false,
}) => {
  // =========================================================================
  // STATE
  // =========================================================================

  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [visibilityDialogOpen, setVisibilityDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteCriteria, setDeleteCriteria] = useState<BatchDeleteCriteria>({
    selectedOnly: true,
    byAction: null,
    byLevel: null,
    byLine: null,
    bySection: null,
    dateFrom: '',
    dateTo: '',
  });
  // Feature-007: Second confirmation state
  const [confirmStep, setConfirmStep] = useState<1 | 2>(1);

  const menuOpen = Boolean(menuAnchor);

  // =========================================================================
  // COMPUTED VALUES
  // =========================================================================

  // Feature-007: Enhanced criteria filtering
  const getRecordsToDelete = (): SavedRepeatedRecord[] => {
    if (deleteCriteria.selectedOnly) {
      return selectedRows;
    }

    let records = [...allRecords];

    if (deleteCriteria.byAction) {
      records = records.filter((r) => r.action === deleteCriteria.byAction);
    }
    if (deleteCriteria.byLevel) {
      records = records.filter((r) => r.level === deleteCriteria.byLevel);
    }
    if (deleteCriteria.byLine) {
      records = records.filter((r) => r.line === deleteCriteria.byLine);
    }
    if (deleteCriteria.bySection) {
      records = records.filter((r) => {
        const section = r.section || '';
        return section === deleteCriteria.bySection;
      });
    }
    // Feature-007: Date range filtering (using saved_at date)
    if (deleteCriteria.dateFrom) {
      const fromDate = new Date(deleteCriteria.dateFrom);
      records = records.filter((r) => {
        if (!r.saved_at) return false;
        return new Date(r.saved_at) >= fromDate;
      });
    }
    if (deleteCriteria.dateTo) {
      const toDate = new Date(deleteCriteria.dateTo);
      toDate.setHours(23, 59, 59, 999); // Include entire day
      records = records.filter((r) => {
        if (!r.saved_at) return false;
        return new Date(r.saved_at) <= toDate;
      });
    }

    return records;
  };

  const recordsToDelete = getRecordsToDelete();
  
  // Feature-007: Check if deletion is potentially dangerous (no date filter)
  const isDangerousDeletion = !deleteCriteria.selectedOnly && 
    !deleteCriteria.dateFrom && 
    !deleteCriteria.dateTo && 
    recordsToDelete.length > 10;

  // =========================================================================
  // HANDLERS
  // =========================================================================

  const handleMenuOpen = (event: React.MouseEvent<HTMLButtonElement>) => {
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handleOpenVisibilityDialog = () => {
    handleMenuClose();
    setVisibilityDialogOpen(true);
  };

  const handleOpenDeleteDialog = () => {
    handleMenuClose();
    setDeleteCriteria({
      selectedOnly: selectedRows.length > 0,
      byAction: null,
      byLevel: null,
      byLine: null,
      bySection: null,
      dateFrom: '',
      dateTo: '',
    });
    setConfirmStep(1); // Feature-007: Reset to first step
    setDeleteDialogOpen(true);
  };

  const handleAutoFit = () => {
    handleMenuClose();
    onAutoFitColumns();
  };

  const handleExportSelected = () => {
    handleMenuClose();
    onExportRecords(selectedRows.length > 0 ? selectedRows : allRecords);
  };

  const handleToggleColumnGroup = (group: string, visible: boolean) => {
    const columns = COLUMN_GROUPS[group as keyof typeof COLUMN_GROUPS] || [];
    const newModel = { ...columnVisibility };
    columns.forEach((col) => {
      newModel[col] = visible;
    });
    onColumnVisibilityChange(newModel);
  };

  const handleToggleColumn = (column: string) => {
    onColumnVisibilityChange({
      ...columnVisibility,
      [column]: !columnVisibility[column],
    });
  };

  const handleConfirmDelete = async () => {
    if (recordsToDelete.length === 0) return;

    setDeleting(true);
    try {
      const ids = recordsToDelete.map((r) => r.record_id);
      await onDeleteRecords(ids);
      setDeleteDialogOpen(false);
    } finally {
      setDeleting(false);
    }
  };

  // =========================================================================
  // RENDER
  // =========================================================================

  return (
    <>
      {/* Main Button */}
      <Button
        variant="outlined"
        startIcon={<ViewColumnIcon />}
        endIcon={<ArrowDropDownIcon />}
        onClick={handleMenuOpen}
        disabled={loading}
      >
        Column Management
      </Button>

      {/* Dropdown Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={menuOpen}
        onClose={handleMenuClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
      >
        <MenuItem onClick={handleOpenVisibilityDialog}>
          <ListItemIcon>
            <VisibilityIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Show/Hide Columns</ListItemText>
        </MenuItem>

        <MenuItem onClick={handleAutoFit}>
          <ListItemIcon>
            <AutoFixHighIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Auto-fit Column Widths</ListItemText>
        </MenuItem>

        <Divider />

        <MenuItem onClick={handleOpenDeleteDialog} disabled={loading}>
          <ListItemIcon>
            <DeleteSweepIcon fontSize="small" color="error" />
          </ListItemIcon>
          <ListItemText>
            <Typography color="error">Batch Delete</Typography>
          </ListItemText>
        </MenuItem>
      </Menu>

      {/* Column Visibility Dialog */}
      <Dialog
        open={visibilityDialogOpen}
        onClose={() => setVisibilityDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Show/Hide Columns</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, pt: 1 }}>
            {Object.entries(COLUMN_GROUPS).map(([group, columns]) => (
              <Box key={group}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2" fontWeight={600}>
                    {group}
                  </Typography>
                  <Box>
                    <Button
                      size="small"
                      onClick={() => handleToggleColumnGroup(group, true)}
                    >
                      All
                    </Button>
                    <Button
                      size="small"
                      onClick={() => handleToggleColumnGroup(group, false)}
                    >
                      None
                    </Button>
                  </Box>
                </Box>
                <FormGroup>
                  {columns.map((col) => (
                    <FormControlLabel
                      key={col}
                      control={
                        <Checkbox
                          size="small"
                          checked={columnVisibility[col] !== false}
                          onChange={() => handleToggleColumn(col)}
                        />
                      }
                      label={col.replace(/_/g, ' ')}
                    />
                  ))}
                </FormGroup>
              </Box>
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setVisibilityDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Batch Delete Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <WarningIcon color="warning" />
            Batch Delete Records
          </Box>
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This action cannot be undone. Please select the deletion criteria carefully.
          </Alert>

          <FormGroup>
            <FormControlLabel
              control={
                <Checkbox
                  checked={deleteCriteria.selectedOnly}
                  onChange={(e) =>
                    setDeleteCriteria((prev) => ({
                      ...prev,
                      selectedOnly: e.target.checked,
                      byAction: null,
                      byLevel: null,
                      byLine: null,
                      bySection: null,
                      dateFrom: '',
                      dateTo: '',
                    }))
                  }
                />
              }
              label={`Delete selected rows only (${selectedRows.length} selected)`}
              disabled={selectedRows.length === 0}
            />
          </FormGroup>

          {!deleteCriteria.selectedOnly && (
            <Box sx={{ mt: 2, pl: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Or delete by criteria:
              </Typography>

              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                <Typography variant="body2">Action:</Typography>
                {ACTION_OPTIONS.map((opt) => (
                  <Chip
                    key={opt}
                    label={opt}
                    size="small"
                    variant={deleteCriteria.byAction === opt ? 'filled' : 'outlined'}
                    color={deleteCriteria.byAction === opt ? 'primary' : 'default'}
                    onClick={() =>
                      setDeleteCriteria((prev) => ({
                        ...prev,
                        byAction: prev.byAction === opt ? null : opt,
                      }))
                    }
                  />
                ))}
              </Box>

              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                <Typography variant="body2">Level:</Typography>
                {LEVEL_OPTIONS.map((opt) => (
                  <Chip
                    key={opt}
                    label={opt}
                    size="small"
                    variant={deleteCriteria.byLevel === opt ? 'filled' : 'outlined'}
                    color={deleteCriteria.byLevel === opt ? 'primary' : 'default'}
                    onClick={() =>
                      setDeleteCriteria((prev) => ({
                        ...prev,
                        byLevel: prev.byLevel === opt ? null : opt,
                      }))
                    }
                  />
                ))}
              </Box>

              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                <Typography variant="body2">Line:</Typography>
                {LINE_OPTIONS.map((opt) => (
                  <Chip
                    key={opt}
                    label={opt}
                    size="small"
                    variant={deleteCriteria.byLine === opt ? 'filled' : 'outlined'}
                    color={deleteCriteria.byLine === opt ? 'primary' : 'default'}
                    onClick={() =>
                      setDeleteCriteria((prev) => ({
                        ...prev,
                        byLine: prev.byLine === opt ? null : opt,
                      }))
                    }
                  />
                ))}
              </Box>

              {/* Feature-007: Section filter */}
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                <Typography variant="body2">Section:</Typography>
                {SECTION_OPTIONS.map((opt) => (
                  <Chip
                    key={opt}
                    label={opt}
                    size="small"
                    variant={deleteCriteria.bySection === opt ? 'filled' : 'outlined'}
                    color={deleteCriteria.bySection === opt ? 'primary' : 'default'}
                    onClick={() =>
                      setDeleteCriteria((prev) => ({
                        ...prev,
                        bySection: prev.bySection === opt ? null : opt,
                      }))
                    }
                  />
                ))}
              </Box>

              {/* Feature-007: Date range filter */}
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" sx={{ mb: 1 }}>Date Range (Saved At):</Typography>
                <Stack direction="row" spacing={2}>
                  <TextField
                    label="From"
                    type="date"
                    size="small"
                    value={deleteCriteria.dateFrom}
                    onChange={(e) => setDeleteCriteria((prev) => ({ ...prev, dateFrom: e.target.value }))}
                    InputLabelProps={{ shrink: true }}
                    sx={{ width: 160 }}
                  />
                  <TextField
                    label="To"
                    type="date"
                    size="small"
                    value={deleteCriteria.dateTo}
                    onChange={(e) => setDeleteCriteria((prev) => ({ ...prev, dateTo: e.target.value }))}
                    InputLabelProps={{ shrink: true }}
                    sx={{ width: 160 }}
                  />
                </Stack>
              </Box>
            </Box>
          )}

          {/* Feature-007: Warning for broad deletions */}
          {isDangerousDeletion && confirmStep === 1 && (
            <Alert severity="error" sx={{ mt: 2 }}>
              <strong>Warning:</strong> No date range specified. This will delete{' '}
              <strong>{recordsToDelete.length}</strong> records. 
              Consider adding a date filter to limit the scope.
            </Alert>
          )}

          <Box sx={{ mt: 3, p: 2, bgcolor: recordsToDelete.length > 50 ? 'error.50' : 'grey.100', borderRadius: 1 }}>
            <Typography variant="body2" fontWeight={600} color={recordsToDelete.length > 50 ? 'error' : 'inherit'}>
              Records to delete: {recordsToDelete.length}
            </Typography>
          </Box>

          {/* Feature-007: Second confirmation step */}
          {confirmStep === 2 && (
            <Alert severity="error" sx={{ mt: 2 }}>
              <strong>Final Confirmation:</strong> You are about to permanently delete{' '}
              <strong>{recordsToDelete.length}</strong> records. This action CANNOT be undone.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleting}>
            Cancel
          </Button>
          {/* Feature-007: Two-step confirmation */}
          {confirmStep === 1 ? (
            <Button
              onClick={() => setConfirmStep(2)}
              color="warning"
              variant="contained"
              disabled={recordsToDelete.length === 0}
            >
              Continue ({recordsToDelete.length} records)
            </Button>
          ) : (
            <Button
              onClick={handleConfirmDelete}
              color="error"
              variant="contained"
              disabled={deleting || recordsToDelete.length === 0}
              startIcon={deleting ? <CircularProgress size={16} /> : <DeleteSweepIcon />}
            >
              {deleting ? 'Deleting...' : `Confirm Delete ${recordsToDelete.length} Records`}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </>
  );
};

export default ColumnManagementMenu;
