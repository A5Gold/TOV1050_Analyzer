/** Preserve structured engineering/configuration diagnostics in the UI. */
export const apiErrorMessage = (error: any, fallback = '操作失敗'): string => {
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
