import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import MainLayout from '../MainLayout';

afterEach(() => vi.unstubAllGlobals());

it('shows the requested sidebar order and Wear Calculator label', () => {
  vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})));

  render(
    <MainLayout activeView="wear" onViewChange={vi.fn()}>
      <div>Content</div>
    </MainLayout>,
  );

  const labels = screen.getAllByRole('button')
    .map(button => button.textContent?.trim())
    .filter((label): label is string => Boolean(label));

  expect(labels).toEqual([
    'About',
    'Generate',
    'History',
    'Version Difference',
    'Records',
    'Wear Calculator',
    'Stagger',
    'Trends',
    'Settings',
  ]);
  expect(screen.queryByRole('button', { name: 'Upload' })).not.toBeInTheDocument();
});
