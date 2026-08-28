import React from 'react';
import {
  Box,
  Button,
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
import staggerAlgorithmImage from '../../assets/stagger-calculation-algorithm.png';

interface StaggerAlgorithmDialogProps {
  open: boolean;
  onClose: () => void;
}

const cardSx = {
  p: 2,
  borderRadius: 2,
  border: '1px solid',
  borderColor: 'divider',
  bgcolor: 'background.paper',
  height: '100%',
};

const steps = [
  [
    'Step 1 / 步驟一',
    'Select Source / 選取資料來源',
    'Case A uses the Exception Report only. Case B only applies when the n_Repeated summary contains a matching stagger ID. / Case A 只使用 Exception Report；Case B 只在 n_Repeated summary 內存在對應 stagger ID 時介入。',
  ],
  [
    'Step 2 / 步驟二',
    'Locate Ch_I / 定位 Ch_I',
    'Case A uses Summary MaxLocation. Case B prefers MaxLocation from the repeated report when it is available. / Case A 使用 Summary 的 MaxLocation；Case B 優先使用 repeated report 的 MaxLocation。',
  ],
  [
    'Step 3 / 步驟三',
    'Find Supports / 找支點',
    'Resolve Spt_A, Spt_I, and Spt_B from the support reference, then calculate Span_AI and Span_IB. / 由 support reference 找到 Spt_A、Spt_I、Spt_B，再計算 Span_AI 與 Span_IB。',
  ],
  [
    'Step 4 / 步驟四',
    'Judge Result / 判定結果',
    'Evaluate K_eq, P, S, E, and Allowable to conclude pass, fail, or n/a. / 綜合 K_eq、P、S、E 與 Allowable，輸出 pass、fail 或 n/a。',
  ],
] as const;

const terms = [
  [
    'Ch_I',
    'The local chainage reference for the alarm under review. / 目前檢視 alarm 的本地 chainage 參考點。',
  ],
  [
    'Spt_A / Spt_I / Spt_B',
    'Support points before, at, and after the local position. Missing supports lead to partial trace output. / 代表前、中、後三個支點；若缺值，trace 會退化成 partial。',
  ],
  [
    'K_eq',
    'Equivalent stiffness selected from K_A, K_I, and K_B. / 由 K_A、K_I、K_B 選出的等效剛性。',
  ],
  [
    'Allowable',
    'The final allowable stagger limit after combining B, E, and height correction. / 結合 B、E 與高度修正後的最終允許 stagger 上限。',
  ],
] as const;

const StaggerAlgorithmDialog: React.FC<StaggerAlgorithmDialogProps> = ({ open, onClose }) => {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth scroll="paper">
      <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Stack spacing={0.5}>
          <Typography variant="h5" fontWeight={700}>
            Stagger Algorithm Explain / Stagger 演算法說明
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Explain how Case A / Case B choose data sources, resolve support points, and judge the final stagger result. / 說明 Case A / Case B 如何選取資料來源、定位支點，並判定最終 stagger 結果。
          </Typography>
        </Stack>
      </DialogTitle>

      <DialogContent sx={{ p: 3 }}>
        <Stack spacing={3}>
          <Box>
            <Typography variant="subtitle1" fontWeight={700} gutterBottom>
              流程概覽 Process Overview
            </Typography>
            <Grid container spacing={1.5}>
              {steps.map(([step, title, desc]) => (
                <Grid item xs={12} md={3} key={step}>
                  <Paper variant="outlined" sx={cardSx}>
                    <Typography variant="overline" color="primary.main">{step}</Typography>
                    <Typography variant="subtitle2" fontWeight={700}>{title}</Typography>
                    <Typography variant="body2" color="text.secondary">{desc}</Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle1" fontWeight={700} gutterBottom>
              公式摘要 Formula Summary
            </Typography>
            <Paper variant="outlined" sx={{ ...cardSx, bgcolor: 'grey.50' }}>
              <Stack spacing={1}>
                <Typography variant="body2"><strong>K_eq</strong> = max(K_A, K_I, K_B)</Typography>
                <Typography variant="body2"><strong>Span_AI</strong> = |Spt_A - Spt_I|, <strong>Span_IB</strong> = |Spt_I - Spt_B|</Typography>
                <Typography variant="body2"><strong>B</strong> = 0.6137 * 0.8 * 1.08 * (34.3 * K_eq)^2 * 0.0132 * Span^2 / (32 * Tension)</Typography>
                <Typography variant="body2"><strong>P</strong> = |(Stg_X + Stg_I) / 2|, <strong>S</strong> = |Stg_X - Stg_I|</Typography>
                <Typography variant="body2"><strong>E</strong> = S^2 / (16 * B)</Typography>
                <Typography variant="body2"><strong>Allowable</strong> = 505 - (B + E) - HeightCorrection</Typography>
              </Stack>
            </Paper>
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle1" fontWeight={700} gutterBottom>
              Visual Reference
            </Typography>
            <Paper variant="outlined" sx={{ ...cardSx, p: 2 }}>
              <Box
                component="img"
                src={staggerAlgorithmImage}
                alt="Stagger calculation algorithm"
                sx={{ width: '100%', height: 'auto', display: 'block', borderRadius: 1 }}
              />
            </Paper>
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle1" fontWeight={700} gutterBottom>
              關鍵詞彙 Key Terms
            </Typography>
            <Grid container spacing={1.5}>
              {terms.map(([name, desc]) => (
                <Grid item xs={12} md={3} key={name}>
                  <Paper variant="outlined" sx={cardSx}>
                    <Typography variant="subtitle2" fontWeight={700}>{name}</Typography>
                    <Typography variant="body2" color="text.secondary">{desc}</Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle1" fontWeight={700} gutterBottom>
              判定規則 Decision Rules
            </Typography>
            <Paper variant="outlined" sx={cardSx}>
              <Stack spacing={1}>
                <Typography variant="body2">1. Resolve Span_AI and Span_IB from the nearest valid support points. / 先用最近且有效的支點計算 Span_AI 與 Span_IB。</Typography>
                <Typography variant="body2">2. If short-circuit conditions are met, return <strong>pass_short_circuit</strong> first. / 若命中 short-circuit 條件，先回傳 <strong>pass_short_circuit</strong>。</Typography>
                <Typography variant="body2">3. Compare <strong>P</strong> against <strong>Allowable</strong> to determine pass or fail. / 以 <strong>P</strong> 與 <strong>Allowable</strong> 的比較判定 pass 或 fail。</Typography>
                <Typography variant="body2">4. Missing references keep the trace partial and may result in <strong>n/a</strong>. / 若支點或必要參考值缺失，trace 會維持 partial，並可能輸出 <strong>n/a</strong>。</Typography>
              </Stack>
            </Paper>
          </Box>
        </Stack>
      </DialogContent>

      <DialogActions sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <Button onClick={onClose} variant="contained">關閉 Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default StaggerAlgorithmDialog;
