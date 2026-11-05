import { test, expect, type Page } from '@playwright/test';

// API fixtures isolate real browser / Plotly pointer hit testing from raw I/O.
async function openChart(page: Page, duplicateMarker = false) {
  const chainage = Array.from({ length: 201 }, (_, i) => i * 10);
  const chart: Record<string, number[]> = { Chainage: chainage };
  for (const metric of ['height', 'stagger', 'wear']) for (let i = 1; i <= 4; i++) {
    chart[`${metric}${i}`] = chainage.map(() => metric === 'height' ? 4000 : metric === 'stagger' ? 240 : 9.5);
  }
  const exceptions = Object.fromEntries([
    ['High Height', 'H', 4000], ['Stagger Left', 'S', 240], ['Wire Wear', 'W', 9.5],
  ].map(([type, id, value]) => [type, [{ id, 'exception type': type, level: 'L1', FromM: 995,
    ToM: 1005, length: 10, maxLocation: 1000, maxValue: value, Section: 'Mainline' }]]));
  if (duplicateMarker) exceptions['High Height'].push({ ...exceptions['High Height'][0], id: 'H2' });
  const threshold_segments = [
    { from_m: 0, to_m: 2000, metric: 'height', exception_type: 'High Height', level: 'L1', value: 4500 },
    { from_m: 0, to_m: 2000, metric: 'height', exception_type: 'Low Height', level: 'L2', value: 3900 },
    { from_m: 0, to_m: 2000, metric: 'stagger', exception_type: 'Stagger Left', level: 'L1', value: 300 },
    { from_m: 0, to_m: 2000, metric: 'stagger', exception_type: 'Stagger Right', level: 'L2', value: -250 },
    { from_m: 0, to_m: 2000, metric: 'stagger', exception_type: 'Stagger Left', level: 'L3', value: 200 },
    { from_m: 0, to_m: 2000, metric: 'wear', exception_type: 'Wire Wear', level: 'L1', value: 8.9 },
    { from_m: 0, to_m: 2000, metric: 'wear', exception_type: 'Wire Wear', level: 'L2', value: 10.2 },
  ];
  let params: any;
  const windows: any[] = [];
  await page.addInitScript(() => { (window as any).electronAPI = { openFile: async () => 'C:/Test/20260907_TWL_UT.csv' }; });
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (!url.pathname.startsWith('/api/')) return route.continue();
    if (url.pathname.endsWith('/analysis/jobs')) {
      params = route.request().postDataJSON();
      return route.fulfill({ json: { job_id: 'pointer-qa', kind: 'analysis', status: 'ready', stage: 'ready', elapsed_seconds: 1 } });
    }
    if (url.pathname.endsWith('/jobs/pointer-qa/result')) return route.fulfill({ json: {
      status: 'success', analysis_mode: 'median', chart_view: 'chainage_median', analysis_revision: 'pointer-r1', params,
      chart_data: chart, chart_domain: { from_m: 0, to_m: 2000 }, threshold_segments, boundaries: [], exceptions,
    } });
    if (url.pathname.endsWith('/analyze/chart-data')) {
      windows.push(Object.fromEntries(url.searchParams));
      const from = Number(url.searchParams.get('from_m')), to = Number(url.searchParams.get('to_m'));
      const indexes = chainage.map((x, i) => x >= from && x <= to ? i : -1).filter(i => i >= 0);
      return route.fulfill({ json: { chart_data: Object.fromEntries(Object.entries(chart).map(([key, values]) => [key, indexes.map(i => values[i])])),
        chart_domain: { from_m: 0, to_m: 2000 }, threshold_segments } });
    }
    return route.fulfill({ json: { status: 'ok' } });
  });
  await page.goto(process.env.TOV1050_E2E_URL || '/');
  await page.getByRole('button', { name: 'Exception Generator', exact: true }).click();
  await page.getByRole('button', { name: 'Start New Analysis' }).click();
  await page.getByRole('button', { name: 'Browse', exact: true }).click();
  await page.getByRole('combobox', { name: 'Line', exact: true }).click();
  await page.getByRole('option', { name: 'TWL', exact: true }).click();
  await page.getByLabel('Station Start', { exact: true }).fill('CEN');
  await page.getByLabel('Station End', { exact: true }).fill('TSW');
  await page.getByRole('button', { name: 'Start Analysis', exact: true }).click();
  const plot = page.locator('.js-plotly-plot');
  await expect(plot).toBeVisible({ timeout: 60000 });
  await expect.poll(() => plot.evaluate((gd: any) => gd._fullLayout?.yaxis3?._length || 0)).toBeGreaterThan(0);
  await plot.evaluate((gd: any) => {
    (window as any).__pointerEvents = [];
    gd.on('plotly_click', (event: any) => (window as any).__pointerEvents.push({
      points: event.points.map((p: any) => ({ name: p.data?.name, x: p.x, y: p.y, customdata: p.customdata })),
      target: event.event?.target?.tagName,
    }));
  });
  return { plot, windows };
}

