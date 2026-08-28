import React, { useMemo, useState } from 'react';
import { 
  Paper, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, TableSortLabel, Box, Typography,
  TextField, FormControl, InputLabel, Select, MenuItem,
  Grid, IconButton, Tooltip, Stack
} from '@mui/material';
import FilterListOffIcon from '@mui/icons-material/FilterListOff';
import { AnalysisResponse, ExceptionRecord } from '../types/api';

import { safetyColors } from '../theme/AppTheme';
import { alpha } from '@mui/material/styles';

// Phase 10.10-E: Strict Column Order per spec 12.2
const COLUMNS: { id: keyof ExceptionRecord | string; label: string; minWidth?: number; isTaskRunData?: boolean }[] = [
  // Task Run Data columns (#1-#7)
  { id: 'task_run_date', label: 'Run Date', minWidth: 100, isTaskRunData: true },
  { id: 'line', label: 'Line', minWidth: 60, isTaskRunData: true },
  { id: 'track', label: 'Track', minWidth: 60, isTaskRunData: true },
  { id: 'Section', label: 'Section', minWidth: 80 },
  { id: 'task_no', label: 'Task No', minWidth: 80, isTaskRunData: true },
  { id: 'station_start', label: 'St. Start', minWidth: 80, isTaskRunData: true },
  { id: 'station_end', label: 'St. End', minWidth: 80, isTaskRunData: true },
  // Exception Details columns (#8-#21)
  { id: 'id', label: 'ID', minWidth: 260 },
  { id: 'FromM', label: 'FromM', minWidth: 90 },
  { id: 'ToM', label: 'ToM', minWidth: 90 },
  { id: 'length', label: 'Length', minWidth: 90 },
  { id: 'exception type', label: 'Exception Type', minWidth: 120 },
  { id: 'maxValue', label: 'MaxValue', minWidth: 90 },
  { id: 'maxLocation', label: 'MaxLocation', minWidth: 100 },
  { id: 'Overlap', label: 'Overlap', minWidth: 80 },
  { id: 'Tension Length', label: 'Tension Length', minWidth: 120 },
  { id: 'Track Type', label: 'Track Type', minWidth: 100 },
  { id: 'level', label: 'Level', minWidth: 60 },
  { id: 'Landmark', label: 'Landmark', minWidth: 100 },
  { id: 'Class', label: 'Class', minWidth: 80 },
  { id: 'Threshold Value', label: 'Threshold', minWidth: 90 },
];

type Order = 'asc' | 'desc';

// Bug 10.6-4: Added TaskRunData interface for Task Run Data display
// Phase 10.10-E: Added line and track fields
interface TaskRunData {
  line?: string;
  track?: string;
  task_no?: string;
  station_start?: string;
  station_end?: string;
  task_run_date?: string;  // YYYYMMDD format
}

interface ExceptionTableProps {
  result: AnalysisResponse | null;
  taskRunData?: TaskRunData;  // Bug 10.6-4: Added Task Run Data prop
}

