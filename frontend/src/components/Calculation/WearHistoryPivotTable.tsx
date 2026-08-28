import React from 'react';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import {
  alpha, Box, IconButton, Paper, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Tooltip,
  TablePagination,
} from '@mui/material';
import type { Theme } from '@mui/material/styles';
import type { WearCycleMatrixRow, WearRecordChange, WearWorkbenchColumn } from '../../types/api';

interface Props {
  columns: WearWorkbenchColumn[]
  rows: WearCycleMatrixRow[]
  pendingChanges: WearRecordChange[]
  selectedTensionLength?: string | null
  newCycleDates?: Set<string>
  onAdd: (cycleDate: string, tensionLength: string) => void
  onEdit: (cycleDate: string, tensionLength: string, value: number) => void
  onDeleteCell: (cycleDate: string, tensionLength: string) => void
  onDeleteRow: (cycleDate: string) => void
}

const CYCLE_DATE_WIDTH = 156;
const TENSION_LENGTH_WIDTH = 112;
const VISIBLE_COLUMN_COUNT = 14;
const COLUMN_OVERSCAN = 2;

type PendingKind = WearRecordChange['kind'];

const PENDING_PRESENTATION = {
  add: { label: '待新增', Icon: AddCircleOutlineIcon },
  edit: { label: '待更新', Icon: EditOutlinedIcon },
  delete_cell: { label: '待刪除', Icon: DeleteOutlineIcon },
  delete_row: { label: '整列待刪除', Icon: DeleteOutlineIcon },
} as const;

const pendingStyles = (theme: Theme, continuousRow = false) => {
  const warning = theme.palette.warning;
  const border = alpha(warning.main, theme.palette.mode === 'dark' ? 0.72 : 0.58);
  return {
    bgcolor: alpha(warning.main, theme.palette.mode === 'dark' ? 0.24 : 0.12),
    color: theme.palette.mode === 'dark' ? warning.light : warning.dark,
    boxShadow: continuousRow
      ? `inset 0 1px ${border}, inset 0 -1px ${border}`
      : `inset 0 0 0 1px ${border}`,
    '&:focus-visible': {
      outline: `2px solid ${warning.main}`,
      outlineOffset: '-2px',
    },
  };
};

const PendingMarker = ({ kind }: { kind: PendingKind }) => {
  const { label, Icon } = PENDING_PRESENTATION[kind];
  return <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, fontSize: '0.75rem', fontWeight: 700, whiteSpace: 'nowrap' }}>
    <Icon sx={{ fontSize: 15 }} aria-hidden />
    <Box component="span">{label}</Box>
  </Box>;
};

