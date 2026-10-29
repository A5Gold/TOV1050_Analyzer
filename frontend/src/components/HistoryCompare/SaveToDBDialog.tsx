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

import { PARENT_LINES, sectionOptionsForLine, normalizeReportIdentity } from '../../config/lineCatalog';

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
const LINE_OPTIONS = PARENT_LINES.map(value => ({ value, label: value }));

// --- Component ---
const SaveToDBDialog: React.FC<SaveToDBDialogProps> = ({
  open,
  onClose,
  onSave,
  recordCount,
  detectedLine = '',
  detectedSection = '',
  isSaving = false,
}) => {
  // State for user selections
  const [selectedLine, setSelectedLine] = useState<string>(detectedLine);
  const [selectedSection, setSelectedSection] = useState<string>(detectedSection);

  // Reset state when dialog opens with new detected values
  useEffect(() => {
    if (open) {
      const identity = normalizeReportIdentity(detectedLine, detectedSection);
      setSelectedLine(identity.line);
      setSelectedSection(identity.section);
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
  const canSave = !hasNoRecords && !isSaving && !!selectedLine && !!selectedSection;

  // Handlers
  const handleLineChange = (event: any) => {
    const nextLine = event.target.value as string;
    setSelectedLine(nextLine);
    setSelectedSection(sectionOptionsForLine(nextLine)[0]?.value || '');
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
