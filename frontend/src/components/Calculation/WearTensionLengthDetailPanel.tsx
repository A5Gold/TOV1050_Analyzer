import { Button, Paper, Stack, Typography } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import type { WireWearSavedRecord } from '../../types/api';

interface Props {
  tensionLength: string | null
  records: WireWearSavedRecord[]
  onEdit: (record: WireWearSavedRecord) => void
  onDelete: (record: WireWearSavedRecord) => void
}

export default function WearTensionLengthDetailPanel({ tensionLength, records, onEdit, onDelete }: Props) {
  const toRecord = (row: WireWearSavedRecord & { id?: number }): WireWearSavedRecord => {
    const { id, ...record } = row;
    void id;
    return record;
  };

  const columns: GridColDef[] = [
    { field: 'cycle_date', headerName: 'Cycle Date', width: 120 },
    { field: 'line_class', headerName: 'Class', width: 90 },
    { field: 'track', headerName: 'Track', width: 90 },
    { field: 'section', headerName: 'Section', width: 110 },
    { field: 'from_m', headerName: 'From (m)', width: 100 },
    { field: 'to_m', headerName: 'To (m)', width: 100 },
    { field: 'avg_wear_min', headerName: 'Avg Wear Min', width: 130 },
    { field: 'wear_percentage', headerName: 'Wear %', width: 100 },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 180,
      sortable: false,
      renderCell: params => (
        <Stack direction="row" spacing={1}>
          <Button size="small" startIcon={<EditIcon />} onClick={() => onEdit(toRecord(params.row))}>Edit</Button>
          <Button size="small" color="error" startIcon={<DeleteIcon />} onClick={() => onDelete(toRecord(params.row))}>Delete</Button>
        </Stack>
      ),
    },
  ];

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
        Raw Wire Wear Records{tensionLength ? ` - ${tensionLength}` : ''}
      </Typography>
      <DataGrid
        rows={records.map(record => ({ ...record, id: record.record_id }))}
        columns={columns}
        autoHeight
        disableRowSelectionOnClick
        hideFooter={records.length <= 25}
        pageSizeOptions={[25, 50]}
      />
    </Paper>
  );
}
