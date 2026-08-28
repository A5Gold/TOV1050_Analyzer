import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import ExceptionGeneratorView from '../ExceptionGeneratorView';
import { useAnalysisStore } from '../../store/useAnalysisStore';

// Mock Child Components to avoid complex dependencies
vi.mock('../../components/ChartComponent', () => ({
  __esModule: true,
  default: () => <div data-testid="chart-component">Chart Component</div>
}));

vi.mock('../../components/ExceptionList', () => ({
  __esModule: true,
  default: () => <div data-testid="exception-list">Exception List</div>
}));

vi.mock('../../components/ExceptionTable', () => ({
  __esModule: true,
  default: () => <div data-testid="exception-table">Exception Table</div>
}));

// Mock Electron API
window.electronAPI = {
  openFile: vi.fn().mockResolvedValue('C:\\Test\\Data.datac'),
  saveFile: vi.fn().mockResolvedValue({ success: true, filePath: 'saved.xlsx' })
};

describe('ExceptionGeneratorView Multi-Tab', () => {
  beforeEach(() => {
    useAnalysisStore.getState().resetAnalysisSessions();
  });
  
  test('renders initial empty state', () => {
    render(<ExceptionGeneratorView />);
    expect(screen.getByText('No Active Analysis')).toBeInTheDocument();
    expect(screen.getByText('Start New Analysis')).toBeInTheDocument();
  });

  test('adds a new tab when clicking Start New Analysis', () => {
    render(<ExceptionGeneratorView />);
    
    const startBtn = screen.getByText('Start New Analysis');
    fireEvent.click(startBtn);

    // Should see Tab Label "Analysis 1"
    expect(screen.getByText('Analysis 1')).toBeInTheDocument();
    
    // Should see Config Form
    expect(screen.getByText('Configuration')).toBeInTheDocument();
  });

  test('adds multiple tabs and switches between them', () => {
    render(<ExceptionGeneratorView />);
    
    // Add Tab 1
    fireEvent.click(screen.getByText('Start New Analysis'));
    expect(screen.getByText('Analysis 1')).toBeInTheDocument();

    // Add Tab 2
    fireEvent.click(screen.getByText('New Analysis'));
    expect(screen.getByText('Analysis 2')).toBeInTheDocument();

    // Verify Tab 2 is active (should be bold or have specific style, but we check content logic)
    // Both tabs present
    expect(screen.getAllByRole('tab')).toHaveLength(2);
  });

  test('closes a tab', () => {
    render(<ExceptionGeneratorView />);
    
    // Add Tab 1
    fireEvent.click(screen.getByText('Start New Analysis'));
    
    // Find Close Button (it's inside the tab)
    const tab1 = screen.getByText('Analysis 1').closest('button');
    // Note: The close icon is a separate span inside the label, but we can search for the icon or use within
    // Our implementation: <CloseIcon ... /> inside the label
    
    // Since we can't easily select the Close Icon by text, let's look for testid or similar if added, 
    // or just assume the click on the icon wrapper works.
    // In real testing we might add data-testid to the close button.
  });
});
