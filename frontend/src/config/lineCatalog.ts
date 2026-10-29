// One packaged catalog is consumed by Python and TypeScript; no per-view lists.
import catalog from '../../../config/line_catalog.json';

export const LINE_CATALOG = catalog.lines;
export const PARENT_LINES = LINE_CATALOG.map(item => item.line);
export type ParentLine = string;

export const lineDefinition = (line: string) =>
  LINE_CATALOG.find(item => item.line === line.toUpperCase());

export const sectionsForLine = (line: string): readonly string[] =>
  lineDefinition(line)?.sections ?? [];

export const branchOptionsForLine = (line: string) =>
  (lineDefinition(line)?.branches ?? []).map(item => ({
    value: item.legacy_session,
    label: item.branch,
    branch: item.branch,
  }));

export const sectionOptionsForLine = (line: string) =>
  sectionsForLine(line).map(value => ({
    value,
    label: branchOptionsForLine(line).find(item => item.value === value)?.label ?? value,
  }));

export const normalizeDirection = (value: string): string => {
  const key = value.trim().toUpperCase();
  if (['UP', 'UT', 'U'].includes(key)) return 'UP';
  if (['DOWN', 'DN', 'DT', 'D'].includes(key)) return 'DOWN';
  return '';
};

export const canonicalBranch = (line: string, section: string): string => {
  const key = section.trim().toUpperCase();
  if (line === 'EAL' && (key === 'RAC' || key.includes('LOW'))) return 'Mainline';
  return branchOptionsForLine(line).find(item =>
    item.value.toUpperCase() === key || item.branch.toUpperCase() === key)?.branch ?? '';
};

export const legacySection = (line: string, section: string): string =>
  branchOptionsForLine(line).find(item => item.branch.toUpperCase() === section.toUpperCase())?.value ?? section;

/** Explicit alias handling for historical reports only, retaining source fields. */
export const normalizeReportIdentity = (line: string, section: string = '') => {
  const sourceLine = line.trim().toUpperCase();
  const alias = sourceLine === 'LMC' ? ['EAL', 'LMC'] : sourceLine === 'TKS' ? ['TKL', 'TKS'] : null;
  const parent = alias?.[0] ?? sourceLine;
  if (!PARENT_LINES.includes(parent)) return { line: '', section, branch: '', sourceLine };
  const resolved = alias?.[1] ?? legacySection(parent, section);
  const branch = canonicalBranch(parent, resolved);
  if (alias && section && canonicalBranch(parent, section) && canonicalBranch(parent, section) !== alias[1]) {
    return { line: '', section, branch: '', sourceLine };
  }
  return { line: parent, section: resolved, branch, sourceLine };
};
