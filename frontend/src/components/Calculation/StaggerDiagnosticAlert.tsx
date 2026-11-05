import { useState } from 'react';
import { Alert, Box, Button, Stack, TextField, Typography } from '@mui/material';
import { apiDiagnosticText, type ApiErrorDiagnostic } from '../../api/errorMessage';

export default function StaggerDiagnosticAlert({ diagnostic }: { diagnostic: ApiErrorDiagnostic }) {
  const [copyState, setCopyState] = useState('');
  const text = apiDiagnosticText(diagnostic);
  const copyDetails = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyState('已複製診斷詳情');
    } catch {
      setCopyState('無法自動複製，請在下方選取診斷詳情後複製。');
    }
  };

  return (
    <Alert severity={diagnostic.code === 'STAGGER_CONFIG_UNAVAILABLE' ? 'warning' : 'error'}>
      <Stack spacing={1}>
        <Typography>{diagnostic.message}</Typography>
        {diagnostic.filename && <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>檔案：{diagnostic.filename}</Typography>}
        <Typography variant="body2">診斷代碼：{diagnostic.code}</Typography>
        {diagnostic.code === 'STAGGER_CONFIG_UNAVAILABLE' && (
          <Typography variant="body2">下一步：提供並核准此路線、分支及方向的支撐點資料與 Keq 規則後，再啟用計算。</Typography>
        )}
        <Box component="details">
          <Box component="summary" sx={{ cursor: 'pointer' }}>診斷詳情</Box>
          <Stack spacing={1} sx={{ mt: 1 }}>
            <TextField label="可複製診斷詳情" value={text} multiline fullWidth InputProps={{ readOnly: true }} />
            <Button variant="outlined" onClick={copyDetails} sx={{ alignSelf: 'flex-start' }}>複製診斷詳情</Button>
            <Typography variant="body2" role="status">{copyState}</Typography>
          </Stack>
        </Box>
      </Stack>
    </Alert>
  );
}
