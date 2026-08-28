import React from 'react';
import StorageOutlinedIcon from '@mui/icons-material/StorageOutlined';
import {
  Alert,
  Box,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Typography,
} from '@mui/material';

import type { DiagnosticsResponse } from '../../types/api';

interface DiagnosticsPanelProps {
  diagnostics: DiagnosticsResponse | null;
  loading: boolean;
  error: string;
}

const DiagnosticsPanel: React.FC<DiagnosticsPanelProps> = ({ diagnostics, loading, error }) => (
  <Box
    aria-live="polite"
    sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: { xs: 1.5, sm: 2 } }}
  >
    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
      <StorageOutlinedIcon color="primary" />
      <Typography variant="subtitle1" component="h4" fontWeight={700}>Active Database Path</Typography>
    </Stack>

    {loading ? (
      <Stack spacing={1} aria-label="正在載入執行環境診斷">
        <Skeleton variant="text" width="42%" />
        <Skeleton variant="rounded" height={42} />
        <Skeleton variant="text" width="72%" />
        <Skeleton variant="text" width="58%" />
      </Stack>
    ) : null}

    {!loading && error ? (
      <Alert severity="error">
        無法載入執行環境診斷。操作指南及開發者參考仍可使用。<br />
        <code>{error}</code>
      </Alert>
    ) : null}

    {!loading && diagnostics ? (
      <TableContainer>
        <Table size="small" aria-label="執行環境診斷">
          <TableBody>
            <TableRow>
              <TableCell component="th" scope="row" sx={{ width: { sm: 168 } }}>資料庫</TableCell>
              <TableCell sx={{ wordBreak: 'break-all' }}><code>{diagnostics.database_path}</code></TableCell>
            </TableRow>
            <TableRow>
              <TableCell component="th" scope="row">資料目錄</TableCell>
              <TableCell sx={{ wordBreak: 'break-all' }}><code>{diagnostics.database_directory}</code></TableCell>
            </TableRow>
            <TableRow>
              <TableCell component="th" scope="row">Config 目錄</TableCell>
              <TableCell sx={{ wordBreak: 'break-all' }}><code>{diagnostics.config_directory}</code></TableCell>
            </TableRow>
            <TableRow>
              <TableCell component="th" scope="row">Runtime mode</TableCell>
              <TableCell>{diagnostics.mode}</TableCell>
            </TableRow>
            <TableRow>
              <TableCell component="th" scope="row">Package target</TableCell>
              <TableCell>{diagnostics.packaging.current_target}，建議 {diagnostics.packaging.recommended_target}</TableCell>
            </TableRow>
            <TableRow>
              <TableCell component="th" scope="row">寫入提示</TableCell>
              <TableCell>{diagnostics.packaging.single_exe_note}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>
    ) : null}
  </Box>
);

export default DiagnosticsPanel;
