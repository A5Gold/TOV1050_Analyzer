export interface MarkerHit { id: string; x: number }

// Plotly scattergl can report the measurement line when a marker shares its
// coordinates. Resolve only visible exception circles under the actual click,
// in CSS pixels; never substitute the nearest chainage elsewhere in the plot.
export function hitTestExceptionMarkers(plot: any, clientX: number, clientY: number): MarkerHit[] {
  if (!plot?._fullLayout || !Number.isFinite(clientX) || !Number.isFinite(clientY)) return [];
  const rect = plot.getBoundingClientRect(), layout = plot._fullLayout;
  const scaleX = rect.width / layout.width || 1, scaleY = rect.height / layout.height || 1;
  const hits = new Map<string, MarkerHit>();
  for (const trace of plot._fullData || []) {
    if (trace.visible !== true || !trace.mode?.includes('markers')) continue;
    const xa = layout[(trace.xaxis || 'x').replace('x', 'xaxis')];
    const ya = layout[(trace.yaxis || 'y').replace('y', 'yaxis')];
    if (!xa || !ya) continue;
    const left = rect.left + xa._offset * scaleX, top = rect.top + ya._offset * scaleY;
    if (clientX < left || clientX > left + xa._length * scaleX || clientY < top || clientY > top + ya._length * scaleY) continue;
    for (let i = 0; i < (trace.x?.length || 0); i++) {
      const marker = trace.customdata?.[i];
      if (marker?.kind !== 'exception-marker') continue;
      const x = trace.x[i], y = trace.y?.[i];
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      const px = left + xa.l2p(x) * scaleX, py = top + ya.l2p(y) * scaleY;
      if (px < left || px > left + xa._length * scaleX || py < top || py > top + ya._length * scaleY) continue;
      const size = Array.isArray(trace.marker?.size) ? trace.marker.size[i] : trace.marker?.size;
      const radius = Math.max(4, Number(size || 8) / 2) + 2;
      if (Math.hypot(clientX - px, clientY - py) <= radius) hits.set(marker.id, { id: marker.id, x });
    }
  }
  return [...hits.values()];
}
