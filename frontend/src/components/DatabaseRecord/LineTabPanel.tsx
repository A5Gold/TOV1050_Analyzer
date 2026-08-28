/**
 * Line Tab Panel Component
 * =========================
 * Provides Tab-based navigation for Database Record Module.
 * Data is split by the TOV1050 logical line into separate tabs.
 * 
 * Features:
 * - Tabs for AEL, TCL, DRL, KTL, ISL, TWL and TKL lines
 * - Sub-tabs for the selected line's sessions
 * - Automatic data filtering based on selected tab/subtab
 * 
 * Version: 1.0
 * Date: 2026-02-01
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Chip,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Paper,
  Collapse,
  IconButton,
  Tooltip,
} from '@mui/material';
import TrainIcon from '@mui/icons-material/Train';
import TramIcon from '@mui/icons-material/Tram';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { RepeatedRecordSectionCounts, SavedRepeatedRecord } from '../../types/api';
import FilterPanel from './FilterPanel';
import { useDatabaseStore } from '../../store/useDatabaseStore';
import { TOV1050_LINES, TOV1050_SESSIONS } from '../../config/tov1050';

// =============================================================================
// TYPES
// =============================================================================

interface LineTabPanelProps {
  /** All records (unfiltered by Line/Section) */
  records: SavedRepeatedRecord[];
  /** Loading state */
  loading: boolean;
  /** Callback when Line/Section filter changes (legacy, optional) */
  onFilterChange?: (line: string | null, section: string | null) => void;
  /** Child component to render the table */
  children: (filteredRecords: SavedRepeatedRecord[]) => React.ReactNode;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

// =============================================================================
// CONSTANTS
// =============================================================================

const LINE_TABS = TOV1050_LINES.map((line, index) => ({
  label: line,
  value: line,
  icon: index % 2 === 0 ? <TrainIcon /> : <TramIcon />,
  color: index % 2 === 0 ? '#2b63c9' : '#55708f',
}));

// Feature-006: Separate section options for EAL (all) vs TML (Mainline only)
// BUG 10.9.1-1 FIX: Use 'LOW S1' as value to match DatabaseRecordView SECTION_OPTIONS
// This prevents MUI "out-of-range value" warning when selecting LOW S1 button
const sectionOptionsForLine = (line: string) => [
  { label: 'All Sections', value: null },
  ...(TOV1050_SESSIONS[line as keyof typeof TOV1050_SESSIONS] ?? ['Mainline'])
    .map((value) => ({ label: value, value })),
];

const SECTION_COUNT_KEYS: Record<string, keyof RepeatedRecordSectionCounts> = {
  Mainline: 'mainline',
  PL: 'mainline',
  TKS: 'mainline',
  Unknown: 'unknown',
};

const EMPTY_SECTION_COUNTS: RepeatedRecordSectionCounts = {
  all: 0,
  mainline: 0,
  rac: 0,
  low_s1: 0,
  lmc: 0,
  unknown: 0,
};

