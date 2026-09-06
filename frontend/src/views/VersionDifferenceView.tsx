import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  IconButton,
  Paper,
  Stack,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import CloseIcon from '@mui/icons-material/Close';
import CompareArrowsOutlinedIcon from '@mui/icons-material/CompareArrowsOutlined';
import UploadFileOutlinedIcon from '@mui/icons-material/UploadFileOutlined';
import VersionDifferenceChart from '../components/VersionDifference/VersionDifferenceChart';
import {
  VERSION_DIFFERENCE_CYCLES,
  type VersionDifferenceCycle,
} from '../constants/versionDifferenceCycles';
import {
  MAX_VERSION_DIFFERENCE_TABS,
  useVersionDifferenceStore,
  type VersionDifferenceFileRole,
} from '../store/useVersionDifferenceStore';
import TaskLoadingState from '../components/TaskLoadingState';

interface FileSlotProps {
  cycle: VersionDifferenceCycle;
  file: File | null;
  disabled?: boolean;
  onChange: (file: File | null) => void;
  onInvalidFile: (message: string) => void;
}

const isExcelFile = (file: File) => /\.(xlsx|xlsm|xls)$/i.test(file.name);

const FileSlot = ({ cycle, file, disabled, onChange, onInvalidFile }: FileSlotProps) => {
  const [dragActive, setDragActive] = useState(false);
  const { label, required, color } = cycle;
  const roleLabel = label;

  const acceptFile = (nextFile: File | undefined) => {
    if (!nextFile) return;
    if (!isExcelFile(nextFile)) {
      onInvalidFile(`${roleLabel} must be an Excel workbook.`);
      return;
    }
    onChange(nextFile);
  };

  return (
    <Paper
      variant="outlined"
      role="group"
      aria-label={`${roleLabel} report upload`}
      onDragOver={event => { event.preventDefault(); if (!disabled) setDragActive(true); }}
      onDragLeave={event => { event.preventDefault(); setDragActive(false); }}
      onDrop={event => {
        event.preventDefault();
        setDragActive(false);
        if (!disabled) acceptFile(event.dataTransfer.files[0]);
      }}
      sx={{
        minHeight: 136,
        p: 1.5,
        display: 'flex',
        flexDirection: 'column',
        borderStyle: 'dashed',
        borderColor: color,
        bgcolor: dragActive ? `${color}16` : 'background.paper',
        borderWidth: 1,
        transition: 'background-color 150ms ease-out, border-color 150ms ease-out',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, minWidth: 0 }}>
          <Box data-cycle-swatch aria-hidden="true" sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: color, flex: '0 0 auto' }} />
          <Typography variant="subtitle2" fontWeight={750}>{label}</Typography>
        </Box>
        <Typography variant="caption" color="text.secondary">{required ? 'Required' : 'Optional'}</Typography>
      </Box>
      <Button
        component="label"
        variant="outlined"
        size="small"
        startIcon={<UploadFileOutlinedIcon />}
        disabled={disabled}
        sx={{ mt: 1 }}
      >
        Select file
        <input
          hidden
          type="file"
          accept=".xlsx,.xlsm,.xls"
          aria-label={`Select ${roleLabel} report`}
          onChange={event => {
            acceptFile(event.target.files?.[0]);
            event.target.value = '';
          }}
        />
      </Button>
      <Box sx={{ mt: 1, minHeight: 30, display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <Typography variant="caption" color={file ? 'text.primary' : 'text.secondary'} noWrap sx={{ flex: 1 }}>
          {file?.name ?? 'No file selected'}
        </Typography>
        {file && (
          <IconButton aria-label={`Remove ${roleLabel} report`} size="small" disabled={disabled} onClick={() => onChange(null)}>
            <CloseIcon sx={{ fontSize: 17 }} />
          </IconButton>
        )}
      </Box>
    </Paper>
  );
};

const VersionDifferenceView = () => {
  const {
    tabs,
    activeTabId,
    addTab,
    closeTab,
    setActiveTab,
    setFile,
    setError,
    compareActive,
  } = useVersionDifferenceStore();
  const activeTab = tabs.find(tab => tab.id === activeTabId) ?? tabs[0];
  const { files, response, loading, error } = activeTab;

  const updateFile = (role: VersionDifferenceFileRole, file: File | null) => setFile(role, file);

  return (
    <Stack spacing={2.5} sx={{ width: '100%', maxWidth: 1600, mx: 'auto' }}>
      <Box sx={{ display: 'flex', alignItems: { xs: 'stretch', sm: 'center' }, justifyContent: 'space-between', flexDirection: { xs: 'column', sm: 'row' }, gap: 1.5 }}>
        <Typography variant="h4">Version Difference</Typography>
        <Button
          variant="contained"
          startIcon={<CompareArrowsOutlinedIcon />}
          onClick={() => void compareActive()}
          disabled={!files.latest || !files.previous1 || loading}
          sx={{ alignSelf: { xs: 'stretch', sm: 'center' } }}
        >
          {loading ? 'Comparing...' : 'Compare'}
        </Button>
      </Box>

      <Paper variant="outlined" sx={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
        <Tabs
          value={activeTabId}
          onChange={(_, id: string) => setActiveTab(id)}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="Version Difference comparisons"
          sx={{ flex: 1, minWidth: 0, minHeight: 44 }}
        >
          {tabs.map(tab => (
            <Tab
              key={tab.id}
              value={tab.id}
              sx={{ minHeight: 44, textTransform: 'none' }}
              label={(
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                  {tab.loading && <CircularProgress size={14} aria-label={`${tab.label} comparing`} />}
                  <Typography component="span" variant="body2" fontWeight={tab.id === activeTabId ? 700 : 400}>
                    {tab.label}
                  </Typography>
                  <IconButton
                    component="span"
                    role="button"
                    aria-label={`Close ${tab.label}`}
                    size="small"
                    disabled={tabs.length <= 1}
                    onClick={event => {
                      event.stopPropagation();
                      closeTab(tab.id);
                    }}
                    sx={{ p: 0.25 }}
                  >
                    <CloseIcon sx={{ fontSize: 15 }} />
                  </IconButton>
                </Box>
              )}
            />
          ))}
        </Tabs>
        <Tooltip title={tabs.length >= MAX_VERSION_DIFFERENCE_TABS ? 'Maximum 6 comparisons' : 'Add comparison'}>
          <span>
            <IconButton
              aria-label="Add comparison"
              onClick={addTab}
              disabled={tabs.length >= MAX_VERSION_DIFFERENCE_TABS}
              size="small"
              sx={{ mx: 1 }}
            >
              <AddIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      </Paper>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', lg: 'repeat(3, minmax(0, 1fr))', xl: 'repeat(5, minmax(0, 1fr))' }, gap: 1.5 }}>
        {VERSION_DIFFERENCE_CYCLES.map(cycle => (
          <FileSlot
            key={cycle.role}
            cycle={cycle}
            file={files[cycle.role]}
            disabled={loading}
            onChange={file => updateFile(cycle.role, file)}
            onInvalidFile={setError}
          />
        ))}
      </Box>

      {error && !response && <Alert severity="error">{error}</Alert>}
      <Divider />
      {loading && <TaskLoadingState stage="detecting" />}
      <VersionDifferenceChart key={activeTab.id} response={response} loading={loading} error={error} />
    </Stack>
  );
};

export default VersionDifferenceView;
