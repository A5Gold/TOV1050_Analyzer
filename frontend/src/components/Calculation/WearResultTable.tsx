import React, { useMemo } from 'react';
import { Box, Chip, Tooltip } from '@mui/material';
import { DataGrid, type GridColDef, type GridRenderCellParams } from '@mui/x-data-grid';
import type { WearCycleRecord } from '../../types/api';
import { getAvgWearMinStatusStyle, naturalTensionLengthComparator } from './wearAnalysisPresentation';

interface Props { rows: WearCycleRecord[] }

const columns: GridColDef[] = [
  { field: 'cycleDate', headerName: 'Cycle Date', width: 112 },
  { field: 'lineGroup', headerName: 'Line', width: 72 },
  { field: 'track', headerName: 'Track', width: 90 },
  { field: 'tensionLength', headerName: 'Tension Length', minWidth: 130, flex: 1, sortComparator: naturalTensionLengthComparator, renderCell: (p: GridRenderCellParams) => <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>{p.value}{p.row.hasDataConflict && <Chip size="small" color="warning" label="Data Conflict" />}</Box> },
  { field: 'fromM', headerName: 'From (m)', width: 100 },
  { field: 'toM', headerName: 'To (m)', width: 100 },
  {
    field: 'intervalCount', headerName: 'Intervals', width: 88,
    renderCell: (p: GridRenderCellParams) => (
      <Tooltip title={p.row.intervals.map((item: WearCycleRecord['intervals'][number]) => `${item.track} ${item.fromM}-${item.toM}`).join('\n')}>
        <span>{p.value}</span>
      </Tooltip>
    ),
  },
  { field: 'avgWearMin', headerName: 'Avg Wear Min', width: 128, renderCell: (p: GridRenderCellParams) => <Box sx={{ width: '100%', px: 1 }} style={getAvgWearMinStatusStyle(Number(p.value))}>{p.value}</Box> },
  { field: 'wearPercentage', headerName: 'Wear %', width: 96, renderCell: (p: GridRenderCellParams) => <Tooltip title={`${p.value}%`}><span>{Math.round(Number(p.value))}%</span></Tooltip> },
  { field: 'measurementSd', headerName: 'Measurement SD', width: 132, valueFormatter: (value: number | null) => value ?? 'N/A' },
];

const WearResultTable: React.FC<Props> = ({ rows }) => {
  const gridRows = useMemo(() => rows.slice().sort((a, b) => a.fromM - b.fromM).map(row => ({
    ...row, id: `${row.key.lineGroup}-${row.key.cycleDate}-${row.key.tensionLength}`,
    lineGroup: row.key.lineGroup, cycleDate: row.key.cycleDate, tensionLength: row.key.tensionLength,
  })), [rows]);
  return <DataGrid rows={gridRows} columns={columns} autoHeight disableRowSelectionOnClick pageSizeOptions={[25, 50, 100]} />;
};

export default WearResultTable;
