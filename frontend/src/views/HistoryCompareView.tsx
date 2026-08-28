import React, { useState } from 'react';
import { 
  Box, Typography, Button, Paper, 
  CircularProgress, Alert, Stack, List, ListItem, ListItemText,
  IconButton, Tabs, Tab, Tooltip,
  Divider, Snackbar, TextField, Chip
} from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import SaveIcon from '@mui/icons-material/Save';
import CloseIcon from '@mui/icons-material/Close';
import AddIcon from '@mui/icons-material/Add';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import KeyboardArrowLeftIcon from '@mui/icons-material/KeyboardArrowLeft';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import TableChartIcon from '@mui/icons-material/TableChart';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import HistoryIcon from '@mui/icons-material/History';
import EditIcon from '@mui/icons-material/Edit';
import UndoIcon from '@mui/icons-material/Undo';

import apiClient from '../api/client';
import { ExceptionRecord } from '../types/api';
import { useAnalysisStore, CompareSession } from '../store/useAnalysisStore';
import { useDatabaseStore } from '../store/useDatabaseStore';
import ComparisonDataGrid, { ComparisonRow } from '../components/HistoryCompare/ComparisonDataGrid';
import ComparisonFilterPanel from '../components/HistoryCompare/ComparisonFilterPanel';
import ComparisonChart from '../components/HistoryCompare/ComparisonChart';
import AlgorithmTutorialDialog from '../components/HistoryCompare/AlgorithmTutorialDialog';
import SaveToDBDialog, { SaveOptions } from '../components/HistoryCompare/SaveToDBDialog';
import Check1YearDialog, { CheckOptions } from '../components/HistoryCompare/Check1YearDialog';
import BatchEditDialog, { BatchEditValues } from '../components/HistoryCompare/BatchEditDialog';
// M5: Field normalization utility for consistent snake_case field names
import { normalizeRecord, getFieldValue } from '../utils/fieldNormalizer';
import { fillDataRegionSx, scrollablePageSx } from '../utils/pageLayout';

// --- Helpers ---

const generateId = () => Date.now().toString(36) + Math.random().toString(36).substr(2);

