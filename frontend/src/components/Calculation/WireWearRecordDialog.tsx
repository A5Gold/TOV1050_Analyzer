import React from 'react';
import { Autocomplete, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField } from '@mui/material';
import type { WearMetadataCatalogItem, WireWearLineGroup } from '../../types/api';

interface Value { cycleDate: string; tensionLength: string; avgWearMin: number }
interface Props {
  open: boolean
  mode: 'add' | 'edit'
  lineGroup: WireWearLineGroup
  initialValue: Value
  catalog: WearMetadataCatalogItem[]
  onClose: () => void
  onStage: (value: Value & { lineGroup: WireWearLineGroup }) => void
}

export default function WireWearRecordDialog({ open, mode, lineGroup, initialValue, catalog, onClose, onStage }: Props) {
  const [line, setLine] = React.useState(lineGroup);
  const [value, setValue] = React.useState(initialValue);
  React.useEffect(() => { setLine(lineGroup); setValue(initialValue); }, [initialValue, lineGroup, open]);
  const choices = catalog.filter(item => item.lineGroup === line);
  const metadata = choices.find(item => item.tensionLength === value.tensionLength);
  const metadataIntervals = metadata?.intervals?.length
    ? metadata.intervals
    : metadata
      ? [{ track: metadata.track, fromM: metadata.fromM, toM: metadata.toM }]
      : [];
  const intervalCount = metadata?.intervalCount ?? metadataIntervals.length;
  const wearPercentage = Math.max(0, ((13.2 - Number(value.avgWearMin || 0)) / 13.2) * 100);
  const valid = Boolean(value.cycleDate && metadata && Number.isFinite(Number(value.avgWearMin)) && Number(value.avgWearMin) > 0);

  return <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth aria-labelledby="wear-record-dialog-title">
    <DialogTitle id="wear-record-dialog-title">{mode === 'edit' ? 'Edit Wire Wear Record' : 'Add Wire Wear Record'}</DialogTitle>
    <DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
      <TextField label="Line" value={line} onChange={event => { const next = event.target.value.toUpperCase() as WireWearLineGroup; if (next === 'EAL' || next === 'TML') { setLine(next); setValue(current => ({ ...current, tensionLength: '' })); } }} disabled={mode === 'edit'} inputProps={{ list: 'wear-line-options' }} />
      <datalist id="wear-line-options"><option value="EAL" /><option value="TML" /></datalist>
      <TextField label="Cycle Date" type="date" value={value.cycleDate} onChange={event => setValue(current => ({ ...current, cycleDate: event.target.value }))} InputLabelProps={{ shrink: true }} disabled={mode === 'edit'} />
      <Autocomplete
        options={choices.map(item => item.tensionLength)} value={value.tensionLength || null}
        onChange={(_, tensionLength) => setValue(current => ({ ...current, tensionLength: tensionLength ?? '' }))}
        renderInput={params => <TextField {...params} label="Tension Length" />}
        disabled={mode === 'edit'}
      />
      <TextField label="Avg Wear Min" type="number" value={value.avgWearMin} onChange={event => setValue(current => ({ ...current, avgWearMin: Number(event.target.value) }))} inputProps={{ min: 0, step: 0.001 }} />
      <TextField label="Track" value={metadata?.track ?? ''} disabled />
      <TextField label="From (m)" value={metadata?.fromM ?? ''} disabled />
      <TextField label="To (m)" value={metadata?.toM ?? ''} disabled />
      <TextField label="Intervals" value={metadata ? intervalCount : ''} disabled />
      <TextField
        label="Physical Intervals"
        value={metadataIntervals.map(item => `${item.track} ${item.fromM}-${item.toM}`).join('\n')}
        disabled
        multiline
        minRows={intervalCount > 1 ? 2 : 1}
      />
      <TextField label="Wear %" value={metadata ? `${Math.round(wearPercentage)}%` : ''} title={metadata ? `${wearPercentage}%` : undefined} disabled />
    </Stack></DialogContent>
    <DialogActions><Button onClick={onClose}>Cancel</Button><Button variant="contained" disabled={!valid} onClick={() => onStage({ ...value, lineGroup: line })}>Stage {mode}</Button></DialogActions>
  </Dialog>;
}
