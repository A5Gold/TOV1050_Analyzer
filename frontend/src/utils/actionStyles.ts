/**
 * Shared ACTION color mapping for ComparisonDataGrid and RepeatedRecordTable.
 *
 * Phase 12 Bug 2.1: Unify ACTION styling across all DataGrid components.
 *
 * Color spec:
 * - Keep monitoring / Calculation → Blue (#1976d2)
 * - Verify on site → Red (safetyColors.l1)
 * - Verify by next 1st line PM cycle → Light Red (alpha l1 0.6)
 * - Pending → Orange (safetyColors.l2)
 * - No action required (*) → Grey
 */
import { safetyColors } from '../theme/AppTheme';
import { alpha } from '@mui/material/styles';

const ACTION_BLUE = '#1976d2';

interface ActionStyle {
  bgcolor: string;
  color: string;
  fontWeight?: string;
}

export const getActionStyle = (action: string): ActionStyle => {
  switch (action) {
    case 'Keep monitoring':
    case 'Calculation':
      return { bgcolor: ACTION_BLUE, color: 'white', fontWeight: 'bold' };
    case 'Verify on site':
      return { bgcolor: safetyColors.l1, color: 'white', fontWeight: 'bold' };
    case 'Verify by next 1st line PM cycle':
      return { bgcolor: alpha(safetyColors.l1, 0.6), color: 'white', fontWeight: 'bold' };
    case 'Pending':
      return { bgcolor: safetyColors.l2, color: 'white', fontWeight: 'bold' };
    case 'No action required (Overshoot)':
    case 'No action required (Verified within 1 year)':
    case 'No action required (Overlapping area)':
      return { bgcolor: 'action.disabledBackground', color: 'text.secondary' };
    default:
      return { bgcolor: 'action.disabledBackground', color: 'text.primary' };
  }
};
