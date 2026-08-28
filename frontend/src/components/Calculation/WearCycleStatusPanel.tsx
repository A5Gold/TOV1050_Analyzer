import React from 'react';
import { Alert, Box, Button, Chip, LinearProgress, Stack, Typography } from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import type { WearCyclePreview } from '../../types/api';

interface Props { preview: WearCyclePreview; onAcceptConflict: (id: string) => void; onSave: () => void; isSaving?: boolean }
export default function WearCycleStatusPanel({ preview, onAcceptConflict, onSave, isSaving = false }: Props) {
  const hasMissingSegments = preview.blockingReasons.includes('segment_missing');
  const hardBlockingReasons = preview.blockingReasons.filter(reason => reason !== 'segment_missing');

  return <Stack spacing={2}>
    <Box><Typography variant="subtitle2">Expected Segments</Typography><Stack spacing={1} sx={{ mt: 1 }}>{preview.segments.map(segment => <Box key={segment.segmentName} sx={{ display: 'grid', gridTemplateColumns: '110px minmax(120px, 1fr) auto', gap: 1, alignItems: 'center' }}><Stack direction="row" spacing={0.5} alignItems="center"><Typography variant="body2">{segment.segmentName}</Typography><Chip size="small" color={segment.isPresent ? 'success' : 'warning'} label={segment.isPresent ? 'Detected' : 'Missing'} /></Stack><LinearProgress variant="determinate" value={segment.coveragePercentage} /><Typography variant="body2">{segment.coveragePercentage}%</Typography><Typography variant="caption" color="text.secondary" sx={{ gridColumn: '2 / -1' }}>{segment.sourceFileNames.join(', ') || 'No source file'}{segment.diagnosticGaps.length ? ` | Gaps: ${segment.diagnosticGaps.join(', ')}` : ''}</Typography></Box>)}</Stack></Box>
    {preview.conflicts.map(conflict => <Alert key={conflict.conflictId} severity="warning" action={!conflict.isAccepted && <Button size="small" color="warning" onClick={() => onAcceptConflict(conflict.conflictId)}>Accept Lower Value</Button>}><Typography variant="subtitle2">Data Conflict</Typography><Typography variant="body2">{conflict.sourceValues.map(([file, value]) => `${file}: ${value}`).join(' | ')}. Proposed: {conflict.selectedWearMin}</Typography></Alert>)}
    {hasMissingSegments && <Alert severity="warning">Some expected segments are missing. You can save the detected records now and upload the remaining sessions later.</Alert>}
    {hardBlockingReasons.length > 0 && <Alert severity="error">{hardBlockingReasons.join('; ')}</Alert>}
    <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}><Button variant="contained" startIcon={<SaveIcon />} disabled={!preview.canSave || isSaving} onClick={onSave}>{isSaving ? 'Saving...' : 'Save Records'}</Button></Box>
  </Stack>;
}
