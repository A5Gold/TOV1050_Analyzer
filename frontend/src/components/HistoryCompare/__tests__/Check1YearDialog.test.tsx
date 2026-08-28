/**
 * Check1YearDialog Test Suite
 * Feature-001: History Compare Integration - Check 1 Year Record Dialog
 * 
 * Tests for the Check1YearDialog component that allows users to configure
 * query scope and filters before checking repeated exception records
 * against the database for records within the past year.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Check1YearDialog from '../Check1YearDialog';

describe('Check1YearDialog', () => {
  const mockOnClose = vi.fn();
  const mockOnCheck = vi.fn();
  
  const defaultProps = {
    open: true,
    onClose: mockOnClose,
    onCheck: mockOnCheck,
    recordCount: 10,
    detectedLine: 'EAL',
    detectedSection: 'Mainline',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render dialog when open is true', () => {
      render(<Check1YearDialog {...defaultProps} />);
      
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Check 1 Year Record')).toBeInTheDocument();
    });

    it('should not render dialog when open is false', () => {
      render(<Check1YearDialog {...defaultProps} open={false} />);
      
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('should display record count', () => {
      render(<Check1YearDialog {...defaultProps} recordCount={15} />);
      
      const alert = screen.getByRole('alert');
      expect(alert).toHaveTextContent('15');
      expect(alert).toHaveTextContent('records');
    });

    it('should display query scope selector', () => {
      render(<Check1YearDialog {...defaultProps} />);
      
      expect(screen.getByText(/Query Scope/i)).toBeInTheDocument();
    });
  });

  describe('Query Scope Selection', () => {
    it('should default to "All Records" scope', () => {
      render(<Check1YearDialog {...defaultProps} />);
      
      expect(screen.getByLabelText(/All Records/i)).toBeChecked();
    });

    it('should allow switching to "Specific Filters" scope', async () => {
      const user = userEvent.setup();
      render(<Check1YearDialog {...defaultProps} />);
      
      const specificRadio = screen.getByLabelText(/Specific Filters/i);
      await user.click(specificRadio);
      
      expect(specificRadio).toBeChecked();
    });

    it('should show filter options when "Specific Filters" is selected', async () => {
      const user = userEvent.setup();
      render(<Check1YearDialog {...defaultProps} />);
      
      // Switch to specific filters
      await user.click(screen.getByLabelText(/Specific Filters/i));
      
      // Filter options should now be visible
      expect(screen.getByRole('combobox', { name: /Line/i })).toBeInTheDocument();
      expect(screen.getByRole('combobox', { name: /Section/i })).toBeInTheDocument();
      // DatePicker renders multiple elements with label, use getAllBy
      expect(screen.getAllByLabelText(/Date From/i).length).toBeGreaterThan(0);
      expect(screen.getAllByLabelText(/Date To/i).length).toBeGreaterThan(0);
    });

    it('should hide filter options when "All Records" is selected', () => {
      render(<Check1YearDialog {...defaultProps} />);
      
      // Default is "All Records", filter options should be hidden
      expect(screen.queryByRole('combobox', { name: /^Line$/i })).not.toBeInTheDocument();
    });
  });

  describe('Filter Options', () => {
    it('should auto-populate line filter from detected line', async () => {
      const user = userEvent.setup();
      render(<Check1YearDialog {...defaultProps} detectedLine="EAL" />);
      
      await user.click(screen.getByLabelText(/Specific Filters/i));
      
      // Use more specific selector - the select's role and label
      const lineSelect = screen.getByRole('combobox', { name: /Line/i });
      expect(lineSelect).toHaveTextContent('EAL');
    });

    it('should auto-populate section filter from detected section', async () => {
      const user = userEvent.setup();
      render(<Check1YearDialog {...defaultProps} detectedSection="RAC" />);
      
      await user.click(screen.getByLabelText(/Specific Filters/i));
      
      const sectionSelect = screen.getByRole('combobox', { name: /Section/i });
      expect(sectionSelect).toHaveTextContent('RAC');
    });

    it('should allow changing line filter', async () => {
      const user = userEvent.setup();
      render(<Check1YearDialog {...defaultProps} detectedLine="EAL" />);
      
      await user.click(screen.getByLabelText(/Specific Filters/i));
      
      const lineSelect = screen.getByRole('combobox', { name: /Line/i });
      await user.click(lineSelect);
      await user.click(screen.getByRole('option', { name: 'TML' }));
      
      expect(lineSelect).toHaveTextContent('TML');
    });

    it('should reset section to Mainline when changing line from EAL to TML', async () => {
      const user = userEvent.setup();
      render(<Check1YearDialog {...defaultProps} detectedLine="EAL" detectedSection="RAC" />);
      
      await user.click(screen.getByLabelText(/Specific Filters/i));
      
      const lineSelect = screen.getByRole('combobox', { name: /Line/i });
      await user.click(lineSelect);
      await user.click(screen.getByRole('option', { name: 'TML' }));
      
      // Section should reset to Mainline (TML only supports Mainline)
      const sectionSelect = screen.getByRole('combobox', { name: /Section/i });
      expect(sectionSelect).toHaveTextContent('Mainline');
    });
  });

  describe('Actions', () => {
    it('should call onClose when Cancel button is clicked', async () => {
      const user = userEvent.setup();
      render(<Check1YearDialog {...defaultProps} />);
      
      await user.click(screen.getByRole('button', { name: /Cancel/i }));
      
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('should call onCheck with "all" scope when All Records is selected', async () => {
      const user = userEvent.setup();
      render(<Check1YearDialog {...defaultProps} />);
      
      await user.click(screen.getByRole('button', { name: /Check/i }));
      
      expect(mockOnCheck).toHaveBeenCalledWith({
        scope: 'all',
        filters: undefined,
      });
    });

    it('should call onCheck with filters when Specific Filters is selected', async () => {
      const user = userEvent.setup();
      render(<Check1YearDialog {...defaultProps} detectedLine="EAL" detectedSection="Mainline" />);
      
      // Switch to specific filters
      await user.click(screen.getByLabelText(/Specific Filters/i));
      
      await user.click(screen.getByRole('button', { name: /Check/i }));
      
      expect(mockOnCheck).toHaveBeenCalledWith({
        scope: 'specific',
        filters: expect.objectContaining({
          line: 'EAL',
          section: 'Mainline',
        }),
      });
    });

    it('should disable Check button when isChecking is true', () => {
      render(<Check1YearDialog {...defaultProps} isChecking={true} />);
      
      expect(screen.getByRole('button', { name: /Checking/i })).toBeDisabled();
    });
  });

  describe('Validation', () => {
    it('should show warning when record count is 0', () => {
      render(<Check1YearDialog {...defaultProps} recordCount={0} />);
      
      expect(screen.getByText(/No records to check/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Check/i })).toBeDisabled();
    });
  });
});
