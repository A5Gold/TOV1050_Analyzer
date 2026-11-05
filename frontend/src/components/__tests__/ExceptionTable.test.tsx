import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import ExceptionTable from '../ExceptionTable';
import type { AnalysisResponse } from '../../types/api';

afterEach(cleanup);

describe('ExceptionTable enrichment data states', () => {
  it('shows position-specific gaps and review evidence without filling a candidate into formal columns', () => {
    const response = {
      status: 'success', params: {}, chart_data: {}, boundaries: [],
      metadata_capabilities: { capabilities: {}, boundary_review: [{
        tension_length: 'CR289', observed_from_m: 99731, observed_to_m: 99991, point_count: 31,
        status: 'unresolved_pairing', gaps: ['no_contact_boundaries'], known_boundaries: [], candidate: null,
        source_rows: [{ sheet: 'ISL UT', excel_row: 699, source_sheet: 'ISL UT', source_excel_row: 2 }],
      }] },
      exceptions: { 'Low Height': [{ id: 'evidence', 'exception type': 'Low Height',
        FromM: 99740, ToM: 99750, maxLocation: 99745, level: 'L1',
        Overlap: null, 'Tension Length': null, Landmark: null,
        metadata_enrichment: JSON.stringify({ tl_status: 'no_approved_interval', overlap_status: 'unresolved_pairing', landmark_status: 'outside_coverage' }),
      }] },
    } as unknown as AnalysisResponse;
    render(<ExceptionTable result={response} />);
    const row = screen.getByText('evidence').closest('tr')!;
    expect(within(row).getByText('邊界配對或完整性待確認')).toBeInTheDocument();
    expect(within(row).queryByText('CR289')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '查看 evidence 的邊界依據' }));
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText(/CR289：31 個觀察點/)).toBeInTheDocument();
    expect(within(dialog).getByText('缺口：缺少明確 Contact 終端')).toBeInTheDocument();
    expect(within(dialog).getByText(/ISL UT 第 699 列/)).toBeInTheDocument();
  }, 15000);
  it('keeps all enrichment columns, distinguishes unavailable data from known non-overlap, and preserves actual values', () => {
    const response = {
      status: 'success', params: {}, chart_data: {}, boundaries: [],
      metadata_capabilities: { capabilities: {
        overlap_intervals: { status: 'unavailable', reason: 'No approved physical interval source' },
        tension_length_intervals: { status: 'unavailable', reason: 'No approved TL scope' },
        landmark_intervals: { status: 'available', reason: '' },
      } },
      exceptions: { 'Low Height': [
        { id: 'missing', 'exception type': 'Low Height', maxLocation: 100, level: 'L1', Overlap: null, 'Tension Length': '', Landmark: null },
        { id: 'known', 'exception type': 'Low Height', maxLocation: 200, level: 'L2', Overlap: 'N', 'Tension Length': 'TL-23', Landmark: 'Station' },
      ] },
    } as unknown as AnalysisResponse;
    render(<ExceptionTable result={response} />);
    const headers = screen.getAllByRole('columnheader').map(header => header.textContent);
    expect(headers).toEqual(expect.arrayContaining(['Overlap', 'Tension Length', 'Landmark']));
    const missingRow = screen.getByText('missing').closest('tr')!;
    expect(within(missingRow).getAllByText('未有核准資料')).toHaveLength(2);
    expect(within(missingRow).getByText('未提供資料')).toBeInTheDocument();
    expect(within(missingRow).queryByText('N')).not.toBeInTheDocument();
    const knownRow = screen.getByText('known').closest('tr')!;
    expect(within(knownRow).getByText('N')).toBeInTheDocument();
    expect(within(knownRow).getByText('TL-23')).toBeInTheDocument();
    expect(within(knownRow).getByText('Station')).toBeInTheDocument();
  }, 15000);
});
