/**
 * BatchEditDialog Component
 * ==========================
 * Phase 11 Issue 4: Batch edit workflow fields for selected rows
 * in ComparisonDataGrid.
 *
 * Allows users to set values for workflow fields (Initial Check,
 * Site Verification, Final Adjustment, Remarks) and apply them
 * to all selected rows at once.
 *
 * Requirement: 4.4
 */
import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Button,
  Grid,
  Stack,
  Checkbox,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';


// =============================================================================
// CONSTANTS
// =============================================================================

const ACTION_OPTIONS = [
  'Keep monitoring',
  'Calculation',
  'Verify on site',
  'Verify by next 1st line PM cycle',
  'No action required (Overshoot)',
  'No action required (Verified within 1 year)',
  'No action required (Overlapping area)',
  'Pending',
] as const;


// =============================================================================
// TYPES
// =============================================================================

export interface BatchEditValues {
  action?: string;
  check_date?: string;
  checked_by?: string;
  check_result?: string;
  verify_deadline?: string;
  verify_date?: string;
  verified_by?: string;
  verify_result?: string;
  adjust_deadline?: string;
  adjust_date?: string;
  adjusted_by?: string;
  adjust_result?: string;
  remarks?: string;
}

interface BatchEditDialogProps {
  open: boolean;
  selectedCount: number;
  onConfirm: (changes: BatchEditValues) => void;
  onClose: () => void;
}

// =============================================================================
// COMPONENT
// =============================================================================

const BatchEditDialog: React.FC<BatchEditDialogProps> = ({
  open,
  selectedCount,
  onConfirm,
  onClose,
}) => {
  const [values, setValues] = useState<BatchEditValues>({});
  const [enabledFields, setEnabledFields] = useState<Set<string>>(new Set());

  const handleFieldToggle = (field: string) => {
    setEnabledFields((prev) => {
      const updated = new Set(prev);
      if (updated.has(field)) {
        updated.delete(field);
      } else {
        updated.add(field);
      }
      return updated;
    });
  };

  const handleValueChange = (field: keyof BatchEditValues, value: string) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleConfirm = () => {
    const changes: BatchEditValues = {};
    enabledFields.forEach((field) => {
      (changes as any)[field] = (values as any)[field] ?? '';
    });
    onConfirm(changes);
    // Reset state
    setValues({});
    setEnabledFields(new Set());
  };

  const handleClose = () => {
    setValues({});
    setEnabledFields(new Set());
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Stack direction="row" spacing={1} alignItems="center">
          <EditIcon color="primary" />
          <span>Batch Edit {selectedCount} Records</span>
        </Stack>
      </DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          Select fields to update and provide new values. Only checked fields will be applied.
        </DialogContentText>
        <Grid container spacing={2}>
          {/* INITIAL CHECK */}
          <Grid item xs={12}>
            <DialogContentText variant="subtitle2" color="primary">
              Initial Check
            </DialogContentText>
          </Grid>
          {renderSelectField('action', 'Action', ACTION_OPTIONS)}
          {renderDateField('check_date', 'Check Date')}
          {renderTextField('checked_by', 'Checked By')}
          {renderTextField('check_result', 'Check Result')}

          {/* SITE VERIFICATION */}
          <Grid item xs={12}>
            <DialogContentText variant="subtitle2" color="secondary">
              Site Verification
            </DialogContentText>
          </Grid>
          {renderDateField('verify_deadline', 'Verify Deadline')}
          {renderDateField('verify_date', 'Verify Date')}
          {renderTextField('verified_by', 'Verified By')}
          {renderTextField('verify_result', 'Verify Result')}

          {/* FINAL ADJUSTMENT */}
          <Grid item xs={12}>
            <DialogContentText variant="subtitle2" color="success.main">
              Final Adjustment
            </DialogContentText>
          </Grid>
          {renderDateField('adjust_deadline', 'Adjust Deadline')}
          {renderDateField('adjust_date', 'Adjust Date')}
          {renderTextField('adjusted_by', 'Adjusted By')}
          {renderTextField('adjust_result', 'Adjust Result')}

          {/* REMARKS */}
          <Grid item xs={12}>
            <DialogContentText variant="subtitle2">Other</DialogContentText>
          </Grid>
          {renderTextField('remarks', 'Remarks')}
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleConfirm}
          disabled={enabledFields.size === 0}
        >
          Apply to {selectedCount} Records
        </Button>
      </DialogActions>
    </Dialog>
  );

  // =========================================================================
  // RENDER HELPERS
  // =========================================================================

  function renderSelectField(
    field: keyof BatchEditValues,
    label: string,
    options: readonly string[],
  ) {
    return (
      <Grid item xs={12} sm={6}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Checkbox
            checked={enabledFields.has(field)}
            onChange={() => handleFieldToggle(field)}
          />
          <FormControl fullWidth size="small" disabled={!enabledFields.has(field)}>
            <InputLabel>{label}</InputLabel>
            <Select
              value={(values as any)[field] ?? ''}
              label={label}
              onChange={(e) => {
                const val = e.target.value;
                handleValueChange(field, val === '(Clear)' ? '' : val);
              }}
            >
              {options.map((opt) => (
                <MenuItem key={opt} value={opt}>
                  {opt === '(Clear)' ? <em>(Clear)</em> : opt}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Stack>
      </Grid>
    );
  }

  function renderDateField(field: keyof BatchEditValues, label: string) {
    return (
      <Grid item xs={12} sm={6}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Checkbox
            checked={enabledFields.has(field)}
            onChange={() => handleFieldToggle(field)}
          />
          <TextField
            fullWidth
            size="small"
            label={label}
            type="date"
            InputLabelProps={{ shrink: true }}
            value={(values as any)[field] ?? ''}
            onChange={(e) => handleValueChange(field, e.target.value)}
            disabled={!enabledFields.has(field)}
          />
        </Stack>
      </Grid>
    );
  }

  function renderTextField(field: keyof BatchEditValues, label: string) {
    return (
      <Grid item xs={12} sm={6}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Checkbox
            checked={enabledFields.has(field)}
            onChange={() => handleFieldToggle(field)}
          />
          <TextField
            fullWidth
            size="small"
            label={label}
            value={(values as any)[field] ?? ''}
            onChange={(e) => handleValueChange(field, e.target.value)}
            disabled={!enabledFields.has(field)}
          />
        </Stack>
      </Grid>
    );
  }
};

export default BatchEditDialog;
