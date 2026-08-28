import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { CalculationResponse } from '../../types/api'

// Mock axios before importing the module under test
const mockPost = vi.fn()
const mockGet = vi.fn()

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      post: mockPost,
      get: mockGet,
      interceptors: {
        response: { use: vi.fn() },
      },
    })),
  },
}))

// Import after mock is set up
const {
  uploadCalculationFiles,
  exportWearCycleExcel,
  exportWearCycleSyncJson,
  mapWireWearCycleWorkbench,
  saveWearCycle,
  fetchWireWearProjection,
  analyzeVersionDifference,
  previewWearRecordCandidates,
  discoverHistoricalWearWorkbook,
  previewHistoricalWearWorkbook,
} = await import('../client')

describe('analyzeVersionDifference', () => {
  beforeEach(() => vi.clearAllMocks())

  it('posts two required reports with explicit role names', async () => {
    mockPost.mockResolvedValue({ data: { status: 'ready', latest_file: 'latest.xlsx', comparisons: [] } })
    const latest = new File(['latest'], 'latest.xlsx')
    const previous1 = new File(['previous-1'], 'previous-1.xlsx')

    await analyzeVersionDifference(latest, previous1)

    const [url, formData, config] = mockPost.mock.calls[0]
    expect(url).toBe('/analyze/version-difference')
    expect((formData as FormData).get('latest')).toBe(latest)
    expect((formData as FormData).get('previous_1')).toBe(previous1)
    expect((formData as FormData).get('previous_2')).toBeNull()
    expect(config.headers['Content-Type']).toBe('multipart/form-data')
  })

  it('includes Previous 2 only when supplied', async () => {
    mockPost.mockResolvedValue({ data: { status: 'ready', latest_file: 'latest.xlsx', comparisons: [] } })
    const latest = new File(['latest'], 'latest.xlsx')
    const previous1 = new File(['previous-1'], 'previous-1.xlsx')
    const previous2 = new File(['previous-2'], 'previous-2.xlsx')

    await analyzeVersionDifference(latest, previous1, previous2)

    const formData = mockPost.mock.calls[0][1] as FormData
    expect(formData.get('previous_2')).toBe(previous2)
  })
})

describe('fetchWireWearProjection', () => {
  beforeEach(() => vi.clearAllMocks())

  it('queries threshold_mm and maps the projection response at the client boundary', async () => {
    mockGet.mockResolvedValue({ data: {
      threshold_mm: 9.1,
      threshold_percentage: 31.0606,
      horizon_years: 30,
      line_groups: {
        EAL: { year_buckets: [{ year: 2030, count: 1, records: [{ line_group: 'EAL', tension_length: '1', latest_cycle_date: '2026-01-01', latest_avg_wear_min: 11, latest_wear_percentage: 16, observation_count: 2, trend_status: 'eligible' }] }], already_at_threshold: [], insufficient_data: [], non_positive_rate: [] },
        TML: { year_buckets: [], already_at_threshold: [], insufficient_data: [], non_positive_rate: [] },
      },
    } })

    const result = await fetchWireWearProjection(9.1)

    expect(mockGet).toHaveBeenCalledWith('/calculation/wear-records/projection', { params: { threshold_mm: 9.1 } })
    expect(result.thresholdMm).toBe(9.1)
    expect(result.lineGroups.EAL.yearBuckets[0].records[0].tensionLength).toBe('1')
  })
})

