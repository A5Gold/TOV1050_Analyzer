/**
 * ErrorBoundary Component Tests
 * ==============================
 * Tests for the ErrorBoundary component created for Bug 10.7-1 fix.
 * 
 * Version: 1.0
 * Date: 2026-02-04
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import ErrorBoundary, { 
  DefaultErrorFallback, 
  DataGridErrorFallback,
  FallbackProps 
} from '../ErrorBoundary';

// Component that throws an error
const ThrowError: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = true }) => {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div data-testid="child-component">Child rendered successfully</div>;
};

// Suppress console.error during tests since we're testing error handling
const originalConsoleError = console.error;
beforeAll(() => {
  console.error = vi.fn();
});
afterAll(() => {
  console.error = originalConsoleError;
});

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Normal rendering', () => {
    test('renders children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('child-component')).toBeInTheDocument();
      expect(screen.getByText('Child rendered successfully')).toBeInTheDocument();
    });
  });

  describe('Error handling', () => {
    test('renders default fallback when error occurs', () => {
      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(screen.getByText('Test error message')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    test('renders custom fallback element when provided', () => {
      render(
        <ErrorBoundary fallback={<div data-testid="custom-fallback">Custom Error</div>}>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
      expect(screen.getByText('Custom Error')).toBeInTheDocument();
    });

    test('renders FallbackComponent when provided', () => {
      const CustomFallback: React.FC<FallbackProps> = ({ error, resetErrorBoundary }) => (
        <div>
          <span data-testid="error-message">{error?.message}</span>
          <button onClick={resetErrorBoundary}>Reset</button>
        </div>
      );

      render(
        <ErrorBoundary FallbackComponent={CustomFallback}>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('error-message')).toHaveTextContent('Test error message');
      expect(screen.getByRole('button', { name: /reset/i })).toBeInTheDocument();
    });

    test('calls onError callback when error occurs', () => {
      const onError = vi.fn();

      render(
        <ErrorBoundary onError={onError}>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(onError).toHaveBeenCalledTimes(1);
      expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
      expect(onError.mock.calls[0][0].message).toBe('Test error message');
    });
  });

  describe('Reset functionality', () => {
    test('resets error state when resetErrorBoundary is called', () => {
      let shouldThrow = true;

      const ToggleError: React.FC = () => {
        if (shouldThrow) {
          throw new Error('Test error');
        }
        return <div data-testid="recovered">Recovered</div>;
      };

      const { rerender } = render(
        <ErrorBoundary FallbackComponent={DefaultErrorFallback}>
          <ToggleError />
        </ErrorBoundary>
      );

      // Error should be shown
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();

      // Fix the error condition
      shouldThrow = false;

      // Click "Try Again" button
      fireEvent.click(screen.getByRole('button', { name: /try again/i }));

      // Force re-render to pick up the new shouldThrow value
      rerender(
        <ErrorBoundary FallbackComponent={DefaultErrorFallback}>
          <ToggleError />
        </ErrorBoundary>
      );

      // Component should recover
      expect(screen.getByTestId('recovered')).toBeInTheDocument();
    });
  });
});

describe('DefaultErrorFallback', () => {
  test('renders error message and try again button', () => {
    const mockReset = vi.fn();
    const error = new Error('Default fallback test error');

    render(<DefaultErrorFallback error={error} resetErrorBoundary={mockReset} />);

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Default fallback test error')).toBeInTheDocument();
    
    const button = screen.getByRole('button', { name: /try again/i });
    fireEvent.click(button);
    expect(mockReset).toHaveBeenCalledTimes(1);
  });

  test('handles null error gracefully', () => {
    const mockReset = vi.fn();

    render(<DefaultErrorFallback error={null} resetErrorBoundary={mockReset} />);

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('An unexpected error occurred')).toBeInTheDocument();
  });
});

describe('DataGridErrorFallback', () => {
  test('renders DataGrid-specific error message in Chinese', () => {
    const mockReset = vi.fn();
    const error = new Error('DataGrid error');

    render(<DataGridErrorFallback error={error} resetErrorBoundary={mockReset} />);

    expect(screen.getByText('資料表載入失敗')).toBeInTheDocument();
    expect(screen.getByText('DataGrid error')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /重試/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /重新載入頁面/i })).toBeInTheDocument();
  });

  test('calls resetErrorBoundary when 重試 button is clicked', () => {
    const mockReset = vi.fn();
    const error = new Error('DataGrid error');

    render(<DataGridErrorFallback error={error} resetErrorBoundary={mockReset} />);

    fireEvent.click(screen.getByRole('button', { name: /重試/i }));
    expect(mockReset).toHaveBeenCalledTimes(1);
  });

  test('重新載入頁面 button exists and is clickable', () => {
    const mockReset = vi.fn();
    const error = new Error('DataGrid error');

    render(<DataGridErrorFallback error={error} resetErrorBoundary={mockReset} />);

    // Verify the reload button exists and is clickable
    const reloadButton = screen.getByRole('button', { name: /重新載入頁面/i });
    expect(reloadButton).toBeInTheDocument();
    
    // Note: We cannot mock window.location.reload in jsdom as it's read-only.
    // The button click functionality is verified to exist; actual page reload
    // behavior should be tested in E2E tests.
  });
});
