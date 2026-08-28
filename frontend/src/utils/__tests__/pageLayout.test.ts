import { describe, expect, it } from 'vitest';
import { boundedDataRegionSx, fillDataRegionSx, scrollablePageSx } from '../pageLayout';

describe('page layout scroll styles', () => {
  it('keeps page roots in natural document flow so the whole view can scroll', () => {
    expect(scrollablePageSx).toMatchObject({
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100%',
      overflow: 'visible',
    });
    expect(scrollablePageSx).not.toHaveProperty('height');
  });

  it('gives large data regions enough height without locking the page root', () => {
    expect(boundedDataRegionSx).toMatchObject({
      minHeight: 520,
      overflow: 'visible',
    });
    expect(boundedDataRegionSx).not.toHaveProperty('height');
  });

  it('keeps virtualized grids and charts in a definite-height region', () => {
    expect(fillDataRegionSx).toMatchObject({
      height: 'calc(100vh - 220px)',
      minHeight: 520,
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    });
  });
});