describe('uploadCalculationFiles', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('posts files as multipart/form-data', async () => {
    const mockResponse: { data: CalculationResponse } = {
      data: { wear_results: [], trend_results: [] },
    }
    mockPost.mockResolvedValue(mockResponse)

    const file = new File(['content'], 'test.datac', { type: 'application/octet-stream' })
    await uploadCalculationFiles([file])

    expect(mockPost).toHaveBeenCalledOnce()
    const [url, body, config] = mockPost.mock.calls[0]
    expect(url).toBe('/calculation/upload')
    expect(body).toBeInstanceOf(FormData)
    expect(config.headers['Content-Type']).toBe('multipart/form-data')
  })

  it('appends each file under the files[] key', async () => {
    mockPost.mockResolvedValue({ data: { wear_results: [], trend_results: [] } })

    const fileA = new File(['a'], 'a.datac')
    const fileB = new File(['b'], 'b.datac')
    await uploadCalculationFiles([fileA, fileB])

    const formData: FormData = mockPost.mock.calls[0][1]
    const entries = formData.getAll('files[]')
    expect(entries).toHaveLength(2)
  })

  it('returns CalculationResponse on success', async () => {
    const expected: CalculationResponse = {
      wear_results: [
        {
          line: 'EAL',
          track: 'UP',
          tension_length: 'TL1',
          from_m: 100,
          to_m: 200,
          avg_wear_min: 5.2,
          sd: 0.3,
          wear_percentage: 12.5,
          dates: ['2026-01-01'],
          record_points: [5.2],
        },
      ],
      trend_results: [
        {
          tension_length: 'TL1',
          from_m: 100,
          to_m: 200,
          level: 'L2',
          dates: ['2026-01-01'],
          record_points: [5.2],
          trend_points: [5.0],
          trend_next: 5.0,
          logic_1: true,
          logic_2: false,
          recommendation: 'verify on site',
        },
      ],
    }
    mockPost.mockResolvedValue({ data: expected })

    const file = new File(['content'], 'test.datac')
    const result = await uploadCalculationFiles([file])

    expect(result).toEqual(expected)
    expect(result.wear_results).toHaveLength(1)
    expect(result.trend_results).toHaveLength(1)
    expect(result.trend_results[0].recommendation).toBe('verify on site')
  })

  it('propagates errors from the API', async () => {
    mockPost.mockRejectedValue(new Error('Network Error'))

    const file = new File(['content'], 'test.datac')
    await expect(uploadCalculationFiles([file])).rejects.toThrow('Network Error')
  })
})

