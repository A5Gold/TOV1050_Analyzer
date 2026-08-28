import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { WearCandidatePreview } from '../../../types/api';
import BatchAddRecordsDialog from '../BatchAddRecordsDialog';

const rows = [{ rowId: 'row-1', tensionLength: 'TL1', avgWearMin: '11.2' }];

const preview = (overrides: Partial<WearCandidatePreview> = {}): WearCandidatePreview => ({
  lineGroup: 'EAL',
  lineClass: 'EAL',
  cycleDate: '2026-08-01',
  wireWearDataVersion: 7,
  counts: { new: 1, update: 0, no_change: 0, duplicate: 0, error: 0 },
  candidates: [{
    status: 'new',
    key: { lineGroup: 'EAL', lineClass: 'EAL', cycleDate: '2026-08-01', tensionLength: 'TL1' },
    avgWearMin: 11.2,
    track: 'UP',
    existingAvgWearMin: null,
    expectedUpdatedAt: null,
    sourceType: 'manual',
    sourceSheet: null,
    sourceRow: 1,
    sourceCell: 'B1',
    originalValue: 11.2,
    excluded: false,
    rowId: 'row-1',
    issues: [],
  }],
  ...overrides,
});

const baseProps = () => ({
  open: true,
  lineClass: 'EAL' as const,
  cycleDate: '2026-08-01',
  rows,
  preview: preview(),
  onLineClassChange: vi.fn(),
  onCycleDateChange: vi.fn(),
  onCellChange: vi.fn(),
  onInsertRow: vi.fn(),
  onDeleteRow: vi.fn(),
  onPasteRows: vi.fn(),
  onStageAll: vi.fn(),
  onClose: vi.fn(),
});

const setViewportMatch = (matches: boolean) => {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation(() => ({
      matches,
      media: '(max-width:599.95px)',
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
};

describe('BatchAddRecordsDialog', () => {
  afterEach(() => vi.restoreAllMocks());

  it('renders the controlled shared context and footer count mapping', async () => {
    setViewportMatch(false);
    const props = baseProps();
    props.preview = preview({ counts: { new: 3, update: 2, no_change: 4, duplicate: 1, error: 0 } });
    const user = userEvent.setup();
    render(<BatchAddRecordsDialog {...props} />);

    const dialog = screen.getByRole('dialog', { name: /Add Wire Wear Records/ });
    expect(within(dialog).getByLabelText('Line')).toHaveTextContent('EAL');
    expect(within(dialog).getByLabelText('Cycle Date')).toHaveValue('2026-08-01');
    expect(within(dialog).getByRole('status')).toHaveTextContent('Valid 3');
    expect(within(dialog).getByRole('status')).toHaveTextContent('Update 2');
    expect(within(dialog).getByRole('status')).toHaveTextContent('Duplicate 1');
    expect(within(dialog).getByRole('status')).toHaveTextContent('Error 0');

    await user.click(within(dialog).getByRole('button', { name: 'Stage All (5)' }));
    expect(props.onStageAll).toHaveBeenCalledWith(props.preview);
  });

  it('disables Stage All for a non-excluded error and shows the exact cell message', () => {
    setViewportMatch(false);
    const props = baseProps();
    props.preview = preview({
      counts: { new: 1, update: 0, no_change: 0, duplicate: 0, error: 1 },
      candidates: [{
        ...preview().candidates[0],
        status: 'error',
        key: null,
        avgWearMin: null,
        originalValue: 'bad',
        issues: [{ code: 'invalid_number', message: 'Enter a finite wear value.', field: 'avg_wear_min', cell: 'B1' }],
      }],
    });
    render(<BatchAddRecordsDialog {...props} />);

    expect(screen.getByRole('button', { name: 'Stage All (1)' })).toBeDisabled();
    expect(screen.getByLabelText('Row 1 Avg Wear Min')).toHaveAccessibleDescription('Enter a finite wear value.');
  });

  it('allows excluded errors but never stages No Change rows', () => {
    setViewportMatch(false);
    const props = baseProps();
    props.preview = preview({
      counts: { new: 1, update: 0, no_change: 1, duplicate: 0, error: 1 },
      candidates: [
        preview().candidates[0],
        { ...preview().candidates[0], status: 'no_change', rowId: 'row-2' },
        { ...preview().candidates[0], status: 'error', key: null, rowId: 'row-3', excluded: true },
      ],
    });
    render(<BatchAddRecordsDialog {...props} />);

    expect(screen.getByRole('button', { name: 'Stage All (1)' })).toBeEnabled();
  });

  it('prevents duplicate actions while validating or staging', () => {
    setViewportMatch(false);
    const previewingProps = baseProps();
    const { rerender } = render(<BatchAddRecordsDialog {...previewingProps} isPreviewing />);
    expect(screen.getByRole('progressbar', { name: 'Validating records' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Stage All (1)' })).toBeDisabled();
    expect(screen.getByLabelText('Row 1 Tension Length')).toBeDisabled();

    const submittingProps = baseProps();
    rerender(<BatchAddRecordsDialog {...submittingProps} isSubmitting />);
    expect(screen.getByRole('button', { name: 'Staging...' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Close Add Wire Wear Records' })).toBeDisabled();
  });

  it('uses a full-screen dialog on a narrow viewport', () => {
    setViewportMatch(true);
    render(<BatchAddRecordsDialog {...baseProps()} />);
    expect(screen.getByRole('dialog', { name: /Add Wire Wear Records/ })).toHaveClass('MuiDialog-paperFullScreen');
  });

  it('keeps Stage All disabled for an empty or informational-only preview', () => {
    setViewportMatch(false);
    const props = baseProps();
    props.rows = [];
    props.preview = preview({
      counts: { new: 0, update: 0, no_change: 1, duplicate: 0, error: 0 },
      candidates: [{ ...preview().candidates[0], status: 'no_change' }],
    });
    render(<BatchAddRecordsDialog {...props} />);
    expect(screen.getByText('No rows. Add a row to begin.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Stage All (0)' })).toBeDisabled();
  });
});
