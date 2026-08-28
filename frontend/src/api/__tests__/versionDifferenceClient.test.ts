import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  VERSION_DIFFERENCE_CYCLES,
  createEmptyVersionDifferenceFiles,
} from '../../constants/versionDifferenceCycles';

const { mockPost } = vi.hoisted(() => ({ mockPost: vi.fn() }));

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      post: mockPost,
      interceptors: { response: { use: vi.fn() } },
    })),
  },
}));

const { analyzeVersionDifference } = await import('../client');

describe('Version Difference cycle descriptor', () => {
  it('keeps the approved roles, fields, labels, requirements, and colors in order', () => {
    expect(VERSION_DIFFERENCE_CYCLES).toEqual([
      { role: 'latest', formField: 'latest', comparisonKey: null, label: 'Latest', required: true, color: '#c74444' },
      { role: 'previous1', formField: 'previous_1', comparisonKey: 'previous_1', label: 'Previous 1', required: true, color: '#2b63c9' },
      { role: 'previous2', formField: 'previous_2', comparisonKey: 'previous_2', label: 'Previous 2', required: false, color: '#2f8a67' },
      { role: 'previous3', formField: 'previous_3', comparisonKey: 'previous_3', label: 'Previous 3', required: false, color: '#b8791b' },
      { role: 'previous4', formField: 'previous_4', comparisonKey: 'previous_4', label: 'Previous 4', required: false, color: '#9467bd' },
    ]);
  });
});

describe('analyzeVersionDifference', () => {
  beforeEach(() => {
    mockPost.mockReset();
    mockPost.mockResolvedValue({
      data: { status: 'ready', latest_file: 'latest.xlsx', comparisons: [] },
    });
  });

  it('posts required reports with descriptor form field names', async () => {
    const files = createEmptyVersionDifferenceFiles();
    files.latest = new File(['latest'], 'latest.xlsx');
    files.previous1 = new File(['previous-1'], 'previous-1.xlsx');

    await analyzeVersionDifference(files);

    const [url, formData, config] = mockPost.mock.calls[0];
    expect(url).toBe('/analyze/version-difference');
    expect(Array.from((formData as FormData).keys())).toEqual(['latest', 'previous_1']);
    expect((formData as FormData).get('latest')).toBe(files.latest);
    expect((formData as FormData).get('previous_1')).toBe(files.previous1);
    expect(config.headers['Content-Type']).toBe('multipart/form-data');
  });

  it('preserves optional gaps and appends only the exact supplied roles', async () => {
    const files = createEmptyVersionDifferenceFiles();
    files.latest = new File(['latest'], 'latest.xlsx');
    files.previous1 = new File(['previous-1'], 'previous-1.xlsx');
    files.previous3 = new File(['previous-3'], 'previous-3.xlsx');
    files.previous4 = new File(['previous-4'], 'previous-4.xlsx');

    await analyzeVersionDifference(files);

    const formData = mockPost.mock.calls[0][1] as FormData;
    expect(Array.from(formData.keys())).toEqual([
      'latest',
      'previous_1',
      'previous_3',
      'previous_4',
    ]);
    expect(formData.get('previous_2')).toBeNull();
    expect(formData.get('previous_3')).toBe(files.previous3);
    expect(formData.get('previous_4')).toBe(files.previous4);
  });
});