describe('complete-cycle client contracts', () => {
  beforeEach(() => vi.clearAllMocks())

  it('downloads Excel and sync JSON from the complete-cycle blob routes', async () => {
    const excel = new Blob(['xlsx'])
    const sync = new Blob(['{}'])
    mockGet.mockResolvedValueOnce({ data: excel }).mockResolvedValueOnce({ data: sync })

    await expect(exportWearCycleExcel({ lineGroup: 'EAL', cycleDate: '2026-05-28' })).resolves.toBe(excel)
    await expect(exportWearCycleSyncJson({ sourceWorkstation: 'Laptop A' })).resolves.toBe(sync)

    expect(mockGet).toHaveBeenNthCalledWith(1, '/calculation/wear-records/export.xlsx', {
      responseType: 'blob', params: {
        line_group: 'EAL', line_class: 'EAL', cycle_date: '2026-05-28',
      },
    })
    expect(mockGet).toHaveBeenNthCalledWith(2, '/calculation/wear-records/sync.json', {
      responseType: 'blob', params: { source_workstation: 'Laptop A' },
    })
  })

  it('maps saved cycle nested payloads to camelCase UI contracts', async () => {
    mockPost.mockResolvedValueOnce({ data: {
      cycle_id: 1, line_group: 'EAL', line_class: 'EAL',
      cycle_date: '2026-05-28', source_type: 'analysis',
      completeness_state: 'complete', acquisition_date_from: null, acquisition_date_to: null,
      source_lineage: ['a.xlsx'], wire_wear_data_version: 4,
      records: [{ line_group: 'EAL', line_class: 'EAL', cycle_date: '2026-05-28', tension_length: 'TL1', track: 'UP', from_m: 1, to_m: 4, interval_count: 2, intervals: [{ track: 'UP', from_m: 1, to_m: 2 }, { track: 'UP', from_m: 3, to_m: 4 }], avg_wear_min: 11, wear_percentage: 10, measurement_sd: null, has_data_conflict: false, conflict_ids: [], updated_at: null }],
      segments: [{ segment_name: 'U1', is_present: true, coverage_percentage: 100, diagnostic_gaps: [], source_file_names: ['a.xlsx'] }],
      conflict_decisions: [{ conflict_id: 'c1', measurement_identity: 'TL1', source_values: [['a.xlsx', 11]], selected_wear_min: 11, is_accepted: true, accepted_at: null }],
    } })

    const result = await saveWearCycle([new File(['a'], 'a.xlsx')], {
      lineGroup: 'EAL', cycleDate: '2026-05-28', expectedPreviewDigest: 'digest', expectedDataVersion: 3,
    })

    expect(result.records[0]).toMatchObject({ key: { lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-05-28', tensionLength: 'TL1' }, avgWearMin: 11, intervalCount: 2, intervals: [{ track: 'UP', fromM: 1, toM: 2 }, { track: 'UP', fromM: 3, toM: 4 }] })
    expect(result.segments[0]).toMatchObject({ segmentName: 'U1', sourceFileNames: ['a.xlsx'] })
    expect(result.conflictDecisions[0]).toMatchObject({ conflictId: 'c1', selectedWearMin: 11 })
    expect(result.records[0]).not.toHaveProperty('avg_wear_min')
  })

  it('maps workbench columns summaries and records without snake_case leakage', () => {
    const result = mapWireWearCycleWorkbench({
      line_group: 'EAL', line_class: 'LMC', wire_wear_data_version: 3,
      columns: [{ tension_length: 'TL1', track: 'UP', from_m: 1, to_m: 4, interval_count: 2, intervals: [{ track: 'UP', from_m: 1, to_m: 2 }, { track: 'UP', from_m: 3, to_m: 4 }] }],
      matrix_rows: [{ cycle_date: '2026-05-28', values: { TL1: 11 } }],
      latest_summary: [{ tension_length: 'TL1', latest_cycle_date: '2026-05-28', latest_avg_wear_min: 11, latest_wear_percentage: 10, historical_sd: null }],
      records: [{ line_group: 'EAL', line_class: 'LMC', cycle_date: '2026-05-28', tension_length: 'TL1', track: 'UP', from_m: 1, to_m: 4, interval_count: 2, physical_intervals: [{ track: 'UP', from_m: 1, to_m: 2 }, { track: 'UP', from_m: 3, to_m: 4 }], avg_wear_min: 11, wear_percentage: 10, measurement_sd: null, has_data_conflict: false, conflict_ids: [], updated_at: null }],
    })

    expect(result.columns[0]).toEqual({ tensionLength: 'TL1', track: 'UP', fromM: 1, toM: 4, intervalCount: 2, intervals: [{ track: 'UP', fromM: 1, toM: 2 }, { track: 'UP', fromM: 3, toM: 4 }] })
    expect(result.matrixRows[0]).toEqual({ cycleDate: '2026-05-28', values: { TL1: 11 } })
    expect(result.matrixRows[0]).not.toHaveProperty('cycle_date')
    expect(result.latestSummary[0]).toMatchObject({ tensionLength: 'TL1', latestCycleDate: '2026-05-28', latestAvgWearMin: 11 })
    expect(result.records[0]).toHaveProperty('avgWearMin', 11)
    expect(result).toMatchObject({ lineGroup: 'EAL', lineClass: 'LMC' })
    expect(result.records[0].key.lineClass).toBe('LMC')
    expect(result.records[0]).toMatchObject({ intervalCount: 2, intervals: [{ track: 'UP', fromM: 1, toM: 2 }, { track: 'UP', fromM: 3, toM: 4 }] })
  })
})

describe('Wire Wear candidate preview contract', () => {
  beforeEach(() => vi.clearAllMocks())

  it('maps batch rows and candidate results at the API boundary', async () => {
    mockPost.mockResolvedValueOnce({ data: {
      line_group: 'EAL', line_class: 'LMC', cycle_date: '2026-02-01',
      wire_wear_data_version: 7,
      counts: { new: 0, update: 1, no_change: 0, duplicate: 0, error: 0 },
      candidates: [{
        status: 'update',
        key: { line_group: 'EAL', line_class: 'LMC', cycle_date: '2026-02-01', tension_length: 'H46' },
        avg_wear_min: 12.1, track: 'UP', existing_avg_wear_min: 12.4,
        expected_updated_at: '2026-08-07T01:02:03Z', source_type: 'manual',
        source_sheet: null, source_row: 1, source_cell: 'B1', original_value: 12.1,
        excluded: false, row_id: 'row-1', issues: [],
      }],
    } })

    const result = await previewWearRecordCandidates({
      lineClass: 'LMC', cycleDate: '2026-02-01',
      rows: [{ rowId: 'row-1', tensionLength: 'H46', avgWearMin: 12.1 }],
    })

    expect(mockPost).toHaveBeenCalledWith('/calculation/wear-records/candidates/preview', {
      line_class: 'LMC', cycle_date: '2026-02-01',
      rows: [{
        row_id: 'row-1', tension_length: 'H46', avg_wear_min: 12.1,
        tension_length_cell: undefined, avg_wear_min_cell: undefined, excluded: false,
      }],
    })
    expect(result.candidates[0]).toMatchObject({
      status: 'update',
      key: { lineGroup: 'EAL', lineClass: 'LMC', cycleDate: '2026-02-01', tensionLength: 'H46' },
      avgWearMin: 12.1, track: 'UP', existingAvgWearMin: 12.4,
      expectedUpdatedAt: '2026-08-07T01:02:03Z',
    })
  })
})

describe('historical wire wear workbook API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('discovers sheets and maps a deterministic multipart preview', async () => {
    const file = new File(['xlsx'], 'history.xlsx')
    mockPost
      .mockResolvedValueOnce({ data: { sheets: [
        { sheet_name: 'EAL', support: 'supported', selected_by_default: true, enabled: true, reason_code: 'supported' },
        { sheet_name: 'LRL', support: 'reserved', selected_by_default: false, enabled: false, reason_code: 'future_support' },
      ] } })
      .mockResolvedValueOnce({ data: {
        sheets: [{ sheet_name: 'EAL', support: 'supported', selected_by_default: true, enabled: true, reason_code: 'supported' }],
        selected_sheets: ['EAL'],
        wire_wear_data_version: 3,
        sheet_summaries: [{ sheet_name: 'EAL', skipped: 2, new: 1, update: 0, no_change: 0, duplicate: 0, error: 0, total: 1 }],
        totals: { skipped: 2, new: 1, update: 0, no_change: 0, duplicate: 0, error: 0, total: 1 },
        candidates: [{
          status: 'new',
          key: { line_group: 'EAL', line_class: 'EAL', cycle_date: '2024-01-01', tension_length: '28' },
          avg_wear_min: 11.2,
          track: 'UP',
          existing_avg_wear_min: null,
          expected_updated_at: null,
          source_type: 'workbook',
          source_sheet: 'EAL',
          source_row: 2,
          source_cell: 'C2',
          original_value: 11.2,
          excluded: false,
          row_id: 'EAL:C2',
          issues: [],
        }],
        diagnostics: [],
      } })

    const discovery = await discoverHistoricalWearWorkbook(file)
    const preview = await previewHistoricalWearWorkbook(file, ['EAL'])

    expect(discovery.sheets[1]).toMatchObject({ name: 'LRL', support: 'reserved', enabled: false })
    expect(preview.sheetSummaries[0]).toMatchObject({ sheetName: 'EAL', noChange: 0, skipped: 2 })
    expect(preview.candidates[0].key).toEqual({
      lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2024-01-01', tensionLength: '28',
    })
    const [, previewForm] = mockPost.mock.calls[1]
    expect((previewForm as FormData).get('file')).toBe(file)
    expect((previewForm as FormData).get('selected_sheets')).toBe('["EAL"]')
  })
})
