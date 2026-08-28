import { SxProps, Theme } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { GridRowClassNameParams } from '@mui/x-data-grid';
import { safetyColors } from '../theme/AppTheme';

/**
 * Shared row style constants for DataGrid components.
 * Used by ComparisonDataGrid and RepeatedRecordTable.
 * Decision: Option B - L1/L2/L3 + pending + selected
 */

export interface RowStyleContext {
  pendingIds?: Set<string | number>;
  selectedIds?: Set<string | number>;
  reviewIds?: Set<string | number>;
}

export function getRowClassName(
  params: GridRowClassNameParams,
  context: RowStyleContext = {}
): string {
  const classes: string[] = [];

  if (context.reviewIds?.has(params.row.id ?? params.row.record_id)) {
    classes.push('row-review-required');
  }

  // L1/L2/L3 level background
  const level = params.row.level;
  if (level) {
    classes.push(`row-level-${level}`);
  }

  // Pending change highlight
  if (context.pendingIds?.has(params.row.id ?? params.row.record_id)) {
    classes.push('row-pending-change');
  }

  // Selected row highlight
  if (context.selectedIds?.has(params.row.id ?? params.row.record_id)) {
    classes.push('row-selected');
  }

  return classes.join(' ');
}

export const rowStylesSx: SxProps<Theme> = {
  '& .row-review-required': {
    // Review state is a stronger semantic state than L1/L2/L3 severity.
    bgcolor: '#ffe3f1 !important',
    borderLeft: '4px solid #c2185b',
    '&:hover': { bgcolor: '#ffd1e7 !important' },
  },
  '& .row-level-L1': {
    bgcolor: (theme: Theme) => alpha(safetyColors.l1, 0.1),
    '&:hover': { bgcolor: (theme: Theme) => alpha(safetyColors.l1, 0.2) },
  },
  '& .row-level-L2': {
    bgcolor: (theme: Theme) => alpha(safetyColors.l2, 0.1),
    '&:hover': { bgcolor: (theme: Theme) => alpha(safetyColors.l2, 0.2) },
  },
  '& .row-level-L3': {
    bgcolor: (theme: Theme) => alpha(safetyColors.l3, 0.1),
    '&:hover': { bgcolor: (theme: Theme) => alpha(safetyColors.l3, 0.2) },
  },
  '& .row-pending-change': {
    fontStyle: 'italic',
    color: '#ED6C02',
    '& .MuiDataGrid-cell': {
      fontStyle: 'italic',
      color: '#ED6C02',
    },
  },
  '& .row-selected': {
    borderLeft: '3px solid',
    borderLeftColor: 'primary.main',
    '& .MuiDataGrid-cellCheckbox .MuiCheckbox-root': {
      visibility: 'visible',
    },
  },
};
