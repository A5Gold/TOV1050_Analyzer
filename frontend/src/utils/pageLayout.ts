export const scrollablePageSx = {
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
  minHeight: '100%',
  overflow: 'visible',
} as const;

export const boundedDataRegionSx = {
  minHeight: 520,
  minWidth: 0,
  overflow: 'visible',
} as const;

export const fillDataRegionSx = {
  minHeight: 520,
  height: 'calc(100vh - 220px)',
  minWidth: 0,
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
} as const;
