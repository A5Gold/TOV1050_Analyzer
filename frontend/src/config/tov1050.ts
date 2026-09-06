export const TOV1050_LINES = ['AEL', 'TCL', 'DRL', 'KTL', 'ISL', 'TWL', 'TKL'] as const;
export type Tov1050Line = typeof TOV1050_LINES[number];
export type Tov1050Direction = typeof TOV1050_DIRECTIONS[number];
export type Tov1050Session = 'Mainline' | 'PL' | 'TKS';

export const TOV1050_SESSIONS: Record<Tov1050Line, readonly string[]> = {
  AEL: ['Mainline'],
  TCL: ['Mainline'],
  DRL: ['Mainline', 'PL'],
  KTL: ['Mainline'],
  ISL: ['Mainline'],
  TWL: ['Mainline'],
  TKL: ['Mainline', 'TKS'],
};

export const TOV1050_DIRECTIONS = ['UT', 'DT'] as const;

export interface Tov1050RunPreset {
  line: string;
  taskNo: string;
  track: Tov1050Direction;
  section: string;
  stationStart: string;
  stationEnd: string;
  taskCode: string;
}

// Source: 00 Reference Document/TOV1050 Run List.xlsx. These are quick-fill
// suggestions only; every field remains editable for special cases.
export const TOV1050_RUN_PRESETS: readonly Tov1050RunPreset[] = [
  { line: 'TWL', taskNo: 'U1', track: 'UT', section: 'Mainline', stationStart: 'CEN', stationEnd: 'TSW', taskCode: '1' },
  { line: 'TWL', taskNo: 'D1', track: 'DT', section: 'Mainline', stationStart: 'TSW', stationEnd: 'CEN', taskCode: '2' },
  { line: 'KTL', taskNo: 'U1', track: 'UT', section: 'Mainline', stationStart: 'WHA', stationEnd: 'TIK', taskCode: '3' },
  { line: 'KTL', taskNo: 'D1', track: 'DT', section: 'Mainline', stationStart: 'TIK', stationEnd: 'WHA', taskCode: '4' },
  { line: 'ISL', taskNo: 'U1', track: 'UT', section: 'Mainline', stationStart: 'KET', stationEnd: 'CHW', taskCode: '5' },
  { line: 'ISL', taskNo: 'D1', track: 'DT', section: 'Mainline', stationStart: 'CHW', stationEnd: 'KET', taskCode: '6' },
  { line: 'TKL', taskNo: 'U1', track: 'UT', section: 'Mainline', stationStart: 'NOP', stationEnd: 'POA', taskCode: '7' },
  { line: 'TKL', taskNo: 'U2', track: 'UT', section: 'TKS', stationStart: 'TKO', stationEnd: 'LHP', taskCode: '7' },
  { line: 'TKL', taskNo: 'D1', track: 'DT', section: 'Mainline', stationStart: 'POA', stationEnd: 'NOP', taskCode: '8' },
  { line: 'TKL', taskNo: 'D2', track: 'DT', section: 'TKS', stationStart: 'LHP', stationEnd: 'TKO', taskCode: '8' },
  { line: 'AEL', taskNo: 'U1', track: 'UT', section: 'Mainline', stationStart: 'HOK', stationEnd: 'TSY', taskCode: '10A' },
  { line: 'AEL', taskNo: 'U2', track: 'UT', section: 'Mainline', stationStart: 'TSY', stationEnd: 'SUN', taskCode: '11A' },
  { line: 'AEL', taskNo: 'U3', track: 'UT', section: 'Mainline', stationStart: 'SHR', stationEnd: 'AWE', taskCode: '13A' },
  { line: 'AEL', taskNo: 'D1', track: 'DT', section: 'Mainline', stationStart: 'TSY', stationEnd: 'HOK', taskCode: '10B' },
  { line: 'AEL', taskNo: 'D2', track: 'DT', section: 'Mainline', stationStart: 'SUN', stationEnd: 'TSY', taskCode: '11B' },
  { line: 'AEL', taskNo: 'D3', track: 'DT', section: 'Mainline', stationStart: 'AWE', stationEnd: 'SHR', taskCode: '13B' },
  { line: 'TCL', taskNo: 'U1', track: 'UT', section: 'Mainline', stationStart: 'HOK', stationEnd: 'TSY', taskCode: '9A' },
  { line: 'TCL', taskNo: 'U2', track: 'UT', section: 'Mainline', stationStart: 'SUN', stationEnd: 'TUC', taskCode: '12A' },
  { line: 'TCL', taskNo: 'D1', track: 'DT', section: 'Mainline', stationStart: 'TSY', stationEnd: 'HOK', taskCode: '9B' },
  { line: 'TCL', taskNo: 'D2', track: 'DT', section: 'Mainline', stationStart: 'TUC', stationEnd: 'SUN', taskCode: '12B' },
  { line: 'DRL', taskNo: 'U1', track: 'UT', section: 'Mainline', stationStart: 'YOT', stationEnd: 'DIS', taskCode: '14' },
  { line: 'DRL', taskNo: 'PL', track: 'DT', section: 'PL', stationStart: 'DIS', stationEnd: 'DIS', taskCode: '14P' },
] as const;

export const TOV1050_METADATA_FILES = [
  'LAR_AEL metadata.xlsx',
  'LAR_TCL metadata.xlsx',
  'DRL metadata.xlsx',
  'KTL metadata.xlsx',
  'ISL metadata.xlsx',
  'TWL metadata.xlsx',
  'TKL metadata.xlsx',
  'TKS metadata.xlsx',
] as const;

export const TOV1050_SECTION_OPTIONS = Array.from(
  new Set(Object.values(TOV1050_SESSIONS).flat()),
);

export const sessionsForLine = (line: string): readonly string[] =>
  TOV1050_SESSIONS[line as Tov1050Line] ?? ['Mainline'];

export const isTov1050Line = (value: string): value is Tov1050Line =>
  (TOV1050_LINES as readonly string[]).includes(value);

export const isTov1050Direction = (value: string): value is Tov1050Direction =>
  (TOV1050_DIRECTIONS as readonly string[]).includes(value);