const ExceptionTable = ({ result, taskRunData }: ExceptionTableProps) => {
  
  // Sort State
  const [order, setOrder] = useState<Order>('asc');
  const [orderBy, setOrderBy] = useState<string>('exception type'); // Default sort: Exception Type

  // Filter State
  const [filterType, setFilterType] = useState<string>('All');
  const [filterLevel, setFilterLevel] = useState<string>('All');
  const [filterClass, setFilterClass] = useState<string>('All');
  const [filterTL, setFilterTL] = useState<string>('All');
  const [minLoc, setMinLoc] = useState<string>('');
  const [maxLoc, setMaxLoc] = useState<string>('');

  // 1. Get All Rows (Flattened)
  const allRows = useMemo(() => {
    if (!result) return [];
    let all: ExceptionRecord[] = [];
    Object.values(result.exceptions).forEach(list => {
      all = [...all, ...list];
    });
    return all;
  }, [result]);

  // 2. Derive Unique Options for Filters
  const { types, classes, tensionLengths } = useMemo(() => {
    const t = new Set<string>();
    const c = new Set<string>();
    const tl = new Set<string>();

    allRows.forEach(row => {
      if (row['exception type']) t.add(row['exception type']);
      if (row.Class) c.add(row.Class);
      if (row['Tension Length']) tl.add(String(row['Tension Length']));
    });

    return {
      types: Array.from(t).sort(),
      classes: Array.from(c).sort(),
      tensionLengths: Array.from(tl).sort()
    };
  }, [allRows]);

  // 3. Filter Logic
  const filteredRows = useMemo(() => {
    return allRows.filter(row => {
      // Type Filter
      if (filterType !== 'All' && row['exception type'] !== filterType) return false;
      
      // Level Filter
      if (filterLevel !== 'All' && row.level !== filterLevel) return false;
      
      // Class Filter
      if (filterClass !== 'All' && row.Class !== filterClass) return false;
      
      // Tension Length Filter
      if (filterTL !== 'All' && row['Tension Length'] !== filterTL) return false;
      
      // Range Filter (FromM / ToM logic)
      // Requirement: "filter by input the 'FromM and ToM' value"
      // Interpretation: Show rows where the exception overlaps with or is within the range?
      // Or simply Min Location and Max Location filter?
      // Usually "From/To" filter implies the user enters a range of chainage they are interested in.
      // We check if the exception's location falls within MinLoc and MaxLoc.
      const rowLoc = row.maxLocation; // Use maxLocation as the representative point
      if (minLoc && !isNaN(parseFloat(minLoc))) {
        if (rowLoc < parseFloat(minLoc)) return false;
      }
      if (maxLoc && !isNaN(parseFloat(maxLoc))) {
        if (rowLoc > parseFloat(maxLoc)) return false;
      }

      return true;
    });
  }, [allRows, filterType, filterLevel, filterClass, filterTL, minLoc, maxLoc]);

  // 4. Sort Logic
  const sortedRows = useMemo(() => {
    return [...filteredRows].sort((a, b) => {
      // Default Sort: Exception Type then MaxLocation
      // If user clicks a header, we sort by that header PRIMARY, 
      // but keep Exception Type -> MaxLocation as secondary/tertiary tie-breakers?
      // The requirement says: "The row order shall follow the same 'Exception Type' and then 'MaxLocation'..."
      // This implies this is the dominant sort order.
      
      // Custom Comparator
      const compare = (valA: any, valB: any, ascending: boolean) => {
         if (valB < valA) return ascending ? 1 : -1;
         if (valB > valA) return ascending ? -1 : 1;
         return 0;
      };

      // If sorting by Exception Type (Default)
      if (orderBy === 'exception type') {
         // Primary: Exception Type
         const typeDiff = compare(a['exception type'], b['exception type'], order === 'asc');
         if (typeDiff !== 0) return typeDiff;
         
         // Secondary: MaxLocation (Always Ascending for logical reading)
         return compare(a.maxLocation, b.maxLocation, true);
      } 
      
      // If sorting by other columns (User override)
      const valA = (a as any)[orderBy];
      const valB = (b as any)[orderBy];
      return compare(valA, valB, order === 'asc');
    });
  }, [filteredRows, order, orderBy]);

  const handleRequestSort = (property: string) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const handleResetFilters = () => {
    setFilterType('All');
    setFilterLevel('All');
    setFilterClass('All');
    setFilterTL('All');
    setMinLoc('');
    setMaxLoc('');
    setOrderBy('exception type');
    setOrder('asc');
  };

  if (!result) return <Typography>No data.</Typography>;

  return (
    <Paper sx={{ width: '100%', overflow: 'hidden', height: '100%', display: 'flex', flexDirection: 'column' }}>
      
      {/* Filters Toolbar */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', bgcolor: 'background.default' }}>
        <Grid container spacing={2} alignItems="center">
          
          {/* Row 1: Dropdowns */}
          <Grid item xs={12} md={10}>
             <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                    <FormControl fullWidth size="small">
                    <InputLabel>Type</InputLabel>
                    <Select value={filterType} label="Type" onChange={(e) => setFilterType(e.target.value)}>
                        <MenuItem value="All">All</MenuItem>
                        {types.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                    </Select>
                    </FormControl>
                </Grid>
                <Grid item xs={6} sm={2}>
                    <FormControl fullWidth size="small">
                    <InputLabel>Level</InputLabel>
                    <Select value={filterLevel} label="Level" onChange={(e) => setFilterLevel(e.target.value)}>
                        <MenuItem value="All">All</MenuItem>
                        <MenuItem value="L1">L1</MenuItem>
                        <MenuItem value="L2">L2</MenuItem>
                        <MenuItem value="L3">L3</MenuItem>
                    </Select>
                    </FormControl>
                </Grid>
                <Grid item xs={6} sm={2}>
                    <FormControl fullWidth size="small">
                    <InputLabel>Class</InputLabel>
                    <Select value={filterClass} label="Class" onChange={(e) => setFilterClass(e.target.value)}>
                        <MenuItem value="All">All</MenuItem>
                        {classes.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}
                    </Select>
                    </FormControl>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <FormControl fullWidth size="small">
                    <InputLabel>Tension Length</InputLabel>
                    <Select value={filterTL} label="Tension Length" onChange={(e) => setFilterTL(e.target.value)}>
                        <MenuItem value="All">All</MenuItem>
                        {tensionLengths.map(tl => <MenuItem key={tl} value={tl}>{tl}</MenuItem>)}
                    </Select>
                    </FormControl>
                </Grid>
             </Grid>
          </Grid>
          
          {/* Row 2: Range & Reset (can wrap on small screens) */}
          <Grid item xs={12} md={10}>
            <Grid container spacing={2} alignItems="center">
                <Grid item>
                    <Typography variant="body2" color="text.secondary">Chainage:</Typography>
                </Grid>
                <Grid item xs={3}>
                    <TextField 
                        label="From (m)" 
                        size="small" 
                        value={minLoc} 
                        onChange={(e) => setMinLoc(e.target.value)} 
                        type="number"
                        fullWidth
                    />
                </Grid>
                <Grid item xs={3}>
                    <TextField 
                        label="To (m)" 
                        size="small" 
                        value={maxLoc} 
                        onChange={(e) => setMaxLoc(e.target.value)} 
                        type="number"
                        fullWidth
                    />
                </Grid>
                <Grid item>
                     <Tooltip title="Reset Filters">
                        <IconButton onClick={handleResetFilters} size="small" color="primary">
                            <FilterListOffIcon />
                        </IconButton>
                    </Tooltip>
                </Grid>
            </Grid>
          </Grid>
          
        </Grid>
      </Box>

      {/* Table */}
      <TableContainer sx={{ flexGrow: 1 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              {COLUMNS.map((column) => (
                <TableCell
                  key={column.id}
                  style={{ minWidth: column.minWidth, fontWeight: 'bold' }}
                  sortDirection={orderBy === column.id ? order : false}
                >
                  <TableSortLabel
                    active={orderBy === column.id}
                    direction={orderBy === column.id ? order : 'asc'}
                    onClick={() => handleRequestSort(column.id as string)}
                  >
                    {column.label}
                  </TableSortLabel>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedRows.length > 0 ? (
                sortedRows.map((row) => {
                    // Fix: Use theme-aware alpha blending for better dark mode visibility
                    // Using 0.1 opacity (10%) to keep text readable
                    const getRowColor = (level: string) => {
                        switch (level) {
                            case 'L1': return (theme: any) => alpha(safetyColors.l1, 0.1);
                            case 'L2': return (theme: any) => alpha(safetyColors.l2, 0.1);
                            case 'L3': return (theme: any) => alpha(safetyColors.l3, 0.1);
                            default: return 'inherit';
                        }
                    };
                    
                    return (
                    <TableRow hover role="checkbox" tabIndex={-1} key={row.id} sx={{ bgcolor: getRowColor(row.level) }}>
                        {COLUMNS.map((column) => {
                        // Bug 10.6-4: Handle Task Run Data columns from taskRunData prop
                        let displayValue: string | number | null = null;
                        
                        if (column.isTaskRunData && taskRunData) {
                          // Get value from taskRunData prop
                          const taskRunValue = taskRunData[column.id as keyof TaskRunData];
                          if (column.id === 'task_run_date' && taskRunValue) {
                            // Format YYYYMMDD to YYYY/MM/DD
                            const d = taskRunValue;
                            displayValue = d.length === 8 
                              ? `${d.slice(0,4)}/${d.slice(4,6)}/${d.slice(6,8)}`
                              : d;
                          } else {
                            displayValue = taskRunValue || '-';
                          }
                        } else {
                          // Original logic for row data
                          const value = (row as any)[column.id];
                          displayValue = value;
                          if (typeof value === 'number') {
                            displayValue = value.toFixed(2);
                          }
                        }
                        
                        return (
                            <TableCell key={column.id}>
                            {displayValue}
                            </TableCell>
                        );
                        })}
                    </TableRow>
                    );
                })
            ) : (
                <TableRow>
                    <TableCell colSpan={COLUMNS.length} align="center">
                        <Typography color="text.secondary" sx={{ py: 3 }}>No exceptions match filters.</Typography>
                    </TableCell>
                </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <Box sx={{ p: 1, borderTop: 1, borderColor: 'divider' }}>
        <Typography variant="caption">Showing {sortedRows.length} of {allRows.length} Exceptions</Typography>
      </Box>
    </Paper>
  );
};

export default ExceptionTable;
