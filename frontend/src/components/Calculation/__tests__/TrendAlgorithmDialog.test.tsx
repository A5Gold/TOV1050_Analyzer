import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import TrendAlgorithmDialog from '../TrendAlgorithmDialog';

describe('TrendAlgorithmDialog', () => {
  it('shows current trend filtering and chart display rules', () => {
    render(<TrendAlgorithmDialog open onClose={() => {}} />);

    expect(screen.getByText('Trend Analysis Logic')).toBeInTheDocument();
    expect(screen.getAllByText(/Case A/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Case B/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/x-axis/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/只保留實際有資料的日期/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/T3/i)).toBeInTheDocument();
    expect(screen.getByAltText('Trend analysis algorithm flow')).toBeInTheDocument();
  });
});
