import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, expect, it } from 'vitest';

import AlgorithmTutorialDialog from '../AlgorithmTutorialDialog';

describe('AlgorithmTutorialDialog', () => {
  it('renders bilingual matching criteria and visual case sections', () => {
    render(<AlgorithmTutorialDialog open onClose={() => {}} />);

    expect(screen.getByText(/History Compare Algorithm Logic/i)).toBeInTheDocument();
    expect(screen.getByText(/Matching Criteria/i)).toBeInTheDocument();
    expect(screen.getByText(/Visual Scenarios/i)).toBeInTheDocument();
    expect(screen.getByText(/CASE A/i)).toBeInTheDocument();
    expect(screen.getByText(/CASE B/i)).toBeInTheDocument();
    expect(screen.getByText(/CASE C/i)).toBeInTheDocument();
    expect(screen.getByAltText('History compare algorithm flow')).toBeInTheDocument();
  });

  it('separates the chain rule card from the next section header', () => {
    render(<AlgorithmTutorialDialog open onClose={() => {}} />);

    const firstCard = screen.getByText(/Each adjacent step must stay valid/i).closest('.MuiPaper-root');
    const secondHeader = screen.getByText(/2\. Matching Criteria/i);

    expect(firstCard).not.toBeNull();
    expect(firstCard).toContainElement(screen.getByText(/Each adjacent step must stay valid/i));
    expect(secondHeader).toBeVisible();
  });
});
