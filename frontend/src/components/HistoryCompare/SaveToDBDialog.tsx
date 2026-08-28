/**
 * SaveToDBDialog Component
 * Feature-001: History Compare Integration
 * 
 * A dialog that allows users to select Sub Tab (EAL/TML) and
 * Sub Table (Mainline, RAC, LOW S1, LMC) before saving repeated
 * exception records to the database.
 * 
 * Features:
 * - Auto-detection of line and section from data
 * - User override capability
 * - TML-specific section restriction (only Mainline)
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
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  Alert,
  CircularProgress,
  Divider,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import WarningIcon from '@mui/icons-material/Warning';

// --- Types ---
export interface SaveToDBDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (options: SaveOptions) => void;
  recordCount: number;
  detectedLine?: string;
  detectedSection?: string;
  isSaving?: boolean;
}

export interface SaveOptions {
  line: string;
  section: string;
}

// --- Constants ---
const LINE_OPTIONS = [
  { value: 'EAL', label: 'EAL' },
  { value: 'TML', label: 'TML' },
];

const EAL_SECTION_OPTIONS = [
  { value: 'Mainline', label: 'Mainline' },
  { value: 'RAC', label: 'RAC' },
  { value: 'LOW S1', label: 'LOW S1' },
  { value: 'LMC', label: 'LMC' },
];

const TML_SECTION_OPTIONS = [
  { value: 'Mainline', label: 'Mainline' },
];

// --- Component ---
const SaveToDBDialog: React.FC<SaveToDBDialogProps> = ({
  open,
  onClose,
  onSave,
  recordCount,
  detectedLine = 'EAL',
  detectedSection = 'Mainline',
  isSaving = false,
}) => {
  // State for user selections
  const [selectedLine, setSelectedLine] = useState<string>(detectedLine);
  const [selectedSection, setSelectedSection] = useState<string>(detectedSection);

  // Reset state when dialog opens with new detected values
  useEffect(() => {
    if (open) {
      setSelectedLine(detectedLine || 'EAL');
      setSelectedSection(detectedSection || 'Mainline');
    }
  }, [open, detectedLine, detectedSection]);

  // Get available sections based on selected line
  const sectionOptions = useMemo(() => {
    return selectedLine === 'TML' ? TML_SECTION_OPTIONS : EAL_SECTION_OPTIONS;
  }, [selectedLine]);

  // Reset section to Mainline when changing to TML (TML only supports Mainline)
  useEffect(() => {
    if (selectedLine === 'TML' && selectedSection !== 'Mainline') {
      setSelectedSection('Mainline');
    }
  }, [selectedLine, selectedSection]);

  // Validation
  const hasNoRecords = recordCount === 0;
  const canSave = !hasNoRecords && !isSaving;

  // Handlers
  const handleLineChange = (event: any) => {
    setSelectedLine(event.target.value as string);
  };

  const handleSectionChange = (event: any) => {
    setSelectedSection(event.target.value as string);
  };

  const handleSave = () => {
    onSave({
      line: selectedLine,
      section: selectedSection,
    });
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <SaveIcon color="primary" />
        Save to Database
      </DialogTitle>

      <DialogContent>
        {/* Record Count Info */}
        <Box sx={{ mb: 3 }}>
          {hasNoRecords ? (
            <Alert severity="warning" icon={<WarningIcon />}>
              No records to save
            </Alert>
          ) : (
            <Alert severity="info">
              <strong>{recordCount}</strong> records will be saved to the database.
            </Alert>
          )}
        </Box>

        <Divider sx={{ mb: 3 }} />

        {/* Selection Controls */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Line (Sub Tab) Selector */}
          <FormControl fullWidth>
            <InputLabel id="line-select-label">Line (Sub Tab)</InputLabel>
            <Select
              labelId="line-select-label"
              id="line-select"
              value={selectedLine}
              label="Line (Sub Tab)"
              onChange={handleLineChange}
              disabled={isSaving}
            >
              {LINE_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Section (Sub Table) Selector */}
          <FormControl fullWidth>
            <InputLabel id="section-select-label">Section (Sub Table)</InputLabel>
            <Select
              labelId="section-select-label"
              id="section-select"
              value={selectedSection}
              label="Section (Sub Table)"
              onChange={handleSectionChange}
              disabled={isSaving}
            >
              {sectionOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {/* TML Info Note */}
        {selectedLine === 'TML' && (
          <Box sx={{ mt: 2 }}>
            <Alert severity="info" variant="outlined">
              TML line only supports Mainline section.
            </Alert>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button 
          onClick={onClose} 
          disabled={isSaving}
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={!canSave}
          startIcon={isSaving ? <CircularProgress size={16} /> : <SaveIcon />}
        >
          {isSaving ? 'Saving...' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SaveToDBDialog;
