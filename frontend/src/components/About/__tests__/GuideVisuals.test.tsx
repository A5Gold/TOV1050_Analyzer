import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, expect, it } from 'vitest';

import {
  CoverageExample,
  StagedChangesVisual,
  StaggerSpanVisual,
  ThresholdRangeChart,
  WearResolutionVisual,
} from '../GuideVisuals';

describe('About GuideVisuals', () => {
  it('為關鍵圖解提供可讀表格及狀態文字', () => {
    render(
      <>
        <ThresholdRangeChart />
        <WearResolutionVisual />
        <CoverageExample />
        <StagedChangesVisual />
        <StaggerSpanVisual />
      </>,
    );

    expect(screen.getByRole('table', { name: 'Wear 狀態門檻表' })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Wear 張力段分類表' })).toBeInTheDocument();
    expect(screen.getByText('MAINLINE')).toBeInTheDocument();
    expect(screen.getByText('SIDING')).toBeInTheDocument();
    expect(screen.getByText('UNKNOWN')).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'MAINLINE-only coverage 示例表' })).toBeInTheDocument();
    expect(screen.getByText(/2 \/ 3 = 66\.7%/)).toBeInTheDocument();
    expect(screen.getByText('待新增')).toBeInTheDocument();
    expect(screen.getByText('待更新')).toBeInTheDocument();
    expect(screen.getByText('待刪除')).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Stagger span 判斷表' })).toBeInTheDocument();
  });
});
