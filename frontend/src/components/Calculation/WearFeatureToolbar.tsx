import React from 'react';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { Box, Button, Tab, Tabs } from '@mui/material';

export type WearFeatureTab = 'analysis' | 'records' | 'dashboard' | 'projection' | 'remaining-life';

interface WearFeatureToolbarProps {
  activeTab: WearFeatureTab;
  onTabChange: (tab: WearFeatureTab) => void;
  onOpenAlgorithm: () => void;
}

const WearFeatureToolbar: React.FC<WearFeatureToolbarProps> = ({ activeTab, onTabChange, onOpenAlgorithm }) => (
  <Box
    component="nav"
    aria-label="Wear workspace views"
    sx={{
      mt: 3,
      display: 'flex',
      alignItems: 'center',
      gap: 1,
      borderTop: '1px solid',
      borderColor: 'divider',
      minWidth: 0,
    }}
  >
    <Tabs
      value={activeTab}
      onChange={(_, value: WearFeatureTab) => onTabChange(value)}
      variant="scrollable"
      scrollButtons="auto"
      allowScrollButtonsMobile
      sx={{ flexGrow: 1, minWidth: 0 }}
    >
      <Tab value="analysis" label="Analysis" />
      <Tab value="records" label="Wire Wear Records" />
      <Tab value="dashboard" label="Dashboard" />
      <Tab value="projection" label="Projection" />
      <Tab value="remaining-life" label="Remaining Life" />
    </Tabs>
    <Button size="small" variant="text" startIcon={<InfoOutlinedIcon />} onClick={onOpenAlgorithm} sx={{ mr: 1, flexShrink: 0, whiteSpace: 'nowrap' }}>
      Method guide
    </Button>
  </Box>
);

export default WearFeatureToolbar;
