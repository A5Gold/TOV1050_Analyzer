import React from 'react';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import {
  Box,
  Button,
  Chip,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';

import type {
  WearCandidatePreviewItem,
  WearCandidateRowInput,
  WearCandidateStatus,
} from '../../types/api';

export type BatchAddRecordRow = WearCandidateRowInput & { rowId: string };
export type BatchAddRecordField = 'tensionLength' | 'avgWearMin';
export interface BatchAddPastedRow {
  tensionLength: string;
  avgWearMin: string;
}

export interface BatchAddRecordsGridProps {
  rows: BatchAddRecordRow[];
  candidates?: WearCandidatePreviewItem[];
  disabled?: boolean;
  onCellChange: (rowId: string, field: BatchAddRecordField, value: string) => void;
  onInsertRow: (afterRowId?: string) => void;
  onDeleteRow: (rowId: string) => void;
  onPasteRows: (startRowId: string, rows: BatchAddPastedRow[]) => void;
}

const statusPresentation: Record<WearCandidateStatus, { label: string; color: 'default' | 'success' | 'warning' | 'info' | 'error' }> = {
  new: { label: 'New', color: 'success' },
  update: { label: 'Update', color: 'warning' },
  no_change: { label: 'No Change', color: 'default' },
  duplicate: { label: 'Duplicate', color: 'info' },
  error: { label: 'Error', color: 'error' },
};

const fieldMatches = (issueField: string, field: BatchAddRecordField) => {
  if (field === 'tensionLength') return issueField === 'tension_length' || issueField === 'tensionLength';
  return issueField === 'avg_wear_min' || issueField === 'avgWearMin';
};

const parseTwoColumnPaste = (value: string): BatchAddPastedRow[] => {
  const lines = value.replace(/\r/g, '').split('\n');
  while (lines.length && lines[lines.length - 1] === '') lines.pop();
  return lines
    .map(line => {
      const [tensionLength = '', avgWearMin = ''] = line.split('\t');
      return { tensionLength: tensionLength.trim(), avgWearMin: avgWearMin.trim() };
    })
    .filter(row => row.tensionLength !== '' || row.avgWearMin !== '');
};

export default function BatchAddRecordsGrid({
  rows,
  candidates = [],
  disabled = false,
  onCellChange,
  onInsertRow,
  onDeleteRow,
  onPasteRows,
}: BatchAddRecordsGridProps) {
  const inputRefs = React.useRef(new Map<string, HTMLInputElement>());
  const pendingFocus = React.useRef<{ rowIndex: number; field: BatchAddRecordField } | null>(null);
  const candidateByRowId = React.useMemo(
    () => new Map(candidates.filter(candidate => candidate.rowId).map(candidate => [candidate.rowId as string, candidate])),
    [candidates],
  );

  React.useEffect(() => {
    const target = pendingFocus.current;
    if (!target || target.rowIndex >= rows.length) return;
    pendingFocus.current = null;
    inputRefs.current.get(`${rows[target.rowIndex].rowId}:${target.field}`)?.focus();
  }, [rows]);

  const focusCell = (rowIndex: number, field: BatchAddRecordField) => {
    if (rowIndex < 0 || rowIndex >= rows.length) return;
    inputRefs.current.get(`${rows[rowIndex].rowId}:${field}`)?.focus();
  };

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLInputElement>,
    rowIndex: number,
    rowId: string,
    field: BatchAddRecordField,
  ) => {
    if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
      event.preventDefault();
      focusCell(rowIndex + (event.key === 'ArrowDown' ? 1 : -1), field);
      return;
    }
    if (event.key !== 'Enter') return;
    event.preventDefault();
    if (rowIndex < rows.length - 1) {
      focusCell(rowIndex + 1, field);
      return;
    }
    pendingFocus.current = { rowIndex: rowIndex + 1, field };
    onInsertRow(rowId);
  };

  const handlePaste = (event: React.ClipboardEvent<HTMLInputElement>, rowId: string) => {
    const clipboardText = event.clipboardData.getData('text/plain');
    if (!clipboardText.includes('\t') && !clipboardText.includes('\n') && !clipboardText.includes('\r')) return;
    const pastedRows = parseTwoColumnPaste(clipboardText);
    if (!pastedRows.length) return;
    event.preventDefault();
    onPasteRows(rowId, pastedRows);
  };

  const renderField = (
    row: BatchAddRecordRow,
    rowIndex: number,
    field: BatchAddRecordField,
    candidate?: WearCandidatePreviewItem,
  ) => {
    const issue = candidate?.issues.find(item => fieldMatches(item.field, field));
    const label = field === 'tensionLength' ? 'Tension Length' : 'Avg Wear Min';
    const value = field === 'tensionLength' ? row.tensionLength : row.avgWearMin ?? '';
    return (
      <TextField
        fullWidth
        size="small"
        value={value}
        error={Boolean(issue)}
        helperText={issue?.message ?? ' '}
        disabled={disabled}
        inputRef={(element: HTMLInputElement | null) => {
          const key = `${row.rowId}:${field}`;
          if (element) inputRefs.current.set(key, element);
          else inputRefs.current.delete(key);
        }}
        inputProps={{
          'aria-label': `Row ${rowIndex + 1} ${label}`,
          inputMode: field === 'avgWearMin' ? 'decimal' : 'text',
        }}
        FormHelperTextProps={{
          sx: {
            mx: 0,
            minHeight: 18,
            lineHeight: 1.25,
            whiteSpace: 'normal',
          },
        }}
        onChange={event => onCellChange(row.rowId, field, event.target.value)}
        onKeyDown={event => handleKeyDown(event as React.KeyboardEvent<HTMLInputElement>, rowIndex, row.rowId, field)}
        onPaste={event => handlePaste(event as React.ClipboardEvent<HTMLInputElement>, row.rowId)}
      />
    );
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
        <Button
          size="small"
          startIcon={<AddIcon />}
          onClick={() => onInsertRow(rows[rows.length - 1]?.rowId)}
          disabled={disabled}
        >
          Add Row
        </Button>
      </Box>
      <TableContainer
        sx={{
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          overflowX: 'auto',
        }}
      >
        <Table size="small" aria-label="Batch Add Records grid" sx={{ minWidth: 760, tableLayout: 'fixed' }}>
          <TableHead>
            <TableRow sx={{ bgcolor: 'action.hover' }}>
              <TableCell sx={{ width: 56, fontWeight: 700 }}>#</TableCell>
              <TableCell sx={{ width: 250, fontWeight: 700 }}>Tension Length</TableCell>
              <TableCell sx={{ width: 210, fontWeight: 700 }}>Avg Wear Min</TableCell>
              <TableCell sx={{ width: 180, fontWeight: 700 }}>Status</TableCell>
              <TableCell align="center" sx={{ width: 64, fontWeight: 700 }}>Delete</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} sx={{ py: 4, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary">No rows. Add a row to begin.</Typography>
                </TableCell>
              </TableRow>
            ) : rows.map((row, rowIndex) => {
              const candidate = candidateByRowId.get(row.rowId);
              const status = candidate ? statusPresentation[candidate.status] : null;
              return (
                <TableRow key={row.rowId} data-row-id={row.rowId} sx={{ verticalAlign: 'top' }}>
                  <TableCell component="th" scope="row" sx={{ pt: 2.25, color: 'text.secondary' }}>
                    {rowIndex + 1}
                  </TableCell>
                  <TableCell>{renderField(row, rowIndex, 'tensionLength', candidate)}</TableCell>
                  <TableCell>{renderField(row, rowIndex, 'avgWearMin', candidate)}</TableCell>
                  <TableCell sx={{ pt: 1.75 }}>
                    {status ? (
                      <Box>
                        <Chip size="small" label={status.label} color={status.color} variant={candidate?.status === 'no_change' ? 'outlined' : 'filled'} />
                        {candidate?.status === 'update' && candidate.existingAvgWearMin != null ? (
                          <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
                            Existing {candidate.existingAvgWearMin.toFixed(3)}
                          </Typography>
                        ) : null}
                      </Box>
                    ) : (
                      <Chip size="small" label="Pending" variant="outlined" />
                    )}
                  </TableCell>
                  <TableCell align="center" sx={{ pt: 1.25 }}>
                    <Tooltip title={`Delete row ${rowIndex + 1}`}>
                      <span>
                        <IconButton
                          size="small"
                          aria-label={`Delete row ${rowIndex + 1}`}
                          onClick={() => onDeleteRow(row.rowId)}
                          disabled={disabled}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
