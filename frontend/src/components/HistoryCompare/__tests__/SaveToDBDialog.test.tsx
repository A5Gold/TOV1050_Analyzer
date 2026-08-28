/**
 * SaveToDBDialog Test Suite
 * Feature-001: History Compare Integration - Save to DB Dialog
 * 
 * Tests for the SaveToDBDialog component that allows users to select
 * Sub Tab (EAL/TML) and Sub Table (Mainline, RAC, LOW S1, LMC) before
 * saving repeated exception records to the database.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SaveToDBDialog from '../SaveToDBDialog';

describe('SaveToDBDialog', () => {
  const mockOnClose = vi.fn();
  const mockOnSave = vi.fn();
  
  const defaultProps = {
    open: true,
    onClose: mockOnClose,
    onSave: mockOnSave,
    recordCount: 10,
    detectedLine: 'EAL',
    detectedSection: 'Mainline',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render dialog when open is true', () => {
      render(<SaveToDBDialog {...defaultProps} />);
      
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Save to Database')).toBeInTheDocument();
    });

    it('should not render dialog when open is false', () => {
      render(<SaveToDBDialog {...defaultProps} open={false} />);
      
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('should display record count', () => {
      render(<SaveToDBDialog {...defaultProps} recordCount={25} />);
      
      // Text is split by multiple elements (<strong>25</strong> records...)
      // Use getByRole('alert') and check textContent
      const alert = screen.getByRole('alert');
      expect(alert).toHaveTextContent('25');
      expect(alert).toHaveTextContent('records');
    });

    it('should display Sub Tab selector with EAL and TML options', () => {
      render(<SaveToDBDialog {...defaultProps} />);
      
      expect(screen.getByLabelText(/Line \(Sub Tab\)/i)).toBeInTheDocument();
      expect(screen.getByText('EAL')).toBeInTheDocument();
    });

    it('should display Sub Table selector with section options', () => {
      render(<SaveToDBDialog {...defaultProps} />);
      
      expect(screen.getByLabelText(/Section \(Sub Table\)/i)).toBeInTheDocument();
    });
  });

  describe('Auto-detection', () => {
    it('should auto-select EAL when detectedLine is EAL', () => {
      render(<SaveToDBDialog {...defaultProps} detectedLine="EAL" />);
      
      const lineSelect = screen.getByLabelText(/Line \(Sub Tab\)/i);
      expect(lineSelect).toHaveTextContent('EAL');
    });

    it('should auto-select TML when detectedLine is TML', () => {
      render(<SaveToDBDialog {...defaultProps} detectedLine="TML" />);
      
      const lineSelect = screen.getByLabelText(/Line \(Sub Tab\)/i);
      expect(lineSelect).toHaveTextContent('TML');
    });

    it('should auto-select Mainline when detectedSection is Mainline', () => {
      render(<SaveToDBDialog {...defaultProps} detectedSection="Mainline" />);
      
      const sectionSelect = screen.getByLabelText(/Section \(Sub Table\)/i);
      expect(sectionSelect).toHaveTextContent('Mainline');
    });

    it('should auto-select RAC when detectedSection is RAC', () => {
      render(<SaveToDBDialog {...defaultProps} detectedSection="RAC" />);
      
      const sectionSelect = screen.getByLabelText(/Section \(Sub Table\)/i);
      expect(sectionSelect).toHaveTextContent('RAC');
    });
  });

  describe('User Override', () => {
    it('should allow user to change Sub Tab from EAL to TML', async () => {
      const user = userEvent.setup();
      render(<SaveToDBDialog {...defaultProps} detectedLine="EAL" />);
      
      const lineSelect = screen.getByLabelText(/Line \(Sub Tab\)/i);
      await user.click(lineSelect);
      await user.click(screen.getByRole('option', { name: 'TML' }));
      
      expect(lineSelect).toHaveTextContent('TML');
    });

    it('should allow user to change Sub Table from Mainline to RAC', async () => {
      const user = userEvent.setup();
      render(<SaveToDBDialog {...defaultProps} detectedSection="Mainline" />);
      
      const sectionSelect = screen.getByLabelText(/Section \(Sub Table\)/i);
      await user.click(sectionSelect);
      await user.click(screen.getByRole('option', { name: 'RAC' }));
      
      expect(sectionSelect).toHaveTextContent('RAC');
    });

    it('should show only Mainline option for TML line', async () => {
      const user = userEvent.setup();
      render(<SaveToDBDialog {...defaultProps} detectedLine="TML" />);
      
      const sectionSelect = screen.getByLabelText(/Section \(Sub Table\)/i);
      await user.click(sectionSelect);
      
      // TML only has Mainline, not RAC/LOW/LMC
      expect(screen.getByRole('option', { name: 'Mainline' })).toBeInTheDocument();
      expect(screen.queryByRole('option', { name: 'RAC' })).not.toBeInTheDocument();
      expect(screen.queryByRole('option', { name: 'LOW S1' })).not.toBeInTheDocument();
      expect(screen.queryByRole('option', { name: 'LMC' })).not.toBeInTheDocument();
    });

    it('should show all section options for EAL line', async () => {
      const user = userEvent.setup();
      render(<SaveToDBDialog {...defaultProps} detectedLine="EAL" />);
      
      const sectionSelect = screen.getByLabelText(/Section \(Sub Table\)/i);
      await user.click(sectionSelect);
      
      expect(screen.getByRole('option', { name: 'Mainline' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'RAC' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'LOW S1' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'LMC' })).toBeInTheDocument();
    });
  });

  describe('Actions', () => {
    it('should call onClose when Cancel button is clicked', async () => {
      const user = userEvent.setup();
      render(<SaveToDBDialog {...defaultProps} />);
      
      await user.click(screen.getByRole('button', { name: /Cancel/i }));
      
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('should call onSave with selected values when Save button is clicked', async () => {
      const user = userEvent.setup();
      render(<SaveToDBDialog {...defaultProps} detectedLine="EAL" detectedSection="Mainline" />);
      
      await user.click(screen.getByRole('button', { name: /Save/i }));
      
      expect(mockOnSave).toHaveBeenCalledWith({
        line: 'EAL',
        section: 'Mainline',
      });
    });

    it('should call onSave with user-modified values', async () => {
      const user = userEvent.setup();
      render(<SaveToDBDialog {...defaultProps} detectedLine="EAL" detectedSection="Mainline" />);
      
      // Change to TML and Mainline (TML only has Mainline)
      const lineSelect = screen.getByLabelText(/Line \(Sub Tab\)/i);
      await user.click(lineSelect);
      await user.click(screen.getByRole('option', { name: 'TML' }));
      
      await user.click(screen.getByRole('button', { name: /Save/i }));
      
      expect(mockOnSave).toHaveBeenCalledWith({
        line: 'TML',
        section: 'Mainline',
      });
    });

    it('should disable Save button when isSaving is true', () => {
      render(<SaveToDBDialog {...defaultProps} isSaving={true} />);
      
      expect(screen.getByRole('button', { name: /Saving/i })).toBeDisabled();
    });
  });

  describe('Validation', () => {
    it('should show warning when record count is 0', () => {
      render(<SaveToDBDialog {...defaultProps} recordCount={0} />);
      
      expect(screen.getByText(/No records to save/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Save/i })).toBeDisabled();
    });

    it('should reset section to Mainline when changing from EAL to TML', async () => {
      const user = userEvent.setup();
      render(<SaveToDBDialog {...defaultProps} detectedLine="EAL" detectedSection="RAC" />);
      
      // Start with RAC selected
      expect(screen.getByLabelText(/Section \(Sub Table\)/i)).toHaveTextContent('RAC');
      
      // Change to TML
      const lineSelect = screen.getByLabelText(/Line \(Sub Tab\)/i);
      await user.click(lineSelect);
      await user.click(screen.getByRole('option', { name: 'TML' }));
      
      // Section should be reset to Mainline (TML only supports Mainline)
      expect(screen.getByLabelText(/Section \(Sub Table\)/i)).toHaveTextContent('Mainline');
    });
  });
});
