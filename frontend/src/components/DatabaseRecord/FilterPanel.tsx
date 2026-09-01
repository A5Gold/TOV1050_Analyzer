/**
 * Filter Panel Component
 * =======================
 * Filter controls for the Database Record Module.
 * Each TOV1050 line tab has its own independent FilterPanel instance.
 *
 * Features:
 * - Visibility is controlled by LineTabPanel
 * - Independent filter state per tab (local state, not shared)
 * - Task Number: Dynamic dropdown from distinct-values API
 * - Date: Toggle (Saved Date / Task Run Date) + 2 Date Selectors
 * - Immediate trigger for Select changes; 500ms debounce for text inputs
 * - Chainage: Only triggers when both values are provided
 *
 * Phase: 10.10-C (Bug 1.1 + 1.2 + 1.6)
 * Version: 1.0
 * Date: 2026-02-06
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Box,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Stack,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Chip,
  Tooltip,
} from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
import ClearIcon from '@mui/icons-material/Clear';

import { useDatabaseStore } from '../../store/useDatabaseStore';
import { DatabaseFilters } from '../../types/api';
import { formatDateToCompact } from '../../utils/dateFormatter';
import { TOV1050_DIRECTIONS, Tov1050Line, Tov1050Session } from '../../config/tov1050';

// =============================================================================
// CONSTANTS
// =============================================================================

const TRACK_OPTIONS = ['All', ...TOV1050_DIRECTIONS] as const;
const LEVEL_OPTIONS = ['All', 'L1', 'L2', 'L3'] as const;
const ACTION_OPTIONS = [
  'Pending',
  'Keep monitoring',
  'Calculation',
  'Verify on site',
  'Verify by next 1st line PM cycle',
  'No action required (Overshoot)',
  'No action required (Verified within 1 year)',
  'No action required (Overlapping area)',
] as const;
const EXCEPTION_TYPE_OPTIONS = [
  'All',
  'Low Height',
  'High Height',
  'Stagger Left',
  'Stagger Right',
  'Wire Wear',
] as const;
const DATE_TYPE_OPTIONS = [
  { value: 'saved_at', label: 'Saved Date' },
  { value: 'task_run_date', label: 'Task Run Date' },
] as const;

/** Debounce delay (ms) for text input filters */
const TEXT_DEBOUNCE_MS = 500;

/** Select-type filter keys that trigger immediate fetch */
const SELECT_FILTER_KEYS = new Set([
  'track',
  'level',
  'action',
  'exception_type',
  'task_number',
  'date_type',
]);

// =============================================================================
// TYPES
// =============================================================================

interface FilterPanelProps {
  /** Current TOV1050 line from parent tab */
  line: Tov1050Line;
  /** Current section from parent sub-tab (null = All Sections) */
  section: Tov1050Session | null;
  /** Loading state from parent */
  loading: boolean;
}

interface LocalFilterState {
  track: string;
  level: string;
  action: string;
  exception_type: string;
  task_number: string;
  date_type: 'saved_at' | 'task_run_date';
  date_from: string;
  date_to: string;
  chainage_from: string;
  chainage_to: string;
}

const INITIAL_FILTER_STATE: LocalFilterState = {
  track: 'All',
  level: 'All',
  action: '',
  exception_type: 'All',
  task_number: '',
  date_type: 'saved_at',
  date_from: '',
  date_to: '',
  chainage_from: '',
  chainage_to: '',
};

// =============================================================================
// HELPERS
// =============================================================================

/** Count active filters (non-default values) */
function countActiveFilters(filters: LocalFilterState): number {
  let count = 0;
  if (filters.track !== 'All') count++;
  if (filters.level !== 'All') count++;
  if (filters.action !== '') count++;
  if (filters.exception_type !== 'All') count++;
  if (filters.task_number !== '') count++;
  if (filters.date_from !== '') count++;
  if (filters.date_to !== '') count++;
  if (filters.chainage_from !== '' && filters.chainage_to !== '') count++;
  return count;
}

/**
 * Build API filters from local state + line context.
 * 
 * Section is sent to the API so records can be loaded from the complete
 * filtered dataset instead of only the current client-side subset.
 */
function buildApiFilters(
  localFilters: LocalFilterState,
  line: Tov1050Line,
  section: Tov1050Session | null,
): DatabaseFilters {
  const apiFilters: DatabaseFilters = { line };

  if (section) {
    apiFilters.section = section;
  }
  
  if (localFilters.track !== 'All') {
    apiFilters.track = localFilters.track;
  }
  if (localFilters.level !== 'All') {
    apiFilters.level = localFilters.level;
  }
  if (localFilters.action) {
    apiFilters.action = localFilters.action;
  }
  if (localFilters.exception_type !== 'All') {
    apiFilters.exception_type = localFilters.exception_type;
  }
  if (localFilters.task_number) {
    apiFilters.task_number = localFilters.task_number;
  }

  // Date filters: convert YYYY-MM-DD to YYYYMMDD for API
  apiFilters.date_type = localFilters.date_type;
  if (localFilters.date_from) {
    apiFilters.date_from = formatDateToCompact(localFilters.date_from) ?? localFilters.date_from;
  }
  if (localFilters.date_to) {
    apiFilters.date_to = formatDateToCompact(localFilters.date_to) ?? localFilters.date_to;
  }

  // Chainage: only send when BOTH values are provided
  const chainageFrom = parseFloat(localFilters.chainage_from);
  const chainageTo = parseFloat(localFilters.chainage_to);
  if (!isNaN(chainageFrom) && !isNaN(chainageTo)) {
    apiFilters.chainage_from = chainageFrom;
    apiFilters.chainage_to = chainageTo;
  }

  return apiFilters;
}

