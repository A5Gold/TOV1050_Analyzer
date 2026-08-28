import React, { useState } from 'react';
import {
  Alert, Box, Button, CircularProgress,
  Dialog, DialogActions, DialogContent, DialogTitle,
  FormControl, IconButton, InputLabel, MenuItem, Paper,
  Select, Stack, Tab, Tabs, TextField, Tooltip, Typography
} from '@mui/material';
import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import AddIcon from '@mui/icons-material/Add';
import CloseIcon from '@mui/icons-material/Close';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import DownloadIcon from '@mui/icons-material/Download';
import FolderOpenOutlinedIcon from '@mui/icons-material/FolderOpenOutlined';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import { useWearStore } from '../store/useWearStore';
import { useWearRecordsStore } from '../store/useWearRecordsStore';
import WearResultTable from '../components/Calculation/WearResultTable';
import WearAlgorithmDialog from '../components/Calculation/WearAlgorithmDialog';
import WearRecordsPanel from '../components/Calculation/WearRecordsPanel';
import WearCycleStatusPanel from '../components/Calculation/WearCycleStatusPanel';
import WearAnalysisCharts from '../components/Calculation/WearAnalysisCharts';
import WearDashboardPanel from '../components/Calculation/WearDashboardPanel';
import WearProjectionPanel from '../components/Calculation/WearProjectionPanel';
import RemainingLifePanel from '../components/Calculation/RemainingLifePanel';
import WearFeatureToolbar, { type WearFeatureTab } from '../components/Calculation/WearFeatureToolbar';
import { scrollablePageSx } from '../utils/pageLayout';
import type { WireWearLineClass } from '../types/api';
import { exportWearCycleExcel } from '../api/client';

