import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, expect, it } from 'vitest';

import StaggerAlgorithmDialog from '../StaggerAlgorithmDialog';

describe('StaggerAlgorithmDialog', () => {
  it('shows the staged explanation structure for the stagger algorithm', () => {
    render(<StaggerAlgorithmDialog open onClose={() => {}} />);

    expect(screen.getByText(/Step 1 \/ 步驟一/i)).toBeInTheDocument();
    expect(screen.getByText(/Step 4 \/ 步驟四/i)).toBeInTheDocument();
    expect(screen.getByText(/流程概覽 Process Overview/i)).toBeInTheDocument();
    expect(screen.getByText(/公式摘要 Formula Summary/i)).toBeInTheDocument();
    expect(screen.getByText(/關鍵詞彙 Key Terms/i)).toBeInTheDocument();
    expect(screen.getByText(/判定規則 Decision Rules/i)).toBeInTheDocument();
    expect(screen.getAllByText(/K_eq/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Allowable/i).length).toBeGreaterThan(0);
  });

  it('renders the bundled algorithm visual asset', () => {
    render(<StaggerAlgorithmDialog open onClose={() => {}} />);

    expect(screen.getByAltText(/Stagger calculation algorithm/i)).toBeInTheDocument();
  });
});
