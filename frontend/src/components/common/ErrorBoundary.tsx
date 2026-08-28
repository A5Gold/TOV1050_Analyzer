/**
 * Error Boundary Component
 * ========================
 * A React Error Boundary that catches JavaScript errors in child component tree
 * and displays a fallback UI instead of crashing the entire app.
 * 
 * Usage:
 * <ErrorBoundary fallback={<CustomFallback />}>
 *   <ChildComponent />
 * </ErrorBoundary>
 * 
 * Or with render prop:
 * <ErrorBoundary FallbackComponent={MyFallbackComponent}>
 *   <ChildComponent />
 * </ErrorBoundary>
 * 
 * Version: 1.0
 * Date: 2026-02-04
 * Created for: Bug 10.7-1 fix
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import RefreshIcon from '@mui/icons-material/Refresh';

// =============================================================================
// TYPES
// =============================================================================

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Simple fallback element to render on error */
  fallback?: ReactNode;
  /** Fallback component that receives error info */
  FallbackComponent?: React.ComponentType<FallbackProps>;
  /** Callback when error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Reset keys - when these change, the error boundary resets */
  resetKeys?: unknown[];
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export interface FallbackProps {
  error: Error | null;
  resetErrorBoundary: () => void;
}

// =============================================================================
// DEFAULT FALLBACK COMPONENT
// =============================================================================

export const DefaultErrorFallback: React.FC<FallbackProps> = ({ error, resetErrorBoundary }) => (
  <Paper sx={{ p: 4, textAlign: 'center', bgcolor: 'error.light', color: 'error.contrastText' }}>
    <ErrorOutlineIcon sx={{ fontSize: 48, mb: 2 }} />
    <Typography variant="h6" gutterBottom>
      Something went wrong
    </Typography>
    <Typography variant="body2" sx={{ mb: 2, opacity: 0.9 }}>
      {error?.message || 'An unexpected error occurred'}
    </Typography>
    <Button
      variant="contained"
      color="inherit"
      startIcon={<RefreshIcon />}
      onClick={resetErrorBoundary}
      sx={{ color: 'error.main' }}
    >
      Try Again
    </Button>
  </Paper>
);

/**
 * DataGrid-specific error fallback with reload option
 */
export const DataGridErrorFallback: React.FC<FallbackProps> = ({ error, resetErrorBoundary }) => (
  <Box sx={{ p: 4, textAlign: 'center' }}>
    <ErrorOutlineIcon sx={{ fontSize: 48, mb: 2, color: 'error.main' }} />
    <Typography variant="h6" color="error" gutterBottom>
      資料表載入失敗
    </Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
      {error?.message || 'An unexpected error occurred while loading the data grid'}
    </Typography>
    <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
      <Button
        variant="outlined"
        color="primary"
        startIcon={<RefreshIcon />}
        onClick={resetErrorBoundary}
      >
        重試
      </Button>
      <Button
        variant="contained"
        color="primary"
        onClick={() => window.location.reload()}
      >
        重新載入頁面
      </Button>
    </Box>
    {/* Debug info in development */}
    {process.env.NODE_ENV === 'development' && error && (
      <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1, textAlign: 'left' }}>
        <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {error.stack}
        </Typography>
      </Box>
    )}
  </Box>
);

// =============================================================================
// ERROR BOUNDARY CLASS COMPONENT
// =============================================================================

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render shows the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('[ErrorBoundary] Caught error:', error);
      console.error('[ErrorBoundary] Component stack:', errorInfo.componentStack);
    }
    
    // Call optional error callback
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps): void {
    // Reset error state when resetKeys change
    if (this.state.hasError && this.props.resetKeys) {
      const prevResetKeys = prevProps.resetKeys || [];
      const currentResetKeys = this.props.resetKeys;
      
      const hasResetKeyChanged = currentResetKeys.some(
        (key, index) => key !== prevResetKeys[index]
      );
      
      if (hasResetKeyChanged) {
        this.resetErrorBoundary();
      }
    }
  }

  resetErrorBoundary = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    const { hasError, error } = this.state;
    const { children, fallback, FallbackComponent } = this.props;

    if (hasError) {
      // Use FallbackComponent if provided
      if (FallbackComponent) {
        return (
          <FallbackComponent 
            error={error} 
            resetErrorBoundary={this.resetErrorBoundary} 
          />
        );
      }
      
      // Use simple fallback if provided
      if (fallback) {
        return fallback;
      }
      
      // Use default fallback
      return (
        <DefaultErrorFallback 
          error={error} 
          resetErrorBoundary={this.resetErrorBoundary} 
        />
      );
    }

    return children;
  }
}

export default ErrorBoundary;
