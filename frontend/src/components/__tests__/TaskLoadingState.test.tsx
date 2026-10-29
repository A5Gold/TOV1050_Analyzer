import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, expect, test } from 'vitest';
import '@testing-library/jest-dom';
import TaskLoadingState from '../TaskLoadingState';

afterEach(cleanup);
test('shows only the measured percentage of the current stage', () => {
  render(<TaskLoadingState stage="exporting" exportMode progress={{ job_id: 'x', kind: 'export', status: 'running', stage: 'exporting', elapsed_seconds: 62, processed: 25, total: 100, unit: 'rows' }} />);
  expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '25');
  expect(screen.getByText(/本階段 25.0%/)).toHaveTextContent('01:02');
});
test('finalization without a denominator stays indeterminate', () => {
  render(<TaskLoadingState stage="finalizing" exportMode progress={{ job_id: 'x', kind: 'export', status: 'running', stage: 'finalizing', elapsed_seconds: 2, total: null }} />);
  expect(screen.getByRole('progressbar')).not.toHaveAttribute('aria-valuenow');
  expect(screen.queryByText(/100%/)).not.toBeInTheDocument();
});