export default function WearHistoryPivotTable({ columns, rows, pendingChanges, selectedTensionLength = null, newCycleDates = new Set(), onAdd, onEdit, onDeleteCell, onDeleteRow }: Props) {
  const [page, setPage] = React.useState(0);
  const [columnWindowStart, setColumnWindowStart] = React.useState(0);
  const rowsPerPage = 50;
  const scrollRef = React.useRef<HTMLDivElement | null>(null);
  const pendingFor = (date: string, tl?: string) => pendingChanges.find(change => change.kind === 'delete_row'
    ? change.cycleDate === date
    : change.key.cycleDate === date && change.key.tensionLength === tl);

  React.useEffect(() => {
    setPage(current => Math.min(current, Math.max(0, Math.ceil(rows.length / rowsPerPage) - 1)));
  }, [rows.length]);

  const visibleRows = React.useMemo(
    () => rows.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage),
    [page, rows],
  );

  const maxWindowStart = Math.max(0, columns.length - VISIBLE_COLUMN_COUNT);
  const windowStart = Math.min(columnWindowStart, maxWindowStart);
  const windowEnd = Math.min(columns.length, windowStart + VISIBLE_COLUMN_COUNT);
  const visibleColumns = columns.slice(windowStart, windowEnd);
  const leadingSpacerWidth = windowStart * TENSION_LENGTH_WIDTH;
  const trailingSpacerWidth = (columns.length - windowEnd) * TENSION_LENGTH_WIDTH;

  React.useEffect(() => {
    if (!selectedTensionLength) return;
    const selectedIndex = columns.findIndex(column => column.tensionLength === selectedTensionLength);
    if (selectedIndex < 0) return;
    const nextStart = Math.min(maxWindowStart, Math.max(0, selectedIndex - 1));
    setColumnWindowStart(nextStart);
    if (scrollRef.current) scrollRef.current.scrollLeft = selectedIndex * TENSION_LENGTH_WIDTH;
  }, [columns, maxWindowStart, selectedTensionLength]);

  const spacerCell = (key: string, width: number) => width > 0
    ? <TableCell key={key} aria-hidden sx={{ p: 0, width, minWidth: width, maxWidth: width }} />
    : null;

  const selectedColumnSx = (theme: Theme, selected: boolean, header = false) => selected ? {
    bgcolor: alpha(theme.palette.primary.main, theme.palette.mode === 'dark' ? 0.22 : 0.09),
    ...(header ? { boxShadow: `inset 0 -2px ${theme.palette.primary.main}` } : {}),
  } : {};

  return (
    <TableContainer
      component={Paper}
      variant="outlined"
      ref={scrollRef}
      data-testid="history-matrix-scroll"
      onScroll={event => {
        const rawStart = Math.floor(event.currentTarget.scrollLeft / TENSION_LENGTH_WIDTH) - COLUMN_OVERSCAN;
        setColumnWindowStart(Math.min(maxWindowStart, Math.max(0, rawStart)));
      }}
      onWheel={event => {
        if (event.shiftKey) event.currentTarget.scrollLeft += event.deltaY;
      }}
      sx={{ maxHeight: 420, overflowX: 'scroll' }}
    >
      <Table stickyHeader size="small" sx={{ tableLayout: 'fixed', width: CYCLE_DATE_WIDTH + columns.length * TENSION_LENGTH_WIDTH }} aria-label="Historical Avg Wear Min matrix">
        <TableHead data-testid="history-header"><TableRow>
          <TableCell sx={theme => ({
            position: 'sticky',
            left: 0,
            top: 0,
            zIndex: 5,
            width: CYCLE_DATE_WIDTH,
            minWidth: CYCLE_DATE_WIDTH,
            fontWeight: 700,
            bgcolor: theme.palette.background.paper,
            borderRight: 1,
            borderColor: 'divider',
          })}>Cycle Date</TableCell>
          {spacerCell('head-leading-spacer', leadingSpacerWidth)}
          {visibleColumns.map(column => {
            const selected = column.tensionLength === selectedTensionLength;
            return <TableCell
              key={column.tensionLength}
              align="right"
              aria-selected={selected || undefined}
              data-selected={selected || undefined}
              sx={theme => ({
                position: 'sticky',
                top: 0,
                zIndex: 3,
                bgcolor: theme.palette.background.paper,
                width: TENSION_LENGTH_WIDTH,
                minWidth: TENSION_LENGTH_WIDTH,
                fontWeight: 700,
                ...selectedColumnSx(theme, selected, true),
              })}
            >{column.tensionLength}</TableCell>;
          })}
          {spacerCell('head-trailing-spacer', trailingSpacerWidth)}
        </TableRow></TableHead>
        <TableBody>
          {visibleRows.map(row => {
            const rowPending = pendingFor(row.cycleDate)?.kind === 'delete_row';
            const rowMarker: PendingKind | null = rowPending
              ? 'delete_row'
              : newCycleDates.has(row.cycleDate) ? 'add' : null;
            return <TableRow key={row.cycleDate} data-testid={`history-row-${row.cycleDate}`} data-pending={rowPending ? 'delete-row' : undefined}>
              <TableCell sx={theme => ({
                position: 'sticky',
                left: 0,
                zIndex: 2,
                width: CYCLE_DATE_WIDTH,
                minWidth: CYCLE_DATE_WIDTH,
                bgcolor: theme.palette.background.paper,
                borderRight: 1,
                borderColor: 'divider',
                ...(rowMarker ? pendingStyles(theme, rowPending) : {}),
                ...(rowPending ? { textDecoration: 'line-through' } : {}),
              })}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'nowrap', whiteSpace: 'nowrap' }}>
                  <Box component="span" sx={{ flexShrink: 0 }}>{row.cycleDate}</Box>
                  {rowMarker && <PendingMarker kind={rowMarker} />}
                  <Tooltip title={`Delete row ${row.cycleDate}`}><IconButton size="small" aria-label={`Delete row ${row.cycleDate}`} onClick={() => onDeleteRow(row.cycleDate)}><DeleteOutlineIcon fontSize="inherit" /></IconButton></Tooltip>
                </Box>
              </TableCell>
              {spacerCell(`${row.cycleDate}-leading-spacer`, leadingSpacerWidth)}
              {visibleColumns.map(column => {
                const value = row.values[column.tensionLength];
                const pending = pendingFor(row.cycleDate, column.tensionLength);
                const pendingKind: PendingKind | undefined = rowPending ? 'delete_row' : pending?.kind;
                const selected = column.tensionLength === selectedTensionLength;
                return <TableCell
                  key={column.tensionLength}
                  tabIndex={0}
                  data-testid={`history-cell-${row.cycleDate}-${column.tensionLength}${value == null ? '-empty' : ''}`}
                  data-pending={pendingKind}
                  data-selected={selected || undefined}
                  aria-selected={selected || undefined}
                  onDoubleClick={() => value == null ? onAdd(row.cycleDate, column.tensionLength) : onEdit(row.cycleDate, column.tensionLength, value)}
                  onKeyDown={event => {
                    if (event.key !== 'Enter' && event.key !== ' ') return;
                    event.preventDefault();
                    if (value == null) onAdd(row.cycleDate, column.tensionLength);
                    else onEdit(row.cycleDate, column.tensionLength, value);
                  }}
                  align="right"
                  sx={theme => ({
                    ...selectedColumnSx(theme, selected),
                    ...(pendingKind ? pendingStyles(theme, rowPending) : {}),
                    '& .cell-delete': { opacity: 0 },
                    '&:hover .cell-delete, &:focus-within .cell-delete': { opacity: 1 },
                  })}
                >
                  <Box sx={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5, minHeight: 28, width: '100%' }}>
                    {pendingKind && pendingKind !== 'delete_row' && <PendingMarker kind={pendingKind} />}
                    {typeof value === 'number' && <span style={{ textDecoration: pendingKind === 'delete_cell' || pendingKind === 'delete_row' ? 'line-through' : undefined }}>{value.toFixed(3)}</span>}
                    {typeof value === 'number' && <IconButton className="cell-delete" size="small" aria-label={`Delete ${column.tensionLength} on ${row.cycleDate}`} onClick={() => onDeleteCell(row.cycleDate, column.tensionLength)}><DeleteOutlineIcon fontSize="inherit" /></IconButton>}
                  </Box>
                </TableCell>;
              })}
              {spacerCell(`${row.cycleDate}-trailing-spacer`, trailingSpacerWidth)}
            </TableRow>;
          })}
        </TableBody>
      </Table>
      {rows.length === 0 && <Box sx={{ p: 2, color: 'text.secondary' }}>No history records</Box>}
      {rows.length > rowsPerPage && (
        <TablePagination
          component="div"
          count={rows.length}
          page={page}
          rowsPerPage={rowsPerPage}
          rowsPerPageOptions={[rowsPerPage]}
          onPageChange={(_event, nextPage) => setPage(nextPage)}
        />
      )}
    </TableContainer>
  );
}
