import React from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  Paper,
  Stack,
  Typography,
  useTheme,
} from '@mui/material';
import { safetyColors } from '../../theme/AppTheme';

interface AlgorithmTutorialDialogProps {
  open: boolean;
  onClose: () => void;
}

const sectionCardSx = {
  p: 2.5,
  borderRadius: 2,
};

const caseCardSx = {
  p: 2,
  borderRadius: 2,
  height: '100%',
  position: 'relative',
  overflow: 'hidden',
};

const sectionBlockSx = {
  pt: 0.5,
  borderTop: 1,
  borderColor: 'divider',
};

const badgeSx = (bgcolor: string) => ({
  position: 'absolute',
  top: 0,
  right: 0,
  px: 1.5,
  py: 0.5,
  bgcolor,
  color: '#fff',
  fontSize: '0.75rem',
  fontWeight: 700,
  borderBottomLeftRadius: 4,
});

const AlgorithmTutorialDialog: React.FC<AlgorithmTutorialDialogProps> = ({ open, onClose }) => {
  const theme = useTheme();
  const colorLatest = safetyColors.l1;
  const colorPrevious = theme.palette.primary.main;
  const colorText = theme.palette.text.secondary;
  const svgHeight = 120;
  const barHeight = 24;
  const barYLatest = 40;
  const barYPrevious = 70;

  const renderPeak = (cx: number, cy: number, color: string) => (
    <polygon points={`${cx},${cy} ${cx - 5},${cy + 8} ${cx + 5},${cy + 8}`} fill={color} />
  );

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      scroll="paper"
      sx={{ '& .MuiDialog-paper': { fontFamily: '"Noto Sans", sans-serif' } }}
    >
      <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
        <Typography variant="h5" component="div" fontWeight={700}>
          History Compare Algorithm Logic / History Compare 演算法邏輯
        </Typography>
      </DialogTitle>

      <DialogContent sx={{ p: 0 }}>
        <Stack spacing={0}>
          <Box sx={{ px: 3, py: 2.5 }}>
            <Stack spacing={2}>
              <Typography variant="h6" color="primary" fontWeight={700}>
                1. Chain Rule / 鏈式法則
              </Typography>
              <Typography variant="body1">
                History Compare links the latest report to earlier reports one step at a time. A repeated defect is only confirmed when the chain stays valid across adjacent cycles. / History Compare 會把最新報表與較早期報表逐步串接。只有當每一個相鄰週期的比對都成立時，系統才會將異常判定為 repeated defect。
              </Typography>

              <Paper variant="outlined" sx={{ ...sectionCardSx, textAlign: 'center' }}>
                <Stack spacing={2}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
                    <Paper elevation={2} sx={{ p: 1.5, minWidth: 120, border: `2px solid ${colorLatest}`, color: colorLatest, fontWeight: 700 }}>
                      Latest / 最新
                    </Paper>
                    <Typography variant="h4" color="text.disabled" aria-hidden="true">
                      →
                    </Typography>
                    <Paper elevation={1} sx={{ p: 1.5, minWidth: 120, border: `2px solid ${colorPrevious}`, color: colorPrevious }}>
                      Prev 1 / 前一次
                    </Paper>
                    <Typography variant="h4" color="text.disabled" aria-hidden="true">
                      →
                    </Typography>
                    <Paper elevation={0} sx={{ p: 1.5, minWidth: 120, border: `1px dashed ${theme.palette.text.disabled}`, color: theme.palette.text.secondary }}>
                      Prev N / 更早期
                    </Paper>
                    <Typography variant="h4" color="success.main" aria-hidden="true">
                      =
                    </Typography>
                    <Paper elevation={3} sx={{ p: 1.5, minWidth: 150, bgcolor: theme.palette.success.main, color: '#fff', fontWeight: 700 }}>
                      Repeated / 重複異常
                    </Paper>
                  </Box>

                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                    Each adjacent step must stay valid. If one step fails, the repeated chain stops. / 每一個相鄰步驟都必須成立；只要其中一步失敗，repeated chain 就會中斷。
                  </Typography>
                </Stack>
              </Paper>
            </Stack>
          </Box>

          <Box sx={{ ...sectionBlockSx, px: 3, py: 2.5 }}>
            <Stack spacing={2}>
              <Typography variant="h6" color="primary" fontWeight={700}>
                2. Matching Criteria / 比對條件
              </Typography>
              <Typography variant="body1">
                Two records are treated as the same defect only when both the overlap rule and the peak-position rule remain consistent. / 只有在 overlap 規則與 peak position 規則都成立時，兩筆資料才會被視為同一個 defect。
              </Typography>
              <Paper variant="outlined" sx={sectionCardSx}>
                <Stack spacing={1}>
                  <Typography variant="body2">
                    <strong>Overlap / 區間重疊：</strong>
                    defect 的起點與終點區間必須互相重疊。
                  </Typography>
                  <Typography variant="body2">
                    <strong>Peak Inclusion / 峰值位置包含：</strong>
                    其中一筆資料的 Max Location 必須落在重疊區域內。
                  </Typography>
                </Stack>
              </Paper>
            </Stack>
          </Box>

          <Box sx={{ ...sectionBlockSx, px: 3, py: 2.5 }}>
            <Stack spacing={2}>
              <Typography variant="h6" color="primary" fontWeight={700}>
                3. Multiple Report Matching / 多份報表比對
              </Typography>
              <Typography variant="body1">
                The chain is built by checking Latest vs Prev 1 first, then validating the combined result against Prev 2. / 系統會先檢查 Latest 與 Prev 1，再把成立的結果往前與 Prev 2 驗證。
              </Typography>
              <Paper variant="outlined" sx={sectionCardSx}>
                <Grid container alignItems="center" justifyContent="center" spacing={2}>
                  <Grid item xs={12} md={3} textAlign="center">
                    <Typography variant="subtitle2" fontWeight={700}>Step 1 / 步驟一</Typography>
                    <Typography variant="caption">Latest vs Prev 1</Typography>
                    <Box sx={{ mt: 1, p: 1, border: '1px solid #ddd', borderRadius: 1 }}>
                      Match Found? / 是否匹配
                    </Box>
                  </Grid>
                  <Grid item aria-hidden="true">
                    <Typography variant="h5" color="text.disabled">→</Typography>
                  </Grid>
                  <Grid item xs={12} md={3} textAlign="center">
                    <Typography variant="subtitle2" fontWeight={700}>Step 2 / 步驟二</Typography>
                    <Typography variant="caption">Match(L+P1) vs Prev 2</Typography>
                    <Box sx={{ mt: 1, p: 1, border: '1px solid #ddd', borderRadius: 1 }}>
                      Match Found? / 是否匹配
                    </Box>
                  </Grid>
                  <Grid item aria-hidden="true">
                    <Typography variant="h5" color="text.disabled">→</Typography>
                  </Grid>
                  <Grid item xs={12} md={3} textAlign="center">
                    <Typography variant="subtitle2" fontWeight={700}>Result / 結果</Typography>
                    <Typography variant="caption">Repeated Chain</Typography>
                    <Box sx={{ mt: 1, p: 1, bgcolor: 'success.main', color: 'white', borderRadius: 1 }}>
                      Confirmed / 確認成立
                    </Box>
                  </Grid>
                </Grid>
              </Paper>
            </Stack>
          </Box>

          <Box sx={{ ...sectionBlockSx, px: 3, py: 2.5 }}>
            <Stack spacing={2}>
              <Typography variant="subtitle1" fontWeight={700}>
                4. Visual Scenarios / 視覺案例
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <Paper variant="outlined" sx={caseCardSx}>
                    <Box sx={badgeSx(theme.palette.success.main)}>
                      CASE A
                    </Box>
                    <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                      Valid Match / 有效匹配
                    </Typography>
                    <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 2 }}>
                      Ranges overlap and both peak positions stay in the shared area. / 區間重疊，且兩個 peak 都落在共同區域內。
                    </Typography>
                    <svg width="100%" height={svgHeight} viewBox="0 0 200 120">
                      <line x1="80" y1="20" x2="80" y2="100" stroke={theme.palette.divider} strokeDasharray="4" />
                      <line x1="150" y1="20" x2="150" y2="100" stroke={theme.palette.divider} strokeDasharray="4" />
                      <rect x="80" y="35" width="70" height="65" fill={theme.palette.success.light} fillOpacity="0.1" />
                      <rect x="50" y={barYLatest} width="100" height={barHeight} fill={colorLatest} rx={4} opacity="0.8" />
                      {renderPeak(100, barYLatest + barHeight, colorLatest)}
                      <text x="30" y={barYLatest + 16} fontSize="10" fill={colorText}>New</text>
                      <rect x="80" y={barYPrevious} width="100" height={barHeight} fill={colorPrevious} rx={4} opacity="0.8" />
                      {renderPeak(110, barYPrevious + barHeight, colorPrevious)}
                      <text x="30" y={barYPrevious + 16} fontSize="10" fill={colorText}>Old</text>
                    </svg>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Paper variant="outlined" sx={caseCardSx}>
                    <Box sx={badgeSx(theme.palette.text.disabled)}>
                      CASE B
                    </Box>
                    <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                      Gap / 無重疊
                    </Typography>
                    <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 2 }}>
                      The ranges never overlap, so the chain cannot continue. / 區間沒有交集，因此鏈式比對無法繼續。
                    </Typography>
                    <svg width="100%" height={svgHeight} viewBox="0 0 200 120">
                      <rect x="20" y={barYLatest} width="50" height={barHeight} fill={colorLatest} rx={4} opacity="0.8" />
                      {renderPeak(45, barYLatest + barHeight, colorLatest)}
                      <text x="5" y={barYLatest + 16} fontSize="10" fill={colorText}>New</text>
                      <rect x="100" y={barYPrevious} width="50" height={barHeight} fill={colorPrevious} rx={4} opacity="0.8" />
                      {renderPeak(125, barYPrevious + barHeight, colorPrevious)}
                      <text x="5" y={barYPrevious + 16} fontSize="10" fill={colorText}>Old</text>
                    </svg>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Paper variant="outlined" sx={caseCardSx}>
                    <Box sx={badgeSx(theme.palette.error.main)}>
                      CASE C
                    </Box>
                    <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                      Peak Drift / 峰值偏移
                    </Typography>
                    <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 2 }}>
                      Ranges overlap, but the peak falls outside the valid overlap zone. / 區間雖然重疊，但 peak 落在有效 overlap 區域之外。
                    </Typography>
                    <svg width="100%" height={svgHeight} viewBox="0 0 200 120">
                      <line x1="120" y1="20" x2="120" y2="100" stroke={theme.palette.divider} strokeDasharray="4" />
                      <line x1="150" y1="20" x2="150" y2="100" stroke={theme.palette.divider} strokeDasharray="4" />
                      <rect x="120" y="35" width="30" height="65" fill={theme.palette.error.light} fillOpacity="0.1" />
                      <rect x="50" y={barYLatest} width="100" height={barHeight} fill={colorLatest} rx={4} opacity="0.8" />
                      {renderPeak(80, barYLatest + barHeight, colorLatest)}
                      <text x="25" y={barYLatest + 16} fontSize="10" fill={colorText}>New</text>
                      <rect x="120" y={barYPrevious} width="100" height={barHeight} fill={colorPrevious} rx={4} opacity="0.8" />
                      {renderPeak(180, barYPrevious + barHeight, colorPrevious)}
                      <text x="25" y={barYPrevious + 16} fontSize="10" fill={colorText}>Old</text>
                      <text x="123" y="110" fontSize="10" fill={theme.palette.error.main} fontWeight="bold">Out</text>
                    </svg>
                  </Paper>
                </Grid>
              </Grid>
            </Stack>
          </Box>
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} variant="contained">
          關閉 Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AlgorithmTutorialDialog;
