import { describe, it, expect } from 'vitest';
import { shouldSuppressApiErrorLog } from '../client';

describe('shouldSuppressApiErrorLog', () => {
  it('suppresses expected wire wear duplicate check conflicts', () => {
    expect(shouldSuppressApiErrorLog({
      response: { status: 409 },
      config: {
        method: 'post',
        url: '/calculation/wear-records',
        params: { check_only: true, overwrite: false },
      },
    })).toBe(true);
  });

  it('keeps logging unexpected API errors', () => {
    expect(shouldSuppressApiErrorLog({
      response: { status: 500 },
      config: {
        method: 'post',
        url: '/calculation/wear-records',
        params: { check_only: true },
      },
    })).toBe(false);
  });
});
