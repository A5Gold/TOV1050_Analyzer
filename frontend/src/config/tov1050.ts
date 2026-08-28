export const TOV1050_LINES = ['AEL', 'TCL', 'DRL', 'KTL', 'ISL', 'TWL', 'TKL'] as const;
export type Tov1050Line = typeof TOV1050_LINES[number];

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
