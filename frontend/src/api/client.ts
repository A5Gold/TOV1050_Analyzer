import axios from 'axios';
import type {
  ApiSuccessResponse,
  WearResponse,
  TrendResponse,
  CalculationResponse,
  StaggerResponse,
  WireWearDashboardResponse,
  DiagnosticsResponse,
  WireWearProjectionResponse,
  WireWearRemainingLifeResponse,
  WireWearRecordsResponse,
  WireWearSaveRequest,
  WireWearSaveResponse,
  WireWearUpdateRequest,
  WireWearWorkbenchResponse,
  WireWearSyncImportSummary,
  WireWearCyclePreview,
  WireWearCycleSaveResponse,
  WearCycleSaveResponse,
  WireWearChangeSet,
  WireWearChangeSetResponse,
  WireWearMetadataPreviewResponse,
  WireWearCycleWorkbenchResponse,
  WearCycleWorkbenchResponse,
  WearCyclePreview,
  WearCycleRecord,
  WearCycleSegment,
  WearCycleConflict,
  WearRecordChange,
  WearBusinessKey,
  WearChangeSetResult,
  WearMetadataCatalogItem,
  WireWearMetadataCatalogItem,
  WearWorkbenchColumn,
  WearLatestSummary,
  VersionDifferenceResponse,
  WearCandidatePreview,
  WearCandidatePreviewRequest,
  WireWearCandidatePreviewResponse,
  WearHistoricalWorkbookDiscovery,
  WearHistoricalWorkbookPreview,
  WireWearHistoricalWorkbookDiscoveryResponse,
  WireWearHistoricalWorkbookPreviewResponse,
  WearSyncApplySummary,
  WearSyncConflictDecision,
  WearSyncPreview,
  WearSyncValueSnapshot,
  WireWearSyncApplyResponse,
  WireWearSyncPreviewResponse,
} from '../types/api';
import {
  VERSION_DIFFERENCE_CYCLES,
  type VersionDifferenceFiles,
} from '../constants/versionDifferenceCycles';
import { TOV1050_LINES } from '../config/tov1050';

// Python Backend URL
// In dev mode, use a relative path so Vite proxy handles the request server-side
// (avoids CORS — proxy forwards /api → http://127.0.0.1:8000 without cross-origin headers).
// In production (Electron packaged, file:// origin), use the absolute localhost URL directly.
export const API_BASE_URL = import.meta.env.DEV ? '/api' : 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const shouldSuppressApiErrorLog = (error: any): boolean => {
  const status = error?.response?.status;
  const method = String(error?.config?.method ?? '').toLowerCase();
  const url = String(error?.config?.url ?? '');
  const params = error?.config?.params ?? {};

  return status === 409
    && method === 'post'
    && url.includes('/calculation/wear-records')
    && params.check_only === true
    && params.overwrite !== true;
};

// Response Interceptor for better error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!shouldSuppressApiErrorLog(error)) {
      console.error('API Error:', error.response || error.message);
    }
    return Promise.reject(error);
  }
);

// Metadata API Helper
export const metadataApi = {
  getMetadata: async (filename: string, sheetName: string = 'threshold'): Promise<any[]> => {
    // Returns Wide Format (List of Dicts)
    const response = await apiClient.get<any[]>(`/metadata/${filename}`, { params: { sheet_name: sheetName } });
    return response.data;
  },

  getSheetNames: async (filename: string): Promise<string[]> => {
    const response = await apiClient.get<string[]>(`/metadata/${filename}/sheets`);
    return response.data;
  },
  
  saveMetadata: async (filename: string, data: any[], sheetName: string = 'threshold') => {
    const response = await apiClient.post<{status: string, backup: string}>(`/metadata/${filename}`, data, { params: { sheet_name: sheetName } });
    return response.data;
  }
};

