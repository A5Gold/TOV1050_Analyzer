import React, { useMemo, useState } from 'react';
import { Box, Button, Chip } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import * as XLSX from 'xlsx';
import { TrendResult } from '../../types/api';

interface TrendResultTableProps {
  results: TrendResult[];
  onViewChart: (result: TrendResult) => void;
  selectedId: string | null;
}

const RECOMMENDATION_COLORS: Record<TrendResult['recommendation'], 'success' | 'warning' | 'default'> = {
  'confirmed valid L2': 'success',
  'verify on site': 'warning',
  'no action required': 'default',
};

function exportExcel(results: TrendResult[]): void {
  const headers = [
    'Chart', 'Recommendation', 'Logic 1', 'Logic 2', 'ID',
    'Task Run Date', 'Line', 'Track', 'Section', 'Task No', 'Stn Start', 'Stn End',
    'FromM', 'ToM', 'MaxValue', 'MaxLocation', 'TL',
    'RP 0', 'RP 1', 'RP 2', 'RP 3', 'RP 4', 'RP 5',
    'TP 0', 'TP 1', 'TP 2', 'TP 3', 'TP 4', 'TP 5',
  ];

  const rows = results.map(r => [
    'View',
    r.recommendation ?? '',
    r.logic_1 ? 'TRUE' : 'FALSE',
    r.logic_2 ? 'TRUE' : 'FALSE',
    r.exception_id,
    r.task_run_date, r.line, r.track, r.section, r.task_no,
    r.station_start, r.station_end,
    r.from_m != null ? Number(r.from_m).toFixed(2) : '',
    r.to_m != null ? Number(r.to_m).toFixed(2) : '',
    r.max_value != null ? Number(r.max_value).toFixed(2) : '',
    r.max_location != null ? Number(r.max_location).toFixed(2) : '',
    r.tension_length,
    ...Array.from({ length: 6 }, (_, i) => r.record_points?.[i] != null ? Number(r.record_points[i]).toFixed(2) : '-'),
    ...Array.from({ length: 6 }, (_, i) => r.trend_points?.[i] != null ? Number(r.trend_points[i]).toFixed(2) : '-'),
  ]);

  const ws = XLSX.utils.aoa_to_sheet([headers, ...rows]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Trend Analysis');

  const r0 = results[0];
  const date = (r0.task_run_date || '').replace(/[-/]/g, '').slice(0, 8);
  const line = r0.line || '';
  const hasCustomFields = r0.task_no && r0.station_start && r0.station_end;
  const filename = hasCustomFields
    ? `${date}_${line}_${r0.task_no}_${r0.station_start}-${r0.station_end}_Wire_Wear_L2_Trend_Report.xlsx`
    : `${date}_${line}_${r0.track || ''}_${r0.section || ''}_Wire_Wear_L2_Trend_Report.xlsx`;

  XLSX.writeFile(wb, filename);
}

const rpColumns: GridColDef[] = Array.from({ length: 6 }, (_, i) => ({
  field: `rp_${i}`,
  headerName: `RP ${i}`,
  width: 80,
  sortable: false,
  valueGetter: (_value: any, row: any) => row.record_points?.[i] ?? null,
  valueFormatter: (value: any) => value != null ? Number(value).toFixed(2) : '-',
}));

const tpColumns: GridColDef[] = Array.from({ length: 6 }, (_, i) => ({
  field: `tp_${i}`,
  headerName: `TP ${i}`,
  width: 80,
  sortable: false,
  valueGetter: (_value: any, row: any) => row.trend_points?.[i] ?? null,
  valueFormatter: (value: any) => value != null ? Number(value).toFixed(2) : '-',
}));

const TrendResultTable = ({ results, onViewChart, selectedId }: TrendResultTableProps) => {
  const [filterRec, setFilterRec] = useState<TrendResult['recommendation'] | null>(null);

  const rows = useMemo(
    () => results.map((r, i) => ({ ...r, id: r.exception_id || `${r.tension_length}-${i}` })),
    [results]
  );

  const counts: Record<TrendResult['recommendation'], number> = {
    'confirmed valid L2': 0,
    'verify on site': 0,
    'no action required': 0,
  };
  rows.forEach(r => { if (r.recommendation) counts[r.recommendation]++; });

  const filteredRows = filterRec ? rows.filter(r => r.recommendation === filterRec) : rows;

  const columns: GridColDef[] = useMemo(() => [
    {
      field: 'actions',
      headerName: 'Chart',
      width: 80,
      sortable: false,
      renderCell: (params: GridRenderCellParams) => (
        <Button
          size="small"
          variant={selectedId === params.row.exception_id ? 'contained' : 'outlined'}
          onClick={() => onViewChart(params.row as TrendResult)}
        >
          View
        </Button>
      ),
    },
    {
      field: 'recommendation',
      headerName: 'Recommendation',
      width: 180,
      renderCell: (params: GridRenderCellParams<any, TrendResult['recommendation']>) => {
        const value = params.value ?? 'no action required';
        return (
          <Chip
            label={value}
            color={RECOMMENDATION_COLORS[value] ?? 'default'}
            size="small"
            variant="outlined"
            data-testid={`recommendation-chip-${params.row.exception_id}`}
          />
        );
      },
    },
    {
      field: 'logic_1',
      headerName: 'Logic 1',
      width: 80,
      renderCell: (params: GridRenderCellParams<any, boolean>) => (params.value ? 'Yes' : 'No'),
    },
    {
      field: 'logic_2',
      headerName: 'Logic 2',
      width: 80,
      renderCell: (params: GridRenderCellParams<any, boolean>) => (params.value ? 'Yes' : 'No'),
    },
    { field: 'exception_id', headerName: 'ID', width: 220 },
    { field: 'task_run_date', headerName: 'Task Run Date', width: 120 },
    { field: 'line', headerName: 'Line', width: 70 },
    { field: 'track', headerName: 'Track', width: 70 },
    { field: 'section', headerName: 'Section', width: 100 },
    { field: 'task_no', headerName: 'Task No', width: 100 },
    { field: 'station_start', headerName: 'Stn Start', width: 100 },
    { field: 'station_end', headerName: 'Stn End', width: 100 },
    {
      field: 'from_m',
      headerName: 'FromM',
      width: 100,
      valueFormatter: (value: any) => value != null ? Number(value).toFixed(2) : '',
    },
    {
      field: 'to_m',
      headerName: 'ToM',
      width: 100,
      valueFormatter: (value: any) => value != null ? Number(value).toFixed(2) : '',
    },
    {
      field: 'max_value',
      headerName: 'MaxValue',
      width: 100,
      valueFormatter: (value: any) => value != null ? Number(value).toFixed(2) : '',
    },
    {
      field: 'max_location',
      headerName: 'MaxLocation',
      width: 110,
      valueFormatter: (value: any) => value != null ? Number(value).toFixed(2) : '',
    },
    { field: 'tension_length', headerName: 'TL', width: 80 },
    ...rpColumns,
    ...tpColumns,
  ], [selectedId, onViewChart]);

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
        <Button
          size="small"
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={() => exportExcel(results)}
          disabled={results.length === 0}
        >
          Export Excel
        </Button>
      </Box>
      <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
        {(Object.entries(counts) as [TrendResult['recommendation'], number][]).map(([rec, count]) => (
          <Chip
            key={rec}
            label={`${rec}: ${count}`}
            color={RECOMMENDATION_COLORS[rec]}
            size="small"
            variant={filterRec === rec ? 'filled' : 'outlined'}
            onClick={() => setFilterRec(prev => prev === rec ? null : rec)}
            sx={{ cursor: 'pointer' }}
          />
        ))}
      </Box>
      <DataGrid
        rows={filteredRows}
        columns={columns}
        autoHeight
        disableRowSelectionOnClick
        pageSizeOptions={[10, 25, 50]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        density="compact"
      />
    </Box>
  );
};

export default TrendResultTable;
