import React from 'react';
import DeleteForeverOutlinedIcon from '@mui/icons-material/DeleteForeverOutlined';
import {
  Box,
  Chip,
  FormControlLabel,
  Radio,
  RadioGroup,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';

export type WireWearSyncActionStatus =
  | 'new'
  | 'update'
  | 'keep_local'
  | 'no_change'
  | 'conflict'
  | 'error'
  | 'delete';

export type WireWearSyncStatusFilter = 'all' | WireWearSyncActionStatus;
export type WireWearConflictChoice = 'local' | 'incoming';

export interface WireWearSyncLineIdentity {
  lineGroup: string;
  lineClass: string;
  cycleDate: string;
  tensionLength: string;
}

export interface WireWearSyncValueSnapshot {
  avgWearMin?: number | null;
  track?: string | null;
  updatedAt?: string | null;
  deletedAt?: string | null;
  source?: string | null;
}

export interface WireWearSyncPreviewRow {
  id: string;
  status: WireWearSyncActionStatus;
  key: WireWearSyncLineIdentity;
  local?: WireWearSyncValueSnapshot | null;
  incoming?: WireWearSyncValueSnapshot | null;
  detail?: string | null;
  resolution?: WireWearConflictChoice | null;
}

export interface WireWearSyncPreviewTableProps {
  rows: WireWearSyncPreviewRow[];
  filter: WireWearSyncStatusFilter;
  disabled?: boolean;
  onFilterChange: (filter: WireWearSyncStatusFilter) => void;
  onResolveConflict: (rowId: string, choice: WireWearConflictChoice) => void;
}

const statusPresentation: Record<WireWearSyncActionStatus, {
  label: string;
  color: 'default' | 'success' | 'warning' | 'info' | 'secondary' | 'error';
}> = {
  new: { label: 'New', color: 'success' },
  update: { label: 'Update', color: 'warning' },
  keep_local: { label: 'Keep Local', color: 'info' },
  no_change: { label: 'No Change', color: 'default' },
  conflict: { label: 'Conflict', color: 'secondary' },
  error: { label: 'Error', color: 'error' },
  delete: { label: 'Delete', color: 'error' },
};

const filters: WireWearSyncStatusFilter[] = [
  'all', 'new', 'update', 'keep_local', 'no_change', 'conflict', 'error', 'delete',
];

const filterLabel = (filter: WireWearSyncStatusFilter) => (
  filter === 'all' ? 'All' : statusPresentation[filter].label
);

const formatValue = (value: number | null | undefined) => (
  value === null || value === undefined ? '-' : value.toFixed(3)
);

function Snapshot({ value, emptyLabel }: { value?: WireWearSyncValueSnapshot | null; emptyLabel: string }) {
  if (!value) return <Typography variant="body2" color="text.secondary">{emptyLabel}</Typography>;
  const timestamp = value.deletedAt || value.updatedAt;
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="body2" fontWeight={700}>
        {value.deletedAt ? 'Deleted' : `Wear ${formatValue(value.avgWearMin)}`}
      </Typography>
      {value.track ? <Typography variant="caption" display="block">Track {value.track}</Typography> : null}
      <Typography variant="caption" color="text.secondary" display="block" sx={{ overflowWrap: 'anywhere' }}>
        {timestamp || 'No timestamp'}
      </Typography>
      {value.source ? <Typography variant="caption" color="text.secondary" display="block">{value.source}</Typography> : null}
    </Box>
  );
}

