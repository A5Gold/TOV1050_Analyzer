import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import WearCycleStatusPanel from '../WearCycleStatusPanel';
import type { WearCyclePreview } from '../../../types/api';

const preview: WearCyclePreview = {
  lineGroup: 'EAL', cycleDate: '2026-05-28', records: [],
  segments: [{ segmentName: 'U1', isPresent: true, coveragePercentage: 83.5, diagnosticGaps: ['100-110m'], sourceFileNames: ['u1.xlsx'] }],
  conflicts: [{ conflictId: 'conflict-28', measurementIdentity: 'm-1', sourceValues: [['a.xlsx', 10.2], ['b.xlsx', 9.9]], selectedWearMin: 9.9, isAccepted: false, acceptedAt: null }],
  unresolved: [], blockingReasons: ['Accept conflicts'], canSave: false, previewDigest: 'digest', expectedDataVersion: 4,
};

it('shows coverage and requires explicit conflict acceptance', async () => {
  const onAcceptConflict = vi.fn();
  render(<WearCycleStatusPanel preview={preview} onAcceptConflict={onAcceptConflict} onSave={vi.fn()} />);
  expect(screen.getByText('83.5%')).toBeInTheDocument();
  expect(screen.getByText(/u1\.xlsx/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /save records/i })).toBeDisabled();
  await userEvent.click(screen.getByRole('button', { name: /accept lower value/i }));
  expect(onAcceptConflict).toHaveBeenCalledWith('conflict-28');
});

it('shows missing segments as a warning and allows partial records to be saved', async () => {
  const onSave = vi.fn();
  render(
    <WearCycleStatusPanel
      preview={{
        ...preview,
        segments: [{ segmentName: 'D2', isPresent: false, coveragePercentage: 0, diagnosticGaps: [], sourceFileNames: [] }],
        conflicts: [],
        blockingReasons: ['segment_missing'],
        canSave: true,
      }}
      onAcceptConflict={vi.fn()}
      onSave={onSave}
    />,
  );

  expect(screen.getByText(/save the detected records now/i)).toBeInTheDocument();
  expect(screen.queryByText('segment_missing')).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: /save records/i }));
  expect(onSave).toHaveBeenCalledTimes(1);
});
