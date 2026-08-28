import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import MetadataEditorView, { transformGridToMetadata, transformMetadataToGrid } from '../MetadataEditorView';
import { metadataApi } from '../../api/client';

// Mock the methods on the real object
// We don't mock the whole module, just the methods we need.
// Since metadataApi is an object exported from client.ts, we can spy on it.

describe('MetadataEditorView', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    
    // Setup spies
    vi.spyOn(metadataApi, 'getMetadata').mockResolvedValue([]);
    vi.spyOn(metadataApi, 'getSheetNames').mockResolvedValue(['threshold', 'Exception Boundarys', 'EAL UP']);
    vi.spyOn(metadataApi, 'saveMetadata').mockResolvedValue({ status: 'success', backup: 'backup.xlsx' });
  });

  test('renders sheet tabs dynamically', async () => {
    render(<MetadataEditorView />);
    
    // Wait for tabs to load
    await waitFor(() => {
        expect(screen.getByText('Thresholds')).toBeInTheDocument(); // Mapped from 'threshold'
        expect(screen.getByText('Boundaries')).toBeInTheDocument(); // Mapped from 'Exception Boundarys'
        expect(screen.getByText('EAL UP')).toBeInTheDocument(); // Raw name
    });
  });

  test('renders undo button', async () => {
    render(<MetadataEditorView />);
    const undoBtn = screen.getByRole('button', { name: /undo/i });
    expect(undoBtn).toBeInTheDocument();
    expect(undoBtn).toBeDisabled();
  });

  test('maps Wire Wear L2 null metadata to blank grid value', () => {
    const [row] = transformMetadataToGrid([
      {
        Class: 'Mainline',
        'Track Type': 'Tangent',
        'Exc Type': 'Wire Wear',
        'Wire Wear L1': 9.1,
        'Wire Wear L2': null,
        'Wire Wear L3': 12.3,
      },
    ]);

    expect(row.L1).toBe(9.1);
    expect(row.L2).toBeNull();
    expect(row._prefix).toBe('Wire Wear');
  });

  test('maps blank Wire Wear L2 grid value to explicit backend null', () => {
    const [row] = transformGridToMetadata([
      {
        id: 'wire-wear-row',
        Class: 'Mainline',
        'Track Type': 'Tangent',
        'Exc Type': 'Wire Wear',
        L1: 9.1,
        L2: null,
        L3: 12.3,
        _prefix: 'Wire Wear',
      },
    ]);

    expect(row).toHaveProperty('Wire Wear L2', null);
  });

  test('does not add blank-prefixed level columns for non-threshold rows', () => {
    const [row] = transformGridToMetadata([
      {
        id: 'boundary-row',
        Class: 'Mainline',
        'UP Track FromM': 1,
        'UP Track ToM': 2,
        L1: null,
        L2: null,
        L3: null,
        _prefix: '',
      },
    ]);

    expect(row).not.toHaveProperty(' L1');
    expect(row).not.toHaveProperty(' L2');
    expect(row).not.toHaveProperty(' L3');
  });
});