const formatFileSize = (size: number) => {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

const WearCalculatorView: React.FC = () => {
  const {
    tabs, activeTabId,
    addTab, closeTab, setActiveTab,
    setLineClass, setCycleDate, addFile, removeFile, resetAll,
    previewCycle, saveCycle, acceptConflict,
  } = useWearStore();
  const {
    duplicateConflict,
    clearDuplicateConflict,
    hasPendingChanges,
    shouldBlockNavigation,
    saveChanges,
    discardChanges,
    isSaving: recordsAreSaving,
  } = useWearRecordsStore();

  const activeTab = tabs.find(t => t.id === activeTabId)!;
  const {
    cyclePreview,
    cyclePreviewLoading,
    cycleSaveLoading,
    cycleError,
    lastCycleSave,
  } = activeTab;
  const showEmptySuccess = activeTab.hasAnalyzed
    && activeTab.wearResults.length === 0
    && !activeTab.isLoading
    && !activeTab.error;
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [algoOpen, setAlgoOpen] = useState(false);
  const [featureTab, setFeatureTab] = useState<WearFeatureTab>('analysis');
  const [pendingFeatureTab, setPendingFeatureTab] = useState<WearFeatureTab | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
    Array.from(e.dataTransfer.files).forEach(addFile);
  };

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) { Array.from(e.target.files).forEach(addFile); e.target.value = ''; }
  };

  const handleSaveWearRecords = () => { void saveCycle(); };

  const handleFeatureTabChange = (nextTab: WearFeatureTab) => {
    if (nextTab === featureTab) return;
    if (featureTab === 'records' && hasPendingChanges && shouldBlockNavigation) {
      setPendingFeatureTab(nextTab);
      return;
    }
    setFeatureTab(nextTab);
  };

  const handleGuardSave = async () => {
    await saveChanges();
    if (!useWearRecordsStore.getState().hasPendingChanges && pendingFeatureTab) {
      setFeatureTab(pendingFeatureTab);
      setPendingFeatureTab(null);
    }
  };

  const handleGuardDiscard = () => {
    discardChanges();
    if (pendingFeatureTab) setFeatureTab(pendingFeatureTab);
    setPendingFeatureTab(null);
  };

  const handleDownloadExcel = async () => {
    if (!lastCycleSave) return;
    const blob = await exportWearCycleExcel({ lineGroup: lastCycleSave.lineGroup, cycleDate: lastCycleSave.cycleDate });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${lastCycleSave.cycleDate}_${lastCycleSave.lineGroup}_Wear_Cycle.xlsx`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const renderAnalysis = () => (
    <>
      <Box component="section" aria-labelledby="wear-upload-title" sx={{ pt: { xs: 0, sm: 1 } }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2, mb: 3 }}>
          <Box>
            <Typography id="wear-upload-title" component="h1" variant="h4">Upload files</Typography>
            <Typography variant="body2" sx={{ mt: 0.75, color: 'text.secondary' }}>Add exception report files to create a wire wear analysis cycle.</Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 0.5, flexShrink: 0 }}>
            <Tooltip title={tabs.length >= 6 ? 'Maximum 6 upload sessions' : 'New upload session'}><span><IconButton aria-label="New upload session" onClick={addTab} disabled={tabs.length >= 6} sx={{ border: '1px solid', borderColor: 'divider', bgcolor: '#ffffff' }}><AddIcon fontSize="small" /></IconButton></span></Tooltip>
            {tabs.length > 1 && <Tooltip title="Clear all upload sessions"><IconButton aria-label="Reset all upload sessions" color="error" onClick={resetAll} sx={{ border: '1px solid', borderColor: 'divider', bgcolor: '#ffffff' }}><DeleteSweepIcon fontSize="small" /></IconButton></Tooltip>}
          </Box>
        </Box>
        {tabs.length > 1 && (
          <Box sx={{ display: 'flex', alignItems: 'center', borderBottom: '1px solid', borderColor: 'divider', mb: 2 }}>
            <Tabs value={activeTabId} onChange={(_, value) => setActiveTab(value)} variant="scrollable" scrollButtons="auto" sx={{ flexGrow: 1, minWidth: 0 }}>
              {tabs.map((tab) => <Tab key={tab.id} value={tab.id} label={<Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>{tab.label}<IconButton size="small" component="span" onClick={(event) => { event.stopPropagation(); closeTab(tab.id); }} sx={{ p: 0.25 }}><CloseIcon sx={{ fontSize: 14 }} /></IconButton></Box>} />)}
            </Tabs>
          </Box>
        )}
        <Box
          role="button" tabIndex={0} aria-label="Upload XLSX exception report files"
          onDrop={handleDrop} onDragEnter={(event) => { event.preventDefault(); setIsDragActive(true); }} onDragLeave={(event) => { event.preventDefault(); setIsDragActive(false); }} onDragOver={(event) => event.preventDefault()}
          onClick={() => inputRef.current?.click()} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); inputRef.current?.click(); } }}
          sx={{ minHeight: { xs: 264, sm: 304 }, px: 3, py: 4, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', cursor: 'pointer', border: '1.5px dashed', borderColor: isDragActive ? 'primary.main' : '#b9c3d0', borderRadius: 1.5, bgcolor: isDragActive ? '#f0f5ff' : '#fbfcfe', transition: 'background-color 160ms ease-out, border-color 160ms ease-out', '&:hover': { borderColor: 'primary.main', bgcolor: '#f4f7fd' }, '&:focus-visible': { outline: '3px solid rgba(43, 99, 201, 0.25)', outlineOffset: 3 } }}
        >
          <Box sx={{ width: 64, height: 64, mb: 2, display: 'grid', placeItems: 'center', borderRadius: '50%', bgcolor: '#eaf1ff', color: 'primary.main' }}><CloudUploadOutlinedIcon sx={{ fontSize: 34 }} /></Box>
          <Typography variant="h6" sx={{ color: '#2b3a50' }}>Drag and drop files here</Typography>
          <Typography variant="body2" sx={{ mt: 0.75, color: 'text.secondary' }}>or click to browse from your computer</Typography>
          <Typography variant="caption" sx={{ mt: 1.5, color: '#7a8596' }}>XLSX exception reports only • 50 MB maximum per file</Typography>
          <input ref={inputRef} type="file" accept=".xlsx" hidden multiple onChange={handleInput} />
        </Box>
        {activeTab.uploadedFiles.length > 0 && (
          <Box sx={{ mt: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1.25, overflow: 'hidden', bgcolor: '#ffffff' }}>
            {activeTab.uploadedFiles.map((file, index) => <Box key={file.name} sx={{ minHeight: 66, px: { xs: 1.5, sm: 2 }, display: 'grid', gridTemplateColumns: '34px minmax(0, 1fr) auto', alignItems: 'center', gap: 1.25, borderBottom: index === activeTab.uploadedFiles.length - 1 ? 0 : '1px solid #edf0f4' }}><Box sx={{ width: 32, height: 32, display: 'grid', placeItems: 'center', borderRadius: 1, bgcolor: '#f0f4fa', color: 'primary.main' }}><DescriptionOutlinedIcon fontSize="small" /></Box><Box sx={{ minWidth: 0 }}><Typography noWrap sx={{ fontSize: '0.86rem', fontWeight: 700, color: '#354258' }}>{file.name}</Typography><Typography sx={{ mt: 0.15, fontSize: '0.73rem', color: 'text.secondary' }}>XLSX • {formatFileSize(file.size)}</Typography></Box><IconButton aria-label={`Remove ${file.name}`} size="small" color="error" onClick={(event) => { event.stopPropagation(); removeFile(file.name); }}><CloseIcon fontSize="small" /></IconButton></Box>)}
          </Box>
        )}
        {activeTab.uploadedFiles.length > 0 && (
          <Box sx={{ mt: 2, px: { xs: 0, sm: 0.5 }, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1.25 }}>
            <FormControl size="small" sx={{ minWidth: 146 }}><InputLabel id="wear-line-class-label">Line group</InputLabel><Select labelId="wear-line-class-label" value={activeTab.lineClass} label="Line group" onChange={(event) => setLineClass(event.target.value as WireWearLineClass)}><MenuItem value="EAL">EAL</MenuItem><MenuItem value="TML">TML</MenuItem></Select></FormControl>
            <TextField size="small" type="date" label="Cycle date" value={cyclePreview?.cycleDate ?? activeTab.date} onChange={(event) => setCycleDate(event.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 178 }} />
          </Box>
        )}
        {(activeTab.error || cycleError) && <Alert severity="error" sx={{ mt: 2 }}>{activeTab.error || cycleError}</Alert>}
        <Box sx={{ mt: 2.5, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', alignItems: 'center', gap: 1 }}>
          <Button variant="contained" disabled={activeTab.uploadedFiles.length === 0 || cyclePreviewLoading} onClick={() => void previewCycle()} startIcon={cyclePreviewLoading ? <CircularProgress size={16} color="inherit" /> : <FolderOpenOutlinedIcon />} sx={{ minWidth: 154 }}>{cyclePreviewLoading ? 'Analyzing...' : 'Process files'}</Button>
          <Button variant="outlined" color="inherit" disabled={activeTab.uploadedFiles.length === 0} onClick={() => resetAll()} startIcon={<RestartAltIcon />} sx={{ borderColor: '#cfd6e1', color: '#58667a', '&:hover': { borderColor: '#9ca9ba', bgcolor: '#ffffff' } }}>Clear all</Button>
          {lastCycleSave && <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => void handleDownloadExcel()}>Download Excel</Button>}
        </Box>
      </Box>

      {lastCycleSave && (
        <Alert severity="success" role="status">
          Cycle saved: {lastCycleSave.lineGroup} {lastCycleSave.cycleDate}
        </Alert>
      )}

      {cyclePreview ? (
        <Stack spacing={2} sx={{ mt: 3 }}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <WearCycleStatusPanel preview={cyclePreview} onAcceptConflict={(id) => void acceptConflict(id)} onSave={handleSaveWearRecords} isSaving={cycleSaveLoading} />
          </Paper>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <WearAnalysisCharts rows={cyclePreview.records} />
          </Paper>
          <Paper variant="outlined" sx={{ p: 2, flexGrow: 1 }}>
          <WearResultTable
            rows={cyclePreview.records}
          />
          </Paper>
        </Stack>
      ) : showEmptySuccess ? (
        <Paper variant="outlined" sx={{ mt: 3, p: 4 }}>
          <Alert severity="info">
            <Typography variant="body1">
              No wear records were found after filtering.
            </Typography>
            <Typography variant="body2" sx={{ mt: 0.5 }}>
              The calculation completed successfully with 0 result.
            </Typography>
          </Alert>
        </Paper>
      ) : null}
    </>
  );

  return (
    <Box sx={scrollablePageSx}>
      <WearFeatureToolbar activeTab={featureTab} onTabChange={handleFeatureTabChange} onOpenAlgorithm={() => setAlgoOpen(true)} />
      {featureTab === 'analysis' && renderAnalysis()}
      {featureTab === 'records' && <WearRecordsPanel />}
      {featureTab === 'dashboard' && <WearDashboardPanel />}
      {featureTab === 'projection' && <WearProjectionPanel />}
      {featureTab === 'remaining-life' && <RemainingLifePanel />}
      <Dialog open={Boolean(pendingFeatureTab)} onClose={() => setPendingFeatureTab(null)} aria-labelledby="wear-navigation-guard-title">
        <DialogTitle id="wear-navigation-guard-title">Unsaved wire wear changes</DialogTitle>
        <DialogContent>
          <Typography variant="body2">Save or discard the pending record changes before leaving this tab.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendingFeatureTab(null)}>Cancel</Button>
          <Button color="warning" onClick={handleGuardDiscard}>Discard</Button>
          <Button variant="contained" onClick={() => void handleGuardSave()} disabled={recordsAreSaving}>
            {recordsAreSaving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog open={Boolean(duplicateConflict)} onClose={clearDuplicateConflict}>
        <DialogTitle>Wire wear records already exist</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            {duplicateConflict?.duplicate_count ?? 0} record(s) match this cycle. Overwrite them to update the saved database.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={clearDuplicateConflict}>Cancel</Button>
          <Button variant="contained" color="warning" onClick={handleSaveWearRecords}>Overwrite</Button>
        </DialogActions>
      </Dialog>
      <WearAlgorithmDialog open={algoOpen} onClose={() => setAlgoOpen(false)} />
    </Box>
  );
};

export default WearCalculatorView;
