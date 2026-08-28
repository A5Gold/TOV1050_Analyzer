/**
 * Date Formatter Utility Tests
 * ============================
 * TDD Phase A - Bug 1.5: Date filter format error
 * 
 * Problem: HTML date input requires YYYY-MM-DD format, 
 *          but DB stores task_run_date as YYYYMMDD.
 *          Need conversion functions between formats.
 */

import { describe, it, expect } from 'vitest';
import {
  formatDateForHtmlInput,
  formatDateToCompact,
  formatDateDisplay,
  formatDateStrForApi,
  isValidDate,
  parseDateStr,
} from '../dateFormatter';

// ============================================================
// NEW: Bug 1.5 - formatDateForHtmlInput (YYYYMMDD → YYYY-MM-DD)
// Used for: Setting HTML <input type="date"> value from DB format
// ============================================================
describe('formatDateForHtmlInput', () => {
  it('should convert YYYYMMDD to YYYY-MM-DD', () => {
    expect(formatDateForHtmlInput('20260201')).toBe('2026-02-01');
  });

  it('should pass through YYYY-MM-DD unchanged', () => {
    expect(formatDateForHtmlInput('2026-02-01')).toBe('2026-02-01');
  });

  it('should return empty string for null/undefined', () => {
    expect(formatDateForHtmlInput(null)).toBe('');
    expect(formatDateForHtmlInput(undefined)).toBe('');
    expect(formatDateForHtmlInput('')).toBe('');
  });

  it('should handle YYYY/MM/DD format', () => {
    expect(formatDateForHtmlInput('2026/02/01')).toBe('2026-02-01');
  });

  it('should return empty string for invalid date', () => {
    expect(formatDateForHtmlInput('invalid')).toBe('');
    expect(formatDateForHtmlInput('abc')).toBe('');
  });
});

// ============================================================
// NEW: Bug 1.5 - formatDateToCompact (YYYY-MM-DD → YYYYMMDD)
// Used for: Sending date filter value to API in DB-compatible format
// ============================================================
describe('formatDateToCompact', () => {
  it('should convert YYYY-MM-DD to YYYYMMDD', () => {
    expect(formatDateToCompact('2026-02-01')).toBe('20260201');
  });

  it('should pass through YYYYMMDD unchanged', () => {
    expect(formatDateToCompact('20260201')).toBe('20260201');
  });

  it('should return undefined for null/undefined', () => {
    expect(formatDateToCompact(null)).toBeUndefined();
    expect(formatDateToCompact(undefined)).toBeUndefined();
    expect(formatDateToCompact('')).toBeUndefined();
  });

  it('should handle YYYY/MM/DD format', () => {
    expect(formatDateToCompact('2026/02/01')).toBe('20260201');
  });

  it('should return undefined for invalid date', () => {
    expect(formatDateToCompact('invalid')).toBeUndefined();
  });
});

// ============================================================
// EXISTING: Verify existing functions still work (regression)
// ============================================================
describe('formatDateDisplay (existing)', () => {
  it('should format YYYYMMDD to YYYY/MM/DD', () => {
    expect(formatDateDisplay('20260201')).toBe('2026/02/01');
  });

  it('should return - for null/undefined', () => {
    expect(formatDateDisplay(null)).toBe('-');
    expect(formatDateDisplay(undefined)).toBe('-');
  });
});

describe('formatDateStrForApi (existing)', () => {
  it('should convert YYYY-MM-DD to YYYYMMDD', () => {
    expect(formatDateStrForApi('2026-02-01')).toBe('20260201');
  });

  it('should convert YYYY/MM/DD to YYYYMMDD', () => {
    expect(formatDateStrForApi('2026/02/01')).toBe('20260201');
  });

  it('should return undefined for null', () => {
    expect(formatDateStrForApi(null)).toBeUndefined();
  });
});

describe('isValidDate (existing)', () => {
  it('should validate YYYYMMDD', () => {
    expect(isValidDate('20260201')).toBe(true);
  });

  it('should validate YYYY-MM-DD', () => {
    expect(isValidDate('2026-02-01')).toBe(true);
  });

  it('should reject invalid', () => {
    expect(isValidDate(null)).toBe(false);
    expect(isValidDate('abc')).toBe(false);
  });
});

describe('parseDateStr (existing)', () => {
  it('should parse YYYYMMDD', () => {
    const date = parseDateStr('20260201');
    expect(date).not.toBeNull();
    expect(date!.getFullYear()).toBe(2026);
    expect(date!.getMonth()).toBe(1); // 0-indexed
    expect(date!.getDate()).toBe(1);
  });

  it('should return null for invalid', () => {
    expect(parseDateStr(null)).toBeNull();
    expect(parseDateStr('abc')).toBeNull();
  });
});