export const uploadCalculationFiles = async (
  files: File[],
): Promise<CalculationResponse> => {
  const formData = new FormData();
  files.forEach(file => formData.append('files[]', file));
  const response = await apiClient.post<CalculationResponse>('/calculation/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const uploadWearFiles = async (
  files: File[],
  lineOrOptions: string | { line?: string; cycleDate?: string; acceptedConflictIds?: string[] } = TOV1050_LINES[0],
  track?: string,
  section?: string,
): Promise<WearResponse> => {
  const options = typeof lineOrOptions === 'string' ? { line: lineOrOptions } : lineOrOptions;
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  formData.append('line', options.line ?? TOV1050_LINES[0]);
  if (track) formData.append('track', track);
  if (section) formData.append('section', section);
  if (options.cycleDate) formData.append('cycle_date', options.cycleDate);
  if (options.acceptedConflictIds) formData.append('accepted_conflict_ids', JSON.stringify(options.acceptedConflictIds));
  const response = await apiClient.post<WearResponse>('/calculation/wear', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

const asRecord = (value: unknown): Record<string, any> => (
  value && typeof value === 'object' ? value as Record<string, any> : {}
);

const first = (record: Record<string, any>, ...keys: string[]) => {
  for (const key of keys) if (record[key] !== undefined) return record[key];
  return undefined;
};

export const mapWireWearBusinessKey = (value: unknown): WearBusinessKey => {
  const record = asRecord(value);
  const lineGroup = first(record, 'line_group', 'lineGroup') as 'EAL' | 'TML';
  return {
    lineGroup,
    lineClass: (first(record, 'line_class', 'lineClass') ?? lineGroup) as 'EAL' | 'LMC' | 'TML',
    cycleDate: String(first(record, 'cycle_date', 'cycleDate') ?? ''),
    tensionLength: String(first(record, 'tension_length', 'tensionLength') ?? ''),
  };
};

export const mapWireWearCycleRecord = (value: unknown): WearCycleRecord => {
  const record = asRecord(value);
  const key = first(record, 'key', 'business_key', 'businessKey');
  const conflictIds = first(record, 'conflict_ids', 'conflictIds');
  const intervalValues = first(record, 'physical_intervals', 'physicalIntervals', 'intervals');
  const intervals = Array.isArray(intervalValues) && intervalValues.length > 0
    ? intervalValues.map((item: unknown) => {
        const interval = asRecord(item);
        return {
          track: (first(interval, 'track') ?? record.track ?? 'UP') as WearCycleRecord['track'],
          fromM: Number(first(interval, 'from_m', 'fromM') ?? 0),
          toM: Number(first(interval, 'to_m', 'toM') ?? 0),
        };
      })
    : [{
        track: (first(record, 'track', 'track_name', 'trackName') ?? 'UP') as WearCycleRecord['track'],
        fromM: Number(first(record, 'from_m', 'fromM') ?? 0),
        toM: Number(first(record, 'to_m', 'toM') ?? 0),
      }];
  return {
    key: mapWireWearBusinessKey(key ?? record),
    track: (first(record, 'track', 'track_name', 'trackName') ?? 'UP') as WearCycleRecord['track'],
    fromM: Number(first(record, 'from_m', 'fromM') ?? 0),
    toM: Number(first(record, 'to_m', 'toM') ?? 0),
    intervalCount: Number(first(record, 'interval_count', 'intervalCount') ?? intervals.length),
    intervals,
    avgWearMin: Number(first(record, 'avg_wear_min', 'avgWearMin') ?? 0),
    wearPercentage: Number(first(record, 'wear_percentage', 'wearPercentage') ?? 0),
    measurementSd: first(record, 'measurement_sd', 'measurementSd', 'sd') == null ? null : Number(first(record, 'measurement_sd', 'measurementSd', 'sd')),
    hasDataConflict: Boolean(first(record, 'has_data_conflict', 'hasDataConflict', 'data_conflict')),
    conflictIds: Array.isArray(conflictIds) ? conflictIds : [],
    updatedAt: first(record, 'updated_at', 'updatedAt') ?? null,
  };
};

export const mapWireWearCycleSegment = (value: unknown): WearCycleSegment => {
  const record = asRecord(value);
  const gaps = first(record, 'diagnostic_gaps', 'diagnosticGaps');
  const files = first(record, 'source_file_names', 'sourceFileNames');
  return {
    segmentName: String(first(record, 'segment_name', 'segmentName', 'name') ?? ''),
    isPresent: Boolean(first(record, 'is_present', 'isPresent', 'present')),
    coveragePercentage: Number(first(record, 'coverage_percentage', 'coveragePercentage') ?? 0),
    diagnosticGaps: Array.isArray(gaps) ? gaps : [],
    sourceFileNames: Array.isArray(files) ? files : [],
    acquisitionDates: Array.isArray(first(record, 'acquisition_dates', 'acquisitionDates')) ? first(record, 'acquisition_dates', 'acquisitionDates') : undefined,
    acquisitionDateFrom: first(record, 'acquisition_date_from', 'acquisitionDateFrom') ?? null,
    acquisitionDateTo: first(record, 'acquisition_date_to', 'acquisitionDateTo') ?? null,
  };
};

export const mapWireWearCycleConflict = (value: unknown): WearCycleConflict => {
  const record = asRecord(value);
  const sourceValues = first(record, 'source_values', 'sourceValues');
  return {
    conflictId: String(first(record, 'conflict_id', 'conflictId') ?? ''),
    measurementIdentity: String(first(record, 'measurement_identity', 'measurementIdentity') ?? ''),
    sourceValues: Array.isArray(sourceValues) ? sourceValues.map((item: any) => Array.isArray(item) ? [String(item[0]), Number(item[1])] as [string, number] : [String(item?.source ?? item?.file ?? ''), Number(item?.value ?? item?.wear_min ?? 0)] as [string, number]) : [],
    selectedWearMin: Number(first(record, 'selected_wear_min', 'selectedWearMin') ?? 0),
    isAccepted: Boolean(first(record, 'is_accepted', 'isAccepted')),
    acceptedAt: first(record, 'accepted_at', 'acceptedAt') ?? null,
  };
};

export const mapWireWearCyclePreview = (value: WireWearCyclePreview): WearCyclePreview => {
  const record = asRecord(value);
  const records = first(record, 'records') ?? [];
  const segments = first(record, 'segments') ?? [];
  const conflicts = first(record, 'conflicts') ?? [];
  return {
    lineGroup: first(record, 'line_group', 'lineGroup') as 'EAL' | 'TML',
    lineClass: (first(record, 'line_class', 'lineClass')
      ?? first(record, 'line_group', 'lineGroup')) as 'EAL' | 'LMC' | 'TML',
    cycleDate: String(first(record, 'cycle_date', 'cycleDate') ?? ''),
    records: Array.isArray(records) ? records.map(mapWireWearCycleRecord) : [],
    segments: Array.isArray(segments) ? segments.map(mapWireWearCycleSegment) : [],
    conflicts: Array.isArray(conflicts) ? conflicts.map(mapWireWearCycleConflict) : [],
    unresolved: Array.isArray(first(record, 'unresolved')) ? first(record, 'unresolved') : [],
    blockingReasons: Array.isArray(first(record, 'blocking_reasons', 'blockingReasons')) ? first(record, 'blocking_reasons', 'blockingReasons') : [],
    canSave: Boolean(first(record, 'can_save', 'canSave')),
    previewDigest: String(first(record, 'preview_digest', 'previewDigest') ?? ''),
    expectedDataVersion: Number(first(record, 'expected_data_version', 'expectedDataVersion') ?? 0),
  };
};

export const mapWearRecordChangeToWire = (change: WearRecordChange): WireWearChangeSet['operations'][number] => {
  const record = change as any;
  if (record.kind === 'delete_row') return {
    kind: 'delete_row',
    line_group: record.lineGroup,
    line_class: record.lineClass,
    cycle_date: record.cycleDate,
  };
  const key = mapWireWearBusinessKey(record.key);
  const wireKey = {
    line_group: key.lineGroup,
    line_class: key.lineClass,
    cycle_date: key.cycleDate,
    tension_length: key.tensionLength,
  };
  if (record.kind === 'add') return { kind: 'add', key: wireKey, avg_wear_min: record.avgWearMin };
  if (record.kind === 'edit') return { kind: 'edit', key: wireKey, avg_wear_min: record.avgWearMin, expected_updated_at: record.expectedUpdatedAt };
  return { kind: 'delete_cell', key: wireKey, expected_updated_at: record.expectedUpdatedAt };
};

export interface WearCyclePreviewOptions {
  lineGroup: 'EAL' | 'TML';
  lineClass?: 'EAL' | 'LMC' | 'TML';
  cycleDate?: string;
  acceptedConflictIds?: string[];
}

/** Parse complete-cycle files without mutating the database. */
export const previewWearCycle = async (
  files: File[],
  options: WearCyclePreviewOptions,
): Promise<WearCyclePreview> => {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  formData.append('line_group', options.lineGroup);
  formData.append('line_class', options.lineClass ?? options.lineGroup);
  if (options.cycleDate) formData.append('cycle_date', options.cycleDate);
  formData.append('accepted_conflict_ids', JSON.stringify(options.acceptedConflictIds ?? []));
  const response = await apiClient.post<WireWearCyclePreview>('/calculation/wear', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return mapWireWearCyclePreview(response.data);
};

/** Commit a previously previewed cycle, guarded by digest and data version. */
export const saveWearCycle = async (
  files: File[],
  options: WearCyclePreviewOptions & {
    expectedPreviewDigest: string;
    expectedDataVersion: number;
  },
): Promise<WearCycleSaveResponse> => {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  formData.append('line_group', options.lineGroup);
  formData.append('line_class', options.lineClass ?? options.lineGroup);
  formData.append('cycle_date', options.cycleDate ?? '');
  formData.append('accepted_conflict_ids', JSON.stringify(options.acceptedConflictIds ?? []));
  formData.append('expected_preview_digest', options.expectedPreviewDigest);
  formData.append('expected_data_version', String(options.expectedDataVersion));
  const response = await apiClient.post<WireWearCycleSaveResponse>('/calculation/wear-records/cycles', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  const value = response.data;
  return {
    cycleId: value.cycle_id,
    lineGroup: value.line_group,
    lineClass: value.line_class ?? value.line_group,
    cycleDate: value.cycle_date,
    sourceType: value.source_type,
    completenessState: value.completeness_state,
    acquisitionDateFrom: value.acquisition_date_from,
    acquisitionDateTo: value.acquisition_date_to,
    sourceLineage: value.source_lineage ?? [],
    records: (value.records ?? []).map(mapWireWearCycleRecord),
    segments: (value.segments ?? []).map(mapWireWearCycleSegment),
    conflictDecisions: (value.conflict_decisions ?? []).map(mapWireWearCycleConflict),
    wireWearDataVersion: Number(value.wire_wear_data_version ?? 0),
  };
};

export const applyWearChanges = async (
  changeSet: WireWearChangeSet | {
    operations: WearRecordChange[]
    expectedDataVersion: number
    origin?: 'manual' | 'workbook'
  },
): Promise<WireWearChangeSetResponse> => {
  const wireChangeSet = 'expectedDataVersion' in changeSet
    ? {
      operations: changeSet.operations.map(mapWearRecordChangeToWire),
      expected_data_version: changeSet.expectedDataVersion,
      origin: changeSet.origin ?? 'manual',
    }
    : changeSet;
  const response = await apiClient.post<WireWearChangeSetResponse>('/calculation/wear-records/changes', wireChangeSet);
  return response.data;
};

// Staged workbench edits use the explicit name exposed by the UI store.
export const applyWireWearChanges = applyWearChanges;

export const mapWearCandidatePreview = (
  value: WireWearCandidatePreviewResponse,
): WearCandidatePreview => ({
  lineGroup: value.line_group,
  lineClass: value.line_class,
  cycleDate: value.cycle_date,
  wireWearDataVersion: Number(value.wire_wear_data_version),
  counts: value.counts,
  candidates: value.candidates.map(candidate => ({
    status: candidate.status,
    key: candidate.key ? mapWireWearBusinessKey(candidate.key) : null,
    avgWearMin: candidate.avg_wear_min,
    track: candidate.track,
    existingAvgWearMin: candidate.existing_avg_wear_min,
    expectedUpdatedAt: candidate.expected_updated_at,
    sourceType: candidate.source_type,
    sourceSheet: candidate.source_sheet,
    sourceRow: candidate.source_row,
    sourceCell: candidate.source_cell,
    originalValue: candidate.original_value,
    excluded: candidate.excluded,
    rowId: candidate.row_id,
    issues: candidate.issues,
  })),
});

export const previewWearRecordCandidates = async (
  payload: WearCandidatePreviewRequest,
): Promise<WearCandidatePreview> => {
  const response = await apiClient.post<WireWearCandidatePreviewResponse>(
    '/calculation/wear-records/candidates/preview',
    {
      line_class: payload.lineClass,
      cycle_date: payload.cycleDate,
      rows: payload.rows.map(row => ({
        row_id: row.rowId,
        tension_length: row.tensionLength,
        avg_wear_min: row.avgWearMin,
        tension_length_cell: row.tensionLengthCell,
        avg_wear_min_cell: row.avgWearMinCell,
        excluded: row.excluded ?? false,
      })),
    },
  );
  return mapWearCandidatePreview(response.data);
};

const mapHistoricalSheet = (
  sheet: WireWearHistoricalWorkbookDiscoveryResponse['sheets'][number],
) => ({
  name: sheet.sheet_name,
  support: sheet.support,
  selectedByDefault: sheet.selected_by_default,
  enabled: sheet.enabled,
  reasonCode: sheet.reason_code,
});

export const discoverHistoricalWearWorkbook = async (
  file: File,
): Promise<WearHistoricalWorkbookDiscovery> => {
  const form = new FormData();
  form.append('file', file);
  const response = await apiClient.post<WireWearHistoricalWorkbookDiscoveryResponse>(
    '/calculation/wear-records/historical/discover',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return { sheets: response.data.sheets.map(mapHistoricalSheet) };
};

export const previewHistoricalWearWorkbook = async (
  file: File,
  selectedSheets: string[],
): Promise<WearHistoricalWorkbookPreview> => {
  const form = new FormData();
  form.append('file', file);
  form.append('selected_sheets', JSON.stringify(selectedSheets));
  const response = await apiClient.post<WireWearHistoricalWorkbookPreviewResponse>(
    '/calculation/wear-records/historical/preview',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  const value = response.data;
  return {
    sheets: value.sheets.map(mapHistoricalSheet),
    selectedSheets: value.selected_sheets,
    wireWearDataVersion: Number(value.wire_wear_data_version),
    sheetSummaries: value.sheet_summaries.map(summary => ({
      sheetName: summary.sheet_name,
      skipped: summary.skipped,
      new: summary.new,
      update: summary.update,
      noChange: summary.no_change,
      duplicate: summary.duplicate,
      error: summary.error,
      total: summary.total,
    })),
    totals: value.totals,
    candidates: value.candidates.map(candidate => ({
      status: candidate.status,
      key: candidate.key ? mapWireWearBusinessKey(candidate.key) : null,
      avgWearMin: candidate.avg_wear_min,
      track: candidate.track,
      existingAvgWearMin: candidate.existing_avg_wear_min,
      expectedUpdatedAt: candidate.expected_updated_at,
      sourceType: candidate.source_type,
      sourceSheet: candidate.source_sheet,
      sourceRow: candidate.source_row,
      sourceCell: candidate.source_cell,
      originalValue: candidate.original_value,
      excluded: candidate.excluded,
      rowId: candidate.row_id,
      issues: candidate.issues,
    })),
    diagnostics: value.diagnostics.map(diagnostic => ({
      code: diagnostic.code,
      message: diagnostic.message,
      sheet: diagnostic.sheet,
      cell: diagnostic.cell,
      originalValue: diagnostic.original_value,
    })),
  };
};

export const mapWireWearChangeSetResult = (value: WireWearChangeSetResponse): WearChangeSetResult => ({
  added: Number(value.added ?? 0),
  edited: Number(value.edited ?? 0),
  deleted: Number(value.deleted ?? 0),
  backupPath: value.backup_path ?? null,
  wireWearDataVersion: Number(value.wire_wear_data_version ?? 0),
});

export const mapWireWearMetadataCatalogItem = (value: WireWearMetadataCatalogItem | Record<string, unknown>): WearMetadataCatalogItem => {
  const record = value as Record<string, any>;
  const intervalValues = record.intervals ?? record.physical_intervals ?? record.physicalIntervals;
  const intervals = Array.isArray(intervalValues) && intervalValues.length > 0
    ? intervalValues.map((item: Record<string, any>) => ({
        track: (item.track ?? record.track ?? 'UP') as WearMetadataCatalogItem['track'],
        fromM: Number(item.from_m ?? item.fromM ?? 0),
        toM: Number(item.to_m ?? item.toM ?? 0),
      }))
    : [{
        track: (record.track ?? 'UP') as WearMetadataCatalogItem['track'],
        fromM: Number(record.from_m ?? record.fromM ?? 0),
        toM: Number(record.to_m ?? record.toM ?? 0),
      }];
  return {
    lineGroup: (record.line_group ?? record.lineGroup) as 'EAL' | 'TML',
    lineClass: (record.line_class ?? record.lineClass
      ?? record.line_group ?? record.lineGroup) as 'EAL' | 'LMC' | 'TML',
    tensionLength: String(record.tension_length ?? record.tensionLength ?? ''),
    track: (record.track ?? 'UP') as 'UP' | 'DN' | 'Siding',
    fromM: Number(record.from_m ?? record.fromM ?? 0),
    toM: Number(record.to_m ?? record.toM ?? 0),
    intervalCount: Number(record.interval_count ?? record.intervalCount ?? intervals.length),
    intervals,
  };
};

export function analyzeVersionDifference(
  files: Readonly<VersionDifferenceFiles>,
): Promise<VersionDifferenceResponse>;
export function analyzeVersionDifference(
  latest: File,
  previous1: File,
  previous2?: File | null,
  previous3?: File | null,
  previous4?: File | null,
): Promise<VersionDifferenceResponse>;
export async function analyzeVersionDifference(
  filesOrLatest: Readonly<VersionDifferenceFiles> | File,
  previous1?: File | null,
  previous2?: File | null,
  previous3?: File | null,
  previous4?: File | null,
): Promise<VersionDifferenceResponse> {
  const files = 'latest' in filesOrLatest
    ? filesOrLatest
    : Object.fromEntries(
        VERSION_DIFFERENCE_CYCLES.map((cycle, index) => [
          cycle.role,
          [filesOrLatest, previous1, previous2, previous3, previous4][index] ?? null,
        ]),
      ) as VersionDifferenceFiles;
  const formData = new FormData();
  VERSION_DIFFERENCE_CYCLES.forEach(cycle => {
    const file = files[cycle.role];
    if (file) formData.append(cycle.formField, file);
  });
  const response = await apiClient.post<VersionDifferenceResponse>('/analyze/version-difference', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export const mapWireWearWorkbenchColumn = (value: Record<string, unknown>): WearWorkbenchColumn => {
  const mapped = mapWireWearMetadataCatalogItem(value);
  return {
    tensionLength: mapped.tensionLength,
    track: mapped.track,
    fromM: mapped.fromM,
    toM: mapped.toM,
    intervalCount: mapped.intervalCount,
    intervals: mapped.intervals,
  };
};

export const mapWireWearLatestSummary = (value: Record<string, unknown>): WearLatestSummary => ({
  tensionLength: String(value.tension_length ?? value.tensionLength ?? ''),
  latestCycleDate: (value.latest_cycle_date ?? value.latestCycleDate ?? null) as string | null,
  latestAvgWearMin: (value.latest_avg_wear_min ?? value.latestAvgWearMin) == null ? null : Number(value.latest_avg_wear_min ?? value.latestAvgWearMin),
  latestWearPercentage: (value.latest_wear_percentage ?? value.latestWearPercentage) == null ? null : Number(value.latest_wear_percentage ?? value.latestWearPercentage),
  historicalSd: (value.historical_sd ?? value.historicalSd) == null ? null : Number(value.historical_sd ?? value.historicalSd),
  wearRateMmPerYear: (value.wear_rate_mm_per_year ?? value.wearRateMmPerYear) == null ? null : Number(value.wear_rate_mm_per_year ?? value.wearRateMmPerYear),
  observationCount: Number(value.observation_count ?? value.observationCount ?? 0),
  rSquared: (value.r_squared ?? value.rSquared) == null ? null : Number(value.r_squared ?? value.rSquared),
  trendStatus: String(value.trend_status ?? value.trendStatus ?? ''),
});

export const fetchWearMetadataPreview = async (
  lineGroup: 'EAL' | 'TML',
  tensionLength = '',
  lineClass: 'EAL' | 'LMC' | 'TML' = lineGroup,
): Promise<{
  lineGroup: 'EAL' | 'TML';
  lineClass: 'EAL' | 'LMC' | 'TML';
  catalog: WearMetadataCatalogItem[];
}> => {
  const response = await apiClient.get<WireWearMetadataPreviewResponse>('/calculation/wear-records/metadata-preview', {
    params: {
      line_group: lineGroup,
      line_class: lineClass,
      tension_length: tensionLength,
    },
  });
  return {
    lineGroup: response.data.line_group,
    lineClass: response.data.line_class ?? lineClass,
    catalog: (response.data.catalog ?? []).map(mapWireWearMetadataCatalogItem),
  };
};

export const mapWireWearCycleWorkbench = (value: WireWearCycleWorkbenchResponse): WearCycleWorkbenchResponse => {
  const lineGroup = (value.line_group ?? 'EAL') as 'EAL' | 'TML';
  const lineClass = (value.line_class ?? lineGroup) as 'EAL' | 'LMC' | 'TML';
  const matrixRows = (value.matrix_rows ?? []).map(row => ({
    cycleDate: row.cycle_date,
    values: { ...row.values },
  }));
  const latestSummary = (value.latest_summary ?? []).map(mapWireWearLatestSummary);
  const wireWearDataVersion = Number(value.wire_wear_data_version ?? 0);
  return {
    lineGroup,
    lineClass,
    columns: (value.columns ?? []).map(mapWireWearWorkbenchColumn),
    matrixRows,
    latestSummary,
    records: (value.records ?? []).map(mapWireWearCycleRecord),
    catalog: (value.catalog ?? []).map(mapWireWearMetadataCatalogItem),
    selectedTensionLength: value.selected_tension_length ?? null,
    summaryOnly: Boolean(value.summary_only),
    wireWearDataVersion,
    // Backward-compatible aliases used by the existing store/UI.
    line_group: lineGroup,
    line_class: lineClass,
    history_rows: value.matrix_rows ?? [],
    latest_summary_rows: latestSummary,
    wire_wear_data_version: wireWearDataVersion,
  };
};

export const exportWearCycleExcel = async (
  options: {
    lineGroup?: 'EAL' | 'TML';
    lineClass?: 'EAL' | 'LMC' | 'TML';
    cycleDate?: string;
  } = {},
): Promise<Blob> => {
  const response = await apiClient.get<Blob>('/calculation/wear-records/export.xlsx', {
    responseType: 'blob',
    params: {
      line_group: options.lineGroup,
      line_class: options.lineClass ?? options.lineGroup,
      cycle_date: options.cycleDate,
    },
  });
  return response.data;
};

export const exportWearCycleSyncJson = async (
  options: { sourceWorkstation?: string } = {},
): Promise<Blob> => {
  const response = await apiClient.get<Blob>('/calculation/wear-records/sync.json', {
    responseType: 'blob',
    params: { source_workstation: options.sourceWorkstation },
  });
  return response.data;
};

export const exportWearSyncJson = exportWearCycleSyncJson;

export const fetchWearCycleWorkbench = async (
  params: {
    lineGroup?: 'EAL' | 'TML';
    lineClass?: 'EAL' | 'LMC' | 'TML';
    tensionLengthQuery?: string;
    selectedTensionLength?: string;
    summaryOnly?: boolean;
    dateFrom?: string;
    dateTo?: string;
  } = {},
): Promise<WearCycleWorkbenchResponse> => {
  const response = await apiClient.get<WireWearCycleWorkbenchResponse>('/calculation/wear-records/workbench', {
    params: {
      line_group: params.lineGroup,
      line_class: params.lineClass ?? params.lineGroup,
      tension_length_query: params.tensionLengthQuery,
      selected_tension_length: params.selectedTensionLength,
      summary_only: params.summaryOnly,
      date_from: params.dateFrom,
      date_to: params.dateTo,
    },
  });
  return mapWireWearCycleWorkbench(response.data);
};

export const previewWearSync = async (sourcePackage: Record<string, unknown>) => {
  const response = await apiClient.post<WireWearSyncPreviewResponse>(
    '/calculation/wear-records/sync/preview',
    sourcePackage,
  );
  return response.data;
};

export const applyWearSync = async (payload: Record<string, unknown>) => {
  const response = await apiClient.post<WireWearSyncApplyResponse>(
    '/calculation/wear-records/sync/apply',
    payload,
  );
  return response.data;
};

const mapWearSyncSnapshot = (value?: Record<string, any> | null): WearSyncValueSnapshot | null => {
  if (!value) return null;
  const lineage = Array.isArray(value.source_lineage) ? value.source_lineage.join(', ') : null;
  return {
    avgWearMin: value.avg_wear_min == null ? null : Number(value.avg_wear_min),
    track: value.track ?? null,
    updatedAt: value.updated_at ?? null,
    deletedAt: value.deleted_at ?? null,
    source: value.source_package_id ?? lineage,
  };
};

export const previewWireWearSyncPackage = async (file: File): Promise<WearSyncPreview> => {
  const sourcePackage = JSON.parse(await file.text()) as Record<string, unknown>;
  const value = await previewWearSync(sourcePackage);
  const packageValue = value.source_package;
  return {
    sourcePackage: packageValue,
    packageInfo: {
      packageId: String(packageValue.package_id ?? ''),
      sourceWorkstation: packageValue.source_workstation ?? null,
      exportedAt: packageValue.exported_at ?? null,
      schema: packageValue.schema ?? null,
    },
    rows: value.actions.map(action => {
      const [lineGroup, lineClass, cycleDate, tensionLength] = action.key;
      return {
        id: action.key.join(':'),
        status: action.status,
        key: { lineGroup, lineClass, cycleDate, tensionLength },
        local: mapWearSyncSnapshot(action.local_record ?? action.local_tombstone),
        incoming: mapWearSyncSnapshot(action.record ?? action.tombstone),
        detail: action.detail ?? null,
      };
    }),
    expectedDataVersion: Number(value.expected_data_version),
    previewDigest: value.preview_digest,
    warnings: value.warnings ?? [],
  };
};

export const applyWireWearSyncPreview = async (
  preview: WearSyncPreview,
  decisions: WearSyncConflictDecision[],
): Promise<WearSyncApplySummary> => {
  const value = await applyWearSync({
    source_package: preview.sourcePackage,
    preview_digest: preview.previewDigest,
    expected_data_version: preview.expectedDataVersion,
    conflict_decisions: decisions.map(decision => ({
      key: {
        line_group: decision.key.lineGroup,
        line_class: decision.key.lineClass,
        cycle_date: decision.key.cycleDate,
        tension_length: decision.key.tensionLength,
      },
      decision: decision.choice,
    })),
  });
  return {
    created: Number(value.created ?? 0),
    updated: Number(value.updated ?? 0),
    deleted: Number(value.deleted ?? 0),
    keepLocal: Number(value.keep_local ?? 0),
    noChange: Number(value.no_change ?? 0),
    conflictsResolved: Number(value.conflicts_resolved ?? 0),
    backupPath: value.backup_path ?? null,
    dataVersion: Number(value.wire_wear_data_version ?? 0),
  };
};

export const saveWireWearRecords = async (
  payload: WireWearSaveRequest,
  overwrite = false,
  checkOnly = false,
): Promise<WireWearSaveResponse> => {
  const response = await apiClient.post<WireWearSaveResponse>(
    '/calculation/wear-records',
    payload,
    { params: { overwrite, check_only: checkOnly } },
  );
  return response.data;
};

export const fetchWireWearRecords = async (
  params: Record<string, string | undefined> = {},
): Promise<WireWearRecordsResponse> => {
  const response = await apiClient.get<WireWearRecordsResponse>('/calculation/wear-records', { params });
  return response.data;
};

export const fetchWireWearWorkbench = async (
  params: Record<string, string | undefined> = {},
): Promise<WireWearWorkbenchResponse> => {
  const response = await apiClient.get<WireWearWorkbenchResponse>('/calculation/wear-records/workbench', { params });
  return response.data;
};

export const addManualWireWearRecords = async (
  payload: WireWearSaveRequest,
): Promise<WireWearSaveResponse> => {
  const response = await apiClient.post<WireWearSaveResponse>('/calculation/wear-records/manual', payload);
  return response.data;
};

export const updateWireWearRecord = async (
  recordId: number,
  payload: WireWearUpdateRequest,
): Promise<ApiSuccessResponse> => {
  const response = await apiClient.patch<ApiSuccessResponse>(`/calculation/wear-records/${recordId}`, payload);
  return response.data;
};

export const deleteWireWearRecord = async (recordId: number): Promise<ApiSuccessResponse> => {
  const response = await apiClient.delete<ApiSuccessResponse>(`/calculation/wear-records/${recordId}`);
  return response.data;
};

export const exportWireWearRecords = async (
  params: Record<string, string | undefined> = {},
): Promise<Blob> => {
  const response = await apiClient.get('/calculation/wear-records/export', {
    params,
    responseType: 'blob',
  });
  return response.data;
};

export const exportWireWearSyncPackage = async (
  sourceLabel = 'TOV640 Analyzer',
): Promise<Blob> => {
  const response = await apiClient.get('/calculation/wear-records/sync/export', {
    params: { source_label: sourceLabel },
    responseType: 'blob',
  });
  return response.data;
};

export const importWireWearSyncPackage = async (file: File): Promise<WireWearSyncImportSummary> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post<WireWearSyncImportSummary>(
    '/calculation/wear-records/sync/import',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return response.data;
};

export const fetchWireWearDashboard = async (): Promise<WireWearDashboardResponse> => {
  const response = await apiClient.get<WireWearDashboardResponse>('/calculation/wear-records/dashboard');
  return response.data;
};

export const fetchWireWearProjection = async (
  thresholdMm = 10.2,
): Promise<WireWearProjectionResponse> => {
  const response = await apiClient.get<any>('/calculation/wear-records/projection', {
    params: { threshold_mm: thresholdMm },
  });
  const mapRecord = (record: any) => ({
    lineGroup: record.line_group,
    lineClass: record.line_class ?? record.line_group,
    tensionLength: record.tension_length,
    track: record.track ?? null,
    fromM: record.from_m ?? null,
    toM: record.to_m ?? null,
    latestCycleDate: record.latest_cycle_date,
    latestAvgWearMin: record.latest_avg_wear_min,
    latestWearPercentage: record.latest_wear_percentage,
    wearRatePercentPerYear: record.wear_rate_percent_per_year ?? record.wear_percent_per_year ?? null,
    wearRateMmPerYear: record.wear_rate_mm_per_year ?? record.wear_mm_per_year ?? null,
    observationCount: record.observation_count ?? record.record_count,
    rSquared: record.r_squared ?? null,
    trendStatus: record.trend_status,
    projectedCrossingDate: record.projected_crossing_date,
    projectedYear: record.projected_year,
    yearsToThreshold: record.years_to_threshold,
  });
  const mapGroup = (group: any) => ({
    yearBuckets: (group.year_buckets ?? []).map((bucket: any) => ({
      year: bucket.year,
      count: bucket.count,
      records: (bucket.records ?? []).map(mapRecord),
    })),
    alreadyAtThreshold: (group.already_at_threshold ?? []).map(mapRecord),
    insufficientData: (group.insufficient_data ?? []).map(mapRecord),
    nonPositiveRate: (group.non_positive_rate ?? []).map(mapRecord),
  });
  return {
    thresholdMm: response.data.threshold_mm,
    thresholdPercentage: response.data.threshold_percentage,
    horizonYears: response.data.horizon_years ?? response.data.years,
    lineGroups: {
      EAL: mapGroup(response.data.line_groups.EAL),
      TML: mapGroup(response.data.line_groups.TML),
    },
  };
};

export const fetchWireWearRemainingLife = async (
  thresholdMm = 10.2,
): Promise<WireWearRemainingLifeResponse> => {
  const response = await apiClient.get<any>('/calculation/wear-records/remaining-life', {
    params: { threshold_mm: thresholdMm },
  });
  const mapRecord = (record: any) => ({
    lineGroup: record.line_group,
    lineClass: record.line_class ?? record.line_group,
    tensionLength: record.tension_length,
    track: record.track ?? null,
    fromM: record.from_m ?? null,
    toM: record.to_m ?? null,
    latestCycleDate: record.latest_cycle_date ?? null,
    latestAvgWearMin: record.latest_avg_wear_min ?? null,
    latestWearPercentage: record.latest_wear_percentage ?? null,
    wearRatePercentPerYear: record.wear_rate_percent_per_year ?? null,
    wearRateMmPerYear: record.wear_rate_mm_per_year ?? null,
    observationCount: record.observation_count ?? 0,
    rSquared: record.r_squared ?? null,
    trendStatus: record.trend_status,
    projectedCrossingDate: record.projected_crossing_date ?? null,
    remainingDays: record.remaining_days ?? null,
    curve: Array.isArray(record.curve) ? record.curve : [],
  });
  return {
    thresholdMm: response.data.threshold_mm,
    rows: (response.data.rows ?? []).map(mapRecord),
    defaultRows: (response.data.default_rows ?? []).map(mapRecord),
  };
};

export const fetchDiagnostics = async (): Promise<DiagnosticsResponse> => {
  const response = await apiClient.get<DiagnosticsResponse>('/diagnostics');
  return response.data;
};

export const uploadTrendFiles = async (
  files: File[],
  repeatedFile?: File | null,
  line: string = TOV1050_LINES[0],
): Promise<TrendResponse> => {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  formData.append('line', line);
  if (repeatedFile) formData.append('repeated_file', repeatedFile);
  const response = await apiClient.post<TrendResponse>('/calculation/trend', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const uploadStaggerFile = async (
  file: File,
  repeatedFile?: File | null,
): Promise<StaggerResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  if (repeatedFile) {
    formData.append('repeated_file', repeatedFile);
  }
  const response = await apiClient.post<StaggerResponse>('/calculation/stagger', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export default apiClient;
