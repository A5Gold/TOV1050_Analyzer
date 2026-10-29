import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import ExceptionTable from '../ExceptionTable';
import type { AnalysisResponse } from '../../types/api';

afterEach(cleanup);

describe('ExceptionTable enrichment data states', () => {
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
