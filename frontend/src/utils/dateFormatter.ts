/**
 * Date Formatter Utility
 * ======================
 * Provides consistent date formatting across the application.
 * All dates are displayed in Hong Kong timezone (UTC+8).
 * 
 * Date Format Rules:
 * - Date fields: YYYY/MM/DD
 * - Timestamp fields: YYYY/MM/DD HH:MM:SS
 * 
 * Version: 1.0
 * Date: 2026-02-01
 */

import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

// Extend dayjs with timezone support
dayjs.extend(utc);
dayjs.extend(timezone);

// Hong Kong timezone constant
const HK_TIMEZONE = 'Asia/Hong_Kong';

/**
 * Format ISO date string to YYYY/MM/DD format (Hong Kong timezone)
 * @param isoDate - ISO date string or YYYYMMDD string
 * @returns Formatted date string or '-' if invalid
 */
export function formatDateDisplay(isoDate: string | null | undefined): string {
  if (!isoDate) return '-';
  
  // Handle YYYYMMDD format (8 characters, no separators)
  if (isoDate.length === 8 && !isoDate.includes('-') && !isoDate.includes('/')) {
    const year = isoDate.slice(0, 4);
    const month = isoDate.slice(4, 6);
    const day = isoDate.slice(6, 8);
    return `${year}/${month}/${day}`;
  }
  
  // Handle ISO format or other date strings
  const parsed = dayjs(isoDate);
  if (!parsed.isValid()) return '-';
  
  return parsed.tz(HK_TIMEZONE).format('YYYY/MM/DD');
}

/**
 * Format ISO datetime string to YYYY/MM/DD HH:MM:SS format (Hong Kong timezone)
 * @param isoDateTime - ISO datetime string
 * @returns Formatted datetime string or '-' if invalid
 */
export function formatDateTimeDisplay(isoDateTime: string | null | undefined): string {
  if (!isoDateTime) return '-';
  
  // Bug fix: Treat SQL timestamp (no offset, typically YYYY-MM-DD HH:mm:ss) as UTC
  let parsed;
  if (isoDateTime.includes(' ') && !isoDateTime.includes('Z') && !isoDateTime.includes('+')) {
      parsed = dayjs.utc(isoDateTime);
  } else {
      parsed = dayjs(isoDateTime);
  }

  if (!parsed.isValid()) return '-';
  
  return parsed.tz(HK_TIMEZONE).format('YYYY/MM/DD HH:mm:ss');
}

/**
 * Convert user input date (YYYY/MM/DD or YYYY-MM-DD) to ISO format for API
 * @param displayDate - Date string in YYYY/MM/DD or YYYY-MM-DD format
 * @returns ISO date string or undefined if invalid
 */
export function formatDateForApi(displayDate: string | null | undefined): string | undefined {
  if (!displayDate) return undefined;
  
  // Normalize separators
  const normalized = displayDate.replace(/\//g, '-');
  const parsed = dayjs(normalized);
  
  if (!parsed.isValid()) return undefined;
  
  return parsed.toISOString();
}

/**
 * Convert user input date to YYYYMMDD format for date_str field
 * @param displayDate - Date string in YYYY/MM/DD or YYYY-MM-DD format
 * @returns YYYYMMDD string or undefined if invalid
 */
export function formatDateStrForApi(displayDate: string | null | undefined): string | undefined {
  if (!displayDate) return undefined;
  
  // Normalize separators
  const normalized = displayDate.replace(/\//g, '-');
  const parsed = dayjs(normalized);
  
  if (!parsed.isValid()) return undefined;
  
  return parsed.format('YYYYMMDD');
}

/**
 * Get current date as ISO string in Hong Kong timezone
 * @returns Current datetime as ISO string
 */
export function getCurrentDateISO(): string {
  return dayjs().tz(HK_TIMEZONE).toISOString();
}

/**
 * Get current date as YYYYMMDD string
 * @returns Current date as YYYYMMDD string
 */
export function getCurrentDateStr(): string {
  return dayjs().tz(HK_TIMEZONE).format('YYYYMMDD');
}

/**
 * Get current date as YYYY/MM/DD string
 * @returns Current date as YYYY/MM/DD string
 */
export function getCurrentDateDisplay(): string {
  return dayjs().tz(HK_TIMEZONE).format('YYYY/MM/DD');
}

/**
 * Check if a date string is valid
 * @param dateStr - Date string to validate
 * @returns True if valid date
 */
export function isValidDate(dateStr: string | null | undefined): boolean {
  if (!dateStr) return false;
  const normalized = dateStr.replace(/\//g, '-');
  return dayjs(normalized).isValid();
}

/**
 * Parse YYYYMMDD to Date object
 * @param dateStr - YYYYMMDD format string
 * @returns Date object or null if invalid
 */
export function parseDateStr(dateStr: string | null | undefined): Date | null {
  if (!dateStr || dateStr.length !== 8) return null;
  
  const year = parseInt(dateStr.slice(0, 4), 10);
  const month = parseInt(dateStr.slice(4, 6), 10) - 1; // 0-indexed
  const day = parseInt(dateStr.slice(6, 8), 10);
  
  const date = new Date(year, month, day);
  if (isNaN(date.getTime())) return null;
  
  return date;
}

/**
 * Convert date to YYYY-MM-DD format for HTML <input type="date"> value
 * Handles YYYYMMDD, YYYY/MM/DD, and YYYY-MM-DD input formats
 * @param dateStr - Date string in various formats
 * @returns YYYY-MM-DD string or empty string if invalid
 */
export function formatDateForHtmlInput(dateStr: string | null | undefined): string {
  if (!dateStr) return '';

  // Already in YYYY-MM-DD format
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return dateStr;

  // YYYYMMDD format (8 digits, no separators)
  if (/^\d{8}$/.test(dateStr)) {
    const year = dateStr.slice(0, 4);
    const month = dateStr.slice(4, 6);
    const day = dateStr.slice(6, 8);
    return `${year}-${month}-${day}`;
  }

  // YYYY/MM/DD format
  if (/^\d{4}\/\d{2}\/\d{2}$/.test(dateStr)) {
    return dateStr.replace(/\//g, '-');
  }

  // Try parsing with dayjs as fallback
  const parsed = dayjs(dateStr);
  if (!parsed.isValid()) return '';

  return parsed.format('YYYY-MM-DD');
}

/**
 * Convert date to YYYYMMDD compact format for API/DB queries
 * Handles YYYY-MM-DD, YYYY/MM/DD, and YYYYMMDD input formats
 * @param dateStr - Date string in various formats
 * @returns YYYYMMDD string or undefined if invalid
 */
export function formatDateToCompact(dateStr: string | null | undefined): string | undefined {
  if (!dateStr) return undefined;

  // Already in YYYYMMDD format
  if (/^\d{8}$/.test(dateStr)) return dateStr;

  // YYYY-MM-DD or YYYY/MM/DD format
  const normalized = dateStr.replace(/[/-]/g, '');
  if (/^\d{8}$/.test(normalized)) return normalized;

  // Try parsing with dayjs as fallback
  const parsed = dayjs(dateStr);
  if (!parsed.isValid()) return undefined;

  return parsed.format('YYYYMMDD');
}

export default {
  formatDateDisplay,
  formatDateTimeDisplay,
  formatDateForApi,
  formatDateStrForApi,
  formatDateForHtmlInput,
  formatDateToCompact,
  getCurrentDateISO,
  getCurrentDateStr,
  getCurrentDateDisplay,
  isValidDate,
  parseDateStr,
};
