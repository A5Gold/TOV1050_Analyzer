import { test, expect } from '@playwright/test';

for (const viewport of [
  { width: 1280, height: 720 },
  { width: 1033, height: 640 },
  { width: 390, height: 844 },
]) {
  test(`analysis action stays reachable at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.addInitScript(() => {
      (window as any).electronAPI = { openFile: async () => 'C:/Test/Data.csv' };
    });
    await page.route('**/api/health', route => route.fulfill({ json: { status: 'ok' } }));
    await page.route('**/api/analysis/jobs', route => route.fulfill({
      status: 422, json: { detail: 'Analysis test response' },
    }));
    await page.goto(process.env.TOV1050_E2E_URL || '/');
    if (viewport.width < 600) await page.getByRole('button', { name: 'open drawer' }).click();
    await page.getByRole('button', { name: 'Exception Generator', exact: true }).click();
    await page.getByRole('button', { name: 'Start New Analysis' }).click();

    const start = page.getByRole('button', { name: 'Start Analysis', exact: true });
    await expect(start).toHaveCount(1);
    await expect(start).toBeInViewport({ ratio: 1 });
    await expect(start).toBeDisabled();
    await page.getByRole('button', { name: 'Browse', exact: true }).click();
    await start.click();
    await expect(page.getByRole('alert').filter({ hasText: 'Please enter Station Start and Station End' })).toBeVisible();

    await page.getByLabel('Station Start', { exact: true }).fill('CEN');
    await page.getByLabel('Station End', { exact: true }).fill('TSW');
    await expect(page.getByLabel('Station End', { exact: true })).toBeInViewport();
    await expect(start).toBeInViewport({ ratio: 1 });
    // Hit testing also detects a sticky action being covered by the card while scrolling.
    const rect = await start.boundingBox();
    expect(rect).not.toBeNull();
    expect(await start.evaluate(element => {
      const box = element.getBoundingClientRect();
      return element.contains(document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2));
    })).toBe(true);

    const request = page.waitForRequest('**/api/analysis/jobs');
    await start.click();
    expect((await request).postDataJSON()).toMatchObject({
      file_path: 'C:/Test/Data.csv', station_start: 'CEN', station_end: 'TSW',
    });
    await expect(page.getByRole('alert').filter({ hasText: 'Analysis test response' })).toBeVisible();
    await expect(start).toBeEnabled();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `output/exception-generator-${viewport.width}.png` });
  });
}
