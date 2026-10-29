// LEGACY QA FIXTURE (not part of the current acceptance suite).
//
// This historical Plotly interaction script still exercises the former
// chainage-mean/min-max controls.  The current UI uses a median-sample
// analysis mode and a separate raw-overview import action; those flows are
// covered by exception-generator.spec.ts and the component tests.  Keep this
// file only for comparison with archived screenshots until the old fixtures
// are retired.
// Run against an existing Vite server. API responses are fixtures; Plotly is real.
import { chromium, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

const output = path.resolve('../outputs/exception-performance-2026-10-26', `browser-qa-${new Date().toISOString().replace(/[:.]/g, '-')}`);
await fs.mkdir(output, { recursive: true });
const baseURL = process.env.TOV1050_E2E_URL || 'http://127.0.0.1:5179';
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const report = { baseURL, output, fixture: 'API fixtures, real React/Plotly/WebGL', results: [] };
const points = Array.from({ length: 40 }, (_, i) => 9100 + i * 0.2);
function payload(raw = false, from = -Infinity, to = Infinity) {
  const chainage = points.filter(x => x >= from && x <= to);
  const data = { Chainage: chainage };
  for (const kind of ['height', 'stagger', 'wear']) for (let channel = 1; channel <= 4; channel++) {
    const name = `${kind}${channel}`;
    const center = kind === 'height' ? 4000 + channel * 5 : kind === 'stagger' ? channel * 20 : channel * 0.1;
    data[name] = chainage.map((_, i) => center + (raw ? i % 3 : Math.sin(i / 3)));
    if (!raw) {
      data[`${name}_min`] = data[name].map(x => x - (kind === 'height' ? 20 : 1));
      data[`${name}_max`] = data[name].map((x, i) => kind === 'height' && channel === 1 && i === 20 ? 5800 : x + (kind === 'height' ? 20 : 1));
      data[`${name}_count`] = chainage.map(() => 10);
    }
  }
  if (raw) data.source_row_number = chainage.map((_, i) => i + 2);
  else for (const [name, mapper] of Object.entries({ sample_count: () => 10, group_id: (_, i) => i, pass_id: () => 0,
    source_row_first: (_, i) => i * 10 + 2, source_row_last: (_, i) => i * 10 + 11,
    SampleCount_first: (_, i) => i * 10, SampleCount_last: (_, i) => i * 10 + 9 })) data[name] = chainage.map(mapper);
  return { chart_data: data, chart_resolution: { source_points: chainage.length, returned_points: chainage.length,
    strategy: 'raw', aggregation: raw ? 'raw' : 'chainage_mean', raw_points: chainage.length * (raw ? 1 : 10), grouped_points: chainage.length } };
}
async function chart(page) {
  return page.locator('.js-plotly-plot').evaluate(gd => ({
    data: gd.data.map(t => ({ name: t.name, mode: t.mode, xaxis: t.xaxis, yaxis: t.yaxis, x: Array.from(t.x), y: Array.from(t.y), connectgaps: t.connectgaps })),
    axes: Object.fromEntries(['xaxis', 'yaxis', 'yaxis2', 'yaxis3'].map(k => [k, { range: gd._fullLayout[k].range, anchor: gd._fullLayout[k].anchor, domain: gd._fullLayout[k].domain }])),
    size: gd._fullLayout._size, canvases: gd.querySelectorAll('canvas').length,
  }));
}
async function reachable(locator) {
  const rect = await locator.boundingBox();
  return { rect, hit: await locator.evaluate(e => { const r = e.getBoundingClientRect(); return e.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)); }) };
}
try {
  for (const viewport of [{ width: 1280, height: 720 }, { width: 1033, height: 640 }, { width: 390, height: 844 }]) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    page.setDefaultTimeout(25000);
    const result = { viewport, checks: {}, console: [], errors: [], details: [] };
    report.results.push(result);
    page.on('console', msg => { if (['error', 'warning'].includes(msg.type())) result.console.push({ type: msg.type(), text: msg.text() }); });
    page.on('pageerror', error => result.errors.push(error.message));
    await page.addInitScript(() => { window.electronAPI = { openFile: async () => 'C:/Test/TWL-QA.csv' }; });
    let params;
    let slowDetail = false;
    await page.route('**/api/**', async route => {
      const url = new URL(route.request().url());
      if (!url.pathname.startsWith('/api/')) return route.continue();
      if (url.pathname.endsWith('/health')) return route.fulfill({ json: { status: 'ok' } });
      if (url.pathname.endsWith('/analysis/jobs')) {
        params = route.request().postDataJSON();
        return route.fulfill({ json: { job_id: 'qa-analysis', kind: 'analysis', status: 'ready', stage: 'ready', elapsed_seconds: 1 } });
      }
      if (url.pathname.endsWith('/jobs/qa-analysis/result')) return route.fulfill({ json: {
        status: 'success', analysis_revision: 'qa-r1', params, ...payload(), boundaries: [], exceptions: { 'High Height': [{
          id: 'QA-E1', 'exception type': 'High Height', level: 'L1', FromM: 9103.8, ToM: 9104.2, length: 0.4,
          maxLocation: 9104, maxValue: 5800, Class: 'Mainline', 'Track Type': 'Straight', Overlap: null,
          'Tension Length': 'TL-QA', Landmark: null, 'Threshold Value': 5500, Section: 'Mainline',
        }] },
      } });
      if (url.pathname.endsWith('/analyze/chart-data')) {
        const query = Object.fromEntries(url.searchParams);
        result.details.push(query);
        if (slowDetail) { slowDetail = false; await new Promise(resolve => setTimeout(resolve, 1800)); }
        const data = payload(query.chart_data_mode === 'raw', query.from_m ? Number(query.from_m) : -Infinity, query.to_m ? Number(query.to_m) : Infinity);
        return route.fulfill({ json: data }).catch(() => {});
      }
      return route.fulfill({ status: 418, json: { detail: `QA unexpected API ${url.pathname}` } });
    });
    try {
      await page.goto(baseURL);
      if (viewport.width < 600) await page.getByRole('button', { name: 'open drawer' }).click();
      await page.getByRole('button', { name: 'Exception Generator', exact: true }).click();
      await page.getByRole('button', { name: 'Start New Analysis' }).click();
      await page.getByRole('button', { name: 'Browse', exact: true }).click();
      await page.getByLabel('Station Start', { exact: true }).fill('CEN');
      await page.getByLabel('Station End', { exact: true }).fill('TSW');
      await page.getByRole('button', { name: 'Start Analysis', exact: true }).click();
      await expect(page.locator('.js-plotly-plot')).toBeVisible();
      await expect.poll(async () => (await chart(page)).data.length).toBe(13);
      result.initial = await chart(page);
      result.checks.meanMarkers = result.initial.data.find(t => t.name === 'height1 mean').mode === 'markers';
      result.checks.rawPeak = result.initial.data.find(t => t.name === 'High Height Dots').y[0] === 5800;
      result.checks.sharedXAxis = result.initial.data.every(t => t.xaxis === 'x') && result.initial.axes.yaxis2.anchor === 'x' && result.initial.axes.yaxis3.anchor === 'x';
      result.checks.readablePlotHeight = result.initial.size.h >= 350;
      result.yTitles = await page.locator('.g-ytitle, .g-y2title, .g-y3title').evaluateAll(nodes => nodes.map(node => {
        const r = node.getBoundingClientRect(); return { text: node.textContent, top: r.top, bottom: r.bottom };
      }).sort((a, b) => a.top - b.top));
      result.checks.separateAxisTitles = result.yTitles.length === 3 && result.yTitles.every((title, i, all) => i === 0 || all[i - 1].bottom < title.top);
      result.toolbar = {};
      for (const name of ['完整報表', 'Raw', '精簡報表（同里程平均）', 'Graph', 'Table']) {
        const button = page.getByRole('button', { name, exact: true });
        await button.scrollIntoViewIfNeeded();
        result.toolbar[name] = await reachable(button);
        expect(result.toolbar[name].hit, `${name} hit testing`).toBe(true);
      }
      await page.screenshot({ path: path.join(output, `mean-${viewport.width}.png`) });
      await page.getByRole('checkbox', { name: 'Raw min/max', exact: true }).check();
      await expect.poll(async () => (await chart(page)).data.length).toBe(25);
      const ranges = (await chart(page)).data.find(t => t.name === 'height1 raw min/max');
      result.checks.minMax = ranges.mode === 'lines' && ranges.connectgaps === false && ranges.y.includes(5800) && ranges.x[0] === ranges.x[1] && ranges.x[2] === null;
      await page.screenshot({ path: path.join(output, `minmax-${viewport.width}.png`) });
      const mode = page.getByRole('combobox', { name: 'Chart data' });
      await mode.click(); await page.getByRole('option', { name: 'Raw sample points', exact: true }).click();
      await expect.poll(async () => (await chart(page)).data.some(t => t.name === 'height1' && t.mode === 'markers')).toBe(true);
      result.checks.rawPoints = true;
      await expect(page.getByRole('checkbox', { name: 'Raw min/max', exact: true })).toBeDisabled();
      await mode.click(); await page.getByRole('option', { name: 'Raw acquisition lines', exact: true }).click();
      await expect.poll(async () => (await chart(page)).data.some(t => t.name === 'height1' && t.mode === 'lines')).toBe(true);
      result.checks.rawLines = true;
      await mode.click(); await page.getByRole('option', { name: 'Chainage mean points', exact: true }).click();
      await expect.poll(async () => (await chart(page)).data.some(t => t.name === 'height1 mean')).toBe(true);
      if (viewport.width >= 600) {
        const before = result.details.length;
        const plot = page.locator('.js-plotly-plot');
        await plot.scrollIntoViewIfNeeded();
        const box = await plot.boundingBox();
        const { size } = await chart(page);
        const y = box.y + size.t + size.h * 0.14;
        await page.mouse.move(box.x + size.l + size.w * 0.2, y);
        await page.mouse.down(); await page.mouse.move(box.x + size.l + size.w * 0.8, y + Math.max(8, size.h * 0.05), { steps: 10 }); await page.mouse.up();
        await expect.poll(() => result.details.length).toBeGreaterThan(before);
        await expect(page.getByLabel('Loading chart detail')).toHaveCount(0);
        result.zoom = await chart(page);
        result.checks.mouseZoomDetail = result.details.at(-1).from_m != null && result.zoom.data.find(t => t.name === 'height1 mean').x.length < points.length;
        // Real list selection and real plot rendering retain the original exception value.
        await page.getByText('ID: QA-E1', { exact: true }).click();
        await expect(page.getByRole('button', { name: 'Clear Selection' })).toBeEnabled();
        await expect.poll(() => result.details.at(-1)?.from_m).toBe(String(9003.8));
        await expect(page.getByLabel('Loading chart detail')).toHaveCount(0);
        result.selected = await chart(page);
        result.checks.selectedRawPeak = result.selected.data.find(t => t.name === 'High Height Dots').y[0] === 5800;
        await page.screenshot({ path: path.join(output, `selected-${viewport.width}.png`) });
        // Two relayout events on the real Plotly DOM simulate fast changing windows;
        // the first response is delayed and must not replace the latest window.
        slowDetail = true;
        await plot.evaluate(gd => gd.emit('plotly_relayout', { 'xaxis.range[0]': 9100, 'xaxis.range[1]': 9102 }));
        await expect.poll(() => result.details.at(-1)?.from_m).toBe('9100');
        await plot.evaluate(gd => gd.emit('plotly_relayout', { 'xaxis.range[0]': 9105, 'xaxis.range[1]': 9107 }));
        await expect.poll(() => result.details.at(-1)?.from_m).toBe('9105');
        await expect(page.getByLabel('Loading chart detail')).toHaveCount(0);
        await page.waitForTimeout(1900);
        const latest = (await chart(page)).data.find(t => t.name === 'height1 mean').x;
        result.checks.latestDetail = latest.every(x => x >= 9105 && x <= 9107) && latest.length > 0;
      } else {
        await page.getByText('ID: QA-E1', { exact: true }).click();
        await expect(page.getByRole('button', { name: 'Clear Selection' })).toBeEnabled();
        await expect.poll(() => result.details.at(-1)?.from_m).toBe(String(9003.8));
        await expect(page.getByLabel('Loading chart detail')).toHaveCount(0);
        result.selected = await chart(page);
        result.checks.selectedRawPeak = result.selected.data.find(t => t.name === 'High Height Dots').y[0] === 5800;
        await page.getByRole('combobox', { name: 'Chart data' }).scrollIntoViewIfNeeded();
        await page.screenshot({ path: path.join(output, `selected-${viewport.width}.png`) });
        result.limitation = '390px checks toolbar, chart modes, ranges and list selection; mouse-drag zoom and response-race checks run on desktop sizes.';
      }
      result.documentWidth = await page.evaluate(() => ({ inner: innerWidth, scroll: document.documentElement.scrollWidth }));
      await page.getByRole('button', { name: 'Table', exact: true }).click();
      await expect(page.getByRole('cell', { name: 'QA-E1', exact: true })).toBeVisible();
      result.checks.tableView = (await page.getByRole('table').boundingBox()).height > 50;
      await page.getByRole('button', { name: 'Graph', exact: true }).click();
      await expect(page.locator('.js-plotly-plot')).toBeVisible();
      result.checks.noPageErrors = result.errors.length === 0;
      result.checks.noInvalidAxisWarnings = !result.console.some(item => /invalid.*axis|axis.*invalid|unrecognized.*axis/i.test(item.text));
      result.checks.webglCanvases = result.initial.canvases > 0;
      for (const [check, passed] of Object.entries(result.checks)) expect(passed, `${viewport.width}: ${check}`).toBe(true);
      result.status = 'passed';
    } catch (error) {
      result.status = 'failed'; result.failure = error.stack;
      await page.screenshot({ path: path.join(output, `failure-${viewport.width}.png`), fullPage: true }).catch(() => {});
    }
    await context.close();
    console.log(JSON.stringify({ viewport, status: result.status, checks: result.checks, failure: result.failure?.slice(0, 500) }));
    await fs.writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  }
} finally { await browser.close(); }
console.log(`Report: ${path.join(output, 'report.json')}`);
if (report.results.some(result => result.status === 'failed')) process.exitCode = 1;
