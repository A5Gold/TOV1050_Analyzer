import React, { useEffect, useState } from 'react';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { Box, Stack, Typography } from '@mui/material';

import { fetchDiagnostics } from '../api/client';
import AboutGuideTabs from '../components/About/AboutGuideTabs';
import type { DiagnosticsResponse } from '../types/api';
import { scrollablePageSx } from '../utils/pageLayout';

const AboutView: React.FC = () => {
  const [diagnostics, setDiagnostics] = useState<DiagnosticsResponse | null>(null);
  const [diagnosticsError, setDiagnosticsError] = useState('');
  const [diagnosticsLoading, setDiagnosticsLoading] = useState(true);

  useEffect(() => {
    let disposed = false;

    const loadDiagnostics = async () => {
      try {
        const result = await fetchDiagnostics();
        if (!disposed) {
          setDiagnostics(result);
          setDiagnosticsError('');
        }
      } catch (error) {
        if (!disposed) {
          setDiagnostics(null);
          setDiagnosticsError(error instanceof Error ? error.message : 'Failed to load diagnostics.');
        }
      } finally {
        if (!disposed) setDiagnosticsLoading(false);
      }
    };

    void loadDiagnostics();
    return () => { disposed = true; };
  }, []);

  return (
    <Box sx={{ ...scrollablePageSx, width: '100%' }}>
      <Stack direction="row" spacing={1.25} alignItems="flex-start">
        <InfoOutlinedIcon color="primary" sx={{ mt: 0.5 }} />
        <Box>
          <Typography variant="h5" component="h1" fontWeight={700}>
            關於 TOV1050 Analyzer
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: '76ch' }}>
            供操作人員及開發者查閱目前工作流程、判斷規則、資料合約、架構與執行環境。
          </Typography>
        </Box>
      </Stack>

      <AboutGuideTabs
        diagnostics={diagnostics}
        diagnosticsLoading={diagnosticsLoading}
        diagnosticsError={diagnosticsError}
      />
    </Box>
  );
};

export default AboutView;
