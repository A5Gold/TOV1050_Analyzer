import { createTheme, type ThemeOptions } from '@mui/material/styles';

// Shared safety-level colors used by exception tables, row styling, and dialogs.
export const safetyColors = {
  l1: '#c74444',
  l2: '#b8791b',
  l3: '#2b63c9',
} as const;

export const createAppTheme = (mode: 'light' | 'dark' = 'light') => {
  const options: ThemeOptions = {
    palette: {
      mode,
      primary: { main: '#2b63c9', dark: '#1f4fa6', light: '#eaf1ff', contrastText: '#ffffff' },
      secondary: { main: '#256f62' }, success: { main: '#2f8a67' }, warning: { main: '#b8791b' }, error: { main: '#c74444' },
      background: { default: '#f6f8fb', paper: '#ffffff' }, text: { primary: '#263348', secondary: '#687589' }, divider: '#e2e7ef',
    },
    typography: {
      fontFamily: 'Inter, "Noto Sans", "Segoe UI", sans-serif',
      h4: { fontWeight: 750, fontSize: '1.72rem', lineHeight: 1.22, letterSpacing: 0 }, h5: { fontWeight: 750, fontSize: '1.28rem', lineHeight: 1.3, letterSpacing: 0 }, h6: { fontWeight: 700, fontSize: '1rem', lineHeight: 1.4, letterSpacing: 0 },
      button: { fontWeight: 700, letterSpacing: 0, textTransform: 'none' }, body1: { letterSpacing: 0 }, body2: { letterSpacing: 0 },
    },
    shape: { borderRadius: 8 },
    components: {
      MuiCssBaseline: { styleOverrides: { html: { backgroundColor: '#f6f8fb' }, body: { minWidth: 320, backgroundColor: '#f6f8fb' }, '#root': { minHeight: '100dvh' }, '*': { boxSizing: 'border-box' }, '@media (prefers-reduced-motion: reduce)': { '*, *::before, *::after': { animationDuration: '0.01ms !important', animationIterationCount: '1 !important', transitionDuration: '0.01ms !important', scrollBehavior: 'auto !important' } } } },
      MuiPaper: { defaultProps: { elevation: 0 }, styleOverrides: { root: { backgroundImage: 'none' } } },
      MuiButton: { defaultProps: { disableElevation: true }, styleOverrides: { root: { minHeight: 40, borderRadius: 6 }, containedPrimary: { '&:hover': { backgroundColor: '#1f4fa6' } } } },
      MuiIconButton: { styleOverrides: { root: { borderRadius: 6 } } },
      MuiOutlinedInput: { styleOverrides: { root: { borderRadius: 6, backgroundColor: '#ffffff' } } },
      MuiTab: { styleOverrides: { root: { minHeight: 44, textTransform: 'none', letterSpacing: 0, fontWeight: 650 } } },
    },
  };
  return createTheme(options);
};
