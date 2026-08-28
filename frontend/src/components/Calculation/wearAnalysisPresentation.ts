import type { CSSProperties } from 'react';
import type Plotly from 'plotly.js';
import type { WearCycleRecord, WearResult } from '../../types/api';

export interface AnalysisChartSort {
  field: 'fromM' | 'avgWearMin' | 'wearPercentage';
  direction: 'asc' | 'desc';
}

export type AnalysisDirection = 'UP' | 'DN';

const recordHasDirection = (
  row: WearCycleRecord,
  direction: AnalysisDirection,
): boolean => row.intervals.some(interval => interval.track === direction);

export const visibleAnalysisRows = (
  rows: WearCycleRecord[], directions: AnalysisDirection[], sort: AnalysisChartSort,
): WearCycleRecord[] => {
  const direction = sort.direction === 'asc' ? 1 : -1;
  const value = (row: WearCycleRecord) => sort.field === 'avgWearMin'
    ? row.avgWearMin : sort.field === 'wearPercentage' ? row.wearPercentage : row.fromM;
  return rows.filter(row => directions.some(direction => recordHasDirection(row, direction))).slice()
    .sort((left, right) => direction * (value(left) - value(right)));
};

export const chartAxisRange = (values: number[]): [number, number] => {
  if (!values.length) return [0, 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = Math.max((max - min) * 0.08, Math.abs(max) * 0.01, 0.05);
  return [min - pad, max + pad];
};

export type WearAnalysisMetric = 'wear_percentage' | 'avg_wear_min';

const STATUS_STYLES = {
  green: { backgroundColor: '#d4edda', color: '#155724', fontWeight: 600 },
  yellow: { backgroundColor: '#fff3cd', color: '#7d4e00', fontWeight: 600 },
  red: { backgroundColor: '#ffcccc', color: '#b71c1c', fontWeight: 600 },
} as const;

const STATUS_COLORS = {
  green: '#43a047',
  yellow: '#f9a825',
  red: '#e53935',
} as const;

function sortByFromMValue(a: WearResult, b: WearResult): number {
  return (a.from_m ?? 0) - (b.from_m ?? 0);
}

export function naturalTensionLengthComparator(left: string, right: string): number {
  return left.localeCompare(right, undefined, { numeric: true, sensitivity: 'base' });
}

export function sortByTensionLength(a: WearResult, b: WearResult): number {
  return naturalTensionLengthComparator(a.tension_length, b.tension_length);
}

export function getAvgWearMinStatus(avgWearMin: number): keyof typeof STATUS_STYLES {
  if (avgWearMin > 10.2) return 'green';
  if (avgWearMin >= 9.1) return 'yellow';
  return 'red';
}

export function getAvgWearMinStatusStyle(avgWearMin: number): CSSProperties {
  return STATUS_STYLES[getAvgWearMinStatus(avgWearMin)];
}

export function getAvgWearMinStatusColor(avgWearMin: number): string {
  return STATUS_COLORS[getAvgWearMinStatus(avgWearMin)];
}

export function buildWearAnalysisChartSpec(
  metric: WearAnalysisMetric,
  results: WearResult[],
): { data: Plotly.Data[], layout: Partial<Plotly.Layout> } {
  const sorted = [...results].sort(sortByFromMValue);
  const labels = sorted.map(result => result.tension_length);
  const values = sorted.map(result => metric === 'wear_percentage'
    ? result.wear_percentage
    : result.avg_wear_min);
  const colors = sorted.map(result => getAvgWearMinStatusColor(result.avg_wear_min));
  const isWearPercentage = metric === 'wear_percentage';
  const yTitle = isWearPercentage ? 'Wear %' : 'Avg Wear Min';

  const data: Plotly.Data[] = [{
    x: labels,
    y: values,
    type: 'bar',
    marker: { color: colors },
    text: values.map(value => isWearPercentage ? `${value}%` : `${value}`),
    textposition: 'outside',
  }];

  const layout: Partial<Plotly.Layout> = {
    margin: { t: 30, r: 10, b: 80, l: 58 },
    autosize: true,
    xaxis: { title: { text: 'Tension Length' }, tickangle: -45, type: 'category' },
    yaxis: {
      title: { text: yTitle },
      range: [
        0,
        Math.max(...values, isWearPercentage ? 20 : 13.2) * 1.15,
      ],
    },
    shapes: isWearPercentage ? [] : [
      {
        type: 'line',
        x0: -0.5,
        x1: labels.length - 0.5,
        xref: 'x',
        y0: 10.2,
        y1: 10.2,
        yref: 'y',
        line: { color: '#f9a825', dash: 'dot', width: 1.5 },
      },
      {
        type: 'line',
        x0: -0.5,
        x1: labels.length - 0.5,
        xref: 'x',
        y0: 9.1,
        y1: 9.1,
        yref: 'y',
        line: { color: '#e53935', dash: 'dot', width: 1.5 },
      },
    ],
  };

  return {
    data,
    layout,
  };
}