async function point(page: Page, axis: string, x: number, y: number) {
  const plot = page.locator('.js-plotly-plot');
  await plot.scrollIntoViewIfNeeded();
  return plot.evaluate((gd: any, point) => {
    const rect = gd.getBoundingClientRect(), xa = gd._fullLayout.xaxis, ya = gd._fullLayout[point.axis];
    return { x: rect.x + xa._offset + xa.l2p(point.x), y: rect.y + ya._offset + ya.l2p(point.y) };
  }, { axis, x, y });
}

test('real pointer after hover selects markers coincident with measurement lines in all three panels', async ({ page }, info) => {
  test.setTimeout(120000);
  const { plot, windows } = await openChart(page);
  try {
    for (const [axis, y] of [['yaxis', 4000], ['yaxis2', 240], ['yaxis3', 9.5]] as const) {
      const location = await point(page, axis, 1000, y);
      await page.mouse.move(location.x, location.y);
      await expect(page.locator('.hoverlayer')).toContainText(/Chainage|Loc:/);
      await expect(page.locator('.hoverlayer')).toContainText('實測值:');
      await expect(page.locator('.hoverlayer')).not.toContainText(/來源列|SampleCount|有效樣本|ID:|height1|stagger1|wear1/);
      await page.mouse.click(location.x, location.y);
      await expect.poll(() => plot.evaluate((gd: any) => gd.layout.xaxis.range)).toEqual([900, 1100]);
      await expect.poll(() => windows.some(window => window.from_m === '900' && window.to_m === '1100')).toBe(true);
      await page.getByRole('button', { name: 'Clear Selection' }).click();
    }
    // On the line and inside the edge of the 8px dot: native hit testing may
    // still return the line, but the bounded marker resolver must select it.
    const edge = await point(page, 'yaxis', 1000, 4000);
    await page.mouse.move(edge.x + 4, edge.y);
    await page.mouse.click(edge.x + 4, edge.y);
    await expect.poll(() => plot.evaluate((gd: any) => gd.layout.xaxis.range)).toEqual([900, 1100]);
    // Pan with the real modebar, then refocus the already selected same dot.
    await plot.locator('[data-title="Pan"]').click();
    const origin = await point(page, 'yaxis2', 1050, 240);
    await page.mouse.move(origin.x, origin.y);
    await page.mouse.down(); await page.mouse.move(origin.x - 40, origin.y, { steps: 8 }); await page.mouse.up();
    await expect.poll(() => plot.evaluate((gd: any) => gd.layout.xaxis.range[0])).not.toBe(900);
    const same = await point(page, 'yaxis', 1000, 4000);
    await page.mouse.move(same.x, same.y); await page.mouse.click(same.x, same.y);
    await expect.poll(() => plot.evaluate((gd: any) => gd.layout.xaxis.range)).toEqual([900, 1100]);
    await page.getByRole('button', { name: 'Clear Selection' }).click();
    const ordinary = await point(page, 'yaxis', 600, 4000);
    await page.mouse.click(ordinary.x, ordinary.y);
    await expect(page.getByRole('button', { name: 'Clear Selection' })).toBeDisabled();
    await page.getByRole('button', { name: '門檻設定' }).click();
    await expect(page.getByRole('checkbox', { name: 'Height L3' })).toBeDisabled();
    await expect(page.getByRole('checkbox', { name: 'Wire Wear L3' })).toBeDisabled();
    await page.getByRole('checkbox', { name: 'Height L1' }).uncheck();
    await page.getByRole('button', { name: '完成', exact: true }).click();
    await expect.poll(() => plot.evaluate((gd: any) => gd.layout.shapes.some((shape: any) => shape.y0 === 4500))).toBe(false);
    await page.getByRole('checkbox', { name: '門檻線', exact: true }).uncheck();
    await expect.poll(() => plot.evaluate((gd: any) => gd.layout.shapes.length)).toBe(0);
    await page.getByRole('checkbox', { name: '門檻線', exact: true }).check();
    await page.getByRole('button', { name: 'Table', exact: true }).click();
    await page.getByRole('button', { name: 'Graph', exact: true }).click();
    await page.getByRole('button', { name: '門檻設定' }).click();
    await expect(page.getByRole('checkbox', { name: 'Height L1' })).not.toBeChecked();
    await expect(page.getByRole('checkbox', { name: 'Stagger L1' })).toBeChecked();
    await page.getByRole('button', { name: '完成', exact: true }).click();
    await info.attach('chart-pointer-final', { body: await page.screenshot(), contentType: 'image/png' });
  } finally {
    const events = await page.evaluate(() => (window as any).__pointerEvents);
    console.log('Actual pointer events:', JSON.stringify(events));
    await info.attach('actual-pointer-events', { body: JSON.stringify(events, null, 2), contentType: 'application/json' });
  }
});

