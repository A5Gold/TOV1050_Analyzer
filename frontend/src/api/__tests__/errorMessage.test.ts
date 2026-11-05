import { describe, expect, it } from 'vitest';
import { apiDiagnosticText, apiErrorDiagnostic, apiErrorMessage } from '../errorMessage';

const staggerError = () => ({
  response: {
    status: 422,
    data: { detail: {
      code: 'STAGGER_CONFIG_UNAVAILABLE',
      message: 'Stagger calculation is unavailable for AEL/Mainline/UP',
      context: { line: 'AEL', branch: 'Mainline', direction: 'UP' },
      missing_configuration: ['approved branch support metadata', 'approved Keq strategy/coefficients'],
    } },
    headers: { authorization: 'must-not-copy' },
  },
  config: { headers: { authorization: 'must-not-copy' } },
});

describe('structured API diagnostics', () => {
  it('explains an identified AEL report and missing engineering configuration in Traditional Chinese', () => {
    const diagnostic = apiErrorDiagnostic(staggerError(), 'AEL_report.xlsx')!;
    expect(apiErrorMessage(staggerError())).toBe('已識別 AEL／Mainline／UP，目前缺少核准的分支支撐點資料、核准的 Keq 計算規則及係數，暫停拉出值計算。');
    const copied = JSON.parse(apiDiagnosticText(diagnostic));
    expect(copied).toMatchObject({ filename: 'AEL_report.xlsx', code: 'STAGGER_CONFIG_UNAVAILABLE', status: 422, context: { line: 'AEL', branch: 'Mainline', direction: 'UP' } });
    expect(copied.missing_configuration).toHaveLength(2);
    expect(apiDiagnosticText(diagnostic)).not.toContain('must-not-copy');
  });

  it('retains readable validation, legacy string, and network diagnostics', () => {
    expect(apiErrorMessage({ response: { data: { detail: 'Invalid workbook' } } })).toBe('Invalid workbook');
    expect(apiErrorMessage({ response: { data: { detail: [{ msg: 'Missing file' }] } } })).toBe('Missing file');
    expect(apiErrorMessage({ message: 'Network Error' })).toBe('Network Error');
    expect(apiErrorDiagnostic({ message: 'Network Error' })).toBeNull();
    expect(apiErrorMessage({ response: { data: { detail: { code: 'SCOPE', line: 'TML', message: 'Conflict', missing: ['track'] } } } })).toBe('TML：Conflict：track');
  });
});
