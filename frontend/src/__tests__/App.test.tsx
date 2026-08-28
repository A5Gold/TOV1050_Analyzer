import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

import App from '../App';

vi.mock('../components/Layout/MainLayout', () => ({
  __esModule: true,
  default: ({ children, activeView, onViewChange }: { children: React.ReactNode; activeView: string; onViewChange: (view: string) => void }) => (
    <div data-testid="main-layout" data-active-view={activeView}>
      <button type="button" onClick={() => onViewChange('version-difference')}>Open Version Difference</button>
      {children}
    </div>
  ),
}));

vi.mock('../views/ExceptionGeneratorView', () => ({
  __esModule: true,
  default: () => <div>Exception Generator View</div>,
}));

vi.mock('../views/HistoryCompareView', () => ({
  __esModule: true,
  default: () => <div>History Compare View</div>,
}));

vi.mock('../views/DatabaseRecordView', () => ({
  __esModule: true,
  default: () => <div>Database Record View</div>,
}));

vi.mock('../views/MetadataEditorView', () => ({
  __esModule: true,
  default: () => <div>Metadata Editor View</div>,
}));

vi.mock('../views/WearCalculatorView', () => ({
  __esModule: true,
  default: () => <div>Wear Calculator View</div>,
}));

vi.mock('../views/TrendAnalyzerView', () => ({
  __esModule: true,
  default: () => <div>Trend Analyzer View</div>,
}));

vi.mock('../views/CalculationView', () => ({
  __esModule: true,
  default: () => <div>Calculation View</div>,
}));

vi.mock('../views/AboutView', () => ({
  __esModule: true,
  default: () => <div>About Visual Guide View</div>,
}));

vi.mock('../views/VersionDifferenceView', () => ({
  __esModule: true,
  default: () => <div>Version Difference View</div>,
}));

describe('App', () => {
  it('shows the About module by default on startup', () => {
    render(<App />);

    expect(screen.getByText('About Visual Guide View')).toBeInTheDocument();
    expect(screen.getByTestId('main-layout')).toHaveAttribute('data-active-view', 'about');
  });

  it('opens the independent Version Difference module', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: 'Open Version Difference' }));

    expect(screen.getByText('Version Difference View')).toBeInTheDocument();
    expect(screen.getByTestId('main-layout')).toHaveAttribute('data-active-view', 'version-difference');
  });
});
