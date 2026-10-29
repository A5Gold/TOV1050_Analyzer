import { test, expect } from '@playwright/test';

test('nine parent lines and DRL branch names remain separate from direction', async ({ page }) => {
  test.setTimeout(90000);
  await page.route('**/api/**', route => new URL(route.request().url()).pathname.startsWith('/api/') ? route.fulfill({ json: { status: 'ok' } }) : route.continue());
  page.setDefaultTimeout(30000);
  await page.goto(process.env.TOV1050_E2E_URL || '/');
  await expect(page.getByRole('button', { name: 'Exception Generator', exact: true })).toBeVisible({ timeout: 60000 });
  await page.getByRole('button', { name: 'Exception Generator', exact: true }).click();
  await page.getByRole('button', { name: 'Start New Analysis' }).click();
  const line = page.getByRole('combobox', { name: 'Line', exact: true });
  await line.click();
  for (const name of ['EAL', 'TML', 'AEL', 'TCL', 'KTL', 'ISL', 'TWL', 'TKL', 'DRL']) {
    await expect(page.getByRole('option', { name, exact: true })).toBeVisible();
  }
  await expect(page.getByRole('option', { name: 'LMC', exact: true })).toHaveCount(0);
  await page.getByRole('option', { name: 'DRL', exact: true }).click();
  await page.getByRole('combobox', { name: 'Section', exact: true }).click();
  await expect(page.getByRole('option', { name: 'UT', exact: true })).toBeVisible();
  await expect(page.getByRole('option', { name: 'PL', exact: true })).toBeVisible();
  await page.getByRole('option', { name: 'PL', exact: true }).click();
  await expect(page.getByRole('combobox', { name: 'Track', exact: true })).toHaveText('UT');
  await page.screenshot({ path: '../outputs/dual-system-2026-10-29/browser-drl.png', fullPage: true });
});

test('real Plotly marker focuses 200m and threshold toggle works in overview', async ({ page }) => {
  test.setTimeout(90000);
  page.on('pageerror', error => console.log('PAGE ERROR', error.message));
  const chainage = Array.from({ length: 201 }, (_, i) => i * 10);
  const chart: Record<string, number[]> = { Chainage: chainage };
  for (const metric of ['height', 'stagger', 'wear']) for (let i = 1; i <= 4; i++) {
    chart[`${metric}${i}`] = chainage.map(x => metric === 'height' ? 5300 + Math.sin(x / 100) * 20 : metric === 'stagger' ? 40 : 0.2);
  }
  const threshold_segments = [{ from_m: 0, to_m: 2000, metric: 'height', exception_type: 'High Height', level: 'L1', value: 5500 }];
  let params: any;
  const windows: { from: number; to: number }[] = [];
  await page.addInitScript(() => { (window as any).electronAPI = { openFile: async () => 'C:/Test/20260907_TWL_UT.csv' }; });
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (!url.pathname.startsWith('/api/')) return route.continue();
    if (url.pathname.endsWith('/analysis/jobs')) {
      params = route.request().postDataJSON();
      return route.fulfill({ json: { job_id: 'dual-qa', kind: 'analysis', status: 'ready', stage: 'ready', elapsed_seconds: 1 } });
    }
    if (url.pathname.endsWith('/jobs/dual-qa/result')) return route.fulfill({ json: {
      status: 'success', analysis_mode: 'median', chart_view: 'chainage_median', analysis_revision: 'dual-r1', params,
      chart_data: chart, chart_domain: { from_m: 0, to_m: 2000 }, threshold_segments, boundaries: [],
      exceptions: { 'High Height': [{ id: 'DOT1', 'exception type': 'High Height', level: 'L1',
        FromM: 995, ToM: 1005, length: 10, maxLocation: 1000, maxValue: 5600, Section: 'Mainline' }] },
    } });
    if (url.pathname.endsWith('/analyze/chart-data')) {
      const from = Number(url.searchParams.get('from_m')), to = Number(url.searchParams.get('to_m'));
      windows.push({ from, to });
      const indexes = chainage.map((x, i) => x >= from && x <= to ? i : -1).filter(i => i >= 0);
      return route.fulfill({ json: { chart_data: Object.fromEntries(Object.entries(chart).map(([key, values]) => [key, indexes.map(i => values[i])])),
        chart_domain: { from_m: 0, to_m: 2000 }, threshold_segments } });
    }
    return route.fulfill({ json: { status: 'ok' } });
  });
  page.setDefaultTimeout(30000);
  await page.goto(process.env.TOV1050_E2E_URL || '/');
  await expect(page.getByRole('button', { name: 'Exception Generator', exact: true })).toBeVisible({ timeout: 60000 });
  await page.getByRole('button', { name: 'Exception Generator', exact: true }).click();
  await page.getByRole('button', { name: 'Start New Analysis' }).click();
  await page.getByRole('button', { name: 'Browse', exact: true }).click();
  await page.getByLabel('Station Start', { exact: true }).fill('CEN');
  await page.getByLabel('Station End', { exact: true }).fill('TSW');
  await page.getByRole('button', { name: 'Start Analysis', exact: true }).click();
  const plot = page.locator('.js-plotly-plot');
  await expect(plot).toBeVisible({ timeout: 30000 }).catch(async error => { console.log(await page.locator('body').innerText()); throw error; });
  await expect.poll(() => plot.evaluate((gd: any) => gd.layout.shapes?.some((s: any) => s.y0 === 5500))).toBe(true);
  const threshold = page.getByRole('checkbox', { name: '門檻線' });
  await threshold.uncheck();
  await expect.poll(() => plot.evaluate((gd: any) => gd.layout.shapes?.some((s: any) => s.y0 === 5500) || false)).toBe(false);
  await threshold.check();
  const clickMarker = () => plot.evaluate((gd: any) => {
    const curveNumber = gd.data.findIndex((trace: any) => trace.name === 'High Height Dots');
    gd.emit('plotly_click', { points: [{ curveNumber, pointNumber: 0, pointIndex: 0, x: 1000, y: 5600, data: gd.data[curveNumber] }] });
  });
  await clickMarker();
  await expect.poll(() => plot.evaluate((gd: any) => gd.layout.xaxis.range)).toEqual([900, 1100]);
  await expect.poll(() => windows.some(window => window.from === 900 && window.to === 1100)).toBe(true);
  await clickMarker();
  await expect.poll(() => plot.evaluate((gd: any) => gd.layout.xaxis.range)).toEqual([900, 1100]);
  await page.screenshot({ path: '../outputs/dual-system-2026-10-29/browser-marker.png', fullPage: true });
});
