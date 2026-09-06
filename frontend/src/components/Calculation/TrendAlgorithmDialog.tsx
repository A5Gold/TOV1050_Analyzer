import React from 'react';
import trendAlgorithmImage from '../../assets/trend-analysis-algorithm.png';
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  Paper,
  Stack,
  Typography,
} from '@mui/material';

interface TrendAlgorithmDialogProps {
  open: boolean;
  onClose: () => void;
}

const cardSx = {
  p: 1.5,
  borderRadius: 2,
  border: '1px solid',
  borderColor: 'divider',
  height: '100%',
};

const TrendAlgorithmDialog: React.FC<TrendAlgorithmDialogProps> = ({ open, onClose }) => {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth scroll="paper">
      <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
        <Stack spacing={0.75}>
          <Typography variant="h5" fontWeight={700}>
            Trend Analysis Logic
          </Typography>
          <Typography variant="body2" color="text.secondary">
            目前版本以 Wire Wear 篩選異常、以 ChartData 生成 record points，並在圖表層只保留實際有資料的日期點。
          </Typography>
        </Stack>
      </DialogTitle>

      <DialogContent sx={{ p: 3 }}>
        <Stack spacing={3}>
          <Box component="figure" sx={{ m: 0, display: 'flex', justifyContent: 'center' }}>
            <Box component="img" src={trendAlgorithmImage} alt="Trend analysis algorithm flow" sx={{ width: '100%', maxWidth: 720, maxHeight: 260, objectFit: 'contain', borderRadius: 1 }} />
          </Box>
          <Box>
            <Typography variant="subtitle1" fontWeight={700} gutterBottom>
              1. Current Flow
            </Typography>
            <Grid container spacing={1.5}>
              <Grid item xs={12} md={3}>
                <Paper variant="outlined" sx={cardSx}>
                  <Typography variant="overline" color="primary.main">Step 1</Typography>
                  <Typography variant="subtitle2" fontWeight={700}>Load Reports</Typography>
                  <Typography variant="body2" color="text.secondary">
                    讀取多個 Exception Report，可選填 n_Repeated Exception Report。
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={3}>
                <Paper variant="outlined" sx={cardSx}>
                  <Typography variant="overline" color="primary.main">Step 2</Typography>
                  <Typography variant="subtitle2" fontWeight={700}>Select L2 Scope</Typography>
                  <Typography variant="body2" color="text.secondary">
                    依 Case A / Case B 決定要分析的最新週期 L2 異常。
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={3}>
                <Paper variant="outlined" sx={cardSx}>
                  <Typography variant="overline" color="primary.main">Step 3</Typography>
                  <Typography variant="subtitle2" fontWeight={700}>Build Record Points</Typography>
                  <Typography variant="body2" color="text.secondary">
                    依 each exception 的 from_m / to_m，在各日期取 min(wear_min)。
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={3}>
                <Paper variant="outlined" sx={cardSx}>
                  <Typography variant="overline" color="primary.main">Step 4</Typography>
                  <Typography variant="subtitle2" fontWeight={700}>Regression + Recommendation</Typography>
                  <Typography variant="body2" color="text.secondary">
                    套用單一 ordinary least squares linear regression，再用 Logic 1、Logic 2 輸出 recommendation。
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle1" fontWeight={700} gutterBottom>
              2. Case Filters
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Paper variant="outlined" sx={cardSx}>
                  <Chip label="Case A" size="small" color="primary" sx={{ mb: 1 }} />
                  <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                    無 n_Repeated 檔案
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    從 Wire Wear 篩選 Level = L2、ACTION 空白，並只保留最新 run date 的異常。
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper variant="outlined" sx={cardSx}>
                  <Chip label="Case B" size="small" color="warning" sx={{ mb: 1 }} />
                  <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                    有 n_Repeated 檔案
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    只分析同時出現在 Summary 與 Wire Wear 的 L2 ID，並保留最新 run date。
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </Box>

          <Box>
            <Typography variant="subtitle1" fontWeight={700} gutterBottom>
              3. Chart Display Rule
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: 'grey.50' }}>
              <Stack spacing={1}>
                <Typography variant="body2">
                  x-axis 只保留實際有資料的日期。
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  若某日期同時沒有 record_points 與 trend_points，前端會從圖表中移除該日期，不顯示空白尾段。
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  橙色虛線會以第一個與最後一個有效 fitted point 畫成同一條 regression line，不使用分段斜率演算法。
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  這可避免 EAL 圖在最後一個有效點之後仍延伸空白類別，例如資料已在 <strong>T3</strong> 結束時，x-axis 不再向後拉長。
                </Typography>
              </Stack>
            </Paper>
          </Box>

          <Box>
            <Typography variant="subtitle1" fontWeight={700} gutterBottom>
              4. Recommendation Logic
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <Paper variant="outlined" sx={cardSx}>
                  <Chip label="no action required" size="small" sx={{ mb: 1, bgcolor: '#4caf50', color: '#fff' }} />
                  <Typography variant="body2" color="text.secondary">
                    `trend_point[0] &gt; 10.2`
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={4}>
                <Paper variant="outlined" sx={cardSx}>
                  <Chip label="verify on site" size="small" sx={{ mb: 1, bgcolor: '#ff9800', color: '#fff' }} />
                  <Typography variant="body2" color="text.secondary">
                    `trend_point[0] ≤ 10.2` 且 `|record_points[0] - trend_point[0]| &gt; 0.2`
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={4}>
                <Paper variant="outlined" sx={cardSx}>
                  <Chip label="confirmed valid L2" size="small" sx={{ mb: 1, bgcolor: '#1976d2', color: '#fff' }} />
                  <Typography variant="body2" color="text.secondary">
                    `trend_point[0] ≤ 10.2` 且 `|record_points[0] - trend_point[0]| ≤ 0.2`
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </Box>

          <Box>
            <Typography variant="subtitle1" fontWeight={700} gutterBottom>
              5. Data Fields
            </Typography>
            <Grid container spacing={1.5}>
              <Grid item xs={12} md={4}>
                <Paper variant="outlined" sx={cardSx}>
                  <Typography variant="subtitle2" fontWeight={700}>record_points</Typography>
                  <Typography variant="body2" color="text.secondary">
                    各日期在 exception chainage 範圍內的 `min(wear_min)`。
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={4}>
                <Paper variant="outlined" sx={cardSx}>
                  <Typography variant="subtitle2" fontWeight={700}>trend_points</Typography>
                  <Typography variant="body2" color="text.secondary">
                    由 linear regression 擬合出的歷史趨勢值。
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} md={4}>
                <Paper variant="outlined" sx={cardSx}>
                  <Typography variant="subtitle2" fontWeight={700}>trend_next</Typography>
                  <Typography variant="body2" color="text.secondary">
                    目前實作中代表最新週期對應的擬合值，用於 recommendation 判斷。
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </Box>
        </Stack>
      </DialogContent>

      <DialogActions sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <Button onClick={onClose} variant="contained">關閉</Button>
      </DialogActions>
    </Dialog>
  );
};

export default TrendAlgorithmDialog;