const HistoryCompareView = () => {
  const {
    compareSessions,
    activeCompareTabId,
    addCompareSession,
    removeCompareSession,
    updateCompareSession,
    setActiveCompareTab,
    resetCompareSessions
  } = useAnalysisStore();

  const { saveRepeatedRecords, isSaving, check1YearRecords } = useDatabaseStore();

  const [tutorialOpen, setTutorialOpen] = useState(false);
  const [selectedRow, setSelectedRow] = useState<ComparisonRow | null>(null);
  const [configOpen, setConfigOpen] = useState(true);
  const [latestDragActive, setLatestDragActive] = useState(false);
  const [closestDragActive, setClosestDragActive] = useState(false);
  const [olderDragActive, setOlderDragActive] = useState(false);
  const [resultTabIndex, setResultTabIndex] = useState(0); // 0: Table, 1: Chart
  const [toast, setToast] = useState<{ open: boolean; message: string; severity: 'info' | 'success' | 'error' }>({ open: false, message: '', severity: 'info' });
  const [isChecking1Year, setIsChecking1Year] = useState(false);
  
  // Feature-001: Dialog state for Save to DB and Check 1 Year
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [check1YearDialogOpen, setCheck1YearDialogOpen] = useState(false);

  // Phase 11 Issue 4: Batch edit state
  const [selectedRowIds, setSelectedRowIds] = useState<Set<string>>(new Set());
  const [pendingChanges, setPendingChanges] = useState<Map<string, Partial<ComparisonRow>>>(new Map());
  const [pendingReviewProposals, setPendingReviewProposals] = useState<Array<Record<string, any>>>([]);
  const [approvedReviewProposals, setApprovedReviewProposals] = useState<Array<Record<string, any>>>([]);
  const [check1YearSummary, setCheck1YearSummary] = useState<Record<string, number> | null>(null);
  const [batchEditDialogOpen, setBatchEditDialogOpen] = useState(false);

  // Phase 12 Issue 2: Filtered comparison data (client-side)
  const [filteredComparisonData, setFilteredComparisonData] = useState<ComparisonRow[] | null>(null);

  const handleCloseToast = () => setToast({ ...toast, open: false });

  const handleAddTab = () => {
    const newId = generateId();
    const newSession: CompareSession = {
      id: newId,
      label: `Comparison ${compareSessions.length + 1}`,
      latestFile: null,
      closestPreviousFile: null,
      olderPreviousFiles: [],
      // Initialize optional fields as undefined
      taskNo: undefined,
      stationStart: undefined,
      stationEnd: undefined,
      repeatedData: [],
      latestFileName: '',
      loading: false,
      error: null,
      tabIndex: 0
    };
    addCompareSession(newSession);
    setConfigOpen(true);
  };

  const handleCloseTab = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    removeCompareSession(id);
  };

  const handleResetAll = () => {
    if (window.confirm("Clear all comparison sessions?")) {
        resetCompareSessions();
    }
  };

  // --- Active Session Logic ---
  const activeSession = compareSessions.find(s => s.id === activeCompareTabId);

  // Handle Row Updates (Editing)
  // Phase 11 Issue 4: Queue changes in pendingChanges instead of immediate store update
  const handleRowUpdate = (newRow: ComparisonRow) => {
      if (!activeSession) return;

      // Find the original row to compute diff
      const originalRow = activeSession.repeatedData.find(r => r.id === newRow.id);
      if (!originalRow) return;

      // Compute changed fields only (immutable pattern)
      const existingChanges = pendingChanges.get(newRow.id) || {};
      const mergedChanges: Partial<ComparisonRow> = { ...existingChanges };

      // Check editable workflow fields for changes
      const editableFields = [
        'action', 'check_date', 'checked_by', 'check_result',
        'verify_deadline', 'verify_date', 'verified_by', 'verify_result',
        'adjust_deadline', 'adjust_date', 'adjusted_by', 'adjust_result',
        'remarks',
      ] as const;

      editableFields.forEach((field) => {
        if ((newRow as any)[field] !== (originalRow as any)[field]) {
          (mergedChanges as any)[field] = (newRow as any)[field];
        }
      });

      const updatedMap = new Map(pendingChanges);
      if (Object.keys(mergedChanges).length > 0) {
        updatedMap.set(newRow.id, mergedChanges);
      } else {
        updatedMap.delete(newRow.id);
      }
      setPendingChanges(updatedMap);
  };

  const handleRowClick = (row: ComparisonRow) => {
      setSelectedRow(row);
      // Issue 7: Only highlight, do not switch tab
  };

  const handleViewChart = (row: ComparisonRow) => {
      setSelectedRow(row);
      setResultTabIndex(1);
  };

  // File Handlers
  const handleLatestFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!activeSession) return;
      if (e.target.files && e.target.files.length > 0) {
          updateCompareSession(activeSession.id, { latestFile: e.target.files[0] });
      }
  };

  const handleClosestFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!activeSession) return;
      if (e.target.files && e.target.files.length > 0) {
          updateCompareSession(activeSession.id, { closestPreviousFile: e.target.files[0] });
      }
  };

  const clearLatestFile = () => {
      if (!activeSession) return;
      updateCompareSession(activeSession.id, { latestFile: null });
  };

  const clearClosestFile = () => {
      if (!activeSession) return;
      updateCompareSession(activeSession.id, { closestPreviousFile: null });
  };

  const handleOlderFilesSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!activeSession) return;
      if (e.target.files && e.target.files.length > 0) {
          const newFiles = Array.from(e.target.files);
          updateCompareSession(activeSession.id, { 
              olderPreviousFiles: [...activeSession.olderPreviousFiles, ...newFiles] 
          });
      }
      e.target.value = ''; // Reset
  };

  const removeOlderFile = (index: number) => {
      if (!activeSession) return;
      const newFiles = [...activeSession.olderPreviousFiles];
      newFiles.splice(index, 1);
      updateCompareSession(activeSession.id, { olderPreviousFiles: newFiles });
  };

  const makeDragHandlers = (
    setActive: (v: boolean) => void,
    onDrop: (file: File) => void,
    multi = false
  ) => ({
    onDragOver: (e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); setActive(true); },
    onDragLeave: (e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); setActive(false); },
    onDrop: (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setActive(false);
      if (!activeSession) return;
      const files = Array.from(e.dataTransfer.files);
      if (files.length === 0) return;
      if (multi) {
        files.forEach(f => onDrop(f));
      } else {
        onDrop(files[0]);
      }
    },
  });

  const latestDragHandlers = makeDragHandlers(
    setLatestDragActive,
    (file) => { if (activeSession) updateCompareSession(activeSession.id, { latestFile: file }); }
  );

  const closestDragHandlers = makeDragHandlers(
    setClosestDragActive,
    (file) => { if (activeSession) updateCompareSession(activeSession.id, { closestPreviousFile: file }); }
  );

  const olderDragHandlers = makeDragHandlers(
    setOlderDragActive,
    (file) => {
      if (activeSession) {
        updateCompareSession(activeSession.id, {
          olderPreviousFiles: [...activeSession.olderPreviousFiles, file]
        });
      }
    },
    true
  );

  const handleCompare = async () => {
    if (!activeSession) return;
    if (!activeSession.latestFile) {
        updateCompareSession(activeSession.id, { error: "Latest Cycle Report is required." });
        return;
    }
    if (!activeSession.closestPreviousFile) {
        updateCompareSession(activeSession.id, { error: "Closest Previous Cycle Report is required." });
        return;
    }

    updateCompareSession(activeSession.id, {
      loading: true,
      error: null,
      repeatedData: [],
      latestFileName: '',
      chartData: undefined,
    });

    const formData = new FormData();
    formData.append('files', activeSession.latestFile);
    formData.append('files', activeSession.closestPreviousFile);
    activeSession.olderPreviousFiles.forEach(f => formData.append('files', f));

    try {
      const response = await apiClient.post('/analyze/compare', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.status === 'success') {
        let flat: ExceptionRecord[] = [];
        Object.values(response.data.repeated).forEach((list: any) => {
          flat = [...flat, ...list];
        });
        
        const chain = response.data.chain_order;
        const latest = chain && chain.length > 0 ? chain[0] : '';

        updateCompareSession(activeSession.id, { 
            repeatedData: flat, 
            latestFileName: latest,
            loading: false,
            chartData: response.data.chart_data, // Store chart data
        });
        setConfigOpen(false); // Auto-collapse config on success (Issue 1)
        setResultTabIndex(0); // Show table first
      }
    } catch (err: any) {
      console.error(err);
      const msg = err.response?.data?.detail || "Comparison failed.";
      updateCompareSession(activeSession.id, { error: msg, loading: false });
    }
  };

  const handleDownload = async () => {
      if (!activeSession) return;
      
      setToast({ open: true, message: 'Generating Report...', severity: 'info' });

      try {
          const parsedMeta = activeSession.latestFileName 
              ? parseMetadataFromFileName(activeSession.latestFileName) 
              : { line: 'EAL', track: 'UP', date_str: '', task_run_date: '' };
          const payload = {
              data: activeSession.repeatedData,
              metadata: {
                  filename: activeSession.latestFileName,
                  // Include optional fields for conditional naming
                  task_no: activeSession.taskNo || parsedMeta.task_no,
                  station_start: activeSession.stationStart || parsedMeta.station_start,
                  station_end: activeSession.stationEnd || parsedMeta.station_end
              }
          };

          const response = await apiClient.post('/export/compare/generate', payload, { 
              responseType: 'blob' 
          });
          
          const contentDisposition = response.headers['content-disposition'];
          let filename = 'Repeated_Exception_Report.xlsx';
          
          if (activeSession.latestFileName) {
              const prefix = activeSession.latestFileName.split('.').slice(0, -1).join('.');
              filename = `${prefix}_Compare_Report.xlsx`;
          }
          
          if (contentDisposition) {
              const filenameMatch = contentDisposition.match(/filename\*=utf-8''(.+)/i);
              const filenameMatch2 = contentDisposition.match(/filename="?([^"]+)"?/i);
              
              if (filenameMatch && filenameMatch[1]) {
                  filename = decodeURIComponent(filenameMatch[1]);
              } else if (filenameMatch2 && filenameMatch2[1]) {
                  filename = filenameMatch2[1];
              }
          }

          const url = window.URL.createObjectURL(new Blob([response.data]));
          const link = document.createElement('a');
          link.href = url;
          link.setAttribute('download', filename);
          document.body.appendChild(link);
          link.click();
          link.parentNode?.removeChild(link);
          window.URL.revokeObjectURL(url);
          
          setToast({ open: true, message: 'File Saved Successfully', severity: 'success' });
      } catch (err) {
          console.error("Export failed", err);
          if (activeSession) updateCompareSession(activeSession.id, { error: "Failed to download report." });
          setToast({ open: true, message: 'Export Failed', severity: 'error' });
      }
  };

  /**
   * Phase 11 Issue 4: Handle batch edit confirm from BatchEditDialog
   * Applies selected field values to all selected rows in pendingChanges
   */
  const handleBatchEditConfirm = (changes: BatchEditValues) => {
    setBatchEditDialogOpen(false);
    if (selectedRowIds.size === 0 || Object.keys(changes).length === 0) return;

    const updatedMap = new Map(pendingChanges);
    selectedRowIds.forEach((rowId) => {
      const existing = updatedMap.get(rowId) || {};
      updatedMap.set(rowId, { ...existing, ...changes });
    });
    setPendingChanges(updatedMap);
  };

  /**
   * Phase 11 Issue 4: Save all pending changes to the store
   * Commits pendingChanges into the session's repeatedData
   */
  const handleSaveEdit = () => {
    if (!activeSession || pendingChanges.size === 0) return;

    const updatedList = activeSession.repeatedData.map((row) => {
      const changes = pendingChanges.get(row.id);
      return changes ? { ...row, ...changes } as ExceptionRecord : row;
    });

    updateCompareSession(activeSession.id, { repeatedData: updatedList });
    if (pendingReviewProposals.length) {
      setApprovedReviewProposals(current => [...current, ...pendingReviewProposals]);
      setPendingReviewProposals([]);
    }
    setPendingChanges(new Map());
    setPendingReviewProposals([]);
    setSelectedRowIds(new Set());
    setToast({ open: true, message: `Saved ${pendingChanges.size} record changes`, severity: 'success' });
  };

  /**
   * Phase 11 Issue 4: Discard all pending changes
   */
  const handleDiscardChanges = () => {
    if (pendingChanges.size === 0) return;
    setPendingChanges(new Map());
    setSelectedRowIds(new Set());
    setToast({ open: true, message: 'All pending changes discarded', severity: 'info' });
  };

  /**
   * Feature-001: Open Check 1 Year dialog
   */
  const handleOpenCheck1YearDialog = () => {
    if (!activeSession) {
      setToast({ open: true, message: 'No active session', severity: 'error' });
      return;
    }

    if (activeSession.repeatedData.length === 0) {
      setToast({ open: true, message: 'No repeated exceptions to check', severity: 'error' });
      return;
    }

    const realData = getRealData();
    if (realData.length === 0) {
      setToast({ open: true, message: 'No real data to check (only mock data exists)', severity: 'error' });
      return;
    }

    setCheck1YearDialogOpen(true);
  };

  /**
   * Feature-001: Handle Check 1 Year with options from dialog
   */
  const handleCheck1YearWithOptions = async (options: CheckOptions) => {
    if (!activeSession) return;

    setCheck1YearDialogOpen(false);
    setIsChecking1Year(true);
    setToast({ open: true, message: 'Checking 1 year records in database...', severity: 'info' });

    const realData = getRealData();

    try {
      // Parse the current cycle date from the filename
      const metadata = parseMetadataFromFileName(activeSession.latestFileName);
      
      // Use options from dialog for line filtering (when scope is 'specific')
      const filterLine = options.scope === 'specific' && options.filters?.line 
        ? options.filters.line 
        : metadata.line;
      const filterSection = options.scope === 'specific' && options.filters?.section 
        ? options.filters.section 
        : undefined;
      
      // M5: Prepare exceptions data for the API using normalizer for consistent field names
      const exceptionsForCheck = realData.map(row => {
        const normalized = normalizeRecord(row);
        return {
          id: normalized.exception_id || normalized.id || '',
          exception_type: normalized.exception_type || '',
          level: normalized.level || '',
          max_location: normalized.max_location || 0,
          from_m: normalized.from_m || 0,
          to_m: normalized.to_m || 0,
          line: filterLine,
          track: metadata.track,
          section: normalized.section || filterSection || '',
          task_run_date: normalized.task_run_date || metadata.date_str || '',
          action: normalized.action || '',
          current_check_result: normalized.check_result || '',
        };
      });

      const response = await check1YearRecords({
        current_date: metadata.date_str,
        line: filterLine,
        track: metadata.track,
        section: filterSection,
        date_from: options.filters?.dateFrom,
        date_to: options.filters?.dateTo,
        exceptions: exceptionsForCheck,
      });

      // Backend returns { status, match_count, exceptions } — map to frontend field names
      const isSuccess = response.status === 'success' || response.success;
      if (isSuccess) {
        setCheck1YearSummary({
          checked: response.checked_count ?? exceptionsForCheck.length,
          matches: response.match_count ?? response.matched_count ?? 0,
          autoVerified: response.auto_verified_count ?? 0,
          reviewRequired: response.review_required_count ?? 0,
          keepMonitoring: response.keep_monitoring_count ?? 0,
          unmatched: response.unmatched_count ?? 0,
          skipped: response.skipped_count ?? 0,
        });
        setPendingReviewProposals(response.review_proposals ?? []);
        // Build matched map from updated exceptions returned by backend
        const updatedExceptions: Array<Record<string, any>> = response.exceptions || response.matches || [];
        const matchedMap = new Map<string, { reoccurrence_id: string; action: string }>();
        for (const exc of updatedExceptions) {
          const excId = exc.exception_id || exc.id || '';
          const excAction = exc.action || '';
          const excReoccurrenceId = exc.reoccurrence_id || '';
          if (excReoccurrenceId && excAction) {
            matchedMap.set(excId, { reoccurrence_id: excReoccurrenceId, action: excAction });
          }
        }

        // M5: Use normalized ID for matching
        const updatedData = activeSession.repeatedData.map(row => {
          const rowId = row.id || (row as any).exception_id || '';
          const match = matchedMap.get(rowId);
          if (match) {
            return {
              ...row,
              action: match.action,
              reoccurrence_id: match.reoccurrence_id,
            } as ExceptionRecord;
          }
          return row;
        });

        const staged = new Map(pendingChanges);
        updatedExceptions.filter(exc => exc.check_1_year_status === 'review_required').forEach(exc => {
          const id = String(exc.exception_id || exc.id || '');
          staged.set(id, {
            ...(staged.get(id) || {}),
            action: exc.proposed_action || exc.action,
            reoccurrence_id: exc.proposed_reoccurrence_id || exc.reoccurrence_id,
          });
        });
        setPendingChanges(staged);

        updateCompareSession(activeSession.id, { repeatedData: updatedData });

        const matchCount = response.match_count ?? response.matched_count ?? matchedMap.size;
        const checkedCount = response.checked_count ?? exceptionsForCheck.length;
        setToast({ 
          open: true, 
          message: `Found ${matchCount} matches in database (checked ${checkedCount} records)`, 
          severity: 'success' 
        });
      } else {
        setToast({ open: true, message: response.message || 'Check failed', severity: 'error' });
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to check database';
      console.error("Check 1 year record failed:", err);
      setToast({ open: true, message: errorMsg, severity: 'error' });
    } finally {
      setIsChecking1Year(false);
    }
  };

  /**
   * Parse metadata from filename
   * Expected format: YYYYMMDD_LINE_TRACK_SECTION_... or YYYYMMDD_LINE_TASK_STATIONSTART-STATIONEND_...
   * 
   * Bug 10.6-4: Added task_run_date extraction from filename
   */
  const parseMetadataFromFileName = (filename: string): { 
    line: string; 
    track: string; 
    date_str: string;
    task_run_date: string;
    task_no?: string;
    station_start?: string;
    station_end?: string;
  } => {
    // Default values
    const todayStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const defaults = { line: 'EAL', track: 'UP', date_str: todayStr, task_run_date: todayStr };
    
    if (!filename) return defaults;
    
    // Remove file extension
    const baseName = filename.replace(/\.[^/.]+$/, '');
    const parts = baseName.split('_');
    
    if (parts.length >= 4) {
      const dateStr = parts[0] || defaults.date_str;
      const lineStr = parts[1] || defaults.line;
      
      // Detect Condition B (Custom): parts[3] contains '-' (e.g., "HUH-RAC")
      // Condition A (Default): YYYYMMDD_LINE_TRACK_SECTION_...
      // Condition B (Custom): YYYYMMDD_LINE_TASKNO_STATIONSTART-STATIONEND_...
      const isCustomMode = parts[3] && parts[3].includes('-');
      
      if (isCustomMode) {
        const stationParts = parts[3].split('-');
        return {
          date_str: dateStr,
          task_run_date: dateStr,
          line: lineStr,
          track: defaults.track, // Track not in custom filename; use default
          task_no: parts[2],
          station_start: stationParts[0],
          station_end: stationParts[1],
        };
      }
      
      // Condition A: Default mode
      return {
        date_str: dateStr,
        task_run_date: dateStr,
        line: lineStr,
        track: parts[2] || defaults.track,
      };
    }
    
    return defaults;
  };

  /**
   * Feature-001: Get real data (non-mock) from active session
   * BUG-003 FIX: Check multiple possible ID fields (id, exception_id)
   * BUG 10.9-1 FIX: Enhanced ID extraction using fieldNormalizer for robustness
   * 
   * Backend may use different field names: 'exception_id', 'id', 'ID', 'Exception ID', etc.
   * The getFieldValue helper checks all possible formats from the FIELD_MAP.
   */
  const getRealData = () => {
    if (!activeSession) return [];
    
    const result = activeSession.repeatedData.filter(row => {
      // BUG 10.9-1 FIX: Use getFieldValue to check all possible ID field formats
      // This handles: 'exception_id', 'id', 'ID', and any other mapped formats
      const id = getFieldValue(row, 'exception_id', '') || 
                 (row as any).id || 
                 (row as any).exception_id ||
                 (row as any).ID ||
                 (row as any)['Exception ID'] ||
                 '';
      
      // Skip records without any valid ID
      if (!id) {
        console.warn('[getRealData] Record without ID detected, skipping:', row);
        return false;
      }
      
      // Filter out mock data records
      const idLower = String(id).toLowerCase();
      const isMockData = idLower.startsWith('mock-') || idLower.includes('mock_data');
      
      return !isMockData;
    });
    
    // Debug logging in development
    if (process.env.NODE_ENV === 'development') {
      console.debug('[getRealData] Filtered:', {
        total: activeSession.repeatedData.length,
        real: result.length,
        filtered: activeSession.repeatedData.length - result.length,
      });
    }
    
    return result;
  };

  /**
   * Feature-001: Detect section from repeated data
   * Returns the most common section in the data, defaults to 'Mainline'
   */
  const detectSection = (): string => {
    const realData = getRealData();
    if (realData.length === 0) return 'Mainline';
    
    const sectionCounts: Record<string, number> = {};
    realData.forEach(row => {
      const section = (row as any).Section || 'Mainline';
      sectionCounts[section] = (sectionCounts[section] || 0) + 1;
    });
    
    // Return the most common section
    const sortedSections = Object.entries(sectionCounts).sort((a, b) => b[1] - a[1]);
    return sortedSections[0]?.[0] || 'Mainline';
  };

  /**
   * Feature-001: Open Save to DB dialog
   */
  const handleOpenSaveDialog = () => {
    if (!activeSession) {
      setToast({ open: true, message: 'No active session', severity: 'error' });
      return;
    }

    if (activeSession.repeatedData.length === 0) {
      setToast({ open: true, message: 'No repeated exceptions to save', severity: 'error' });
      return;
    }

    const realData = getRealData();
    if (realData.length === 0) {
      setToast({ open: true, message: 'No real data to save (only mock data exists)', severity: 'error' });
      return;
    }

    setSaveDialogOpen(true);
  };

  /**
   * Feature-001: Handle Save with options from dialog
   */
  const handleSaveWithOptions = async (options: SaveOptions) => {
    if (!activeSession) return;

    setSaveDialogOpen(false);
    setToast({ open: true, message: 'Saving to Database...', severity: 'info' });

    const realData = getRealData();

    try {
      // Parse metadata from filename
      const metadata = parseMetadataFromFileName(activeSession.latestFileName);
      
      // Build comparison files list
      const comparisonFiles: string[] = [];
      if (activeSession.latestFile) comparisonFiles.push(activeSession.latestFile.name);
      if (activeSession.closestPreviousFile) comparisonFiles.push(activeSession.closestPreviousFile.name);
      activeSession.olderPreviousFiles.forEach(f => comparisonFiles.push(f.name));

      // Use options from dialog for line and section
      // Phase 11 Issue 1: Use parsed metadata for task_no/station when user hasn't entered them
      const effectiveTaskNo = activeSession.taskNo || metadata.task_no;
      const effectiveStationStart = activeSession.stationStart || metadata.station_start;
      const effectiveStationEnd = activeSession.stationEnd || metadata.station_end;
      
      const response = await saveRepeatedRecords({
        line: options.line, // From dialog
        track: metadata.track,
        date_str: metadata.date_str,
        task_no: effectiveTaskNo,
        station_start: effectiveStationStart,
        station_end: effectiveStationEnd,
        task_run_date: metadata.task_run_date,
        repeated_exceptions: realData.map(row => ({
          ...row,
          Section: options.section, // Override section from dialog
          // Bug 10.9.1-5 FIX: Sync action field - use existing value or default to 'Pending'
          action: (row as any).action || 'Pending',
        })),
        latest_file_name: activeSession.latestFileName,
        comparison_files: comparisonFiles,
        approved_recurrence_links: approvedReviewProposals.map(proposal => ({
          exception_id: String(proposal.exception_id || ''),
          target_record_id: Number(proposal.target_record_id),
          target_version: String(proposal.target_version || ''),
        })),
      });

      const filteredCount = activeSession.repeatedData.length - realData.length;
      let message = `Saved ${response.saved_count} records to ${options.line} - ${options.section}`;
      if (filteredCount > 0) {
        message += ` (filtered ${filteredCount} mock records)`;
      }

      setToast({ open: true, message, severity: 'success' });
      setApprovedReviewProposals([]);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to save to database';
      console.error("Save to database failed:", err);
      setToast({ open: true, message: errorMsg, severity: 'error' });
    }
  };

  return (
    <Box sx={{ ...scrollablePageSx, width: '100%', gap: 0 }}>
      {/* Top Tab Bar */}
      <Paper elevation={1} square sx={{ display: 'flex', alignItems: 'center', bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider', zIndex: 10 }}>
        <Tabs 
            value={activeCompareTabId} 
            onChange={(_, val) => setActiveCompareTab(val)} 
            variant="scrollable" 
            scrollButtons="auto"
            sx={{ flexGrow: 1, minHeight: 48 }}
        >
            {compareSessions.map(session => (
                <Tab 
                    key={session.id} 
                    value={session.id} 
                    label={
                        <Box sx={{ display: 'flex', alignItems: 'center', textTransform: 'none' }}>
                            <Typography variant="body2" sx={{ mr: 1, fontWeight: activeCompareTabId === session.id ? 'bold' : 'normal' }}>
                                {session.label}
                            </Typography>
                            <Box 
                                component="span"
                                onClick={(e) => handleCloseTab(e, session.id)}
                                sx={{ 
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    borderRadius: '50%', p: 0.2,
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
        <Stack direction="row" spacing={1} sx={{ p: 1, alignItems: 'center' }}>
            {/* Logic Button Left of New */}
            <Button 
                startIcon={<HelpOutlineIcon />} 
                variant="text" 
                size="small"
                onClick={() => setTutorialOpen(true)}
            >
                Logic
            </Button>
            <Button variant="outlined" size="small" startIcon={<AddIcon />} onClick={handleAddTab}>
                New
            </Button>
            <Button variant="outlined" color="error" size="small" startIcon={<RestartAltIcon />} onClick={handleResetAll} disabled={compareSessions.length === 0}>
                Reset
            </Button>
        </Stack>
      </Paper>

      {/* Main Content Split View (Config | Results) */}
      <Box sx={{ ...fillDataRegionSx, flexGrow: 1, flexDirection: 'row' }}>
        
        {/* Left Side: Configuration (Collapsible) - Issue 1 */}
        {activeSession && (
            <Paper 
                elevation={3} 
                sx={{ 
                    width: configOpen ? 320 : 40, 
                    transition: 'width 0.3s ease', 
                    display: 'flex', 
                    flexDirection: 'column', 
                    borderRight: 1, 
                    borderColor: 'divider',
                    flexShrink: 0,
                    overflow: 'hidden',
                    minHeight: 0,
                    bgcolor: 'background.default'
                }}
            >
                <Box sx={{ 
                    p: 1, 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: configOpen ? 'space-between' : 'center', 
                    bgcolor: 'background.paper',
                    borderBottom: 1,
                    borderColor: 'divider'
                }}>
                    {configOpen && <Typography variant="subtitle2" fontWeight="bold">Configuration</Typography>}
                    <IconButton size="small" onClick={() => setConfigOpen(!configOpen)}>
                        {configOpen ? <KeyboardArrowLeftIcon /> : <KeyboardArrowRightIcon />}
                    </IconButton>
                </Box>
                
                {configOpen && (
                    <Box sx={{ p: 2, overflowY: 'auto', flexGrow: 1, minHeight: 0 }}>
                        <Typography variant="caption" color="text.secondary" paragraph>
                            Strict Order: Latest &rarr; Previous.
                        </Typography>

                        <Stack spacing={2}>
                            {/* Latest */}
                            <Paper
                                variant="outlined"
                                {...latestDragHandlers}
                                sx={{
                                    p: 1.5,
                                    bgcolor: 'background.paper',
                                    border: '2px dashed',
                                    borderColor: latestDragActive ? 'primary.main' : 'divider',
                                    transition: 'border-color 0.15s ease',
                                }}
                            >
                                <Typography variant="caption" color="primary" fontWeight="bold">1. Latest Cycle (Newest) *</Typography>
                                <Button fullWidth component="label" variant="outlined" size="small" startIcon={<UploadFileIcon />} sx={{ mt: 1 }}>
                                    Select File
                                    <input type="file" hidden accept=".xlsx,.xls" onChange={handleLatestFileSelect} />
                                </Button>
                                <Box sx={{ mt: 0.5, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <Typography variant="caption" noWrap color="text.secondary" sx={{ flex: 1 }}>
                                        {activeSession.latestFile ? activeSession.latestFile.name : "None"}
                                    </Typography>
                                    {activeSession.latestFile && (
                                        <IconButton aria-label="Remove latest report" size="small" onClick={clearLatestFile} sx={{ p: 0.5 }}>
                                            <CloseIcon fontSize="small" sx={{ fontSize: 14 }} />
                                        </IconButton>
                                    )}
                                </Box>
                                {!activeSession.latestFile && (
                                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, textAlign: 'center' }}>
                                        Drop file here or click Browse
                                    </Typography>
                                )}
                            </Paper>

                            {/* Closest Previous */}
                            <Paper
                                variant="outlined"
                                {...closestDragHandlers}
                                sx={{
                                    p: 1.5,
                                    bgcolor: 'background.paper',
                                    border: '2px dashed',
                                    borderColor: closestDragActive ? 'secondary.main' : 'divider',
                                    transition: 'border-color 0.15s ease',
                                }}
                            >
                                <Typography variant="caption" color="secondary" fontWeight="bold">2. Closest Previous Cycle *</Typography>
                                <Button fullWidth component="label" variant="outlined" size="small" startIcon={<UploadFileIcon />} sx={{ mt: 1 }}>
                                    Select File
                                    <input type="file" hidden accept=".xlsx,.xls" onChange={handleClosestFileSelect} />
                                </Button>
                                <Box sx={{ mt: 0.5, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <Typography variant="caption" noWrap color="text.secondary" sx={{ flex: 1 }}>
                                        {activeSession.closestPreviousFile ? activeSession.closestPreviousFile.name : "None"}
                                    </Typography>
                                    {activeSession.closestPreviousFile && (
                                        <IconButton aria-label="Remove previous report" size="small" onClick={clearClosestFile} sx={{ p: 0.5 }}>
                                            <CloseIcon fontSize="small" sx={{ fontSize: 14 }} />
                                        </IconButton>
                                    )}
                                </Box>
                                {!activeSession.closestPreviousFile && (
                                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, textAlign: 'center' }}>
                                        Drop file here or click Browse
                                    </Typography>
                                )}
                            </Paper>

                            {/* Older */}
                            <Paper
                                variant="outlined"
                                {...olderDragHandlers}
                                sx={{
                                    p: 1.5,
                                    bgcolor: 'background.paper',
                                    border: '2px dashed',
                                    borderColor: olderDragActive ? 'primary.main' : 'divider',
                                    transition: 'border-color 0.15s ease',
                                }}
                            >
                                <Typography variant="caption" color="text.secondary" fontWeight="bold">3. Older Previous (Optional)</Typography>
                                <Button fullWidth component="label" variant="outlined" size="small" startIcon={<AddIcon />} sx={{ mt: 1 }}>
                                    Add Files
                                    <input type="file" hidden multiple accept=".xlsx,.xls" onChange={handleOlderFilesSelect} />
                                </Button>
                                <List dense sx={{ mt: 1, maxHeight: 100, overflow: 'auto', border: 1, borderColor: 'divider', borderRadius: 1 }}>
                                    {activeSession.olderPreviousFiles.map((f, i) => (
                                        <ListItem key={i} disablePadding secondaryAction={
                                            <IconButton edge="end" size="small" onClick={() => removeOlderFile(i)}>
                                                <DeleteIcon fontSize="small" sx={{ fontSize: 16 }} />
                                            </IconButton>
                                        }>
                                            <ListItemText primary={f.name} primaryTypographyProps={{ variant: 'caption', noWrap: true }} />
                                        </ListItem>
                                    ))}
                                    {activeSession.olderPreviousFiles.length === 0 && (
                                        <ListItem disablePadding sx={{ p: 1 }}><Typography variant="caption" color="text.disabled">No older files</Typography></ListItem>
                                    )}
                                </List>
                                {activeSession.olderPreviousFiles.length === 0 && (
                                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, textAlign: 'center' }}>
                                        Drop file here or click Browse
                                    </Typography>
                                )}
                            </Paper>
                        </Stack>

                        {/* Optional Fields for Custom File Naming */}
                        <Divider sx={{ mt: 2, mb: 1 }} />
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                            Optional: Custom File Naming
                        </Typography>
                        <Stack spacing={1.5}>
                            <TextField
                                label="Task Number (Optional)"
                                placeholder="e.g., U1A, D3 (No need for RAC, S1, LMC)"
                                size="small"
                                fullWidth
                                value={activeSession.taskNo || ''}
                                onChange={(e) => updateCompareSession(activeSession.id, { 
                                    taskNo: e.target.value.trim() || undefined 
                                })}
                                helperText="For custom naming"
                                sx={{ bgcolor: 'background.paper' }}
                            />

                            <TextField
                                label="Station Start (Optional)"
                                placeholder="e.g., HUH, LOW"
                                size="small"
                                fullWidth
                                value={activeSession.stationStart || ''}
                                onChange={(e) => updateCompareSession(activeSession.id, { 
                                    stationStart: e.target.value.trim().toUpperCase() || undefined 
                                })}
                                helperText="Station code"
                                sx={{ bgcolor: 'background.paper' }}
                            />

                            <TextField
                                label="Station End (Optional)"
                                placeholder="e.g., TAP, KSR"
                                size="small"
                                fullWidth
                                value={activeSession.stationEnd || ''}
                                onChange={(e) => updateCompareSession(activeSession.id, { 
                                    stationEnd: e.target.value.trim().toUpperCase() || undefined 
                                })}
                                helperText="Station code"
                                sx={{ bgcolor: 'background.paper' }}
                            />
                        </Stack>

                        {activeSession.error && <Alert severity="error" sx={{ mt: 2, fontSize: '0.8rem' }}>{activeSession.error}</Alert>}

                        <Button 
                            variant="contained" 
                            fullWidth 
                            size="large"
                            onClick={handleCompare}
                            disabled={activeSession.loading || !activeSession.latestFile || !activeSession.closestPreviousFile}
                            startIcon={activeSession.loading ? <CircularProgress size={20} color="inherit" /> : <CompareArrowsIcon />}
                            sx={{ mt: 3 }}
                        >
                            {activeSession.loading ? "Running..." : "Compare"}
                        </Button>
                    </Box>
                )}
            </Paper>
        )}

        {/* Right Side: Results Area (Tabs: Table / Chart) */}
        <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0, minHeight: 0 }}>
             {compareSessions.length === 0 ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'text.secondary' }}>
                    <Typography variant="h5" gutterBottom>No Comparison Active</Typography>
                    <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddTab}>Start New Comparison</Button>
                </Box>
            ) : activeSession ? (
                <>
                    {/* Result Toolbar */}
                    <Box
                        aria-label="comparison result toolbar"
                        sx={{
                            borderBottom: 1,
                            borderColor: 'divider',
                            bgcolor: 'background.paper',
                            px: 2,
                            py: 1,
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 1,
                        }}
                    >
                        <Box
                            sx={{
                                display: 'flex',
                                alignItems: { xs: 'stretch', md: 'center' },
                                justifyContent: 'space-between',
                                flexWrap: 'wrap',
                                gap: 1,
                            }}
                        >
                            <Tabs
                                value={resultTabIndex}
                                onChange={(_, v) => setResultTabIndex(v)}
                                sx={{ minHeight: 42, '& .MuiTab-root': { minHeight: 42, py: 0.5 } }}
                            >
                                <Tab icon={<TableChartIcon fontSize="small" />} iconPosition="start" label="Repeated Table" />
                                <Tab icon={<ShowChartIcon fontSize="small" />} iconPosition="start" label="Comparison Chart" />
                            </Tabs>

                            {activeSession.repeatedData.length > 0 && (
                                <Stack
                                    direction="row"
                                    spacing={1}
                                    alignItems="center"
                                    sx={{ flexWrap: 'wrap', rowGap: 1 }}
                                >
                                    <Typography variant="body2" color="success.main" fontWeight="bold">
                                        {activeSession.repeatedData.length} {activeSession.repeatedData.length === 1 ? 'Match' : 'Matches'}
                                    </Typography>
                                    {pendingChanges.size > 0 && (
                                        <Chip
                                            label={`${pendingChanges.size} pending`}
                                            size="small"
                                            color="warning"
                                            variant="outlined"
                                        />
                                    )}
                                </Stack>
                            )}
                        </Box>

                        {activeSession.repeatedData.length > 0 && (
                            <Stack
                                direction={{ xs: 'column', xl: 'row' }}
                                spacing={1}
                                alignItems={{ xs: 'stretch', xl: 'center' }}
                            >
                                {check1YearSummary && check1YearSummary.reviewRequired > 0 && (
                                  <Alert severity="warning" icon={<HelpOutlineIcon />} sx={{ width: '100%' }}>
                                    Check 1 Year 有 {check1YearSummary.reviewRequired} 筆需要複核。請檢查粉紅列及橙色 proposed 欄位，先 Save Edit，再 Save to DB。
                                  </Alert>
                                )}
                                <Stack
                                    aria-label="edit actions"
                                    direction="row"
                                    spacing={1}
                                    useFlexGap
                                    flexWrap="wrap"
                                    alignItems="center"
                                    sx={{ minWidth: 0 }}
                                >
                                    <Button
                                        variant="outlined"
                                        size="small"
                                        color="primary"
                                        startIcon={<EditIcon />}
                                        onClick={() => setBatchEditDialogOpen(true)}
                                        disabled={selectedRowIds.size === 0}
                                    >
                                        Batch Edit ({selectedRowIds.size})
                                    </Button>
                                    <Button
                                        variant="contained"
                                        size="small"
                                        color="warning"
                                        startIcon={<SaveIcon />}
                                        onClick={handleSaveEdit}
                                        disabled={pendingChanges.size === 0}
                                    >
                                        Save Edit
                                    </Button>
                                    <Button
                                        variant="outlined"
                                        size="small"
                                        color="inherit"
                                        startIcon={<UndoIcon />}
                                        onClick={handleDiscardChanges}
                                        disabled={pendingChanges.size === 0}
                                    >
                                        Discard
                                    </Button>
                                </Stack>

                                <Divider flexItem orientation="horizontal" sx={{ display: { xs: 'block', xl: 'none' } }} />
                                <Divider flexItem orientation="vertical" sx={{ display: { xs: 'none', xl: 'block' } }} />

                                <Stack
                                    aria-label="follow-up actions"
                                    direction="row"
                                    spacing={1}
                                    useFlexGap
                                    flexWrap="wrap"
                                    alignItems="center"
                                    sx={{ minWidth: 0 }}
                                >
                                    <Tooltip title="Check if exceptions have been verified in the database within the past year">
                                        <span>
                                        <Button
                                            variant="outlined"
                                            size="small"
                                            color="info"
                                            startIcon={isChecking1Year ? <CircularProgress size={16} /> : <HistoryIcon />}
                                            onClick={handleOpenCheck1YearDialog}
                                            disabled={isChecking1Year || pendingChanges.size > 0 || approvedReviewProposals.length > 0}
                                        >
                                            {isChecking1Year ? 'Checking...' : 'Check 1 Year Record'}
                                        </Button>
                                        </span>
                                    </Tooltip>
                                    <Button
                                        variant="outlined"
                                        size="small"
                                        color="success"
                                        startIcon={<DownloadIcon />}
                                        onClick={handleDownload}
                                    >
                                        Export
                                    </Button>
                                    <Button
                                        variant="contained"
                                        size="small"
                                        color="secondary"
                                        startIcon={<SaveIcon />}
                                        onClick={handleOpenSaveDialog}
                                        disabled={isSaving || pendingChanges.size > 0}
                                    >
                                        {isSaving ? 'Saving...' : 'Save to DB'}
                                    </Button>
                                </Stack>
                            </Stack>
                        )}
                    </Box>

                    {/* Result Content (Scrollable) */}
                    <Box sx={{ flexGrow: 1, minHeight: 0, overflow: 'hidden', position: 'relative', bgcolor: 'background.default' }}>
                        {resultTabIndex === 0 && (
                            <Box sx={{ height: '100%', width: '100%', p: 2, overflow: 'auto' }}>
                                <Paper elevation={0} sx={{ height: '100%', minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                                    {/* Phase 12 Issue 2: Collapsible filter panel */}
                                    <ComparisonFilterPanel
                                        data={activeSession.repeatedData as ComparisonRow[]}
                                        onFilteredDataChange={setFilteredComparisonData}
                                    />
                                    <Box sx={{ flexGrow: 1, minHeight: 0, overflow: 'hidden' }}>
                                    <ComparisonDataGrid 
                                        data={filteredComparisonData ?? activeSession.repeatedData}
                                        hasAnalyzed={!!activeSession.latestFileName}
                                        onRowUpdate={handleRowUpdate} 
                                        onRowClick={handleRowClick}
                                        onViewChart={handleViewChart}
                                        selectedRowIds={selectedRowIds}
                                        onSelectionChange={setSelectedRowIds}
                                        pendingChanges={pendingChanges}
                                        reviewIds={new Set(pendingReviewProposals.map(proposal => String(proposal.exception_id || '')))}
                                        metadata={{
                                            line: activeSession.latestFileName ? parseMetadataFromFileName(activeSession.latestFileName).line : undefined,
                                            track: activeSession.latestFileName ? parseMetadataFromFileName(activeSession.latestFileName).track : undefined,
                                            task_no: activeSession.taskNo || (activeSession.latestFileName ? parseMetadataFromFileName(activeSession.latestFileName).task_no : undefined),
                                            station_start: activeSession.stationStart || (activeSession.latestFileName ? parseMetadataFromFileName(activeSession.latestFileName).station_start : undefined),
                                            station_end: activeSession.stationEnd || (activeSession.latestFileName ? parseMetadataFromFileName(activeSession.latestFileName).station_end : undefined),
                                            task_run_date: activeSession.latestFileName 
                                                ? parseMetadataFromFileName(activeSession.latestFileName).task_run_date 
                                                : undefined
                                        }}
                                    />
                                    </Box>
                                </Paper>
                            </Box>
                        )}
                        {resultTabIndex === 1 && (
                            <Box sx={{ height: '100%', width: '100%', p: 2 }}>
                                <Paper elevation={2} sx={{ height: '100%', p: 1, overflow: 'hidden' }}>
                                    <ComparisonChart 
                                        chartData={activeSession.chartData} 
                                        selectedRow={selectedRow}
                                        onClearSelection={() => setSelectedRow(null)}
                                        sessionId={activeSession.id}
                                    />
                                </Paper>
                            </Box>
                        )}
                    </Box>
                </>
            ) : (
                <Box sx={{ p: 3 }}>Select a tab</Box>
            )}
        </Box>
      </Box>

      <AlgorithmTutorialDialog 
        open={tutorialOpen} 
        onClose={() => setTutorialOpen(false)} 
      />

      {/* Feature-001: Save to DB Dialog */}
      <SaveToDBDialog
        open={saveDialogOpen}
        onClose={() => setSaveDialogOpen(false)}
        onSave={handleSaveWithOptions}
        recordCount={getRealData().length}
        detectedLine={parseMetadataFromFileName(activeSession?.latestFileName || '').line}
        detectedSection={detectSection()}
        isSaving={isSaving}
      />

      {/* Feature-001: Check 1 Year Record Dialog */}
      <Check1YearDialog
        open={check1YearDialogOpen}
        onClose={() => setCheck1YearDialogOpen(false)}
        onCheck={handleCheck1YearWithOptions}
        recordCount={getRealData().length}
        detectedLine={parseMetadataFromFileName(activeSession?.latestFileName || '').line}
        detectedSection={detectSection()}
        isChecking={isChecking1Year}
      />

      {/* Phase 11 Issue 4: Batch Edit Dialog */}
      <BatchEditDialog
        open={batchEditDialogOpen}
        selectedCount={selectedRowIds.size}
        onConfirm={handleBatchEditConfirm}
        onClose={() => setBatchEditDialogOpen(false)}
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

export default HistoryCompareView;
