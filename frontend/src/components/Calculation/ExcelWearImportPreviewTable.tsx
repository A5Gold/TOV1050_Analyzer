import React from 'react';
import DownloadIcon from '@mui/icons-material/Download';
import {
  Box,
  Button,
  Checkbox,
  Chip,
  FormControlLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from '@mui/material';

export type ExcelImportRowStatus = 'new' | 'update' | 'no_change' | 'duplicate' | 'error';
export type ExcelImportStatusFilter = 'all' | 'new' | 'update' | 'no_change' | 'error';

export interface ExcelImportPreviewRow {
  id: string;
  status: ExcelImportRowStatus;
  sheet: string;
  cell?: string | null;
  track?: string | null;
  tensionLength?: string | null;
  cycleDate?: string | null;
  importedValue?: number | string | null;
  existingValue?: number | string | null;
  originalValue?: unknown;
  reason?: string | null;
  excluded?: boolean;
}

export interface ExcelWearImportPreviewTableProps {
  rows: ExcelImportPreviewRow[];
  filter: ExcelImportStatusFilter;
  disabled?: boolean;
  onFilterChange: (filter: ExcelImportStatusFilter) => void;
  onExcludeError: (rowId: string, excluded: boolean) => void;
  onDownloadErrorReport?: () => void;
}

const statusPresentation: Record<ExcelImportRowStatus, {
  label: string;
  color: 'default' | 'success' | 'warning' | 'info' | 'error';
}> = {
  new: { label: 'New', color: 'success' },
  update: { label: 'Update', color: 'warning' },
  no_change: { label: 'No Change', color: 'default' },
  duplicate: { label: 'Duplicate', color: 'info' },
  error: { label: 'Error', color: 'error' },
};

const filterLabels: Record<ExcelImportStatusFilter, string> = {
  all: 'All',
  new: 'New',
  update: 'Update',
  no_change: 'No Change',
  error: 'Error',
};

const DEFAULT_ROWS_PER_PAGE = 100;

const displayValue = (value: unknown) => {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value === 'number') return value.toFixed(3);
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
};