test('real pointer offers explicit choices for coincident exceptions and ignores hidden marker traces', async ({ page }) => {
  test.setTimeout(120000);
  const { plot } = await openChart(page, true);
  const location = await point(page, 'yaxis', 1000, 4000);
  await page.mouse.move(location.x, location.y); await page.mouse.click(location.x, location.y);
  await expect(page.getByRole('menu', { name: '選擇此位置的例外' })).toBeVisible();
  await expect(page.getByRole('menuitem')).toHaveCount(2);
  await page.getByRole('menuitem', { name: 'H2 · High Height · L1' }).click();
  await expect.poll(() => plot.evaluate((gd: any) => gd.layout.xaxis.range)).toEqual([900, 1100]);
  await page.getByRole('button', { name: 'Clear Selection' }).click();
  const legend = await plot.locator('.legendtext').filter({ hasText: /^High Height Dots$/ }).boundingBox();
  if (!legend) throw new Error('Marker legend is missing');
  // The legend's transparent toggle rect is the actual pointer target.
  await page.mouse.click(legend.x + legend.width / 2, legend.y + legend.height / 2);
  await expect.poll(() => plot.evaluate((gd: any) => gd._fullData.find((trace: any) => trace.name === 'High Height Dots').visible)).toBe('legendonly');
  const hidden = await point(page, 'yaxis', 1000, 4000);
  await page.mouse.move(hidden.x, hidden.y); await page.mouse.click(hidden.x, hidden.y);
  await expect(page.getByRole('menu', { name: '選擇此位置的例外' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Clear Selection' })).toBeDisabled();
});

test.describe('threshold panel responsive geometry', () => {
  test.use({ deviceScaleFactor: 1.25 });
  test('keeps the metric/level panel usable at desktop, short and narrow viewports', async ({ page }) => {
    test.setTimeout(180000);
    await openChart(page);
    for (const viewport of [{ width: 1280, height: 720 }, { width: 1033, height: 640 }, { width: 390, height: 844 }]) {
      await page.setViewportSize(viewport);
      await page.getByRole('button', { name: '門檻設定' }).click();
      const dialog = page.getByRole('dialog', { name: '門檻線設定' });
      await expect(dialog).toBeVisible();
      await expect(dialog.locator('..')).toHaveCSS('opacity', '1');
      await expect(dialog.getByRole('checkbox')).toHaveCount(9);
      const box = await dialog.boundingBox();
      if (!box) throw new Error('Threshold panel is not measurable');
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(viewport.width);
      expect(box.y + box.height).toBeLessThanOrEqual(viewport.height);
      await page.screenshot({ path: `../outputs/followup-chart-2026-10-29/thresholds-${viewport.width}.png`, animations: 'disabled' });
      await dialog.getByRole('button', { name: '完成', exact: true }).click();
    }
  });
});
