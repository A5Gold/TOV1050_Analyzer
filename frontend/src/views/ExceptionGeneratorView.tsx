import React, { useEffect, useState } from 'react';
import { 
  Box, Button, Card, CardContent, FormControl, InputLabel, 
  MenuItem, Select, TextField, Typography, CircularProgress, 
  Alert, ToggleButton, ToggleButtonGroup, Stack, Paper, Tabs, Tab, Snackbar
} from '@mui/material';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import BarChartIcon from '@mui/icons-material/BarChart';
import TableChartIcon from '@mui/icons-material/TableChart';
import CloseIcon from '@mui/icons-material/Close';
import AddIcon from '@mui/icons-material/Add';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import DownloadIcon from '@mui/icons-material/Download';
// SaveIcon removed - Sub-module 1 deprecated

import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

import apiClient from '../api/client';
import { AnalyzeRequest, AnalysisResponse } from '../types/api';
import ChartComponent from '../components/ChartComponent';
import ExceptionList from '../components/ExceptionList';
import ExceptionTable from '../components/ExceptionTable';
import { useAnalysisStore, AnalysisSession } from '../store/useAnalysisStore';
// useDatabaseStore removed - Sub-module 1 (Exception Record) deprecated
import ExceptionAlgorithmDialog from '../components/ExceptionGenerator/ExceptionAlgorithmDialog';
import { fillDataRegionSx, scrollablePageSx } from '../utils/pageLayout';
import { TOV1050_DIRECTIONS, TOV1050_LINES, sessionsForLine } from '../config/tov1050';

// Enable custom parsing for dayjs
dayjs.extend(customParseFormat);

// Section Options Configuration
const generateId = () => Date.now().toString(36) + Math.random().toString(36).substr(2);

