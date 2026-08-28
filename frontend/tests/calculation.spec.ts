import { test, expect, Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const cyclePreview = (accepted: boolean) => ({
  line_group: 'EAL',
  cycle_date: '2026-05-28',
  records: [{
    line_group: 'EAL', cycle_date: '2026-05-28', tension_length: '28',
    track: 'Siding', from_m: 100, to_m: 200, avg_wear_min: 10.2,
    wear_percentage: 22.73, measurement_sd: 0.1, source_lineage: ['UP.xlsx', 'DN.xlsx'],
  }],
  segments: [{
    segment_name: 'U1', is_present: true, coverage_percentage: 100,
    diagnostic_gaps: [], source_file_names: ['UP.xlsx', 'DN.xlsx'],
    acquisition_date_from: '2026-05-27', acquisition_date_to: '2026-05-28',
  }],
  conflicts: [{
    conflict_id: 'conflict-1', measurement_identity: 'measurement-1',
    source_values: [['UP.xlsx', 10.4], ['DN.xlsx', 10.2]], selected_wear_min: 10.2,
    is_accepted: accepted, accepted_at: accepted ? '2026-05-28T12:00:00Z' : null,
  }],
  unresolved: [],
  blocking_reasons: accepted ? [] : ['Accept all conflicts before saving'],
  can_save: accepted,
  preview_digest: 'preview-digest',
  expected_data_version: 3,
});

async function mockCompleteCycle(page: Page) {
  await page.route('**/api/calculation/wear', async route => {
    const accepted = (await route.request().postDataBuffer())?.toString().includes('conflict-1') ?? false;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(cyclePreview(accepted)) });
  });
  await page.route('**/api/calculation/wear-records/cycles', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      cycle_id: 7, line_group: 'EAL', cycle_date: '2026-05-28', source_type: 'analysis',
      completeness_state: 'complete', acquisition_date_from: '2026-05-27',
      acquisition_date_to: '2026-05-28', source_lineage: ['UP.xlsx', 'DN.xlsx'],
      records: cyclePreview(true).records, segments: cyclePreview(true).segments,
      conflict_decisions: cyclePreview(true).conflicts, wire_wear_data_version: 4,
    }),
  }));
  await page.route('**/api/calculation/wear-records/workbench**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      line_group: 'EAL',
      columns: [{ tension_length: '28', track: 'Siding', from_m: 100, to_m: 200 }],
      matrix_rows: [{ cycle_date: '2026-05-28', values: { '28': 10.2 } }],
      latest_summary: [], records: [], catalog: [], wire_wear_data_version: 4,
    }),
  }));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Calculation module E2E', () => {

  test('wear calculator complete-cycle workflow', async ({ page }) => {
    await mockCompleteCycle(page);
    await page.goto('/');
    await page.getByText('Wear Calculator', { exact: true }).click();
    for (const tab of ['Analysis', 'Wire Wear Records', 'Dashboard', 'Projection']) {
      await expect(page.getByRole('tab', { name: tab, exact: true })).toBeVisible();
    }

    await page.locator('input[accept=".xlsx"]').first().setInputFiles([
      { name: 'UP.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('up') },
      { name: 'DN.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('dn') },
    ]);
    await page.getByRole('button', { name: 'Analyze Cycle' }).click();
    await expect(page.getByRole('gridcell', { name: 'Siding', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Save Records' })).toBeDisabled();
    await page.getByRole('button', { name: 'Accept Lower Value' }).click();
    await expect(page.getByRole('button', { name: 'Save Records' })).toBeEnabled();
    await page.getByRole('button', { name: 'Save Records' }).click();
    await expect(page.getByText(/cycle saved/i)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Download Excel' })).toBeVisible();

    await page.getByRole('tab', { name: 'Wire Wear Records' }).click();
    await expect(page.getByTestId('history-cell-2026-05-28-28')).toBeVisible();
  });

});
