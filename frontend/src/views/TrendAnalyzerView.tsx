import React, { useState } from 'react';
import {
  Alert, Box, Button, Chip, CircularProgress, Collapse, Divider,
  IconButton, Paper, Stack, Tab, Tabs, Tooltip, Typography
} from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AddIcon from '@mui/icons-material/Add';
import CloseIcon from '@mui/icons-material/Close';
import { useTrendStore } from '../store/useTrendStore';
import TrendChart from '../components/Calculation/TrendChart';
import TrendResultTable from '../components/Calculation/TrendResultTable';
import TrendAlgorithmDialog from '../components/Calculation/TrendAlgorithmDialog';
import { scrollablePageSx } from '../utils/pageLayout';
import TaskLoadingState from '../components/TaskLoadingState';

const TrendAnalyzerView: React.FC = () => {
  const {
    tabs, activeTabId,
    addTab, closeTab, setActiveTab,
    addFile, removeFile, setRepeatedFile, setSelectedResult, analyze, resetTab,
  } = useTrendStore();

  const activeTab = tabs.find(t => t.id === activeTabId)!;
  const hasResults = activeTab.trendResults.length > 0;
  const showEmptySuccess = activeTab.hasAnalyzed && !hasResults && !activeTab.isLoading && !activeTab.error;
  const emptyResultMessage = activeTab.repeatedFile
    ? 'No matching L2 Wire Wear alarms found in the uploaded n_Repeated Exception Report after filter.'
    : 'No matching L2 Wire Wear alarms found in the latest uploaded Exception Report after filter.';
  const inputRef = React.useRef<HTMLInputElement>(null);
  const repeatedInputRef = React.useRef<HTMLInputElement>(null);
  const [algoOpen, setAlgoOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    Array.from(e.dataTransfer.files).forEach(addFile);
  };

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) { Array.from(e.target.files).forEach(addFile); e.target.value = ''; }
  };

  const handleRepeatedDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setRepeatedFile(e.dataTransfer.files[0] ?? null);
  };

  const handleRepeatedInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    setRepeatedFile(e.target.files?.[0] ?? null);
    e.target.value = '';
  };

  return (
    <Box sx={scrollablePageSx}>
      {/* Tab bar */}
      <Box sx={{ display: 'flex', alignItems: 'center', borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={activeTabId}
          onChange={(_, v) => setActiveTab(v)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ flexGrow: 1 }}
        >
          {tabs.map((tab) => (
            <Tab
              key={tab.id}
              value={tab.id}
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  {tab.label}
                  {tabs.length > 1 && (
                    <IconButton
                      size="small"
                      component="span"
                      onClick={(e) => { e.stopPropagation(); closeTab(tab.id); }}
                      sx={{ ml: 0.5, p: 0.25 }}
                    >
                      <CloseIcon sx={{ fontSize: 14 }} />
                    </IconButton>
                  )}
                </Box>
              }
              sx={{ minHeight: 40, textTransform: 'none' }}
            />
          ))}
        </Tabs>
        <Tooltip title={tabs.length >= 6 ? 'Maximum 6 tabs' : 'New analysis tab'}>
          <span>
            <IconButton size="small" onClick={addTab} disabled={tabs.length >= 6} sx={{ mx: 1 }}>
              <AddIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
        <Tooltip title="Reset Current Tab">
          <IconButton aria-label="Reset Current Tab" size="small" onClick={resetTab} sx={{ mr: 1 }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="How the trend algorithm works">
          <IconButton size="small" onClick={() => setAlgoOpen(true)} sx={{ mr: 1 }}>
            <InfoOutlinedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: panelOpen ? 2 : 0 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>Trend Analyzer</Typography>
          <IconButton size="small" onClick={() => setPanelOpen(v => !v)}>
            {panelOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
        <Collapse in={panelOpen}>
          <Stack spacing={2}>
            {/* Zone 1: Exception Reports */}
            <Typography variant="subtitle2" color="text.secondary">Exception Reports (1–6 files)</Typography>
            <Box
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => inputRef.current?.click()}
              sx={{
                border: '2px dashed', borderColor: 'divider', borderRadius: 2, p: 4,
                textAlign: 'center', cursor: 'pointer',
                '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' },
              }}
            >
              <UploadFileIcon sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
              <Typography variant="body1" color="text.secondary">
                Drag & drop multiple Exception Report .xlsx files (different dates), or click to select
              </Typography>
              <input ref={inputRef} type="file" accept=".xlsx" multiple hidden onChange={handleInput} />
            </Box>

            {activeTab.uploadedFiles.length > 0 && (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {activeTab.uploadedFiles.map((f) => (
                  <Chip key={f.name} label={f.name} onDelete={() => removeFile(f.name)} size="small" />
                ))}
              </Box>
            )}

            {/* Zone 2: n_Repeated Exception Report */}
            <Divider />
            <Typography variant="subtitle2" color="text.secondary">n_Repeated Exception Report (optional)</Typography>
            {activeTab.repeatedFile ? (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                <Chip
                  label={activeTab.repeatedFile.name}
                  onDelete={() => setRepeatedFile(null)}
                  size="small"
                  color="secondary"
                  variant="outlined"
                />
              </Box>
            ) : (
              <Box
                onDrop={handleRepeatedDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => repeatedInputRef.current?.click()}
                sx={{
                  border: '2px dashed', borderColor: 'divider', borderRadius: 2, p: 2,
                  textAlign: 'center', cursor: 'pointer',
                  '&:hover': { borderColor: 'secondary.main', bgcolor: 'action.hover' },
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  Drop n_Repeated Exception Report (.xlsx) here, or click to select
                </Typography>
              </Box>
            )}
            <input ref={repeatedInputRef} type="file" accept=".xlsx" multiple={false} hidden onChange={handleRepeatedInput} />

            {activeTab.error && <Alert severity="error">{activeTab.error}</Alert>}

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Button
                variant="contained"
                disabled={activeTab.uploadedFiles.length === 0 || activeTab.isLoading}
                onClick={analyze}
                startIcon={activeTab.isLoading ? <CircularProgress size={16} color="inherit" /> : undefined}
              >
                {activeTab.isLoading ? 'Analyzing…' : 'Analyze'}
              </Button>
            </Box>
          </Stack>
        </Collapse>
      </Paper>

      {activeTab.isLoading && <TaskLoadingState stage="detecting" />}

      {hasResults ? (
        <Paper sx={{ p: 2, flexGrow: 1 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {activeTab.selectedResult && <TrendChart result={activeTab.selectedResult} />}
            <TrendResultTable
              results={activeTab.trendResults}
              onViewChart={setSelectedResult}
              selectedId={activeTab.selectedResult?.exception_id ?? null}
            />
          </Box>
        </Paper>
      ) : showEmptySuccess ? (
        <Paper sx={{ p: 4 }}>
          <Alert severity="info">
            <Typography variant="body1">
              {emptyResultMessage}
            </Typography>
            <Typography variant="body2" sx={{ mt: 0.5 }}>
              The analysis completed successfully with 0 result.
            </Typography>
          </Alert>
        </Paper>
      ) : (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            Upload Exception Report files from multiple inspection dates and click Analyze
          </Typography>
        </Paper>
      )}

      <TrendAlgorithmDialog open={algoOpen} onClose={() => setAlgoOpen(false)} />
    </Box>
  );
};

export default TrendAnalyzerView;
