import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import ComparisonFilterPanel from '../ComparisonFilterPanel';

describe('ComparisonFilterPanel', () => {
  it('does not show an active filter count when no filters are set', () => {
    render(
      <ComparisonFilterPanel
        data={[]}
        onFilteredDataChange={vi.fn()}
      />
    );

    expect(screen.queryByText(/active/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /clear/i })).toBeDisabled();
  });

  it('keeps the active filter count hidden when only one chainage bound is entered', async () => {
    const user = userEvent.setup();

    render(
      <ComparisonFilterPanel
        data={[]}
        onFilteredDataChange={vi.fn()}
      />
    );

    await user.click(screen.getByText(/filters/i));
    await user.type(screen.getByLabelText(/chainage from/i), '100');

    expect(screen.queryByText(/active/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /clear/i })).toBeDisabled();
  });

  it('shows one active filter and enables Clear when both chainage bounds are entered', async () => {
    const user = userEvent.setup();

    render(
      <ComparisonFilterPanel
        data={[]}
        onFilteredDataChange={vi.fn()}
      />
    );

    await user.click(screen.getByText(/filters/i));
    await user.type(screen.getByLabelText(/chainage from/i), '100');
    await user.type(screen.getByLabelText(/chainage to/i), '200');

    expect(screen.getByText(/1 active/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /clear/i })).toBeEnabled();
  });
});