export default function WireWearSyncPreviewTable({
  rows,
  filter,
  disabled = false,
  onFilterChange,
  onResolveConflict,
}: WireWearSyncPreviewTableProps) {
  const counts = React.useMemo(() => rows.reduce<Record<WireWearSyncStatusFilter, number>>((result, row) => {
    result.all += 1;
    result[row.status] += 1;
    return result;
  }, {
    all: 0,
    new: 0,
    update: 0,
    keep_local: 0,
    no_change: 0,
    conflict: 0,
    error: 0,
    delete: 0,
  }), [rows]);
  const filteredRows = React.useMemo(
    () => filter === 'all' ? rows : rows.filter(row => row.status === filter),
    [filter, rows],
  );

  return (
    <Box>
      <Box sx={{ overflowX: 'auto', pb: 0.5, mb: 1 }}>
        <ToggleButtonGroup
          exclusive
          size="small"
          value={filter}
          onChange={(_event, value: WireWearSyncStatusFilter | null) => value && onFilterChange(value)}
          aria-label="Sync action filter"
          disabled={disabled}
          sx={{ minWidth: 'max-content' }}
        >
          {filters.map(value => (
            <ToggleButton key={value} value={value} aria-label={`Show ${filterLabel(value)} actions`}>
              {filterLabel(value)} {counts[value]}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>

      <TableContainer sx={{ border: 1, borderColor: 'divider', borderRadius: 1, overflowX: 'auto' }}>
        <Table size="small" stickyHeader aria-label="Wire Wear sync preview" sx={{ minWidth: 1280, tableLayout: 'fixed' }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ width: 122, fontWeight: 700 }}>Action</TableCell>
              <TableCell sx={{ width: 100, fontWeight: 700 }}>Line</TableCell>
              <TableCell sx={{ width: 100, fontWeight: 700 }}>Class</TableCell>
              <TableCell sx={{ width: 120, fontWeight: 700 }}>Cycle Date</TableCell>
              <TableCell sx={{ width: 170, fontWeight: 700 }}>Tension Length</TableCell>
              <TableCell sx={{ width: 185, fontWeight: 700 }}>Local</TableCell>
              <TableCell sx={{ width: 185, fontWeight: 700 }}>Incoming</TableCell>
              <TableCell sx={{ width: 250, fontWeight: 700 }}>Decision / Detail</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 5 }}>
                  <Typography variant="body2" color="text.secondary">
                    {rows.length === 0 ? 'No sync actions.' : `No ${filterLabel(filter)} actions.`}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : filteredRows.map(row => {
              const presentation = statusPresentation[row.status];
              return (
                <TableRow key={row.id} hover sx={{ verticalAlign: 'top' }}>
                  <TableCell>
                    <Chip
                      size="small"
                      label={presentation.label}
                      color={presentation.color}
                      variant={row.status === 'no_change' || row.status === 'delete' ? 'outlined' : 'filled'}
                      icon={row.status === 'delete' ? <DeleteForeverOutlinedIcon /> : undefined}
                    />
                  </TableCell>
                  <TableCell>{row.key.lineGroup}</TableCell>
                  <TableCell>{row.key.lineClass}</TableCell>
                  <TableCell>{row.key.cycleDate}</TableCell>
                  <TableCell sx={{ overflowWrap: 'anywhere' }}>{row.key.tensionLength}</TableCell>
                  <TableCell><Snapshot value={row.local} emptyLabel="No local record" /></TableCell>
                  <TableCell><Snapshot value={row.incoming} emptyLabel="No incoming record" /></TableCell>
                  <TableCell>
                    {row.status === 'conflict' ? (
                      <Box>
                        <RadioGroup
                          row
                          value={row.resolution || ''}
                          onChange={event => onResolveConflict(row.id, event.target.value as WireWearConflictChoice)}
                          aria-label={`Resolve conflict ${row.key.lineGroup} ${row.key.lineClass} ${row.key.cycleDate} ${row.key.tensionLength}`}
                        >
                          <FormControlLabel value="local" control={<Radio size="small" />} label="Keep Local" disabled={disabled} />
                          <FormControlLabel value="incoming" control={<Radio size="small" />} label="Use Incoming" disabled={disabled} />
                        </RadioGroup>
                        <Typography variant="caption" color="text.secondary">An authoritative side is required.</Typography>
                      </Box>
                    ) : (
                      <Typography
                        variant="body2"
                        color={row.status === 'error' || row.status === 'delete' ? 'error.main' : 'text.secondary'}
                        sx={{ whiteSpace: 'normal' }}
                      >
                        {row.detail || (row.status === 'delete'
                          ? 'Incoming tombstone deletes the local record.'
                          : 'No decision required.')}
                      </Typography>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
        Showing {filteredRows.length} of {rows.length} sync actions
      </Typography>
    </Box>
  );
}
