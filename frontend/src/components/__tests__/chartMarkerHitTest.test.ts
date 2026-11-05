import { describe, expect, it } from 'vitest';
import { hitTestExceptionMarkers } from '../chartMarkerHitTest';

const axis = (offset: number) => ({ _offset: offset, _length: 200, l2p: (value: number) => value });
const trace = (id: string, yaxis = 'y', x = 100, y = 100) => ({ visible: true, mode: 'markers', xaxis: 'x', yaxis,
  x: [x], y: [y], marker: { size: 8 }, customdata: [{ kind: 'exception-marker', id }] });
const plot = (traces: any[]) => ({ getBoundingClientRect: () => ({ left: 10, top: 20, width: 300, height: 700 }),
  _fullLayout: { width: 300, height: 700, xaxis: axis(50), yaxis: axis(30), yaxis2: axis(250), yaxis3: axis(470) }, _fullData: traces });

describe('visible exception pixel hit testing', () => {
  it('uses the actual subplot, keeps coincident candidates, and accepts marker edges', () => {
    const gd = plot([trace('H'), trace('S', 'y2'), trace('W', 'y3'), trace('H2')]);
    expect(hitTestExceptionMarkers(gd, 160, 150)).toEqual([{ id: 'H', x: 100 }, { id: 'H2', x: 100 }]);
    expect(hitTestExceptionMarkers(gd, 165, 370)).toEqual([{ id: 'S', x: 100 }]);
    expect(hitTestExceptionMarkers(gd, 160, 590)).toEqual([{ id: 'W', x: 100 }]);
    expect(hitTestExceptionMarkers(gd, 170, 150)).toEqual([]);
    expect(hitTestExceptionMarkers(gd, 160, 260)).toEqual([]);
  });
  it('does not select hidden traces, offscreen markers, ordinary lines or nonfinite points', () => {
    const hidden = { ...trace('hidden'), visible: 'legendonly' };
    const line = { ...trace('line'), mode: 'lines' };
    const ordinary = { ...trace('ordinary'), customdata: [[1, 2, 3]] };
    expect(hitTestExceptionMarkers(plot([hidden, line, ordinary, trace('outside', 'y', 300), trace('nan', 'y', NaN)]), 160, 150)).toEqual([]);
    expect(hitTestExceptionMarkers(plot([trace('H')]), NaN, 150)).toEqual([]);
  });
});
