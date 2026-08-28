import React, { useMemo, useCallback } from 'react';
import { 
  Box, 
  Paper, 
  Chip, 
  Typography, 
  Card,
  CardContent,
  Grid,
  Alert,
  AlertTitle,
  Checkbox,
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { 
  DataGrid, 
  GridColDef, 
  GridColumnGroupingModel, 
  GridRowModel,
  GridToolbar,
  GridRenderCellParams,
  GridActionsCellItem,
  GridRowParams
} from '@mui/x-data-grid';
import { ExceptionRecord } from '../../types/api';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import { formatDateDisplay } from '../../utils/dateFormatter';
// M5: Field normalization utility for consistent snake_case field names
import { normalizeRecord, getFieldValue } from '../../utils/fieldNormalizer';

import { safetyColors } from '../../theme/AppTheme';
import { alpha } from '@mui/material/styles';
import { getRowClassName, rowStylesSx, RowStyleContext } from '../../utils/rowStyles';

// --- Types ---
export interface ComparisonRow extends ExceptionRecord {
  [key: string]: any; 
}

interface ComparisonDataGridProps {
  data: ExceptionRecord[];
  hasAnalyzed?: boolean;
  onRowUpdate?: (newRow: ComparisonRow) => void;
  onRowClick?: (row: ComparisonRow) => void;
  onViewChart?: (row: ComparisonRow) => void;
  metadata?: {
    line?: string;
    track?: string;
    section?: string;
    task_no?: string;
    station_start?: string;
    station_end?: string;
    task_run_date?: string;
  };
  /** Phase 11 Issue 4: Selected row IDs for batch edit */
  selectedRowIds?: Set<string>;
  /** Phase 11 Issue 4: Selection change callback */
  onSelectionChange?: (selectedIds: Set<string>) => void;
  /** Phase 11 Issue 4: Pending changes map (rowId -> partial changes) */
  pendingChanges?: Map<string, Partial<ComparisonRow>>;
  reviewIds?: Set<string>;
}

// --- Constants ---
const ACTION_OPTIONS = [
    'Keep monitoring',
    'Calculation',
    'Verify on site',
    'Verify by next 1st line PM cycle',
    'No action required (Overshoot)',
    'No action required (Verified within 1 year)',
    'No action required (Overlapping area)',
    'Pending' // Default fallback
];

const historyCompareBaseColumns: GridColDef[] = [
    { field: 'id', headerName: 'ID', width: 168, minWidth: 136 },
    { field: 'FromM', headerName: 'FromM', width: 92, minWidth: 84, type: 'number' },
    { field: 'ToM', headerName: 'ToM', width: 92, minWidth: 84, type: 'number' },
    { field: 'length', headerName: 'Length', width: 74, minWidth: 68, type: 'number' },
    { field: 'Track Type', headerName: 'Track Type', width: 96, minWidth: 88 },
    { field: 'level', headerName: 'Level', width: 68, minWidth: 64 },
];

export const __TEST_ONLY__ = {
    baseColumns: historyCompareBaseColumns,
};

// Phase 12 Bug 2.3: RESULT options unified — ResultEditCell removed (Bug 5)

// --- Helper Functions ---
// ACTION styling imported from shared utility (Phase 12 Bug 2.1)
import { getActionStyle } from '../../utils/actionStyles';

/**
 * Transform backend data to flat object for DataGrid.
 * M5 Enhancement: Uses fieldNormalizer for consistent field name handling.
 * Parses "Previous ID" or "Previous {N}" into separate fields prev_0, prev_1...
 */
export const transformData = (data: ExceptionRecord[]): ComparisonRow[] => {
  return data.map(record => {
    // M5: First normalize the record to snake_case format
    const normalized = normalizeRecord(record);
    const row: ComparisonRow = { ...record, ...normalized };
    
    // Ensure action has a valid default to prevent MUI Select "out-of-range" error
    if (!row.action) {
        row.action = 'Pending'; 
    }

    // =========================================================================
    // BUG FIX: Handle "Previous ID" CSV parsing BEFORE normalized fields
    // The fieldNormalizer maps "Previous ID" -> previous_1, but "Previous ID"
    // may contain CSV like "prev1, prev2" that needs to be split.
    // =========================================================================
    const prevIdRaw = (record as any)['Previous ID'];
    if (prevIdRaw && typeof prevIdRaw === 'string' && prevIdRaw.includes(',')) {
        // CSV format detected - split and assign to prev_0, prev_1, etc.
        const parts = prevIdRaw.split(',').map((s: string) => s.trim());
        parts.forEach((pid: string, idx: number) => {
            row[`prev_${idx}`] = pid;
        });
    } else {
        // Non-CSV format: Use normalized previous_1, previous_2 fields
        // and map to prev_0, prev_1 for backward compatibility
        if (normalized.previous_1) {
            row['prev_0'] = normalized.previous_1;
        }
        if (normalized.previous_2) {
            row['prev_1'] = normalized.previous_2;
        }
    }

    // Legacy handling: "previous" key (string or array) 
    // Still needed for older data formats
    const prevRaw = (record as any)['previous'];
    if (prevRaw && !row['prev_0']) {
        if (typeof prevRaw === 'string') {
            const parts = prevRaw.split(',').map((s: string) => s.trim());
            parts.forEach((pid: string, idx: number) => {
                if (!row[`prev_${idx}`]) {
                    row[`prev_${idx}`] = pid;
                }
            });
        } else if (Array.isArray(prevRaw)) {
            prevRaw.forEach((pid: string, idx: number) => {
                if (!row[`prev_${idx}`]) {
                    row[`prev_${idx}`] = pid;
                }
            });
        }
    }

    // Handle Explicit "Previous X" keys from Backend that weren't normalized
    Object.keys(record).forEach(key => {
        if (key.startsWith('Previous ')) {
            const parts = key.split(' ');
            if (parts.length === 2) {
                if (/^\d+$/.test(parts[1])) {
                    const num = parseInt(parts[1], 10);
                    if (!isNaN(num) && num > 0) {
                        const prevKey = `prev_${num - 1}`;
                        if (!row[prevKey]) {
                            row[prevKey] = (record as any)[key];
                        }
                    }
                }
            }
        }
    });
    
    return row;
  });
};

/**
 * Calculate stats for the summary panel
 */
const calculateStats = (rows: ComparisonRow[]) => {
  const typeCounts: Record<string, number> = {};
  const levelCounts: Record<string, number> = {}; // New: Track Level counts
  const actionCounts: Record<string, number> = {};

  rows.forEach(row => {
    // Count Exception Types
    const type = row['exception type'] as string || 'Unknown';
    typeCounts[type] = (typeCounts[type] || 0) + 1;

    // Count Levels
    const level = row['level'] as string || 'Unknown';
    levelCounts[level] = (levelCounts[level] || 0) + 1;

    // Count Actions
    const action = row['action'] as string || 'Unassigned';
    actionCounts[action] = (actionCounts[action] || 0) + 1;
  });

  return { typeCounts, levelCounts, actionCounts };
};

const ComparisonDataGrid: React.FC<ComparisonDataGridProps> = ({ 
  data, 
  onRowUpdate,
  onRowClick,
  onViewChart,
  metadata,
  hasAnalyzed,
  selectedRowIds,
  onSelectionChange,
  pendingChanges,
  reviewIds,
}) => {
  // Bug-001 Fix: Return empty array instead of MOCK_DATA when no data provided
  // MOCK_DATA was only for initial development/testing and should NOT be used in production
  const displayData = useMemo(() => {
    if (!data || data.length === 0) return [];
    const transformed = transformData(data);
    // Phase 11 Issue 4: Merge pendingChanges into display data
    if (!pendingChanges || pendingChanges.size === 0) return transformed;
    return transformed.map((row) => {
      const changes = pendingChanges.get(row.id);
      return changes ? { ...row, ...changes } : row;
    });
  }, [data, pendingChanges]);

  // 1. Calculate max previous files for dynamic columns
  const maxPreviousCount = useMemo(() => {
    // Bug-001 Fix: When data is empty, return minimum of 2 columns for display
    if (displayData.length === 0) return 2;
    
    let max = 0;
    displayData.forEach(row => {
        let count = 0;
        // Count keys starting with 'prev_'
        Object.keys(row).forEach(key => {
            if (key.startsWith('prev_')) count++;
        });
        if (count > max) max = count;
    });
    // Ensure at least 2 columns for Previous 1 and Previous 2
    return Math.max(max, 2);
  }, [displayData]);

  // 2. Stats
  const stats = useMemo(() => calculateStats(displayData), [displayData]);

  // Phase 11 Issue 4: Checkbox selection handlers
  const handleToggleSelect = useCallback((rowId: string) => {
    if (!onSelectionChange || !selectedRowIds) return;
    const updated = new Set(selectedRowIds);
    if (updated.has(rowId)) {
      updated.delete(rowId);
    } else {
      updated.add(rowId);
    }
    onSelectionChange(updated);
  }, [onSelectionChange, selectedRowIds]);

  const handleSelectAll = useCallback(() => {
    if (!onSelectionChange) return;
    const allIds = displayData.map((r) => r.id);
    const allSelected = selectedRowIds && allIds.length > 0 && allIds.every((id) => selectedRowIds.has(id));
    onSelectionChange(allSelected ? new Set<string>() : new Set(allIds));
  }, [onSelectionChange, selectedRowIds, displayData]);

  // Phase 11 Issue 4: Compute allSelected / someSelected for header checkbox
  const allSelected = useMemo(() => {
    if (!selectedRowIds || displayData.length === 0) return false;
    return displayData.every((r) => selectedRowIds.has(r.id));
  }, [selectedRowIds, displayData]);

  const someSelected = useMemo(() => {
    if (!selectedRowIds || displayData.length === 0) return false;
    return displayData.some((r) => selectedRowIds.has(r.id)) && !allSelected;
  }, [selectedRowIds, displayData, allSelected]);

  // 3. Define Columns
  const columns = useMemo<GridColDef[]>(() => {
    // Phase 11 Issue 4: Custom checkbox column (only when selection is enabled)
    const checkboxCol: GridColDef[] = onSelectionChange ? [{
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
      renderCell: (params: GridRenderCellParams) => (
        <Checkbox
          checked={selectedRowIds?.has(params.row.id) ?? false}
          onChange={() => handleToggleSelect(params.row.id)}
          size="small"
          sx={{ p: 0 }}
          onClick={(e) => e.stopPropagation()}
        />
      ),
    }] : [];

    // Phase 10.10-E: Reordered per spec 12.4
    const baseCols: GridColDef[] = [
        { 
            field: 'actions', 
            type: 'actions', 
            headerName: 'View', 
            width: 50, 
            getActions: (params: GridRowParams) => [
                <GridActionsCellItem
                    key="view-chart"
                    icon={<ShowChartIcon />}
                    label="View Chart"
                    onClick={() => onViewChart && onViewChart(params.row as ComparisonRow)}
                    color="primary"
                />
            ]
        },
        // =====================================================================
        // TASK RUN DATA (#1-#7) - from metadata prop
        // =====================================================================
        { 
            field: 'task_run_date', 
            headerName: 'Run Date', 
            width: 100,
            valueGetter: () => {
                if (!metadata?.task_run_date) return '-';
                const d = metadata.task_run_date;
                if (d.length === 8) {
                    return `${d.slice(0,4)}/${d.slice(4,6)}/${d.slice(6,8)}`;
                }
                return d;
            }
        },
        { 
            field: 'line', 
            headerName: 'Line', 
            width: 60,
            valueGetter: () => metadata?.line || '-'
        },
        { 
            field: 'track', 
            headerName: 'Track', 
            width: 60,
            valueGetter: () => metadata?.track || '-'
        },
        { 
            field: 'section', 
            headerName: 'Section', 
            width: 90,
            valueGetter: (_value: any, row: any) => row.Section ?? row.section ?? metadata?.section ?? '-'
        },
        { 
            field: 'task_no', 
            headerName: 'Task No', 
            width: 90,
            valueGetter: () => metadata?.task_no || '-'
        },
        { 
            field: 'station_start', 
            headerName: 'St. Start', 
            width: 80,
            valueGetter: () => metadata?.station_start || '-'
        },
        { 
            field: 'station_end', 
            headerName: 'St. End', 
            width: 80,
            valueGetter: () => metadata?.station_end || '-'
        },
        // =====================================================================
        // EXCEPTION DETAILS (#8-#18)
        // =====================================================================
        ...historyCompareBaseColumns.filter((column) =>
            ['id', 'FromM', 'ToM', 'length'].includes(column.field)
        ),
        { field: 'exception type', headerName: 'Exception Type', width: 130 },
        { field: 'maxValue', headerName: 'MaxValue', width: 80, type: 'number' },
        { field: 'maxLocation', headerName: 'MaxLocation', width: 100, type: 'number' },
        { field: 'Overlap', headerName: 'Overlap', width: 100, flex: 1, minWidth: 100 },
        { field: 'Tension Length', headerName: 'Tension Length', width: 100, flex: 1, minWidth: 90 },
        ...historyCompareBaseColumns.filter((column) =>
            ['Track Type', 'level'].includes(column.field)
        ),
    ];

    // Dynamic Columns for Previous Files
    const dynamicCols: GridColDef[] = [];
    for (let i = 0; i < maxPreviousCount; i++) {
        dynamicCols.push({
            field: `prev_${i}`,
            headerName: `Previous ${i + 1} ID`, // Issue 3: Explicit ID Header
            width: 150,
            flex: 1,
            minWidth: 120,
            sortable: false,
            renderCell: (params: GridRenderCellParams) => (
                params.value ? <Chip label={params.value} size="small" variant="outlined" /> : '-'
            )
        });
    }

    // Phase 10.10-E: Add remarks column (#21) before workflow columns
    const remarksCols: GridColDef[] = [
        { field: 'reoccurrence_id', headerName: 'Reoccurrence ID', width: 180, editable: false, renderCell: (params: GridRenderCellParams) => (
          <Box sx={reviewIds?.has(params.row.id) || params.row.check_1_year_status === 'review_required' ? { bgcolor: '#fff0d6', color: '#8a4b00', px: 0.5, width: '100%', display: 'flex', alignItems: 'center', gap: 0.5 } : undefined}>
            {(reviewIds?.has(params.row.id) || params.row.check_1_year_status === 'review_required') && <WarningAmberIcon fontSize="small" aria-label="Review required" />}
            {params.value || '-'}
          </Box>
        ) },
        { field: 'remarks', headerName: 'Remarks', width: 150, editable: true },
    ];

    const workflowCols: GridColDef[] = [
        // INITIAL CHECK
        { 
            field: 'action', 
            headerName: 'ACTION', 
            minWidth: 290,
            flex: 1.5, 
            editable: true,
            type: 'singleSelect',
            valueOptions: ACTION_OPTIONS,
            // Phase 12 Bug 5.2: ACTION color highlighting with Chip
            renderCell: (params: GridRenderCellParams) => {
                const style = getActionStyle(params.value || '');
                return (
                    <Chip 
                        icon={(reviewIds?.has(params.row.id) || params.row.check_1_year_status === 'review_required') ? <WarningAmberIcon aria-label="Review required" /> : undefined}
                        label={params.value || '-'} 
                        size="small"
                        sx={{ ...style, borderRadius: 1, ...(reviewIds?.has(params.row.id) || params.row.check_1_year_status === 'review_required' ? { bgcolor: '#fff0d6', color: '#8a4b00', border: '1px solid #e09a2d' } : {}) }}
                    />
                );
            },
        },
        { 
            field: 'check_date', 
            headerName: 'CHECK DATE', 
            minWidth: 120,
            flex: 1, 
            editable: true, 
            type: 'date',
            valueGetter: (value: any) => {
                if (!value) return null;
                const date = new Date(value);
                return isNaN(date.getTime()) ? null : date;
            },
            // Feature-004: Consistent date format
            valueFormatter: (value: any) => formatDateDisplay(value),
        },
        { field: 'checked_by', headerName: 'CHECKED BY', minWidth: 110, flex: 1, editable: true },
        { field: 'check_result', headerName: 'CHECK RESULT', minWidth: 130, flex: 1, editable: true },
        
        // SITE VERIFICATION
        { 
            field: 'verify_deadline', 
            headerName: 'VERIFY DEADLINE', 
            minWidth: 150,
            flex: 1, 
            editable: true, 
            type: 'date',
            valueGetter: (value: any) => {
                if (!value) return null;
                const date = new Date(value);
                return isNaN(date.getTime()) ? null : date;
            },
            // Feature-004: Consistent date format
            valueFormatter: (value: any) => formatDateDisplay(value),
        },
        { 
            field: 'verify_date', 
            headerName: 'VERIFY DATE', 
            minWidth: 120,
            flex: 1, 
            editable: true, 
            type: 'date',
            valueGetter: (value: any) => {
                if (!value) return null;
                const date = new Date(value);
                return isNaN(date.getTime()) ? null : date;
            },
            // Feature-004: Consistent date format
            valueFormatter: (value: any) => formatDateDisplay(value),
        },
        { field: 'verify_result', headerName: 'VERIFY RESULT', minWidth: 135, flex: 1, editable: true },
        { field: 'verified_by', headerName: 'VERIFIED BY', minWidth: 120, flex: 1, editable: true },

        // FINAL ADJUSTMENT
        { 
            field: 'adjust_deadline', 
            headerName: 'ADJUST DEADLINE', 
            minWidth: 150,
            flex: 1, 
            editable: true, 
            type: 'date',
            valueGetter: (value: any) => {
                if (!value) return null;
                const date = new Date(value);
                return isNaN(date.getTime()) ? null : date;
            },
            // Feature-004: Consistent date format
            valueFormatter: (value: any) => formatDateDisplay(value),
        },
        { 
            field: 'adjust_date', 
            headerName: 'ADJUST DATE', 
            minWidth: 120,
            flex: 1, 
            editable: true, 
            type: 'date',
            valueGetter: (value: any) => {
                if (!value) return null;
                const date = new Date(value);
                return isNaN(date.getTime()) ? null : date;
            },
            // Feature-004: Consistent date format
            valueFormatter: (value: any) => formatDateDisplay(value),
        },
        { field: 'adjust_result', headerName: 'ADJUST RESULT', minWidth: 140, flex: 1, editable: true },
        { field: 'adjusted_by', headerName: 'ADJUSTED BY', minWidth: 120, flex: 1, editable: true },
    ];

    return [...checkboxCol, ...baseCols, ...dynamicCols, ...remarksCols, ...workflowCols];
  }, [maxPreviousCount, allSelected, someSelected, handleSelectAll, handleToggleSelect, selectedRowIds, onSelectionChange]);

  // 4. Define Column Grouping - Phase 10.10-E: Reordered per spec 12.4
  const columnGroupingModel = useMemo<GridColumnGroupingModel>(() => [
      {
          groupId: 'Task Run Data',
          headerName: 'TASK RUN DATA',
          children: [
              { field: 'task_run_date' },
              { field: 'line' },
              { field: 'track' },
              { field: 'section' },
              { field: 'task_no' },
              { field: 'station_start' },
              { field: 'station_end' },
          ]
      },
      {
          groupId: 'Exception Details',
          headerName: 'EXCEPTION',
          children: [
              { field: 'id' },
              { field: 'FromM' }, { field: 'ToM' }, { field: 'length' },
              { field: 'exception type' },
              { field: 'maxValue' }, { field: 'maxLocation' },
              { field: 'Overlap' }, { field: 'Tension Length' }, { field: 'Track Type' },
              { field: 'level' },
              ...Array.from({ length: maxPreviousCount }, (_, i) => ({ field: `prev_${i}` })),
              { field: 'reoccurrence_id' },
              { field: 'remarks' },
          ]
      },
      {
          groupId: 'Initial Check',
          headerName: 'INITIAL CHECK',
          children: [{ field: 'action' }, { field: 'check_date' }, { field: 'checked_by' }, { field: 'check_result' }]
      },
      {
          groupId: 'Site Verification',
          headerName: 'SITE VERIFICATION (IF ANY)',
          children: [{ field: 'verify_deadline' }, { field: 'verify_date' }, { field: 'verify_result' }, { field: 'verified_by' }]
      },
      {
          groupId: 'Final Adjustment',
          headerName: 'FINAL ADJUSTMENT (IF ANY)',
          children: [{ field: 'adjust_deadline' }, { field: 'adjust_date' }, { field: 'adjust_result' }, { field: 'adjusted_by' }]
      }
  ], [maxPreviousCount]);

  // 5. Handle Row Updates
  // Phase 11 Issue 4: When pendingChanges is provided, store changes locally
  // instead of triggering immediate save via onRowUpdate
  const processRowUpdate = useCallback((newRow: GridRowModel) => {
      if (onRowUpdate) {
          onRowUpdate(newRow as ComparisonRow);
      }
      return newRow;
  }, [onRowUpdate]);

  const handleProcessRowUpdateError = useCallback((error: any) => {
      console.error("Row update error:", error);
  }, []);

  // Bug-001 Fix: Show empty state when no data is available
  if (hasAnalyzed === false) {
    return (
      <Box sx={{ 
        width: '100%', 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column', 
        justifyContent: 'center', 
        alignItems: 'center',
        p: 4
      }}>
        <Alert 
          severity="info" 
          icon={<InfoIcon />}
          sx={{ maxWidth: 600, width: '100%' }}
        >
          <AlertTitle>Ready to Compare</AlertTitle>
          <Typography variant="body2">
            Upload the Latest Cycle Report and Previous Cycle Report, then click "Compare" to start.
          </Typography>
        </Alert>
      </Box>
    );
  }

  if (displayData.length === 0) {
    return (
      <Box sx={{ 
        width: '100%', 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column', 
        justifyContent: 'center', 
        alignItems: 'center',
        p: 4
      }}>
        <Alert 
          severity="info" 
          icon={<InfoIcon />}
          sx={{ maxWidth: 600, width: '100%' }}
        >
          <AlertTitle>No Repeated Exceptions Found</AlertTitle>
          <Typography variant="body2">
            No repeated exceptions were detected in the comparison.
            This could mean:
          </Typography>
          <Box component="ul" sx={{ mt: 1, pl: 2 }}>
            <li>The uploaded files have no matching exceptions</li>
            <li>The data format may not be compatible (check EAL/TML format)</li>
            <li>Please verify the Excel file structure matches the expected format</li>
          </Box>
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {/* Stats Panel */}
        <Card variant="outlined" sx={{ bgcolor: 'background.default', flexShrink: 0, zIndex: 10 }}>
            <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid item>
                        <Typography variant="subtitle2" color="text.secondary">Matches Breakdown:</Typography>
                    </Grid>
                    {/* Level Counts */}
                    {['L1', 'L2', 'L3'].map(level => (
                        stats.levelCounts[level] > 0 && (
                            <Grid item key={level}>
                                <Chip 
                                    label={`${level}: ${stats.levelCounts[level]}`} 
                                    size="small" 
                                    sx={{ 
                                        fontWeight: 'bold', 
                                        color: 'white',
                                        bgcolor: level === 'L1' ? safetyColors.l1 : level === 'L2' ? safetyColors.l2 : safetyColors.l3 
                                    }} 
                                />
                            </Grid>
                        )
                    ))}
                    <Grid item>
                        <Box sx={{ width: 1, height: 20, borderLeft: 1, borderColor: 'divider', mx: 1 }} />
                    </Grid>
                    {Object.entries(stats.typeCounts).map(([type, count]) => (
                        <Grid item key={type}>
                            <Chip label={`${type}: ${count}`} size="small" variant="outlined" />
                        </Grid>
                    ))}
                    <Grid item>
                        <Box sx={{ width: 1, height: 20, borderLeft: 1, borderColor: 'divider', mx: 1 }} />
                    </Grid>
                    <Grid item>
                        <Typography variant="subtitle2" color="text.secondary">Actions:</Typography>
                    </Grid>
                    {Object.entries(stats.actionCounts).map(([action, count]) => (
                        <Grid item key={action}>
                             <Chip 
                                label={`${action}: ${count}`} 
                                size="small" 
                                sx={getActionStyle(action)}
                             />
                        </Grid>
                    ))}
                </Grid>
            </CardContent>
        </Card>

        {/* Data Grid */}
        <Paper sx={{ flexGrow: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <DataGrid
                rows={displayData}
                columns={columns}
                columnGroupingModel={columnGroupingModel}
                processRowUpdate={processRowUpdate}
                onProcessRowUpdateError={handleProcessRowUpdateError}
                onRowClick={(params) => onRowClick && onRowClick(params.row as ComparisonRow)}
                disableRowSelectionOnClick
                density="compact"
                autosizeOnMount
                slots={{ toolbar: GridToolbar }}
                getRowClassName={(params) => getRowClassName(params, {
                    pendingIds: pendingChanges ? new Set(pendingChanges.keys()) : undefined,
                    selectedIds: selectedRowIds,
                    reviewIds,
                })}
                sx={{
                    border: 0,
                    '& .MuiDataGrid-cell--editable': {
                        bgcolor: (theme) => alpha(theme.palette.action.hover, 0.1),
                    },
                    ...rowStylesSx,
                }}
            />
        </Paper>
    </Box>
  );
};

export default ComparisonDataGrid;
