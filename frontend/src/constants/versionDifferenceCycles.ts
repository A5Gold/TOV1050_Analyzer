export const VERSION_DIFFERENCE_CYCLES = [
  {
    role: 'latest',
    formField: 'latest',
    comparisonKey: null,
    label: 'Latest',
    required: true,
    color: '#c74444',
  },
  {
    role: 'previous1',
    formField: 'previous_1',
    comparisonKey: 'previous_1',
    label: 'Previous 1',
    required: true,
    color: '#2b63c9',
  },
  {
    role: 'previous2',
    formField: 'previous_2',
    comparisonKey: 'previous_2',
    label: 'Previous 2',
    required: false,
    color: '#2f8a67',
  },
  {
    role: 'previous3',
    formField: 'previous_3',
    comparisonKey: 'previous_3',
    label: 'Previous 3',
    required: false,
    color: '#b8791b',
  },
  {
    role: 'previous4',
    formField: 'previous_4',
    comparisonKey: 'previous_4',
    label: 'Previous 4',
    required: false,
    color: '#9467bd',
  },
] as const;

export type VersionDifferenceCycle = (typeof VERSION_DIFFERENCE_CYCLES)[number];
export type VersionDifferenceFileRole = VersionDifferenceCycle['role'];
export type VersionDifferenceComparisonKey = Exclude<
  VersionDifferenceCycle['comparisonKey'],
  null
>;
export type VersionDifferenceFiles = Record<VersionDifferenceFileRole, File | null>;

export const createEmptyVersionDifferenceFiles = (): VersionDifferenceFiles => (
  Object.fromEntries(
    VERSION_DIFFERENCE_CYCLES.map(cycle => [cycle.role, null]),
  ) as VersionDifferenceFiles
);
