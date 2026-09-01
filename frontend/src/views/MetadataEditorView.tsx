import React, { useState, useEffect, useMemo } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  Select, 
  MenuItem, 
  FormControl, 
  InputLabel, 
  Button, 
  Alert, 
  Snackbar,
  Tabs,
  Tab,
  Toolbar,
  Divider,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  DialogContentText
} from '@mui/material';
import { DataGrid, GridColDef, GridToolbar, GridActionsCellItem, GridRowId } from '@mui/x-data-grid';
import SaveIcon from '@mui/icons-material/Save';
import RestoreIcon from '@mui/icons-material/Restore';
import UndoIcon from '@mui/icons-material/Undo';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/DeleteOutlined';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { metadataApi } from '../api/client';
import { fillDataRegionSx, scrollablePageSx } from '../utils/pageLayout';
import { TOV1050_METADATA_FILES } from '../config/tov1050';

// Types
interface MetadataRow {
  id: string; // Generated for Grid
  Class: string;
  'Track Type'?: string;
  'Exc Type'?: string;
  L1: number | null;
  L2: number | null;
  L3: number | null;
  // Original keys stored for reference/save
  _prefix: string; 
  [key: string]: any;
}

interface TabDef {
    label: string;
    sheet: string;
}

const FILES = [...TOV1050_METADATA_FILES];
const IGNORED_SHEETS = ['template', 'Previous template', '2-3 repeated template'];

const EXC_TYPES = ['Low Height', 'High Height', 'Stagger Left', 'Stagger Right', 'Wire Wear'];
const TRACK_TYPES = ['Tangent', 'Curve', 'both'];

// Transform Backend Dict -> Grid Row
export const transformMetadataToGrid = (data: any[]): MetadataRow[] => {
  return data.map((item, index) => {
    const excType = item['Exc Type'] || '';
    let prefix = excType;

    if (excType.includes('Stagger')) prefix = 'Stagger';
    else if (excType.includes('Low Height')) prefix = 'Low Height';
    else if (excType.includes('High Height')) prefix = 'High Height';
    else if (excType.includes('Wire Wear')) prefix = 'Wire Wear';

    return {
      id: `${item['Class'] || 'Unknown'}_${item['Track Type'] || 'any'}_${excType}_${index}_${Date.now()}`,
      ...item,
      Class: item.Class ?? item['Location Type'] ?? '',
      L1: item[`${prefix} L1`] ?? null,
      L2: item[`${prefix} L2`] ?? null,
      L3: item[`${prefix} L3`] ?? null,
      _prefix: prefix
    };
  });
};

// Transform Grid Row -> Backend Dict
export const transformGridToMetadata = (gridRows: MetadataRow[]): any[] => {
  return gridRows.map(row => {
    const { id, L1, L2, L3, _prefix, Class: classValue, ...rest } = row;
    const newItem = { ...rest };

    if (Object.prototype.hasOwnProperty.call(newItem, 'Location Type')) {
      newItem['Location Type'] = classValue;
    } else {
      newItem.Class = classValue;
    }

    // Map generic L values back to specific keys. Preserve null explicitly for blank cells.
    if (_prefix && L1 !== undefined) newItem[`${_prefix} L1`] = L1;
    if (_prefix && L2 !== undefined) newItem[`${_prefix} L2`] = L2;
    if (_prefix && L3 !== undefined) newItem[`${_prefix} L3`] = L3;

    return newItem;
  });
};

