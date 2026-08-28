import type { WearCycleMatrixRow, WearWorkbenchColumn } from '../../types/api';

const PREFIX_ORDER = new Map([
  ['X', 0],
  ['T', 1],
  ['D', 2],
  ['M', 3],
  ['L', 4],
]);

type TensionLengthSortKey = {
  group: number;
  prefix: string;
  numericSuffix: number;
  normalized: string;
};

const sortKey = (value: string): TensionLengthSortKey => {
  const normalized = value.trim().toUpperCase();
  const prefixed = normalized.match(/^([A-Z]+)\s*(\d+(?:\.\d+)?)$/);
  if (prefixed?.[1] === 'H') {
    return { group: 0, prefix: 'H', numericSuffix: Number(prefixed[2]), normalized };
  }
  if (/^\d+(?:\.\d+)?$/.test(normalized)) {
    return { group: 1, prefix: '', numericSuffix: Number(normalized), normalized };
  }
  if (prefixed && PREFIX_ORDER.has(prefixed[1])) {
    return {
      group: 2,
      prefix: prefixed[1],
      numericSuffix: Number(prefixed[2]),
      normalized,
    };
  }
  return { group: 3, prefix: normalized, numericSuffix: Number.POSITIVE_INFINITY, normalized };
};

const compareTensionLength = (left: string, right: string): number => {
  const a = sortKey(left);
  const b = sortKey(right);
  return a.group - b.group
    || (a.group === 2 ? (PREFIX_ORDER.get(a.prefix) ?? 99) - (PREFIX_ORDER.get(b.prefix) ?? 99) : 0)
    || a.numericSuffix - b.numericSuffix
    || a.normalized.localeCompare(b.normalized, undefined, { numeric: true, sensitivity: 'base' });
};

export const sortTensionLengthLabels = (labels: readonly string[]): string[] => (
  labels
    .map((label, index) => ({ label, index }))
    .sort((left, right) => compareTensionLength(left.label, right.label) || left.index - right.index)
    .map(item => item.label)
);

export const sortWearWorkbenchColumns = (
  columns: readonly WearWorkbenchColumn[],
): WearWorkbenchColumn[] => {
  const order = sortTensionLengthLabels(columns.map(column => column.tensionLength));
  const byLabel = new Map(columns.map(column => [column.tensionLength, column]));
  return order.map(label => byLabel.get(label)).filter((column): column is WearWorkbenchColumn => Boolean(column));
};

export const buildHistoricalWearMatrix = (
  columns: readonly WearWorkbenchColumn[],
  rows: readonly WearCycleMatrixRow[],
): Array<Array<string | number | null>> => [
  ['Cycle Date', ...columns.map(column => column.tensionLength)],
  ...rows.map(row => [
    row.cycleDate,
    ...columns.map(column => row.values[column.tensionLength] ?? null),
  ]),
];