// =============================================================================
// HELPER COMPONENTS
// =============================================================================

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`line-tabpanel-${index}`}
      aria-labelledby={`line-tab-${index}`}
      style={{ 
        // Bug-003 Fix: Ensure TabPanel takes full height and allows scrolling
        height: value === index ? 'auto' : 0,
        minHeight: 0,
        display: value === index ? 'flex' : 'none',
        flexDirection: 'column',
        overflow: 'visible',
      }}
      {...other}
    >
      {value === index && (
        <Box sx={{ 
          pt: 2, 
          height: 'auto',
          minHeight: 0,
          display: 'flex', 
          flexDirection: 'column',
          overflow: 'visible',
        }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `line-tab-${index}`,
    'aria-controls': `line-tabpanel-${index}`,
  };
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

const LineTabPanel: React.FC<LineTabPanelProps> = ({
  records,
  loading,
  onFilterChange,
  children,
}) => {
  // =========================================================================
  // STATE
  // =========================================================================

  const [selectedLineIndex, setSelectedLineIndex] = useState(0);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [filterOpen, setFilterOpen] = useState(false);

  // Phase 12 Bug 4: Use API-based line counts instead of local computation
  const { lineCounts, fetchLineCounts, repeatedRecordSectionCounts } = useDatabaseStore();

  // Line badges retain their existing full-database semantics.
  useEffect(() => {
    fetchLineCounts();
  }, [fetchLineCounts]);

  // =========================================================================
  // COMPUTED VALUES
  // =========================================================================

  const selectedLine = LINE_TABS[selectedLineIndex].value;
  const sectionCounts = repeatedRecordSectionCounts ?? EMPTY_SECTION_COUNTS;

  // Feature-006: Get section options based on selected line (TML only shows Mainline)
  const sectionOptions = useMemo(() => {
    const base = sectionOptionsForLine(selectedLine);
    return sectionCounts.unknown > 0
      ? [...base, { label: 'Unknown', value: 'Unknown' } as const]
      : base;
  }, [selectedLine, sectionCounts.unknown]);

  // BUG 10.7-1 FIX: Ensure records is always a valid array before processing
  const safeRecords = useMemo(() => {
    if (!records || !Array.isArray(records)) return [];
    return records;
  }, [records]);

  // The API owns filtering; this defensive filter prevents stale rows from the
  // previous request flashing under a newly selected line or section.
  const filteredRecords = useMemo(() => {
    let filtered = safeRecords.filter((record) => record.line === selectedLine);
    
    if (selectedSection) {
      filtered = filtered.filter((record) => {
        const section = record.section || '';
        // Handle LOW S1 matching - records with 'LOW' in section match 'LOW S1' filter
        if (selectedSection === 'LOW S1') {
          return section.includes('LOW');
        }
        return section === selectedSection;
      });
    }
    
    return filtered;
  }, [safeRecords, selectedLine, selectedSection]);

  // =========================================================================
  // HANDLERS
  // =========================================================================

  const handleLineChange = useCallback(
    (_event: React.SyntheticEvent, newValue: number) => {
      setSelectedLineIndex(newValue);
      // Feature-006: Reset section when changing line (TML only supports Mainline)
      setSelectedSection(null);
      // Legacy callback (optional) — FilterPanel now handles fetch internally
      onFilterChange?.(LINE_TABS[newValue].value, null);
    },
    [onFilterChange]
  );

  const handleSectionChange = useCallback(
    (_event: React.MouseEvent<HTMLElement>, newSection: string | null) => {
      const normalizedSection = newSection || null;
      setSelectedSection(normalizedSection);
      // Legacy callback (optional) — FilterPanel now handles fetch internally
      onFilterChange?.(selectedLine, normalizedSection);
    },
    [onFilterChange, selectedLine]
  );

  // =========================================================================
  // RENDER
  // =========================================================================

  return (
    <Box sx={{ 
      width: '100%', 
      height: 'auto',
      minHeight: 0,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'visible',
    }}>
      {/* Line Tabs */}
      <Paper sx={{ mb: 1, flexShrink: 0 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider', display: 'flex', alignItems: 'center' }}>
          <Tabs
            value={selectedLineIndex}
            onChange={handleLineChange}
            aria-label="Line tabs"
            sx={{
              flex: 1,
              '& .MuiTabs-indicator': {
                height: 3,
              },
            }}
          >
            {LINE_TABS.map((tab, index) => (
              <Tab
                key={tab.value}
                icon={tab.icon}
                iconPosition="start"
                label={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography>{tab.label}</Typography>
                    <Chip
                      label={lineCounts[tab.value]}
                      size="small"
                      color={selectedLineIndex === index ? 'primary' : 'default'}
                      variant={selectedLineIndex === index ? 'filled' : 'outlined'}
                    />
                  </Stack>
                }
                {...a11yProps(index)}
                sx={{
                  minHeight: 44,
                  textTransform: 'none',
                  fontWeight: selectedLineIndex === index ? 600 : 400,
                }}
              />
            ))}
          </Tabs>
          <Tooltip title={filterOpen ? 'Hide filters' : 'Show filters'}>
            <IconButton
              size="small"
              onClick={() => setFilterOpen((v) => !v)}
              sx={{ mr: 1 }}
              aria-label={filterOpen ? 'Collapse filter panel' : 'Expand filter panel'}
            >
              {filterOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Tooltip>
        </Box>

        {/* Section Sub-tabs (Toggle Buttons) — always visible */}
        <Box sx={{ py: 1, px: 1.5, bgcolor: 'background.paper', overflowX: 'auto' }}>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ minWidth: 'max-content' }}>
            <Typography variant="body2" color="text.secondary">
              Section:
            </Typography>
            <ToggleButtonGroup
              value={selectedSection ?? ''}
              exclusive
              onChange={handleSectionChange}
              aria-label="section filter"
              size="small"
            >
              {/* Feature-006: Use dynamic section options based on line */}
              {sectionOptions.map((option) => (
                (() => {
                  const countKey = option.value ? SECTION_COUNT_KEYS[option.value] : 'all';
                  const count = sectionCounts[countKey];
                  return (
                <ToggleButton
                  key={option.label}
                  value={option.value ?? ''}
                  aria-label={`${option.label}, ${count} records`}
                  sx={{
                    textTransform: 'none',
                    px: 1.25,
                  }}
                >
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    <Typography variant="body2">{option.label}</Typography>
                    <Chip
                      label={count}
                      size="small"
                      sx={{ ml: 0.5, height: 18, fontSize: '0.7rem' }}
                    />
                  </Stack>
                </ToggleButton>
                  );
                })()
              ))}
            </ToggleButtonGroup>
          </Stack>
        </Box>
      </Paper>

      {/* Phase 10.10-C / Phase 11 Issue 3: FilterPanel per line tab (independent filter state) */}
      {/* key={selectedLine} ensures each line gets its own FilterPanel instance */}
      <Collapse in={filterOpen} unmountOnExit={false}>
        <Paper sx={{ mb: 1, flexShrink: 0 }}>
          <FilterPanel
            key={selectedLine}
            line={selectedLine}
            section={selectedSection}
            loading={loading}
          />
        </Paper>
      </Collapse>

      {/* Tab Panels - Bug-003 Fix: Flex grow to take remaining space */}
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {LINE_TABS.map((tab, index) => (
          <TabPanel key={tab.value} value={selectedLineIndex} index={index}>
            {children(filteredRecords)}
          </TabPanel>
        ))}
      </Box>
    </Box>
  );
};

export default LineTabPanel;