const ExceptionGeneratorView = () => {
  const { 
    analysisSessions, 
    activeAnalysisTabId, 
    addAnalysisSession, 
    removeAnalysisSession, 
    updateAnalysisSession, 
    setActiveAnalysisTab, 
    resetAnalysisSessions 
  } = useAnalysisStore();

  // Sub-module 1 (Save to DB) deprecated - removed saveExceptionRecords

  const [tutorialOpen, setTutorialOpen] = useState(false);
  const [toast, setToast] = useState<{ open: boolean; message: string; severity: 'info' | 'success' | 'error' }>({ open: false, message: '', severity: 'info' });
  const [isDragActive, setIsDragActive] = React.useState(false);

  const handleCloseToast = () => setToast({ ...toast, open: false });

  const handleAddTab = () => {
    const newId = generateId();
    const newSession: AnalysisSession = {
      id: newId,
      label: `Analysis ${analysisSessions.length + 1}`,
      filePath: '',
      line: TOV1050_LINES[0],
      section: 'Mainline',
      track: TOV1050_DIRECTIONS[0],
      dateStr: new Date().toISOString().slice(0, 10).replace(/-/g, ''),
      // Initialize optional fields as undefined
      taskNo: undefined,
      stationStart: undefined,
      stationEnd: undefined,
      result: null,
      loading: false,
      error: null,
      viewMode: 'graph',
      selectedExceptionId: null
    };
    addAnalysisSession(newSession);
  };

  const handleCloseTab = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    removeAnalysisSession(id);
  };

  const handleResetAll = () => {
    if (window.confirm("Are you sure you want to close all tabs and reset?")) {
        resetAnalysisSessions();
    }
  };

  // --- Active Session Handlers ---

  const activeSession = analysisSessions.find(s => s.id === activeAnalysisTabId);

  const handleOpenFile = async () => {
    if (!activeSession) return;
    if (window.electronAPI) {
      const path = await window.electronAPI.openFile();
      if (path) {
          const fileName = path.split('\\').pop()?.split('/').pop() || path;
          updateAnalysisSession(activeSession.id, { filePath: path, label: fileName });
      }
    } else {
      const mockPath = "C:\\Mock\\Path\\Data.csv";
      updateAnalysisSession(activeSession.id, { filePath: mockPath, label: "Data.csv" });
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    if (!activeSession) return;
    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;
    const filePath = (files[0] as any).path;
    if (filePath) {
      const fileName = filePath.split('\\').pop()?.split('/').pop() || filePath;
      updateAnalysisSession(activeSession.id, { filePath, label: fileName });
    }
  };

  const handleAnalyze = async () => {
    if (!activeSession) return;
    if (!activeSession.filePath) {
      updateAnalysisSession(activeSession.id, { error: "Please select a data file first." });
      return;
    }

    updateAnalysisSession(activeSession.id, { loading: true, error: null });

    const payload: AnalyzeRequest = {
      file_path: activeSession.filePath,
      line: activeSession.line,
      section: activeSession.section,
      track: activeSession.track,
      date_str: activeSession.dateStr,
      // Optional fields for custom naming
      task_no: activeSession.taskNo,
      station_start: activeSession.stationStart,
      station_end: activeSession.stationEnd
    };

    try {
      const response = await apiClient.post<AnalysisResponse>('/analyze', payload);
      updateAnalysisSession(activeSession.id, { result: response.data, loading: false });
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Analysis failed";
      updateAnalysisSession(activeSession.id, { error: msg, loading: false });
    }
  };

    const handleExport = async (type: 'report' | 'raw') => {
        if (!activeSession) return;
        
        setToast({ open: true, message: 'Generating Report...', severity: 'info' });

        try {
            let response;
            if (type === 'report') {
                if (!activeSession.result) {
                    setToast({ open: true, message: 'No analysis result to export.', severity: 'error' });
                    return;
                }
                const payload = {
                    exceptions: activeSession.result.exceptions,
                    boundaries: activeSession.result.boundaries,
                    chart_data: activeSession.result.chart_data,
                    params: activeSession.result.params
                };
                response = await apiClient.post('/export/report/generate', payload, { responseType: 'blob' });
            } else {
                // BUG 10.7-2 FIX: Use POST endpoint with session data instead of GET with global state
                // This ensures each tab exports its own data, not the last analyzed data.
                if (!activeSession.result) {
                    setToast({ open: true, message: 'No analysis result to export.', severity: 'error' });
                    return;
                }
                const payload = {
                    chart_data: activeSession.result.chart_data,
                    params: {
                        date_str: activeSession.dateStr,
                        line: activeSession.line,
                        track: activeSession.track,
                        section: activeSession.section,
                        task_no: activeSession.taskNo,
                        station_start: activeSession.stationStart,
                        station_end: activeSession.stationEnd
                    }
                };
                response = await apiClient.post('/export/raw/generate', payload, { responseType: 'blob' });
            }
            
            // Try to extract filename from Content-Disposition header
            const contentDisposition = response.headers['content-disposition'];
            let filename = type === 'report' ? 'Analysis_Report.xlsx' : 'Raw_Data.csv';
            
            // Construct fallback filename based on current session with conditional naming logic
            if (activeSession) {
                 const { dateStr, line, track, section, taskNo, stationStart, stationEnd } = activeSession;
                 const ext = type === 'report' ? 'xlsx' : 'csv';
                 const suffix = type === 'report' ? 'Exception_Report' : 'Catenary_Report';
                 
                 // Conditional naming logic (same as backend)
                 const useCustomMode = taskNo && stationStart && stationEnd;
                 const middlePart = useCustomMode 
                     ? `${taskNo}_${stationStart.toUpperCase()}-${stationEnd.toUpperCase()}`
                     : `${track}_${section}`;
                 
                 filename = `${dateStr}_${line}_${middlePart}_${suffix}.${ext}`;
            }
            
            if (contentDisposition) {
                 // Priority 1: UTF-8 filename
                 const filenameMatch = contentDisposition.match(/filename\*=utf-8''(.+)/i);
                 // Priority 2: Standard filename
                 const filenameMatch2 = contentDisposition.match(/filename="?([^"]+)"?/i);
                 
                 if (filenameMatch && filenameMatch[1]) {
                     filename = decodeURIComponent(filenameMatch[1]);
                 } else if (filenameMatch2 && filenameMatch2[1]) {
                     filename = filenameMatch2[1];
                 }
            }

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
            
            setToast({ open: true, message: 'File Saved Successfully', severity: 'success' });
        } catch (err) {
            console.error("Export failed", err);
            updateAnalysisSession(activeSession.id, { error: "Export failed." });
            setToast({ open: true, message: 'Export Failed', severity: 'error' });
        }
    };

  // Sub-module 1 (Save to DB) has been deprecated and removed
  // Use History Compare module -> Save to DB for repeated exceptions

  // Dynamic Section Logic for Active Session
  useEffect(() => {
    if (!activeSession) return;
      const validSections = sessionsForLine(activeSession.line);
    if (!validSections.includes(activeSession.section)) {
       updateAnalysisSession(activeSession.id, { section: validSections[0] || '' });
    }
  }, [activeSession?.line]); // Only run when line changes

  // --- Render ---

  return (
    <Box sx={{ ...scrollablePageSx, width: '100%', gap: 0 }}>
      {/* Top Bar: Tabs & Actions */}
      <Paper elevation={1} square sx={{ display: 'flex', alignItems: 'center', bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider' }}>
        <Tabs 
            value={activeAnalysisTabId} 
            onChange={(_, val) => setActiveAnalysisTab(val)} 
            variant="scrollable" 
            scrollButtons="auto"
            sx={{ flexGrow: 1, minHeight: 48 }}
        >
            {analysisSessions.map(session => (
                <Tab 
                    key={session.id} 
                    value={session.id} 
                    label={
                        <Box sx={{ display: 'flex', alignItems: 'center', textTransform: 'none' }}>
                            <Typography variant="body2" sx={{ mr: 1, fontWeight: activeAnalysisTabId === session.id ? 'bold' : 'normal' }}>
                                {session.label}
                            </Typography>
                            <Box 
                                component="span"
                                onClick={(e) => handleCloseTab(e, session.id)}
                                sx={{ 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    justifyContent: 'center',
                                    borderRadius: '50%', 
                                    p: 0.2,
                                    '&:hover': { bgcolor: 'rgba(0,0,0,0.1)' } 
                                }}
                            >
                                <CloseIcon fontSize="small" sx={{ fontSize: '0.9rem' }} />
                            </Box>
                        </Box>
                    }
                    sx={{ minHeight: 48 }}
                />
            ))}
        </Tabs>
        <Stack direction="row" spacing={1} sx={{ p: 1 }}>
            {/* Logic Button Left of New Analysis */}
            <Button 
                startIcon={<HelpOutlineIcon />} 
                variant="text" 
                size="small"
                onClick={() => setTutorialOpen(true)}
            >
                Logic
            </Button>
            <Button 
                variant="outlined" 
                size="small" 
                startIcon={<AddIcon />} 
                onClick={handleAddTab}
            >
                New Analysis
            </Button>
            <Button 
                variant="outlined" 
                color="error"
                size="small" 
                startIcon={<RestartAltIcon />} 
                onClick={handleResetAll}
                disabled={analysisSessions.length === 0}
            >
                Reset All
            </Button>
        </Stack>
      </Paper>

      {/* Main Content Area */}
      <Box sx={{ ...fillDataRegionSx, flexGrow: 1, position: 'relative' }}>
        {analysisSessions.length === 0 ? (
            <Box sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                justifyContent: 'center', 
                height: '100%',
                color: 'text.secondary'
            }}>
                <Typography variant="h5" gutterBottom>No Active Analysis</Typography>
                <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddTab}>
                    Start New Analysis
                </Button>
            </Box>
        ) : activeSession ? (
            // Show Active Session
            activeSession.result ? (
                // Result View
                <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', minHeight: 0 }}>
                     {/* Toolbar */}
                    <Paper 
                        elevation={0} 
                        sx={{ 
                        p: 1, 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center',
                        borderBottom: 1,
                        borderColor: 'divider'
                        }}
                    >
                        <Stack direction="row" spacing={2} alignItems="center">
                             <Typography variant="subtitle2" color="primary">
                                {activeSession.label}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                {activeSession.line} - {activeSession.track} - {activeSession.section} ({activeSession.dateStr})
                            </Typography>
                            <Button 
                                variant="outlined" 
                                size="small" 
                                startIcon={<DownloadIcon />} 
                                onClick={() => handleExport('report')}
                            >
                                Report
                            </Button>
                            <Button 
                                variant="outlined" 
                                size="small" 
                                startIcon={<DownloadIcon />} 
                                onClick={() => handleExport('raw')}
                            >
                                Raw
                            </Button>
                            {/* Save to DB button removed - Sub-module 1 deprecated */}
                        </Stack>
                        
                        <ToggleButtonGroup
                            value={activeSession.viewMode}
                            exclusive
                            onChange={(_, newView) => {
                                if (newView) updateAnalysisSession(activeSession.id, { viewMode: newView });
                            }}
                            size="small"
                        >
                            <ToggleButton value="graph">
                                <BarChartIcon sx={{ mr: 1 }} /> Graph
                            </ToggleButton>
                            <ToggleButton value="table">
                                <TableChartIcon sx={{ mr: 1 }} /> Table
                            </ToggleButton>
                        </ToggleButtonGroup>
                    </Paper>

                    {/* Content */}
                    <Box sx={{ flexGrow: 1, minHeight: 0, overflow: 'hidden' }}>
                        {activeSession.viewMode === 'graph' ? (
                            <Box sx={{ display: 'flex', width: '100%', height: '100%' }}>
                                <Box sx={{ flexGrow: 1, height: '100%', minWidth: 0 }}>
                                    <ChartComponent 
                                        result={activeSession.result}
                                        selectedExceptionId={activeSession.selectedExceptionId}
                                        onSelectException={(id) => updateAnalysisSession(activeSession.id, { selectedExceptionId: id })}
                                        sessionId={activeSession.id}
                                    />
                                </Box>
                                <Box sx={{ width: 320, height: '100%', flexShrink: 0 }}>
                                    <ExceptionList 
                                        result={activeSession.result}
                                        selectedExceptionId={activeSession.selectedExceptionId}
                                        onSelectException={(id) => updateAnalysisSession(activeSession.id, { selectedExceptionId: id })}
                                    />
                                </Box>
                            </Box>
                        ) : (
                            <Box sx={{ width: '100%', height: '100%', p: 2 }}>
                                {/* Bug 10.6-4: Pass Task Run Data to ExceptionTable */}
                                <ExceptionTable 
                                  result={activeSession.result} 
                                  taskRunData={{
                                    line: activeSession.line,
                                    track: activeSession.track,
                                    task_no: activeSession.taskNo,
                                    station_start: activeSession.stationStart,
                                    station_end: activeSession.stationEnd,
                                    task_run_date: activeSession.dateStr,
                                  }}
                                />
                            </Box>
                        )}
                    </Box>
                </Box>
            ) : (
                // Config View
                <Box sx={{ 
                    display: 'flex', 
                    flexDirection: 'column', 
                    alignItems: 'center', 
                    justifyContent: 'center', 
                    height: '100%',
                    gap: 3,
                    overflow: 'auto'
                }}>
                    <Typography variant="h4" component="h1" gutterBottom>
                        Configuration
                    </Typography>

                    <Card sx={{ minWidth: 400, maxWidth: 600, width: '90%' }}>
                        <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                            {/* File Selection */}
                            <Box
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onDrop={handleDrop}
                                sx={{
                                    border: '2px dashed',
                                    borderColor: isDragActive ? 'primary.main' : 'transparent',
                                    borderRadius: 1,
                                    transition: 'border-color 0.15s ease',
                                    p: isDragActive ? 1 : 0,
                                }}
                            >
                                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                                    <TextField
                                        fullWidth
                                        label="Data File Path"
                                        value={activeSession.filePath}
                                        InputProps={{ readOnly: true }}
                                        size="small"
                                        error={!activeSession.filePath && !!activeSession.error}
                                    />
                                    <Button
                                        variant="contained"
                                        startIcon={<UploadFileIcon />}
                                        onClick={handleOpenFile}
                                        sx={{ whiteSpace: 'nowrap' }}
                                    >
                                        Browse
                                    </Button>
                                </Box>
                                {!activeSession.filePath && (
                                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, textAlign: 'center' }}>
                                        Drop TOV1050 .csv file here or click Browse
                                    </Typography>
                                )}
                            </Box>

                            {/* Parameters */}
                            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                                <FormControl fullWidth size="small">
                                    <InputLabel>Line</InputLabel>
                                    <Select 
                                        value={activeSession.line} 
                                        label="Line" 
                                        onChange={(e) => updateAnalysisSession(activeSession.id, { line: e.target.value })}
                                    >
                                        {TOV1050_LINES.map((line) => <MenuItem key={line} value={line}>{line}</MenuItem>)}
                                    </Select>
                                </FormControl>

                                <FormControl fullWidth size="small">
                                    <InputLabel>Track</InputLabel>
                                    <Select 
                                        value={activeSession.track} 
                                        label="Track" 
                                        onChange={(e) => updateAnalysisSession(activeSession.id, { track: e.target.value })}
                                    >
                                        {TOV1050_DIRECTIONS.map((direction) => <MenuItem key={direction} value={direction}>{direction} Track</MenuItem>)}
                                    </Select>
                                </FormControl>

                                <FormControl fullWidth size="small">
                                    <InputLabel>Section</InputLabel>
                                    <Select 
                                        value={activeSession.section} 
                                        label="Section" 
                                        onChange={(e) => updateAnalysisSession(activeSession.id, { section: e.target.value })}
                                    >
                                        {sessionsForLine(activeSession.line).map((opt) => (
                                            <MenuItem key={opt} value={opt}>{opt}</MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>

                                <LocalizationProvider dateAdapter={AdapterDayjs}>
                                    <DatePicker
                                        label="Date"
                                        format="YYYYMMDD"
                                        value={activeSession.dateStr ? dayjs(activeSession.dateStr, 'YYYYMMDD') : null}
                                        onChange={(newValue) => {
                                            if (newValue) {
                                                updateAnalysisSession(activeSession.id, { dateStr: newValue.format('YYYYMMDD') });
                                            }
                                        }}
                                        slotProps={{ textField: { size: 'small', fullWidth: true } }}
                                    />
                                </LocalizationProvider>
                            </Box>

                            {/* Optional Fields for Custom File Naming */}
                            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 2 }}>
                                <TextField
                                    label="Task Number (Optional)"
                                    placeholder="e.g., inspection task code"
                                    size="small"
                                    fullWidth
                                    value={activeSession.taskNo || ''}
                                    onChange={(e) => updateAnalysisSession(activeSession.id, { 
                                        taskNo: e.target.value.trim() || undefined 
                                    })}
                                    helperText="For custom naming"
                                />

                                <TextField
                                    label="Station Start (Optional)"
                                    placeholder="e.g., HUH, LOW"
                                    size="small"
                                    fullWidth
                                    value={activeSession.stationStart || ''}
                                    onChange={(e) => updateAnalysisSession(activeSession.id, { 
                                        stationStart: e.target.value.trim().toUpperCase() || undefined 
                                    })}
                                    helperText="Station code"
                                />

                                <TextField
                                    label="Station End (Optional)"
                                    placeholder="e.g., TAP, KSR"
                                    size="small"
                                    fullWidth
                                    value={activeSession.stationEnd || ''}
                                    onChange={(e) => updateAnalysisSession(activeSession.id, { 
                                        stationEnd: e.target.value.trim().toUpperCase() || undefined 
                                    })}
                                    helperText="Station code"
                                />
                            </Box>

                            {/* Error Message */}
                            {activeSession.error && <Alert severity="error">{activeSession.error}</Alert>}

                            {/* Submit Action */}
                            <Button 
                                variant="contained" 
                                color="primary" 
                                size="large"
                                startIcon={activeSession.loading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
                                onClick={handleAnalyze}
                                disabled={activeSession.loading || !activeSession.filePath}
                                fullWidth
                            >
                                {activeSession.loading ? "Analyzing..." : "Start Analysis"}
                            </Button>
                        </CardContent>
                    </Card>
                </Box>
            )
        ) : (
             <Box sx={{ p: 3 }}>Select a tab</Box>
        )}
      </Box>

      <ExceptionAlgorithmDialog 
        open={tutorialOpen} 
        onClose={() => setTutorialOpen(false)} 
      />

      <Snackbar 
        open={toast.open} 
        autoHideDuration={6000} 
        onClose={handleCloseToast}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseToast} severity={toast.severity} sx={{ width: '100%' }}>
            {toast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ExceptionGeneratorView;
