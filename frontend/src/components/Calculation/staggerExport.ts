import * as XLSX from 'xlsx';

import type { StaggerResult } from '../../types/api';

const STAGGER_HEADERS = [
  'ID',
  'Result',
  'Status',
  'Run Date',
  'Line',
  'Track',
  'Section',
  'Task No',
  'Station Start',
  'Station End',
  'FromM',
  'ToM',
  'Length',
  'Exception Type',
  'MaxValue',
  'MaxLocation',
  'TL',
  'Track Type',
  'Level',
  'Asset Class',
  'Threshold Value',
  'Chi',
  'Spt_A',
  'Spt_I',
  'Spt_B',
  'Span_AI',
  'Span_IB',
  'K_eq',
  '4B_AI',
  'S_AI',
  'S_AI >= 4B',
  'P_AI',
  'Allowable_AI',
  'P_AI <= Allowable_AI',
  '4B_IB',
  'S_IB',
  'S_IB >= 4B',
  'P_IB',
  'Allowable_IB',
  'P_IB <= Allowable_IB',
  'P <= Allowable',
  'Remark',
];

const formatNumber = (value: number | null | undefined, digits?: number) => {
  if (value == null || Number.isNaN(value)) {
    return '';
  }
  return typeof digits === 'number' ? value.toFixed(digits) : String(value);
};

const formatCriterionNumber = (value: number | null | undefined) => formatNumber(value, 2);

const buildCriterionStatement = (
  left: number | null | undefined,
  operator: '>=' | '<=',
  right: number | null | undefined,
) => {
  if (left == null || right == null || Number.isNaN(left) || Number.isNaN(right)) {
    return '';
  }
  const passed = operator === '>=' ? left >= right : left <= right;
  return `${formatCriterionNumber(left)} ${operator} ${formatCriterionNumber(right)}: ${passed ? 'Pass' : 'Fail'}`;
};

const buildPOverallStatement = (result: StaggerResult) => {
  const spanResults = result.span_results ?? {};
  const parts = (['ai', 'ib'] as const).map((key) => {
    const span = spanResults[key];
    if (typeof span?.p !== 'number' || typeof span?.allowable !== 'number') {
      return null;
    }
    return `${key.toUpperCase()} ${span.p <= span.allowable ? 'Pass' : 'Fail'}`;
  }).filter(Boolean);
  return parts.join('; ');
};

const buildFilename = (firstResult: StaggerResult) => {
  const date = (firstResult.run_date || '').replace(/[-/]/g, '').slice(0, 8);
  const line = firstResult.line || '';
  const hasCustomFields = firstResult.task_no && firstResult.station_start && firstResult.station_end;

  if (hasCustomFields) {
    return `${date}_${line}_${firstResult.task_no}_${firstResult.station_start}-${firstResult.station_end}_Stagger_Report.xlsx`;
  }

  return `${date}_${line}_${firstResult.track || ''}_${firstResult.section || ''}_Stagger_Report.xlsx`;
};

export function exportStaggerResults(results: StaggerResult[]): void {
  if (!results.length) {
    return;
  }

  const rows = results.map((result) => {
    const ai = result.span_results?.ai ?? {};
    const ib = result.span_results?.ib ?? {};
    const fourBAi = typeof ai.b === 'number' ? ai.b * 4 : null;
    const fourBIb = typeof ib.b === 'number' ? ib.b * 4 : null;

    return [
      result.id,
      result.overall_result,
      result.trace_status ?? '',
      result.run_date ?? '',
      result.line,
      result.track,
      result.section ?? '',
      result.task_no ?? '',
      result.station_start ?? '',
      result.station_end ?? '',
      formatNumber(result.from_m),
      formatNumber(result.to_m),
      formatNumber(result.length),
      result.exception_type,
      formatNumber(result.max_value),
      formatNumber(result.max_location),
      result.tension_length ?? '',
      result.track_type ?? '',
      result.level ?? '',
      result.asset_class ?? '',
      formatNumber(result.threshold_value),
      formatNumber(result.chi),
      formatNumber(result.spt_a),
      formatNumber(result.spt_i),
      formatNumber(result.spt_b),
      formatNumber(result.span_ai),
      formatNumber(result.span_ib),
      formatNumber(result.k_eq, 3),
      formatCriterionNumber(fourBAi),
      formatCriterionNumber(ai.s),
      buildCriterionStatement(ai.s, '>=', fourBAi),
      formatCriterionNumber(ai.p),
      formatCriterionNumber(ai.allowable),
      buildCriterionStatement(ai.p, '<=', ai.allowable),
      formatCriterionNumber(fourBIb),
      formatCriterionNumber(ib.s),
      buildCriterionStatement(ib.s, '>=', fourBIb),
      formatCriterionNumber(ib.p),
      formatCriterionNumber(ib.allowable),
      buildCriterionStatement(ib.p, '<=', ib.allowable),
      buildPOverallStatement(result),
      result.remark.join('; '),
    ];
  });

  const worksheet = XLSX.utils.aoa_to_sheet([STAGGER_HEADERS, ...rows]);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Stagger Analysis');

  XLSX.writeFile(workbook, buildFilename(results[0]));
}
