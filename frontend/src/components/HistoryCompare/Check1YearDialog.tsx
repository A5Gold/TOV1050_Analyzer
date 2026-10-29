/**
 * Check1YearDialog Component
 * Feature-001: History Compare Integration
 * 
 * A dialog that allows users to configure query scope and filters
 * before checking repeated exception records against the database
 * for records within the past year.
 * 
 * Features:
 * - Query scope selection (All Records / Specific Filters)
 * - Filter by Line, Section, Date range
 * - Auto-detection from current data
 * - Record count display and validation
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  FormControlLabel,
  InputLabel,
  Select,
  MenuItem,
  Radio,
  RadioGroup,
  Box,
  Typography,
  Alert,
  CircularProgress,
  Divider,
  TextField,
} from '@mui/material';
import HistoryIcon from '@mui/icons-material/History';
import WarningIcon from '@mui/icons-material/Warning';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs, { Dayjs } from 'dayjs';

import { PARENT_LINES, sectionOptionsForLine, normalizeReportIdentity } from '../../config/lineCatalog';

// --- Types ---
export interface Check1YearDialogProps {
  open: boolean;
  onClose: () => void;
  onCheck: (options: CheckOptions) => void;
  recordCount: number;
  detectedLine?: string;
  detectedSection?: string;
  isChecking?: boolean;
}

export interface CheckOptions {
  scope: 'all' | 'specific';
  filters?: CheckFilters;
}

export interface CheckFilters {
  line?: string;
  section?: string;
  dateFrom?: string;
  dateTo?: string;
}

// --- Constants ---
const LINE_OPTIONS = PARENT_LINES.map(value => ({ value, label: value }));

// --- Component ---
const Check1YearDialog: React.FC<Check1YearDialogProps> = ({
  open,
  onClose,
  onCheck,
  recordCount,
  detectedLine = '',
  detectedSection = '',
  isChecking = false,
}) => {
  // State
  const [scope, setScope] = useState<'all' | 'specific'>('all');
  const [selectedLine, setSelectedLine] = useState<string>(detectedLine);
  const [selectedSection, setSelectedSection] = useState<string>(detectedSection);
  const [dateFrom, setDateFrom] = useState<Dayjs | null>(null);
  const [dateTo, setDateTo] = useState<Dayjs | null>(null);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setScope('all');
      const identity = normalizeReportIdentity(detectedLine, detectedSection);
      setSelectedLine(identity.line);
      setSelectedSection(identity.section);
      setDateFrom(null);
      setDateTo(null);
    }
  }, [open, detectedLine, detectedSection]);

  const sectionOptions = useMemo(() => sectionOptionsForLine(selectedLine), [selectedLine]);

  useEffect(() => {
    if (selectedSection && !sectionOptions.some(item => item.value === selectedSection)) {
      setSelectedSection('');
    }
  }, [sectionOptions, selectedSection]);

  // Validation
  const hasNoRecords = recordCount === 0;
  const canCheck = !hasNoRecords && !isChecking && (scope === 'all' || (!!selectedLine && !!selectedSection));

  // Handlers
  const handleScopeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setScope(event.target.value as 'all' | 'specific');
  };

  const handleLineChange = (event: any) => {
    const nextLine = event.target.value as string;
    setSelectedLine(nextLine);
    setSelectedSection(sectionOptionsForLine(nextLine)[0]?.value || '');
  };

  const handleSectionChange = (event: any) => {
    setSelectedSection(event.target.value as string);
  };

  const handleCheck = () => {
    if (scope === 'all') {
      onCheck({
        scope: 'all',
        filters: undefined,
      });
    } else {
      onCheck({
        scope: 'specific',
        filters: {
          line: selectedLine,
          section: selectedSection,
          dateFrom: dateFrom ? dateFrom.format('YYYY-MM-DD') : undefined,
          dateTo: dateTo ? dateTo.format('YYYY-MM-DD') : undefined,
        },
      });
    }
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <HistoryIcon color="primary" />
        Check 1 Year Record
      </DialogTitle>

      <DialogContent>
        {/* Record Count Info */}
        <Box sx={{ mb: 3 }}>
          {hasNoRecords ? (
            <Alert severity="warning" icon={<WarningIcon />}>
              No records to check
            </Alert>
          ) : (
            <Alert severity="info">
              <strong>{recordCount}</strong> records will be checked against the database.
            </Alert>
          )}
        </Box>

        <Divider sx={{ mb: 3 }} />

        {/* Query Scope Selection */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Query Scope
          </Typography>
          <RadioGroup
            value={scope}
            onChange={handleScopeChange}
          >
            <FormControlLabel 
              value="all" 
              control={<Radio />} 
              label="All Records - Check all records in database"
            />
            <FormControlLabel 
              value="specific" 
              control={<Radio />} 
              label="Specific Filters - Apply filters before checking"
            />
          </RadioGroup>
        </Box>

        {/* Filter Options (only shown when scope is 'specific') */}
        {scope === 'specific' && (
          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {/* Line Filter */}
              <FormControl fullWidth size="small">
                <InputLabel id="line-filter-label">Line</InputLabel>
                <Select
                  labelId="line-filter-label"
                  id="line-filter"
                  value={selectedLine}
                  label="Line"
                  onChange={handleLineChange}
                  disabled={isChecking}
                >
                  {LINE_OPTIONS.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* Section Filter */}
              <FormControl fullWidth size="small">
                <InputLabel id="section-filter-label">Section</InputLabel>
                <Select
                  labelId="section-filter-label"
                  id="section-filter"
                  value={selectedSection}
                  label="Section"
                  onChange={handleSectionChange}
                  disabled={isChecking}
                >
                  {sectionOptions.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* Date Range */}
              <Box sx={{ display: 'flex', gap: 2 }}>
                <DatePicker
                  label="Date From"
                  value={dateFrom}
                  onChange={(newValue) => setDateFrom(newValue)}
                  slotProps={{
                    textField: { 
                      size: 'small',
                      fullWidth: true,
                    },
                  }}
                  disabled={isChecking}
                />
                <DatePicker
                  label="Date To"
                  value={dateTo}
                  onChange={(newValue) => setDateTo(newValue)}
                  slotProps={{
                    textField: { 
                      size: 'small',
                      fullWidth: true,
                    },
                  }}
                  disabled={isChecking}
                />
              </Box>
            </Box>
          </LocalizationProvider>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button 
          onClick={onClose} 
          disabled={isChecking}
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleCheck}
          disabled={!canCheck}
          startIcon={isChecking ? <CircularProgress size={16} /> : <HistoryIcon />}
        >
          {isChecking ? 'Checking...' : 'Check'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default Check1YearDialog;
