export interface ApiErrorDiagnostic {
  code: string;
  filename?: string;
  context: Record<string, string>;
  missingConfiguration: string[];
  message: string;
  originalMessage?: string;
  status?: number;
}

const missingConfigurationLabel = (value: string): string => ({
  'approved branch support metadata': '核准的分支支撐點資料',
  'approved Keq strategy/coefficients': '核准的 Keq 計算規則及係數',
  'approved direction-specific support metadata': '核准的方向支撐點資料',
}[value] ?? (value.startsWith('approved Stagger metadata:')
  ? `核准的 Stagger 配置：${value.slice('approved Stagger metadata:'.length).trim()}`
  : value));

/** Keep only actionable server fields, never the Axios request/config or headers. */
export const apiErrorDiagnostic = (error: any, filename?: string): ApiErrorDiagnostic | null => {
  const detail = error?.response?.data?.detail;
  if (!detail || typeof detail !== 'object' || Array.isArray(detail) || !detail.code) return null;
  const sourceContext = detail.context && typeof detail.context === 'object' ? detail.context : detail;
  const context: Record<string, string> = {};
  for (const key of ['line', 'branch', 'direction']) {
    if (typeof sourceContext[key] === 'string' && sourceContext[key]) context[key] = sourceContext[key];
  }
  const missing = detail.missing_configuration ?? detail.missing;
  const missingConfiguration = Array.isArray(missing) ? missing.filter((item): item is string => typeof item === 'string') : [];
  const originalMessage = typeof (detail.message ?? detail.reason) === 'string' ? (detail.message ?? detail.reason) : undefined;
  const scope = ['line', 'branch', 'direction'].map(key => context[key]).filter(Boolean).join('／');
  const message = detail.code === 'STAGGER_CONFIG_UNAVAILABLE'
    ? `已識別${scope ? ` ${scope}` : '報表身份'}，目前缺少${missingConfiguration.length ? missingConfiguration.map(missingConfigurationLabel).join('、') : '核准的 Stagger 計算配置'}，暫停拉出值計算。`
    : originalMessage
      ? [scope, originalMessage, missingConfiguration.join('、')].filter(Boolean).join('：')
      : String(detail.code);
  return {
    code: String(detail.code), filename, context, missingConfiguration, message, originalMessage,
    status: typeof error?.response?.status === 'number' ? error.response.status : undefined,
  };
};

export const apiDiagnosticText = (diagnostic: ApiErrorDiagnostic): string => JSON.stringify({
  code: diagnostic.code,
  filename: diagnostic.filename,
  status: diagnostic.status,
  context: diagnostic.context,
  missing_configuration: diagnostic.missingConfiguration,
  message: diagnostic.message,
  original_message: diagnostic.originalMessage,
}, null, 2);

/** Preserve structured engineering/configuration diagnostics in the UI. */
export const apiErrorMessage = (error: any, fallback = '操作失敗'): string => {
  const diagnostic = apiErrorDiagnostic(error);
  if (diagnostic) return diagnostic.message;
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg || item.message || JSON.stringify(item)).join('; ');
  if (detail && typeof detail === 'object') {
    const message = detail.message || detail.reason;
    const scope = [detail.line, detail.branch, detail.direction].filter(Boolean).join(' / ');
    const missing = Array.isArray(detail.missing) ? detail.missing.join('、') : '';
    if (message) return [scope, String(message), missing].filter(Boolean).join('：');
    if (detail.code) return String(detail.code);
  }
  return error?.message || fallback;
};