const MetadataEditorView: React.FC = () => {
  const [filename, setFilename] = useState<string>(FILES[0]);
  const isTov1050Workbook = TOV1050_METADATA_FILES.includes(filename as (typeof TOV1050_METADATA_FILES)[number]);
  const [tabs, setTabs] = useState<TabDef[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [rows, setRows] = useState<MetadataRow[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingSheets, setLoadingSheets] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error'}>({
    open: false, message: '', severity: 'success'
  });

  // Client-Side Persistence Cache
  const tabsDataCache = React.useRef<Record<string, MetadataRow[]>>({});

  // Undo History
  const [history, setHistory] = useState<MetadataRow[][]>([]);
  const [future, setFuture] = useState<MetadataRow[][]>([]);

  // Filters
  const [filterExcType, setFilterExcType] = useState<string>('All');
  const [filterTrackType, setFilterTrackType] = useState<string>('All');

  // Add Row Dialog
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [newRowData, setNewRowData] = useState<any>({
      Class: 'Support',
      'Track Type': 'UT',
      'Exc Type': 'Low Height',
      L1: 0, L2: 0, L3: 0,
  });

  // 1. Load Sheets when filename changes
  useEffect(() => {
      const loadSheets = async () => {
          setLoadingSheets(true);
          try {
              const sheetNames = await metadataApi.getSheetNames(filename);
              const newTabs: TabDef[] = sheetNames
                  .filter(name => !IGNORED_SHEETS.includes(name))
                  .map(name => {
                      let label = name;
                      if (name === 'threshold') label = 'Thresholds';
                      else if (name === 'location type') label = 'Location intervals';
                      else if (name.toLowerCase() === 'exception boundarys' || name.toLowerCase() === 'exception boundaries') label = 'Boundaries';
                      else if (name.toLowerCase().includes('track type')) label = name.replace(/ track type$/i, ' direction');
                      return { label, sheet: name };
                  });
              
              setTabs(newTabs);
              tabsDataCache.current = {}; // Clear cache on new file
              setActiveTab(0);
          } catch (error) {
              console.error(error);
              showToast('Failed to load sheets', 'error');
              setTabs([]);
          } finally {
              setLoadingSheets(false);
          }
      };
      loadSheets();
  }, [filename]);

  // 2. Load Data when activeTab or Tabs changes
  useEffect(() => {
    // Only load data if we have valid tabs and we are not currently loading sheets
    if (!loadingSheets && tabs.length > 0 && activeTab < tabs.length) {
        loadData();
    } else {
        setRows([]);
    }
  }, [activeTab, tabs, loadingSheets]);

  const loadData = async (forceRefresh = false) => {
    setLoading(true);
    setHistory([]);
    setFuture([]);
    try {
      const sheetName = tabs[activeTab].sheet;

      // Check Cache first
      if (!forceRefresh && tabsDataCache.current[sheetName]) {
          setRows(tabsDataCache.current[sheetName]);
          setLoading(false);
          return;
      }

      const rawData = await metadataApi.getMetadata(filename, sheetName);
      const gridRows = transformMetadataToGrid(rawData);
      setRows(gridRows);
    } catch (error: any) {
      // A workbook's sheet list is authoritative, so a missing sheet is an
      // actual configuration error rather than an expected TOV640 fallback.
      const isSheetNotFound = 
        error?.response?.status === 400 && 
        (error?.response?.data?.detail?.includes('not found') || 
         error?.response?.data?.detail?.includes('invalid'));
      
      if (isSheetNotFound) {
        const sheetName = tabs[activeTab]?.sheet || 'Unknown';
        console.debug(`[MetadataEditor] Sheet '${sheetName}' not found, showing empty grid`);
        setRows([]);
        // Cache empty result to prevent repeated API calls
        tabsDataCache.current[sheetName] = [];
      } else {
        console.error('[MetadataEditor] Failed to load metadata:', error);
        showToast('Failed to load metadata', 'error');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
      // Save current rows to cache
      if (tabs[activeTab]) {
          tabsDataCache.current[tabs[activeTab].sheet] = rows;
      }
      setActiveTab(newValue);
  };

  const handleUndo = () => {
    if (history.length === 0) return;
    const previous = history[history.length - 1];
    const newHistory = history.slice(0, -1);
    
    setFuture([rows, ...future]);
    setRows(previous);
    setHistory(newHistory);
  };

  const addToHistory = () => {
    setHistory([...history, rows]);
    setFuture([]);
  };

  // ISSUE 3: Delete Row
  const handleDeleteClick = (id: GridRowId) => () => {
      addToHistory();
      setRows(rows.filter((row) => row.id !== id));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // 1. Validation
      const currentSheet = tabs[activeTab].sheet;
      if (currentSheet === 'threshold') { // Only validate Threshold logic
          for (const row of rows) {
            if (!validateRow(row)) {
              throw new Error(`Validation Error in row: ${row['Exc Type']} (${row['Class']}). Check Logic.`);
            }
          }
      }

      const rowsSnapshot = rows.map(row => ({ ...row }));
      const payload = transformGridToMetadata(rowsSnapshot);
      const response = await metadataApi.saveMetadata(filename, payload, currentSheet);
      tabsDataCache.current[currentSheet] = rowsSnapshot;
      // ISSUE 4: Notify backup location
      if (response && response.backup) {
          showToast(`Configuration Saved! Backup: ${response.backup}`, 'success');
      } else {
          showToast('Configuration Saved & Backed Up!', 'success');
      }
    } catch (error: any) {
      console.error(error);
      // Clean up error message
      let msg = 'Save Failed';
      if (error.response?.data?.detail) {
          msg = error.response.data.detail;
      } else if (error.message) {
          msg = error.message;
      }
      showToast(msg, 'error');
    } finally {
      setSaving(false);
    }
  };

  const validateRow = (newRow: MetadataRow) => {
    const { L1, L2, L3, _prefix } = newRow;
    const mode = (_prefix.includes('Low') || _prefix.includes('Wear')) ? 'min' : 'max';

    if (mode === 'min') {
      if (L1 !== null && L2 !== null && L1 > L2) return false;
      if (L2 !== null && L3 !== null && L2 > L3) return false;
      if (L1 !== null && L3 !== null && L1 > L3) return false;
    } 
    else {
      if (L1 !== null && L2 !== null && L1 < L2) return false;
      if (L2 !== null && L3 !== null && L2 < L3) return false;
      if (L1 !== null && L3 !== null && L1 < L3) return false;
    }
    return true;
  };

  const processRowUpdate = (newRow: MetadataRow, oldRow: MetadataRow) => {
    const currentSheet = tabs[activeTab].sheet;
    
    // Update prefix if exc type changed
    if (newRow['Exc Type'] !== oldRow['Exc Type']) {
        const excType = newRow['Exc Type'] || '';
        let prefix = excType;
        if (excType.includes('Stagger')) prefix = 'Stagger';
        else if (excType.includes('Low Height')) prefix = 'Low Height';
        else if (excType.includes('High Height')) prefix = 'High Height';
        else if (excType.includes('Wire Wear')) prefix = 'Wire Wear';
        newRow._prefix = prefix;
    }

    if (currentSheet === 'threshold' && !validateRow(newRow)) {
      showToast(`Invalid Logic for ${newRow['Exc Type']}. Check L1/L2/L3 order.`, 'error');
      return oldRow;
    }
    
    addToHistory();
    const updatedRows = rows.map((row) => (row.id === newRow.id ? newRow : row));
    setRows(updatedRows);
    return newRow;
  };

  const handleAddRow = () => {
      setOpenAddDialog(true);
  };

  const confirmAddRow = () => {
      const currentSheet = tabs[activeTab].sheet;
      
      // ISSUE 1 Fix: Logic check in Add Row Dialog
      if (currentSheet === 'threshold') {
          const excType = newRowData['Exc Type'];
          let prefix = excType;
          if (excType.includes('Stagger')) prefix = 'Stagger';
          else if (excType.includes('Low Height')) prefix = 'Low Height';
          else if (excType.includes('High Height')) prefix = 'High Height';
          else if (excType.includes('Wire Wear')) prefix = 'Wire Wear';

          const tempRow: MetadataRow = {
              id: 'temp',
              Class: '',
              L1: Number(newRowData.L1),
              L2: Number(newRowData.L2),
              L3: Number(newRowData.L3),
              _prefix: prefix
          };

          if (!validateRow(tempRow)) {
              showToast(`Invalid Logic for ${excType}. Check L1/L2/L3 order.`, 'error');
              return; // Block add
          }
      }

      addToHistory();
      
      let newRow: MetadataRow;

      if (currentSheet === 'threshold' && isTov1050Workbook) {
          newRow = {
              id: `new_${Date.now()}`,
              Class: newRowData.Class,
              'Location Type': newRowData.Class,
              'Track Type': newRowData['Track Type'],
              'Exc Type': newRowData['Exc Type'],
              min: Number(newRowData.min),
              max: Number(newRowData.max),
              remark: newRowData.remark || '',
              L1: null,
              L2: null,
              L3: null,
              _prefix: '',
          };
      } else if (currentSheet === 'threshold') {
          const excType = newRowData['Exc Type'];
          let prefix = excType;
          if (excType.includes('Stagger')) prefix = 'Stagger';
          else if (excType.includes('Low Height')) prefix = 'Low Height';
          else if (excType.includes('High Height')) prefix = 'High Height';
          else if (excType.includes('Wire Wear')) prefix = 'Wire Wear';

          newRow = {
              id: `new_${Date.now()}`,
              Class: newRowData.Class,
              'Track Type': newRowData['Track Type'],
              'Exc Type': excType,
              L1: Number(newRowData.L1),
              L2: Number(newRowData.L2),
              L3: Number(newRowData.L3),
              _prefix: prefix
          };
      } else {
          return;
      }
      
      setRows([...rows, newRow]);
      setOpenAddDialog(false);
      showToast('Row Added', 'success');
  };

  const showToast = (message: string, severity: 'success' | 'error') => {
    setSnackbar({ open: true, message, severity });
  };

  // Filtered Rows
  const filteredRows = useMemo(() => {
    // Only filter for Threshold sheet
    if (tabs[activeTab]?.sheet !== 'threshold') return rows;

    return rows.filter(row => {
      if (filterExcType !== 'All' && row['Exc Type'] !== filterExcType) return false;
      if (filterTrackType !== 'All' && row['Track Type'] !== filterTrackType) return false;
      return true;
    });
  }, [rows, filterExcType, filterTrackType, tabs, activeTab]);

  // TOV1050 direction sheets contain interval metadata used by the detector.
  const isTrackDataSheet = (sheetName: string) => {
      if (!sheetName) return false;
      const lower = sheetName.toLowerCase();
      return lower.includes('track type');
  };

  // Dynamic Columns based on Tab
  const getColumns = (): GridColDef[] => {
      if (tabs.length === 0) return [];
      const currentSheet = tabs[activeTab].sheet;
      
      const actionCol: GridColDef = {
        field: 'actions',
        type: 'actions',
        headerName: 'Actions',
        width: 80,
        getActions: ({ id }) => {
            return [
                <GridActionsCellItem
                    key="delete"
                    icon={<DeleteIcon />}
                    label="Delete"
                    onClick={handleDeleteClick(id)}
                    color="inherit"
                />,
            ];
        },
      };

      if (currentSheet === 'threshold' && isTov1050Workbook && rows.some(row => 'Location Type' in row || 'min' in row || 'max' in row)) {
          const keys = rows.length > 0
            ? Object.keys(rows[0]).filter(k => !['id', '_prefix', 'L1', 'L2', 'L3', 'Location Type'].includes(k))
            : ['Class', 'Track Type', 'Exc Type', 'min', 'max', 'remark'];
          return [...keys.map(key => ({
            field: key,
            headerName: key === 'Class' ? 'Location Type' : key,
            width: 160,
            editable: true,
            type: ['min', 'max'].includes(key) ? 'number' : 'string',
          } as GridColDef)), actionCol];
      } else if (currentSheet === 'threshold') { // Thresholds
          return [
            { field: 'Class', headerName: 'Class', width: 120, editable: true },
            { 
                field: 'Track Type', 
                headerName: 'Track Type', 
                width: 150, 
                editable: true,
                type: 'singleSelect',
                valueOptions: TRACK_TYPES
            },
            { 
                field: 'Exc Type', 
                headerName: 'Exception Type', 
                width: 180, 
                editable: true,
                type: 'singleSelect',
                valueOptions: EXC_TYPES
            },
            { 
                field: 'L1', 
                headerName: 'Level 1 (Critical)', 
                width: 130, 
                editable: true, 
                type: 'number', 
                align: 'right', 
                headerAlign: 'right',
                cellClassName: 'cell-l1-critical'
            },
            { 
                field: 'L2', 
                headerName: 'Level 2 (Warning)', 
                width: 130, 
                editable: true, 
                type: 'number', 
                align: 'right', 
                headerAlign: 'right',
                cellClassName: 'cell-l2-warning'
            },
            { 
                field: 'L3', 
                headerName: 'Level 3 (Info)', 
                width: 130, 
                editable: true, 
                type: 'number', 
                align: 'right', 
                headerAlign: 'right',
                cellClassName: 'cell-l3-info'
            },
            actionCol
          ];
      } else {
          // TOV1050 direction and location sheets are intentionally rendered
          // from their workbook headers so schema changes remain visible.
          if (rows.length > 0) {
              const keys = Object.keys(rows[0]).filter(k => k !== 'id' && k !== '_prefix' && k !== 'L1' && k !== 'L2' && k !== 'L3');
              return [...keys.map(key => ({
                  field: key,
                  headerName: key,
                  width: 150,
                  editable: true
              })), actionCol];
          }
          
          return [actionCol];
      }
  };

  const currentSheetName = tabs.length > 0 ? tabs[activeTab].sheet : '';
  const isThresholdSheet = currentSheetName === 'threshold';
  const isTrackSheet = isTrackDataSheet(currentSheetName);

  return (
    <Box sx={scrollablePageSx}>
      {/* Header */}
      <Paper sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h6">Metadata Editor</Typography>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Configuration File</InputLabel>
            <Select
              value={filename}
              label="Configuration File"
              onChange={(e) => setFilename(e.target.value)}
            >
              {FILES.map(f => <MenuItem key={f} value={f}>{f}</MenuItem>)}
            </Select>
          </FormControl>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button 
            startIcon={<UndoIcon />} 
            onClick={handleUndo} 
            disabled={history.length === 0}
            variant="outlined"
            aria-label="Undo"
          >
            Undo
          </Button>
          <Button 
            startIcon={<RestoreIcon />} 
            onClick={() => loadData(true)} 
            variant="outlined"
            disabled={loading || saving}
          >
            Reload
          </Button>
          <Button 
            startIcon={<SaveIcon />} 
            variant="contained" 
            onClick={handleSave}
            disabled={loading || saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </Box>
      </Paper>
      
      {/* Tabs */}
      <Paper sx={{ mb: 1, flexShrink: 0 }}>
         {loadingSheets ? (
             <Box sx={{ p: 1 }}><CircularProgress size={24} /></Box>
         ) : (
             <Tabs 
                value={activeTab} 
                onChange={handleTabChange}
                variant="scrollable"
                scrollButtons="auto"
            >
                 {tabs.map((tab, idx) => (
                     <Tab key={idx} label={tab.label} />
                 ))}
             </Tabs>
         )}
      </Paper>

      {/* Warning Banner for direction interval sheets */}
      {isTrackSheet && (
          <Alert severity="warning" icon={<WarningAmberIcon />} sx={{ mb: 1 }}>
              Core Algorithm Data - Edit with Caution. Changing these values may affect track classification logic.
          </Alert>
      )}
      
      {/* Warning Banner for threshold configuration */}
      {isThresholdSheet && (
          <Alert severity="info" sx={{ mb: 1 }}>
              Please double click the latest version ‘WI/CBM/07’ threshold setting before edit.
          </Alert>
      )}

      {/* Threshold rows are the only sheet with a stable add-row contract. */}
      {isThresholdSheet && (
      <Toolbar sx={{ pl: 0, pr: 0, gap: 2, minHeight: 'auto', mb: 1 }}>
          <Button 
            startIcon={<AddIcon />} 
            variant="outlined" 
            onClick={handleAddRow}
          >
            Add Row
          </Button>
          
          {isThresholdSheet && (
          <>
            <Divider orientation="vertical" flexItem />
            <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>Exception Type</InputLabel>
                <Select value={filterExcType} label="Exception Type" onChange={(e) => setFilterExcType(e.target.value)}>
                    <MenuItem value="All">All</MenuItem>
                    {EXC_TYPES.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>Track Type</InputLabel>
                <Select value={filterTrackType} label="Track Type" onChange={(e) => setFilterTrackType(e.target.value)}>
                    <MenuItem value="All">All</MenuItem>
                    {TRACK_TYPES.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                </Select>
            </FormControl>
          </>
          )}
      </Toolbar>
      )}

      {/* Grid */}
      <Paper sx={{ ...fillDataRegionSx, flexGrow: 1, overflow: 'auto' }}>
        <DataGrid
          rows={filteredRows}
          columns={getColumns()}
          loading={loading}
          processRowUpdate={processRowUpdate}
          onProcessRowUpdateError={(err) => console.error(err)}
          disableRowSelectionOnClick
          slots={{ toolbar: GridToolbar }}
          sx={{
            '& .MuiDataGrid-cell:hover': {
              color: 'primary.main',
            },
            '& .cell-l1-critical': {
                color: '#d32f2f',
                fontWeight: 'bold',
                borderRight: '1px solid rgba(211, 47, 47, 0.2)'
            },
            '& .cell-l2-warning': {
                color: '#ed6c02',
                borderRight: '1px solid rgba(237, 108, 2, 0.2)'
            },
            '& .cell-l3-info': {
                color: '#0288d1',
                borderRight: '1px solid rgba(2, 136, 209, 0.2)'
            }
          }}
        />
      </Paper>

      {/* Add Row Dialog */}
      <Dialog open={openAddDialog} onClose={() => setOpenAddDialog(false)}>
          <DialogTitle>Add threshold row</DialogTitle>
          {/* ISSUE 1 Fix: Added pt: 2 to fix top cut-off */}
          <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1, pt: 2, minWidth: 400 }}>
              
              <DialogContentText sx={{ mb: 1, fontSize: '0.875rem', color: 'text.secondary' }}>
                  Add a threshold row using the same location and track labels as the selected workbook.
              </DialogContentText>

              <TextField 
                  label="Class" 
                  value={newRowData.Class} 
                  onChange={(e) => setNewRowData({...newRowData, Class: e.target.value})}
                  fullWidth 
              />
              
              {isThresholdSheet ? (
                  <>
                    <FormControl fullWidth>
                        <InputLabel>Track Type</InputLabel>
                        <Select
                            value={newRowData['Track Type']}
                            label="Track Type"
                            onChange={(e) => setNewRowData({...newRowData, 'Track Type': e.target.value})}
                        >
                            {/* ISSUE 3 Fix: Track Types updated */}
                            {TRACK_TYPES.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                        </Select>
                    </FormControl>
                    <FormControl fullWidth>
                        <InputLabel>Exception Type</InputLabel>
                        <Select
                            value={newRowData['Exc Type']}
                            label="Exception Type"
                            onChange={(e) => setNewRowData({...newRowData, 'Exc Type': e.target.value})}
                        >
                            {EXC_TYPES.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                        </Select>
                    </FormControl>
                    {isTov1050Workbook ? (
                      <>
                        <TextField label="Minimum" type="number" value={newRowData.min ?? ''} onChange={(e) => setNewRowData({...newRowData, min: Number(e.target.value)})} fullWidth />
                        <TextField label="Maximum" type="number" value={newRowData.max ?? ''} onChange={(e) => setNewRowData({...newRowData, max: Number(e.target.value)})} fullWidth />
                        <TextField label="Remark" value={newRowData.remark ?? ''} onChange={(e) => setNewRowData({...newRowData, remark: e.target.value})} fullWidth />
                      </>
                    ) : (<Box sx={{ display: 'flex', gap: 2 }}>
                        <TextField 
                            label="L1 (Critical)" type="number" 
                            value={newRowData.L1} 
                            onChange={(e) => setNewRowData({...newRowData, L1: Number(e.target.value)})}
                        />
                        <TextField 
                            label="L2 (Warning)" type="number" 
                            value={newRowData.L2} 
                            onChange={(e) => setNewRowData({...newRowData, L2: Number(e.target.value)})}
                        />
                        <TextField 
                            label="L3 (Info)" type="number" 
                            value={newRowData.L3} 
                            onChange={(e) => setNewRowData({...newRowData, L3: Number(e.target.value)})}
                        />
                    </Box>)}
                  </>
              ) : null}
          </DialogContent>
          <DialogActions>
              <Button onClick={() => setOpenAddDialog(false)}>Cancel</Button>
              <Button onClick={confirmAddRow} variant="contained">Add</Button>
          </DialogActions>
      </Dialog>

      <Snackbar 
        open={snackbar.open} 
        autoHideDuration={6000} 
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default MetadataEditorView;