// =============================================================================
// COMPONENT
// =============================================================================

const FilterPanel: React.FC<FilterPanelProps> = ({
  line,
  section,
  loading,
}) => {
  // Store actions
  const {
    fetchRepeatedRecords,
    setRepeatedFilters,
    clearRepeatedFilters,
    fetchDistinctValues,
  } = useDatabaseStore();

  // =========================================================================
  // LOCAL FILTER STATE (independent per tab instance)
  // =========================================================================
  const [filters, setFilters] = useState<LocalFilterState>(INITIAL_FILTER_STATE);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Dynamic dropdown options for Task Number
  const [taskNumberOptions, setTaskNumberOptions] = useState<string[]>([]);

  // =========================================================================
  // EFFECTS
  // =========================================================================

  // Fetch Task Number distinct values when line changes
  useEffect(() => {
    const loadTaskNumbers = async () => {
      const values = await fetchDistinctValues('task_no', line);
      setTaskNumberOptions(values);
    };
    loadTaskNumbers();
  }, [line, fetchDistinctValues]);

  // Fetch the complete server-side subset whenever line or section changes.
  useEffect(() => {
    const apiFilters = buildApiFilters(filters, line, section);
    clearRepeatedFilters();
    setRepeatedFilters(apiFilters);
    fetchRepeatedRecords(apiFilters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [line, section]);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // =========================================================================
  // HANDLERS
  // =========================================================================

  /** Core filter change handler with smart debounce */
  const handleFilterChange = useCallback(
    (key: keyof LocalFilterState, value: string) => {
      setFilters((prev) => {
        const updated = { ...prev, [key]: value };

        // Clear existing debounce timer
        if (debounceTimerRef.current) {
          clearTimeout(debounceTimerRef.current);
        }

        const triggerFetch = () => {
          const apiFilters = buildApiFilters(updated, line, section);
          clearRepeatedFilters();
          setRepeatedFilters(apiFilters);
          fetchRepeatedRecords(apiFilters);
        };

        // Select changes trigger immediately; text inputs use debounce
        if (SELECT_FILTER_KEYS.has(key)) {
          triggerFetch();
        } else {
          debounceTimerRef.current = setTimeout(triggerFetch, TEXT_DEBOUNCE_MS);
        }

        return updated;
      });
    },
    [line, section, clearRepeatedFilters, setRepeatedFilters, fetchRepeatedRecords],
  );

  /**
   * Phase 11 Issue 3: Consolidated Clear All + Refresh
   * Resets all filter state AND re-fetches data from API.
   * Requirement 3.5, 3.6, 3.7
   */
  const handleClearFilters = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    setFilters(INITIAL_FILTER_STATE);
    clearRepeatedFilters();

    const apiFilters = buildApiFilters(INITIAL_FILTER_STATE, line, section);
    setRepeatedFilters(apiFilters);
    fetchRepeatedRecords(apiFilters);
  }, [line, section, clearRepeatedFilters, setRepeatedFilters, fetchRepeatedRecords]);

  // =========================================================================
  // COMPUTED
  // =========================================================================

  const activeFilterCount = useMemo(() => countActiveFilters(filters), [filters]);

  // Chainage hint: show when only one value is entered
  const showChainageHint =
    (filters.chainage_from !== '' && filters.chainage_to === '') ||
    (filters.chainage_from === '' && filters.chainage_to !== '');

  // =========================================================================
  // RENDER
  // =========================================================================

  return (
    <Box sx={{ px: 1.5, pb: 1.5 }}>
      <Box sx={{ minHeight: 42, display: 'flex', alignItems: 'center' }}>
        <Stack direction="row" alignItems="center" spacing={1.5} sx={{ width: '100%' }}>
          <FilterListIcon color="action" fontSize="small" />
          <Typography variant="body2" fontWeight={600}>
            Filters
          </Typography>
          {activeFilterCount > 0 && (
            <Chip
              label={`${activeFilterCount} active`}
              size="small"
              color="primary"
              variant="outlined"
              sx={{ height: 20, fontSize: '0.7rem' }}
            />
          )}
          <Box sx={{ flexGrow: 1 }} />
          {/* Phase 11 Issue 3: Consolidated Clear All + Refresh into single button */}
          {/* Phase 11 Issue 2: Wrap potentially disabled button with <span> for Tooltip */}
          <Tooltip title="Clear all filters and refresh data">
            <span>
              <Button
                size="small"
                startIcon={<ClearIcon fontSize="small" />}
                onClick={(e) => {
                  e.stopPropagation();
                  handleClearFilters();
                }}
                disabled={loading}
                sx={{ minWidth: 'auto', px: 1 }}
              >
                Clear All
              </Button>
            </span>
          </Tooltip>
        </Stack>
      </Box>

      <Box>
        <Grid container spacing={1.5}>
          {/* Row 1: Track, Level, Exception Type, Task Number */}
          <Grid item xs={6} sm={4} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Track</InputLabel>
              <Select
                value={filters.track}
                label="Track"
                onChange={(e) => handleFilterChange('track', e.target.value)}
              >
                {TRACK_OPTIONS.map((opt) => (
                  <MenuItem key={opt} value={opt}>
                    {opt}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={6} sm={4} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Level</InputLabel>
              <Select
                value={filters.level}
                label="Level"
                onChange={(e) => handleFilterChange('level', e.target.value)}
              >
                {LEVEL_OPTIONS.map((opt) => (
                  <MenuItem key={opt} value={opt}>
                    {opt}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={6} sm={4} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Exception Type</InputLabel>
              <Select
                value={filters.exception_type}
                label="Exception Type"
                onChange={(e) => handleFilterChange('exception_type', e.target.value)}
              >
                {EXCEPTION_TYPE_OPTIONS.map((opt) => (
                  <MenuItem key={opt} value={opt}>
                    {opt}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          {/* Task Number: Dynamic dropdown from API */}
          <Grid item xs={6} sm={4} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Task Number</InputLabel>
              <Select
                value={filters.task_number}
                label="Task Number"
                onChange={(e) => handleFilterChange('task_number', e.target.value)}
                renderValue={(selected) => selected || 'All'}
              >
                <MenuItem value="">All</MenuItem>
                {taskNumberOptions.map((opt) => (
                  <MenuItem key={opt} value={opt}>
                    {opt}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          {/* Action Filter */}
          <Grid item xs={6} sm={4} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Action</InputLabel>
              <Select
                value={filters.action}
                label="Action"
                onChange={(e) => handleFilterChange('action', e.target.value)}
                renderValue={(selected) => selected || 'All'}
              >
                <MenuItem value="">All</MenuItem>
                {ACTION_OPTIONS.map((opt) => (
                  <MenuItem key={opt} value={opt}>
                    {opt}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          {/* Row 2: Date Toggle + Date From + Date To */}
          <Grid item xs={12} sm={4} md={2}>
            <ToggleButtonGroup
              value={filters.date_type}
              exclusive
              onChange={(_, value) => {
                if (value) handleFilterChange('date_type', value);
              }}
              size="small"
              fullWidth
              sx={{ height: 40 }}
            >
              {DATE_TYPE_OPTIONS.map((opt) => (
                <ToggleButton
                  key={opt.value}
                  value={opt.value}
                  sx={{ fontSize: '0.65rem', textTransform: 'none', py: 0 }}
                >
                  {opt.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Grid>

          <Grid item xs={6} sm={4} md={2}>
            <TextField
              fullWidth
              size="small"
              label={
                filters.date_type === 'task_run_date' ? 'Task Run From' : 'Saved From'
              }
              type="date"
              InputLabelProps={{ shrink: true }}
              value={filters.date_from}
              onChange={(e) => handleFilterChange('date_from', e.target.value)}
            />
          </Grid>

          <Grid item xs={6} sm={4} md={2}>
            <TextField
              fullWidth
              size="small"
              label={
                filters.date_type === 'task_run_date' ? 'Task Run To' : 'Saved To'
              }
              type="date"
              InputLabelProps={{ shrink: true }}
              value={filters.date_to}
              onChange={(e) => handleFilterChange('date_to', e.target.value)}
            />
          </Grid>

          {/* Row 3: Chainage From + Chainage To */}
          <Grid item xs={6} sm={4} md={2}>
            <TextField
              fullWidth
              size="small"
              label="Chainage From"
              type="number"
              InputLabelProps={{ shrink: true }}
              inputProps={{ step: 0.01 }}
              value={filters.chainage_from}
              onChange={(e) => handleFilterChange('chainage_from', e.target.value)}
              placeholder="e.g. 1000"
            />
          </Grid>

          <Grid item xs={6} sm={4} md={2}>
            <TextField
              fullWidth
              size="small"
              label="Chainage To"
              type="number"
              InputLabelProps={{ shrink: true }}
              inputProps={{ step: 0.01 }}
              value={filters.chainage_to}
              onChange={(e) => handleFilterChange('chainage_to', e.target.value)}
              placeholder="e.g. 5000"
              helperText={showChainageHint ? 'Enter both From and To' : undefined}
              FormHelperTextProps={{
                sx: { fontSize: '0.65rem', mt: 0.25 },
              }}
            />
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default FilterPanel;
