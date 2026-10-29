import React, { useEffect, useState } from 'react';
import {
  Box, Button, Card, CardContent, FormControl, InputLabel,
  MenuItem, Select, TextField, Typography, CircularProgress,
  Alert, ToggleButton, ToggleButtonGroup, Stack, Paper, Tabs, Tab, Snackbar, Autocomplete, Chip
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
import { AnalysisMode, AnalyzeRequest, AnalysisResponse, BackgroundJob } from '../types/api';
import { isActiveJob, jobErrorMessage, JOB_REQUEST_TIMEOUT, waitForJob } from '../api/analysisJobs';
import ChartComponent from '../components/ChartComponent';
import ExceptionList from '../components/ExceptionList';
import ExceptionTable from '../components/ExceptionTable';
import { useAnalysisStore, AnalysisSession } from '../store/useAnalysisStore';
// useDatabaseStore removed - Sub-module 1 (Exception Record) deprecated
import ExceptionAlgorithmDialog from '../components/ExceptionGenerator/ExceptionAlgorithmDialog';
import TaskLoadingState from '../components/TaskLoadingState';
import { fillDataRegionSx, scrollablePageSx } from '../utils/pageLayout';
import { TOV1050_DIRECTIONS, TOV1050_LINES, TOV1050_RUN_PRESETS, Tov1050RunPreset } from '../config/tov1050';
import { PARENT_LINES, sectionsForLine, sectionOptionsForLine, lineDefinition } from '../config/lineCatalog';

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
    const session = useAnalysisStore.getState().analysisSessions.find(s => s.id === id);
    [session?.analysisJob, session?.exportJob].forEach(job => {
      if (isActiveJob(job)) void apiClient.post(`/jobs/${job!.job_id}/cancel`, null, {
        params: { client_session_id: id }, timeout: JOB_REQUEST_TIMEOUT,
      }).catch(() => undefined);
    });
    removeAnalysisSession(id);
  };

  const handleResetAll = () => {
    if (window.confirm("Are you sure you want to close all tabs and reset?")) {
        analysisSessions.forEach(session => [session.analysisJob, session.exportJob].forEach(job => {
          if (isActiveJob(job)) void apiClient.post(`/jobs/${job!.job_id}/cancel`, null, {
            params: { client_session_id: session.id }, timeout: JOB_REQUEST_TIMEOUT,
          }).catch(() => undefined);
        }));
        resetAnalysisSessions();
    }
  };

  // --- Active Session Handlers ---

  const activeSession = analysisSessions.find(s => s.id === activeAnalysisTabId);
  const exporting = !!activeSession?.exporting;
  const rawOverview = activeSession?.result?.analysis_mode === 'raw_overview';

  const runPresetsForLine = activeSession
    ? TOV1050_RUN_PRESETS.filter(preset => preset.line === activeSession.line)
    : [];
  const selectedRunPreset = activeSession
    ? runPresetsForLine.find(preset => (
      preset.track === activeSession.track
      && preset.section === activeSession.section
      && preset.taskNo === activeSession.taskNo
      && preset.stationStart === activeSession.stationStart
      && preset.stationEnd === activeSession.stationEnd
    )) || null
    : null;

  const applyRunPreset = (preset: Tov1050RunPreset | null) => {
    if (!activeSession || !preset) return;
    updateAnalysisSession(activeSession.id, {
      line: preset.line,
      track: preset.track,
      section: preset.section,
      taskNo: preset.taskNo,
      stationStart: preset.stationStart,
      stationEnd: preset.stationEnd,
      result: null,
      error: null,
    });
  };

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
    if (!activeSession || activeSession.loading || isActiveJob(activeSession.analysisJob)) return;
    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;
    const filePath = (files[0] as any).path;
    if (filePath) {
      const fileName = filePath.split('\\').pop()?.split('/').pop() || filePath;
      updateAnalysisSession(activeSession.id, { filePath, label: fileName });
    }
  };

  const handleAnalyze = async (mode: AnalysisMode = 'median') => {
    if (!activeSession || activeSession.loading || isActiveJob(activeSession.analysisJob)) return;
    if (!activeSession.filePath) {
      updateAnalysisSession(activeSession.id, { error: "Please select a data file first." });
      return;
    }
    if (!activeSession.stationStart || !activeSession.stationEnd) {
      updateAnalysisSession(activeSession.id, {
        error: "Please enter Station Start and Station End before analysis. These fields define the output report context.",
      });
      return;
    }

    const session = activeSession;
    updateAnalysisSession(session.id, { loading: true, error: null, analysisJob: null, result: null,
      analysisMode: mode, selectedExceptionId: null, viewMode: 'graph', exportJob: null, downloadStatus: null });
    const payload: AnalyzeRequest = {
      file_path: session.filePath, line: session.line, section: session.section,
      track: session.track, date_str: session.dateStr, task_no: session.taskNo,
      station_start: session.stationStart, station_end: session.stationEnd,
      client_session_id: session.id, analysis_mode: mode, chart_data_mode: mode === 'median' ? 'chainage_median' : 'raw',
    };
    try {
      const response = await apiClient.post<BackgroundJob>('/analysis/jobs', payload, { timeout: JOB_REQUEST_TIMEOUT });
      const current = getSession(session.id);
      if (!current) {
        void apiClient.post(`/jobs/${response.data.job_id}/cancel`, null, {
          params: { client_session_id: session.id }, timeout: JOB_REQUEST_TIMEOUT,
        }).catch(() => undefined);
        return;
      }
      updateAnalysisSession(session.id, { analysisJob: response.data });
      await observeAnalysis(session.id, response.data);
    } catch (error) {
      updateAnalysisSession(session.id, { loading: false, error: await jobErrorMessage(error, '分析失敗') });
    }
  };

  const getSession = (id: string) => useAnalysisStore.getState().analysisSessions.find(s => s.id === id);
  const ownsJob = (id: string, job: BackgroundJob, kind: 'analysisJob' | 'exportJob') => (
    getSession(id)?.[kind]?.job_id === job.job_id
  );

  const observeAnalysis = async (id: string, initial: BackgroundJob) => {
    updateAnalysisSession(id, { loading: true, error: null });
    try {
      const ready = await waitForJob(initial, id,
        job => { if (ownsJob(id, initial, 'analysisJob')) updateAnalysisSession(id, { analysisJob: job }); },
        () => ownsJob(id, initial, 'analysisJob'));
      const response = await apiClient.get<AnalysisResponse>(`/jobs/${ready.job_id}/result`, {
        params: { client_session_id: id }, timeout: JOB_REQUEST_TIMEOUT,
      });
      if (ownsJob(id, initial, 'analysisJob')) updateAnalysisSession(id, {
        result: response.data, loading: false, exportJob: null, exporting: false, downloadStatus: null,
        selectedExceptionId: null, viewMode: 'graph',
      });
    } catch (error) {
      if (ownsJob(id, initial, 'analysisJob')) updateAnalysisSession(id, {
        error: await jobErrorMessage(error, '分析失敗'), loading: false,
      });
    }
  };

  const saveDownload = (response: any, fallback: string) => {
    const disposition = response.headers?.['content-disposition'];
    const encoded = disposition?.match(/filename\*=utf-8''([^;]+)/i);
    const plain = disposition?.match(/filename="?([^";]+)"?/i);
    const filename = encoded ? decodeURIComponent(encoded[1]) : plain?.[1] || fallback;
    const url = window.URL.createObjectURL(response.data instanceof Blob ? response.data : new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => window.URL.revokeObjectURL(url), 1_000);
  };

  const downloadReport = async (id: string, job: BackgroundJob) => {
    if (!ownsJob(id, job, 'exportJob')) return;
    updateAnalysisSession(id, { downloadStatus: 'downloading', error: null });
    try {
      const response = await apiClient.get(`/jobs/${job.job_id}/download`, {
        params: { client_session_id: id }, responseType: 'blob', timeout: 300_000,
      });
      if (!ownsJob(id, job, 'exportJob')) return;
      saveDownload(response, 'Exception_Report.xlsx');
      updateAnalysisSession(id, { downloadStatus: 'downloaded' });
      setToast({ open: true, message: '報表已交由瀏覽器下載', severity: 'success' });
    } catch (error) {
      if (ownsJob(id, job, 'exportJob')) updateAnalysisSession(id, {
        error: await jobErrorMessage(error, '下載失敗，可重試下載'), downloadStatus: 'failed',
      });
    }
  };

  const observeExport = async (id: string, initial: BackgroundJob) => {
    updateAnalysisSession(id, { exporting: true, error: null });
    try {
      const ready = await waitForJob(initial, id,
        job => { if (ownsJob(id, initial, 'exportJob')) updateAnalysisSession(id, { exportJob: job }); },
        () => ownsJob(id, initial, 'exportJob'));
      await downloadReport(id, ready);
    } catch (error) {
      if (ownsJob(id, initial, 'exportJob')) updateAnalysisSession(id, {
        error: await jobErrorMessage(error, '報表產生失敗'),
      });
    } finally {
      if (ownsJob(id, initial, 'exportJob')) updateAnalysisSession(id, { exporting: false });
    }
  };

  const cancelJob = async (id: string, job: BackgroundJob, kind: 'analysisJob' | 'exportJob') => {
    try {
      const response = await apiClient.post<BackgroundJob>(`/jobs/${job.job_id}/cancel`, null, {
        params: { client_session_id: id }, timeout: JOB_REQUEST_TIMEOUT,
      });
      if (ownsJob(id, job, kind) && isActiveJob(getSession(id)?.[kind])) {
        updateAnalysisSession(id, { [kind]: response.data });
      }
    } catch (error) {
      if (ownsJob(id, job, kind)) updateAnalysisSession(id, { error: await jobErrorMessage(error, '無法取消，請重試') });
    }
  };

  const handleExport = async () => {
    if (!activeSession?.result || activeSession.exporting || activeSession.result.analysis_mode === 'raw_overview') return;
    const session = activeSession;
    updateAnalysisSession(session.id, { exporting: true, error: null });
    try {
      const response = await apiClient.post<BackgroundJob>('/export/report/jobs', {
        client_session_id: session.id, analysis_revision: session.result!.analysis_revision,
        chart_data_mode: 'chainage_median',
      }, { timeout: JOB_REQUEST_TIMEOUT });
      const current = getSession(session.id);
      if (!current || current.result?.analysis_revision !== session.result!.analysis_revision) {
        void apiClient.post(`/jobs/${response.data.job_id}/cancel`, null, {
          params: { client_session_id: session.id }, timeout: JOB_REQUEST_TIMEOUT,
        }).catch(() => undefined);
        return;
      }
      updateAnalysisSession(session.id, { exportJob: response.data, exportMode: 'chainage_median', downloadStatus: null });
      await observeExport(session.id, response.data);
    } catch (error) {
      updateAnalysisSession(session.id, { error: await jobErrorMessage(error, '匯出失敗') });
    } finally {
      updateAnalysisSession(session.id, { exporting: false });
    }
  };

  // Sub-module 1 (Save to DB) has been deprecated and removed
  // Use History Compare module -> Save to DB for repeated exceptions

  // Dynamic Section Logic for Active Session
  useEffect(() => {
    if (!activeSession) return;
      const validSections = sectionsForLine(activeSession.line);
    if (!validSections.includes(activeSession.section)) {
       updateAnalysisSession(activeSession.id, {
         section: validSections[0] || '',
         result: null,
         error: null,
       });
    }
  }, [activeSession?.line]); // Only run when line changes

  // --- Render ---

  return (
    <Box sx={{ ...scrollablePageSx, width: '100%', gap: 0 }}>
      {/* Top Bar: Tabs & Actions */}
      <Paper elevation={1} square sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
            value={activeAnalysisTabId}
            onChange={(_, val) => setActiveAnalysisTab(val)}
            variant="scrollable"
            scrollButtons="auto"
            sx={{ flexGrow: 1, minWidth: 0, maxWidth: '100%', minHeight: 48 }}
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
      <Box sx={{ ...fillDataRegionSx, flexGrow: 1, position: 'relative', overflowY: activeSession?.result && activeSession.viewMode === 'graph' ? 'auto' : 'hidden' }}>
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
                <Box sx={{ display: 'flex', flexDirection: 'column', height: activeSession.viewMode === 'graph' ? 'auto' : '100%', minHeight: activeSession.viewMode === 'graph' ? '100%' : 0, width: '100%', flexShrink: 0 }}>
                     {/* Toolbar */}
                    <Paper
                        elevation={0}
                        sx={{
                        p: 1,
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: 1,
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        borderBottom: 1,
                        borderColor: 'divider'
                        }}
                    >
                        <Stack direction="row" useFlexGap spacing={1} alignItems="center" sx={{ flexWrap: 'wrap', minWidth: 0 }}>
                             <Typography variant="subtitle2" color="primary">
                                {activeSession.label}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                {activeSession.line} - {activeSession.track} - {activeSession.section} ({activeSession.dateStr})
                            </Typography>
                            <Button
                                variant="outlined"
                                size="small"
                                startIcon={exporting ? <CircularProgress size={16} /> : <DownloadIcon />}
                                onClick={handleExport}
                                disabled={rawOverview || exporting || activeSession.downloadStatus === 'downloading' || isActiveJob(activeSession.exportJob)}
                            >
                                匯出例外報表
                            </Button>
                            <Button variant="outlined" size="small"
                              onClick={() => handleAnalyze(rawOverview ? 'median' : 'raw_overview')}
                              disabled={activeSession.loading || exporting || activeSession.downloadStatus === 'downloading' || isActiveJob(activeSession.exportJob)}>
                              {rawOverview ? '返回中位樣本分析' : '原始資料概覽'}
                            </Button>
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
                            <ToggleButton value="table" disabled={rawOverview}>
                                <TableChartIcon sx={{ mr: 1 }} /> Table
                            </ToggleButton>
                        </ToggleButtonGroup>
                    </Paper>

                    {rawOverview && <Alert severity="info">原始資料概覽：略過同 Km 精簡及例外偵測，不能匯出例外報表。切回中位樣本分析會重新讀取原檔。</Alert>}
                    {exporting && (
                      <Box sx={{ px: 2, pt: 1 }}>
                        <TaskLoadingState stage="exporting" exportMode progress={activeSession.exportJob} />
                      </Box>
                    )}

                    {activeSession.error && <Alert severity="error">{activeSession.error}</Alert>}
                    {activeSession.exportJob && <Stack direction="row" spacing={1} sx={{ px: 2 }}>
                      {isActiveJob(activeSession.exportJob) && <Button onClick={() => cancelJob(activeSession.id, activeSession.exportJob!, 'exportJob')}>取消匯出</Button>}
                      {!exporting && isActiveJob(activeSession.exportJob) && <Button onClick={() => observeExport(activeSession.id, activeSession.exportJob!)}>重試查詢</Button>}
                      {activeSession.exportJob.status === 'ready' && activeSession.downloadStatus !== 'downloading' && <Button onClick={() => downloadReport(activeSession.id, activeSession.exportJob!)}>重新下載報表</Button>}
                      {activeSession.downloadStatus === 'downloading' && <Typography>正在下載報表…</Typography>}
                    </Stack>}
                    {/* Content */}
                    <Box sx={{ flex: activeSession.viewMode === 'graph' ? '1 0 auto' : '1 1 0', minHeight: 0, overflow: activeSession.viewMode === 'graph' ? 'visible' : 'hidden' }}>
                        {activeSession.viewMode === 'graph' ? (
                            <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, width: '100%', alignItems: 'stretch' }}>
                                <Box sx={{ flexGrow: 1, minHeight: 700, minWidth: 0 }}>
                                    <ChartComponent
                                        key={activeSession.id}
                                        result={activeSession.result}
                                        selectedExceptionId={activeSession.selectedExceptionId}
                                        onSelectException={(id) => updateAnalysisSession(activeSession.id, { selectedExceptionId: id })}
                                        sessionId={activeSession.id}
                                    />
                                </Box>
                                {!rawOverview && <Box sx={{ width: { xs: '100%', md: 320 }, height: { xs: 360, md: 700 }, flexShrink: 0, '& > .MuiPaper-root': { width: '100%' } }}>
                                    <ExceptionList
                                        result={activeSession.result}
                                        selectedExceptionId={activeSession.selectedExceptionId}
                                        onSelectException={(id) => updateAnalysisSession(activeSession.id, { selectedExceptionId: id })}
                                    />
                                </Box>}
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
                    height: '100%', minHeight: 0, overflowY: 'auto',
                    pb: 2,
                    gap: 3,
                }}>
                    <Box sx={{
                        position: 'sticky', top: 0, zIndex: 1,
                        bgcolor: 'background.default', width: '100%', flexShrink: 0,
                        py: 1.5, borderBottom: 1, borderColor: 'divider',
                    }}>
                        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}
                            alignItems={{ xs: 'stretch', sm: 'center' }} justifyContent="space-between">
                            <Typography variant="h4" component="h1">Configuration</Typography>
                            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ ml: { sm: 'auto' } }}>
                                <Button variant="outlined" onClick={() => handleAnalyze('raw_overview')}
                                  disabled={activeSession.loading || isActiveJob(activeSession.analysisJob) || !activeSession.filePath}>
                                  原始資料概覽
                                </Button>
                                <Button
                                    variant="contained"
                                    size="large"
                                    sx={{ minHeight: 40, bgcolor: '#b84f00', color: '#fff', '&:hover': { bgcolor: '#943f00' } }}
                                    startIcon={activeSession.loading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
                                    onClick={() => handleAnalyze('median')}
                                    disabled={activeSession.loading || isActiveJob(activeSession.analysisJob) || !activeSession.filePath}
                                >
                                    {activeSession.loading ? 'Analyzing...' : 'Start Analysis'}
                                </Button>
                            </Stack>
                        </Stack>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            正常分析會為各 channel 選取同 Km 中位實測樣本，圖表及報表使用相同資料；不另加噪訊濾波。
                        </Typography>
                        {activeSession.error && <Alert severity="error" sx={{ mt: 1 }}>{activeSession.error}</Alert>}
                    </Box>

                    {(activeSession.loading || isActiveJob(activeSession.analysisJob)) && <TaskLoadingState stage="detecting" progress={activeSession.analysisJob} />}
                    {activeSession.analysisJob && <Stack direction="row" spacing={1}>
                      {isActiveJob(activeSession.analysisJob) && <Button onClick={() => cancelJob(activeSession.id, activeSession.analysisJob!, 'analysisJob')}>取消分析</Button>}
                      {!activeSession.loading && (isActiveJob(activeSession.analysisJob) || activeSession.analysisJob.status === 'ready') && <Button onClick={() => observeAnalysis(activeSession.id, activeSession.analysisJob!)}>重試查詢</Button>}
                    </Stack>}

                    <Card sx={{ minWidth: 0, maxWidth: 600, width: '100%', flexShrink: 0 }}>
                        <CardContent component="fieldset" disabled={activeSession.loading || isActiveJob(activeSession.analysisJob)} sx={{ border: 0, m: 0, display: 'flex', flexDirection: 'column', gap: 3 }}>
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
                                <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: 1, alignItems: 'stretch' }}>
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
                                        Drop .csv or .datac file here or click Browse
                                    </Typography>
                                )}
                            </Box>

                            <Alert severity="info">
                                請確認 Line／Track／Section。分析及 Exception Report 使用下方選擇值，覆蓋原檔的路線與方向標籤。
                            </Alert>
                            {/* Parameters */}
                            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', sm: 'repeat(2, minmax(0, 1fr))' }, gap: 2 }}>
                            <Box sx={{ gridColumn: '1 / -1' }}>
                                <Autocomplete
                                    disabled={activeSession.loading || isActiveJob(activeSession.analysisJob)}
                                    size="small"
                                    options={runPresetsForLine}
                                    value={selectedRunPreset}
                                    onChange={(_, value) => applyRunPreset(value)}
                                    getOptionLabel={(option) => `${option.taskNo} · ${option.track} · ${option.stationStart} -> ${option.stationEnd}`}
                                    isOptionEqualToValue={(option, value) => option.taskCode === value.taskCode}
                                    renderInput={(params) => (
                                        <TextField {...params} label="Quick select run (from TOV1050 Run List)" placeholder="Choose a standard run or enter fields below" />
                                    )}
                                    noOptionsText="No standard run for this line"
                                />
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.75 }}>
                                    <Typography variant="caption" color="text.secondary">
                                        Quick select fills the context; fields remain editable for special cases.
                                    </Typography>
                                    {!selectedRunPreset && (activeSession.taskNo || activeSession.stationStart || activeSession.stationEnd) && (
                                        <Chip size="small" variant="outlined" color="warning" label="Custom override" />
                                    )}
                                </Box>
                            </Box>
                                <FormControl fullWidth size="small">
                                    <InputLabel id="analysis-line-label">Line</InputLabel>
                                    <Select
                                        labelId="analysis-line-label"
                                        disabled={activeSession.loading || isActiveJob(activeSession.analysisJob)}
                                        value={activeSession.line}
                                        label="Line"
                                        onChange={(e) => {
                                            const nextLine = e.target.value;
                                            updateAnalysisSession(activeSession.id, {
                                                line: nextLine,
                                                section: sectionsForLine(nextLine)[0] || '',
                                                track: lineDefinition(nextLine)?.directions[0] || '',
                                                result: null,
                                                loading: false,
                                                error: null,
                                                selectedExceptionId: null,
                                            });
                                        }}
                                    >
                                        {PARENT_LINES.map((line) => <MenuItem key={line} value={line}>{line}</MenuItem>)}
                                    </Select>
                                </FormControl>

                                <FormControl fullWidth size="small">
                                    <InputLabel id="analysis-section-label">Section</InputLabel>
                                    <Select
                                        labelId="analysis-section-label"
                                        disabled={activeSession.loading || isActiveJob(activeSession.analysisJob)}
                                        value={activeSession.section}
                                        label="Section"
                                        onChange={(e) => updateAnalysisSession(activeSession.id, { section: e.target.value })}
                                    >
                                        {sectionOptionsForLine(activeSession.line).map((opt) => (
                                            <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>

                                <FormControl fullWidth size="small">
                                    <InputLabel id="analysis-track-label">Track</InputLabel>
                                    <Select
                                        labelId="analysis-track-label"
                                        disabled={activeSession.loading || isActiveJob(activeSession.analysisJob)}
                                        value={activeSession.track}
                                        label="Track"
                                        onChange={(e) => updateAnalysisSession(activeSession.id, { track: e.target.value })}
                                    >
                                        {(lineDefinition(activeSession.line)?.directions ?? []).map((direction) => <MenuItem key={direction} value={direction}>{direction}</MenuItem>)}
                                    </Select>
                                </FormControl>

                                <LocalizationProvider dateAdapter={AdapterDayjs}>
                                    <DatePicker
                                        disabled={activeSession.loading || isActiveJob(activeSession.analysisJob)}
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

                            {/* TOV1050 output context */}
                            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', sm: 'repeat(3, minmax(0, 1fr))' }, gap: 2 }}>
                                <TextField
                                    disabled={activeSession.loading || isActiveJob(activeSession.analysisJob)}
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
                                    disabled={activeSession.loading || isActiveJob(activeSession.analysisJob)}
                                    label="Station Start"
                                    placeholder="e.g., HUH, LOW"
                                    size="small"
                                    fullWidth
                                    value={activeSession.stationStart || ''}
                                    onChange={(e) => updateAnalysisSession(activeSession.id, {
                                        stationStart: e.target.value.trim().toUpperCase() || undefined
                                    })}
                                    helperText="Required for TOV1050 output context"
                                />

                                <TextField
                                    disabled={activeSession.loading || isActiveJob(activeSession.analysisJob)}
                                    label="Station End"
                                    placeholder="e.g., TAP, KSR"
                                    size="small"
                                    fullWidth
                                    value={activeSession.stationEnd || ''}
                                    onChange={(e) => updateAnalysisSession(activeSession.id, {
                                        stationEnd: e.target.value.trim().toUpperCase() || undefined
                                    })}
                                    helperText="Required for TOV1050 output context"
                                />
                            </Box>

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
