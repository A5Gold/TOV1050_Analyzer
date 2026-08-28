/**
 * Comparison Filter Panel Component
 * ===================================
 * Collapsible client-side filter panel for ComparisonDataGrid.
 * Filters data already in memory (no API calls needed).
 *
 * Filters:
 * - Chainage (FromM to ToM) — partial overlap logic
 * - Exception Type — Select dropdown
 * - Track Type — Select dropdown
 * - Level — Select dropdown
 * - ACTION — Select dropdown
 *
 * Phase 12 Issue 2
 * Version: 1.0
 * Date: 2026-02-10
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Tooltip,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import FilterListIcon from '@mui/icons-material/FilterList';
import ClearIcon from '@mui/icons-material/Clear';
import { ComparisonRow } from './ComparisonDataGrid';

// =============================================================================
// CONSTANTS
// =============================================================================

const EXCEPTION_TYPE_OPTIONS = [
  'All', 'Low Height', 'High Height', 'Stagger Left', 'Stagger Right', 'Wire Wear',
] as const;

const TRACK_TYPE_OPTIONS = ['All', 'Tangent', 'Curve'] as const;

const LEVEL_OPTIONS = ['All', 'L1', 'L2', 'L3'] as const;

const ACTION_OPTIONS = [
  'All',
  'Keep monitoring',
  'Calculation',
  'Verify on site',
  'Verify by next 1st line PM cycle',
  'No action required (Overshoot)',
  'No action required (Verified within 1 year)',
  'No action required (Overlapping area)',
  'Pending',
] as const;

// =============================================================================
// TYPES
// =============================================================================

interface ComparisonFilterPanelProps {
  data: ComparisonRow[];
  onFilteredDataChange: (filtered: ComparisonRow[]) => void;
}

interface FilterState {
  exception_type: string;
  track_type: string;
  level: string;
  action: string;
  chainage_from: string;
  chainage_to: string;
}

const INITIAL_FILTERS: FilterState = {
  exception_type: 'All',
  track_type: 'All',
  level: 'All',
  action: 'All',
  chainage_from: '',
  chainage_to: '',
};

// =============================================================================
// HELPERS
// =============================================================================

function countActiveFilters(filters: FilterState): number {
  let count = 0;
  if (filters.exception_type !== 'All') count++;
  if (filters.track_type !== 'All') count++;
  if (filters.level !== 'All') count++;
  if (filters.action !== 'All') count++;
  if (filters.chainage_from !== '' && filters.chainage_to !== '') count++;
  return count;
}

function applyFilters(data: ComparisonRow[], filters: FilterState): ComparisonRow[] {
  let filtered = [...data];

  if (filters.exception_type !== 'All') {
    filtered = filtered.filter(
      (row) => row['exception type'] === filters.exception_type
    );
  }

  if (filters.track_type !== 'All') {
    filtered = filtered.filter(
      (row) => row['Track Type'] === filters.track_type
    );
  }

  if (filters.level !== 'All') {
    filtered = filtered.filter((row) => row.level === filters.level);
  }

  if (filters.action !== 'All') {
    filtered = filtered.filter((row) => row.action === filters.action);
  }

  // Chainage: partial overlap — only when both values provided
  const chainageFrom = parseFloat(filters.chainage_from);
  const chainageTo = parseFloat(filters.chainage_to);
  if (!isNaN(chainageFrom) && !isNaN(chainageTo)) {
    filtered = filtered.filter(
      (row) => row.FromM <= chainageTo && row.ToM >= chainageFrom
    );
  }

  return filtered;
}

// =============================================================================
// COMPONENT
// =============================================================================

const ComparisonFilterPanel: React.FC<ComparisonFilterPanelProps> = ({
  data,
  onFilteredDataChange,
}) => {
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);

  // Apply filters whenever data or filters change
  const filteredData = useMemo(() => applyFilters(data, filters), [data, filters]);

  useEffect(() => {
    onFilteredDataChange(filteredData);
  }, [filteredData, onFilteredDataChange]);

  const handleChange = useCallback(
    (key: keyof FilterState, value: string) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const handleClear = useCallback(() => {
    setFilters(INITIAL_FILTERS);
  }, []);

  const activeCount = useMemo(() => countActiveFilters(filters), [filters]);

  const showChainageHint =
    (filters.chainage_from !== '' && filters.chainage_to === '') ||
    (filters.chainage_from === '' && filters.chainage_to !== '');

  return (
    <Accordion defaultExpanded={false} elevation={0} sx={{ mb: 1 }}>
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        aria-label="Toggle filters panel"
        sx={{
          minHeight: 40,
          px: 1.5,
          '& .MuiAccordionSummary-content': { my: 0.5 },
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          spacing={1}
          sx={{ width: '100%', minWidth: 0 }}
        >
          <FilterListIcon color="action" fontSize="small" />
          <Typography variant="body2" fontWeight={600}>Filters</Typography>
          {activeCount > 0 && (
            <Chip
              label={`${activeCount} active`}
              size="small"
              color="primary"
              variant="outlined"
              sx={{ height: 20, fontSize: '0.7rem' }}
            />
          )}
          <Box sx={{ flexGrow: 1 }} />
          <Tooltip title="Clear all filters">
            <span>
              <Button
                size="small"
                startIcon={<ClearIcon fontSize="small" />}
                onClick={(e) => { e.stopPropagation(); handleClear(); }}
                disabled={activeCount === 0}
                sx={{ minWidth: 'auto', px: 1 }}
              >
                Clear
              </Button>
            </span>
          </Tooltip>
        </Stack>
      </AccordionSummary>

      <AccordionDetails sx={{ pt: 0, pb: 1.5 }}>
        <Grid container spacing={1.5}>
          <Grid item xs={6} sm={4} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Exception Type</InputLabel>
              <Select
                value={filters.exception_type}
                label="Exception Type"
                onChange={(e) => handleChange('exception_type', e.target.value)}
              >
                {EXCEPTION_TYPE_OPTIONS.map((opt) => (
                  <MenuItem key={opt} value={opt}>{opt}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={6} sm={4} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Track Type</InputLabel>
              <Select
                value={filters.track_type}
                label="Track Type"
                onChange={(e) => handleChange('track_type', e.target.value)}
              >
                {TRACK_TYPE_OPTIONS.map((opt) => (
                  <MenuItem key={opt} value={opt}>{opt}</MenuItem>
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
                onChange={(e) => handleChange('level', e.target.value)}
              >
                {LEVEL_OPTIONS.map((opt) => (
                  <MenuItem key={opt} value={opt}>{opt}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={6} sm={4} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Action</InputLabel>
              <Select
                value={filters.action}
                label="Action"
                onChange={(e) => handleChange('action', e.target.value)}
              >
                {ACTION_OPTIONS.map((opt) => (
                  <MenuItem key={opt} value={opt}>{opt}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={6} sm={4} md={2}>
            <TextField
              fullWidth
              size="small"
              label="Chainage From"
              type="number"
              InputLabelProps={{ shrink: true }}
              value={filters.chainage_from}
              onChange={(e) => handleChange('chainage_from', e.target.value)}
              placeholder="e.g. 100000"
            />
          </Grid>

          <Grid item xs={6} sm={4} md={2}>
            <TextField
              fullWidth
              size="small"
              label="Chainage To"
              type="number"
              InputLabelProps={{ shrink: true }}
              value={filters.chainage_to}
              onChange={(e) => handleChange('chainage_to', e.target.value)}
              placeholder="e.g. 200000"
              helperText={showChainageHint ? 'Enter both From and To' : undefined}
              FormHelperTextProps={{ sx: { fontSize: '0.65rem', mt: 0.25 } }}
            />
          </Grid>
        </Grid>
      </AccordionDetails>
    </Accordion>
  );
};

export default ComparisonFilterPanel;
