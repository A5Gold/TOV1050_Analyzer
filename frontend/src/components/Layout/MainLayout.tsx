import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  CssBaseline,
  IconButton,
  ThemeProvider,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material';
import AddChartOutlinedIcon from '@mui/icons-material/AddChartOutlined';
import AnalyticsOutlinedIcon from '@mui/icons-material/AnalyticsOutlined';
import CloseIcon from '@mui/icons-material/Close';
import CompareArrowsOutlinedIcon from '@mui/icons-material/CompareArrowsOutlined';
import DashboardCustomizeOutlinedIcon from '@mui/icons-material/DashboardCustomizeOutlined';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import DifferenceOutlinedIcon from '@mui/icons-material/DifferenceOutlined';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import MenuIcon from '@mui/icons-material/Menu';
import RouteOutlinedIcon from '@mui/icons-material/RouteOutlined';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import StorageOutlinedIcon from '@mui/icons-material/StorageOutlined';
import { createAppTheme } from '../../theme/AppTheme';
import { API_BASE_URL } from '../../api/client';

export type ViewType = 'generator' | 'compare' | 'version-difference' | 'database' | 'metadata' | 'wear' | 'trend' | 'calculation' | 'about';

interface MainLayoutProps {
  children: React.ReactNode;
  activeView: ViewType;
  onViewChange: (view: ViewType) => void;
}

const navItems: Array<{ id: ViewType; label: string; fullLabel: string; icon: React.ReactElement }> = [
  { id: 'about', label: 'About', fullLabel: 'About', icon: <InfoOutlinedIcon /> },
  { id: 'generator', label: 'Generate', fullLabel: 'Exception Generator', icon: <AddChartOutlinedIcon /> },
  { id: 'compare', label: 'History', fullLabel: 'History Compare', icon: <CompareArrowsOutlinedIcon /> },
  { id: 'version-difference', label: 'Version Difference', fullLabel: 'Version Difference', icon: <DifferenceOutlinedIcon /> },
  { id: 'database', label: 'Records', fullLabel: 'Database Records', icon: <StorageOutlinedIcon /> },
  { id: 'wear', label: 'Wear Calculator', fullLabel: 'Wear Calculator', icon: <DescriptionOutlinedIcon /> },
  { id: 'calculation', label: 'Stagger', fullLabel: 'Stagger Calculation', icon: <RouteOutlinedIcon /> },
  { id: 'trend', label: 'Trends', fullLabel: 'Trend Analyzer', icon: <AnalyticsOutlinedIcon /> },
  { id: 'metadata', label: 'Settings', fullLabel: 'Metadata Editor', icon: <SettingsOutlinedIcon /> },
];

