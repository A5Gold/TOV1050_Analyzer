import React, { useState } from 'react';
import { Box, Tab, Tabs } from '@mui/material';

import type { DiagnosticsResponse } from '../../types/api';
import { developerNavItems, operatorNavItems } from './aboutGuideContent';
import DeveloperReference from './DeveloperReference';
import GuideSectionNav from './GuideSectionNav';
import OperatorGuide from './OperatorGuide';

interface AboutGuideTabsProps {
  diagnostics: DiagnosticsResponse | null;
  diagnosticsLoading: boolean;
  diagnosticsError: string;
}

type AboutGuideTab = 'operator' | 'developer';

const AboutGuideTabs: React.FC<AboutGuideTabsProps> = ({
  diagnostics,
  diagnosticsLoading,
  diagnosticsError,
}) => {
  const [activeTab, setActiveTab] = useState<AboutGuideTab>('operator');

  return (
    <Box>
      <Tabs
        value={activeTab}
        onChange={(_, value: AboutGuideTab) => setActiveTab(value)}
        variant="scrollable"
        scrollButtons="auto"
        allowScrollButtonsMobile
        aria-label="About guide views"
        sx={{ borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab id="about-tab-operator" value="operator" label="操作指南" aria-controls="about-panel-operator" />
        <Tab id="about-tab-developer" value="developer" label="開發者參考" aria-controls="about-panel-developer" />
      </Tabs>

      {activeTab === 'operator' ? (
        <Box
          id="about-panel-operator"
          role="tabpanel"
          aria-labelledby="about-tab-operator"
          sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: { xs: 2, md: 3 }, pt: 2 }}
        >
          <GuideSectionNav items={operatorNavItems} label="操作指南章節" />
          <Box sx={{ flex: 1, minWidth: 0 }}><OperatorGuide /></Box>
        </Box>
      ) : (
        <Box
          id="about-panel-developer"
          role="tabpanel"
          aria-labelledby="about-tab-developer"
          sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: { xs: 2, md: 3 }, pt: 2 }}
        >
          <GuideSectionNav items={developerNavItems} label="開發者參考章節" />
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <DeveloperReference
              diagnostics={diagnostics}
              diagnosticsLoading={diagnosticsLoading}
              diagnosticsError={diagnosticsError}
            />
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default AboutGuideTabs;