export default function ExcelWearImportPreviewTable({
  rows,
  filter,
  disabled = false,
  onFilterChange,
  onExcludeError,
  onDownloadErrorReport,
}: ExcelWearImportPreviewTableProps) {
  const [page, setPage] = React.useState(0);
  const [rowsPerPage, setRowsPerPage] = React.useState(DEFAULT_ROWS_PER_PAGE);
  const counts = React.useMemo(() => rows.reduce<Record<ExcelImportStatusFilter, number>>((result, row) => {
    result.all += 1;
    if (row.status !== 'duplicate') result[row.status] += 1;
    return result;
  }, { all: 0, new: 0, update: 0, no_change: 0, error: 0 }), [rows]);
  const filteredRows = React.useMemo(
    () => filter === 'all' ? rows : rows.filter(row => row.status === filter),
    [filter, rows],
  );
  const pageCount = Math.max(1, Math.ceil(filteredRows.length / rowsPerPage));
  const safePage = Math.min(page, pageCount - 1);
  const visibleRows = React.useMemo(
    () => filteredRows.slice(safePage * rowsPerPage, (safePage + 1) * rowsPerPage),
    [filteredRows, rowsPerPage, safePage],
  );
  const errorCount = counts.error;

  React.useEffect(() => {
    setPage(0);
  }, [filter]);

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1.5,
          mb: 1.5,
          flexWrap: 'wrap',
        }}
      >
        <ToggleButtonGroup
          exclusive
          size="small"
          value={filter}
          onChange={(_event, value: ExcelImportStatusFilter | null) => value && onFilterChange(value)}
          aria-label="Preview status filter"
          disabled={disabled}
        >
          {(Object.keys(filterLabels) as ExcelImportStatusFilter[]).map(value => (
            <ToggleButton key={value} value={value} aria-label={`Show ${filterLabels[value]} rows`}>
              {filterLabels[value]} {counts[value]}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        {onDownloadErrorReport ? (
          <Button
            size="small"
            startIcon={<DownloadIcon />}
            onClick={onDownloadErrorReport}
            disabled={disabled || errorCount === 0}
          >
            Download Error Report
          </Button>
        ) : null}
      </Box>

      <TableContainer sx={{
        border: 1,
        borderColor: 'divider',
        borderRadius: 1,
        maxHeight: 'min(520px, calc(100dvh - 360px))',
        overflow: 'auto',
      }}>
        <Table size="small" stickyHeader aria-label="Excel import preview" sx={{ minWidth: 1180, tableLayout: 'fixed' }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ width: 112, fontWeight: 700 }}>Status</TableCell>
              <TableCell sx={{ width: 110, fontWeight: 700 }}>Sheet</TableCell>
              <TableCell sx={{ width: 82, fontWeight: 700 }}>Cell</TableCell>
              <TableCell sx={{ width: 90, fontWeight: 700 }}>Track</TableCell>
              <TableCell sx={{ width: 170, fontWeight: 700 }}>Tension Length</TableCell>
              <TableCell sx={{ width: 120, fontWeight: 700 }}>Cycle Date</TableCell>
              <TableCell sx={{ width: 130, fontWeight: 700 }}>Existing</TableCell>
              <TableCell sx={{ width: 130, fontWeight: 700 }}>Imported</TableCell>
              <TableCell sx={{ width: 240, fontWeight: 700 }}>Source / Reason</TableCell>
              <TableCell align="center" sx={{ width: 110, fontWeight: 700 }}>Exclude</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} align="center" sx={{ py: 5 }}>
                  <Typography variant="body2" color="text.secondary">
                    {rows.length === 0 ? 'No preview rows.' : `No ${filterLabels[filter]} rows.`}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : visibleRows.map(row => {
              const presentation = statusPresentation[row.status];
              const canExclude = row.status === 'error';
              const sourceValue = row.status === 'error' ? displayValue(row.originalValue) : null;
              return (
                <TableRow key={row.id} hover sx={{ opacity: row.excluded ? 0.58 : 1 }}>
                  <TableCell>
                    <Chip
                      size="small"
                      label={presentation.label}
                      color={presentation.color}
                      variant={row.status === 'no_change' ? 'outlined' : 'filled'}
                    />
                  </TableCell>
                  <TableCell>{row.sheet}</TableCell>
                  <TableCell>{row.cell || '-'}</TableCell>
                  <TableCell>{row.track || '-'}</TableCell>
                  <TableCell>{row.tensionLength || '-'}</TableCell>
                  <TableCell>{row.cycleDate || '-'}</TableCell>
                  <TableCell>{row.status === 'update' ? displayValue(row.existingValue) : '-'}</TableCell>
                  <TableCell>{displayValue(row.importedValue)}</TableCell>
                  <TableCell>
                    {row.status === 'error' ? (
                      <Box>
                        <Tooltip title={sourceValue} placement="top-start">
                          <Typography variant="body2" noWrap>Original: {sourceValue}</Typography>
                        </Tooltip>
                        <Typography variant="caption" color="error.main" sx={{ display: 'block', whiteSpace: 'normal' }}>
                          {row.reason || 'This source value cannot be imported.'}
                        </Typography>
                      </Box>
                    ) : '-'}
                  </TableCell>
                  <TableCell align="center">
                    {canExclude ? (
                      <FormControlLabel
                        sx={{ m: 0 }}
                        control={(
                          <Checkbox
                            size="small"
                            checked={Boolean(row.excluded)}
                            onChange={event => onExcludeError(row.id, event.target.checked)}
                            disabled={disabled}
                            inputProps={{ 'aria-label': `Exclude error ${row.sheet} ${row.cell || row.id}` }}
                          />
                        )}
                        label={<Typography variant="caption">Exclude</Typography>}
                      />
                    ) : '-'}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={filteredRows.length}
        page={safePage}
        rowsPerPage={rowsPerPage}
        rowsPerPageOptions={[50, 100, 250]}
        onPageChange={(_event, nextPage) => setPage(nextPage)}
        onRowsPerPageChange={event => {
          setRowsPerPage(Number(event.target.value));
          setPage(0);
        }}
        labelDisplayedRows={({ from, to, count }) => (
          `${from}-${to} of ${count} filtered rows (${rows.length} total)`
        )}
      />
    </Box>
  );
}