const MainLayout: React.FC<MainLayoutProps> = ({ children, activeView, onViewChange }) => {
  const [navOpen, setNavOpen] = useState(false);
  const [serverReady, setServerReady] = useState<boolean | null>(null);
  const isCompact = useMediaQuery('(max-width:599.95px)');
  const theme = useMemo(() => createAppTheme('light'), []);

  useEffect(() => {
    let activeController: AbortController | undefined;
    let retryTimer: number | undefined;
    let stopped = false;
    const requestTimeoutMs = 5000;
    const retryIntervalMs = 2000;
    const startupGracePeriodMs = 90000;
    const startedAt = Date.now();
    const checkHealth = async () => {
      const controller = new AbortController();
      activeController = controller;
      const timeoutId = window.setTimeout(() => controller.abort(), requestTimeoutMs);
      try {
        const response = await fetch(`${API_BASE_URL}/health`, { signal: controller.signal });
        if (!stopped && response.ok) {
          setServerReady(true);
          return;
        }
      } catch {
        // Keep showing Connecting while the packaged backend is still booting.
      } finally {
        window.clearTimeout(timeoutId);
      }

      if (!stopped) {
        setServerReady(Date.now() - startedAt >= startupGracePeriodMs ? false : null);
        retryTimer = window.setTimeout(checkHealth, retryIntervalMs);
      }
    };

    checkHealth();
    return () => {
      stopped = true;
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
      activeController?.abort();
    };
  }, []);

  useEffect(() => {
    if (!isCompact) setNavOpen(false);
  }, [isCompact]);

  const handleViewChange = (view: ViewType) => {
    onViewChange(view);
    if (isCompact) setNavOpen(false);
  };

  const statusLabel = serverReady === null ? 'Connecting' : serverReady ? 'Ready' : 'Offline';
  const statusColor = serverReady === null ? '#d69e2e' : serverReady ? '#2f9e72' : '#d14343';

  const navigation = (
    <Box
      component="aside"
      sx={{
        position: { xs: 'fixed', sm: 'sticky' },
        inset: { xs: '0 auto 0 0', sm: 'auto' },
        top: { sm: 0 },
        zIndex: (currentTheme) => currentTheme.zIndex.drawer,
        width: { xs: 236, sm: 116 },
        height: '100dvh',
        display: { xs: navOpen ? 'flex' : 'none', sm: 'flex' },
        flexDirection: 'column',
        alignItems: 'center',
        bgcolor: '#ffffff',
        borderRight: '1px solid #e2e7ef',
        boxShadow: { xs: '4px 0 8px rgba(31, 48, 73, 0.12)', sm: 'none' },
      }}
    >
      <Box sx={{ width: '100%', height: 82, px: { xs: 2, sm: 0 }, display: 'flex', alignItems: 'center', justifyContent: { xs: 'space-between', sm: 'center' }, borderBottom: '1px solid #eef1f5' }}>
        <Tooltip title="TOV Data Analyzer" placement="right">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box aria-hidden="true" sx={{ width: 38, height: 38, display: 'grid', placeItems: 'center', borderRadius: 1.5, bgcolor: 'primary.main', color: '#ffffff' }}>
              <DashboardCustomizeOutlinedIcon sx={{ fontSize: 22 }} />
            </Box>
            <Typography sx={{ display: { xs: 'block', sm: 'none' }, fontWeight: 750, color: '#233147' }}>TOV Analyzer</Typography>
          </Box>
        </Tooltip>
        <IconButton aria-label="close drawer" onClick={() => setNavOpen(false)} sx={{ display: { xs: 'inline-flex', sm: 'none' } }}>
          <CloseIcon />
        </IconButton>
      </Box>

      <Box component="nav" aria-label="Main navigation" sx={{ width: '100%', flex: 1, py: 1.5, px: { xs: 1.25, sm: 1 }, overflowY: 'auto' }}>
        {navItems.map((item) => {
          const isActive = activeView === item.id;
          return (
            <Tooltip key={item.id} title={item.fullLabel} placement="right" enterDelay={500}>
              <Box
                component="button"
                type="button"
                aria-current={isActive ? 'page' : undefined}
                onClick={() => handleViewChange(item.id)}
                sx={{
                  width: '100%', minHeight: { xs: 52, sm: 57 }, mb: 0.5, px: { xs: 1.5, sm: 0.75 }, display: 'flex', flexDirection: { xs: 'row', sm: 'column' }, alignItems: 'center', justifyContent: { xs: 'flex-start', sm: 'center' }, gap: { xs: 1.5, sm: 0.35 }, border: 0, borderRadius: 1.5,
                  bgcolor: isActive ? '#eaf1ff' : 'transparent', color: isActive ? 'primary.main' : '#647083', cursor: 'pointer', font: 'inherit', transition: 'background-color 160ms ease-out, color 160ms ease-out',
                  '& svg': { fontSize: { xs: 22, sm: 21 } },
                  '&:hover': { bgcolor: isActive ? '#eaf1ff' : '#f3f5f8', color: isActive ? 'primary.main' : '#28364a' },
                  '&:focus-visible': { outline: '3px solid rgba(43, 99, 201, 0.26)', outlineOffset: 1 },
                }}
              >
                {item.icon}
                <Typography component="span" sx={{ fontSize: { xs: '0.84rem', sm: '0.68rem' }, lineHeight: 1.15, fontWeight: isActive ? 700 : 600, color: 'inherit', letterSpacing: 0, textAlign: 'center' }}>
                  {isCompact ? item.fullLabel : item.label}
                </Typography>
              </Box>
            </Tooltip>
          );
        })}
      </Box>
    </Box>
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100dvh', display: { sm: 'grid' }, gridTemplateColumns: { sm: '116px minmax(0, 1fr)' }, bgcolor: 'background.default' }}>
        {isCompact && navOpen && <Box aria-hidden="true" onClick={() => setNavOpen(false)} sx={{ position: 'fixed', inset: 0, zIndex: (currentTheme) => currentTheme.zIndex.drawer - 1, bgcolor: 'rgba(21, 31, 46, 0.32)' }} />}
        {navigation}
        <Box sx={{ minWidth: 0, minHeight: '100dvh', display: 'flex', flexDirection: 'column' }}>
          <Box component="header" sx={{ height: 82, px: { xs: 1.5, sm: 3 }, display: 'grid', gridTemplateColumns: { xs: '48px minmax(0, 1fr) auto', sm: '1fr auto 1fr' }, alignItems: 'center', bgcolor: '#ffffff', borderBottom: '1px solid #e2e7ef' }}>
            <IconButton color="inherit" aria-label="open drawer" onClick={() => setNavOpen(true)} sx={{ display: { xs: 'inline-flex', sm: 'none' }, justifySelf: 'start' }}><MenuIcon /></IconButton>
            <Box sx={{ gridColumn: { sm: 2 }, textAlign: 'center', minWidth: 0 }}>
              <Typography component="div" noWrap sx={{ fontSize: { xs: '0.82rem', sm: '0.93rem' }, fontWeight: 800, color: '#243247', letterSpacing: 0 }}>TOV DATA ANALYZER</Typography>
              <Typography component="div" noWrap sx={{ mt: 0.25, fontSize: '0.71rem', color: '#7a8596', letterSpacing: 0 }}>File intelligence workspace</Typography>
            </Box>
            <Box sx={{ gridColumn: { sm: 3 }, justifySelf: 'end', display: 'flex', alignItems: 'center', gap: 0.75, minWidth: 0 }}>
              <Box aria-hidden="true" sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: statusColor, boxShadow: `0 0 0 3px ${statusColor}1f` }} />
              <Typography sx={{ display: { xs: 'none', sm: 'block' }, fontSize: '0.75rem', fontWeight: 700, color: '#667286', letterSpacing: 0 }}>{statusLabel}</Typography>
            </Box>
          </Box>
          <Box component="main" sx={{ flex: 1, minWidth: 0, px: { xs: 2, sm: 4, lg: 6 }, py: { xs: 3, sm: 5 }, overflowX: 'hidden' }}>
            <Box sx={{ width: '100%' }}>{children}</Box>
          </Box>
          <Box component="footer" sx={{ minHeight: 44, px: 2, py: 1.25, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.75, color: '#667286', bgcolor: '#ffffff', borderTop: '1px solid #e7ebf1' }}>
            <RouteOutlinedIcon sx={{ fontSize: 15, color: 'primary.main' }} />
            <Typography sx={{ fontSize: '0.72rem', letterSpacing: 0 }}>Secure processing workspace • TOV1050 CSV input • Version 2.0</Typography>
          </Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
};

export default MainLayout;
