import React from 'react';
import AltRouteIcon from '@mui/icons-material/AltRoute';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import CloseIcon from '@mui/icons-material/Close';
import SaveOutlinedIcon from '@mui/icons-material/SaveOutlined';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';

interface WearAlgorithmDialogProps {
  open: boolean;
  onClose: () => void;
}

const WearAlgorithmDialog: React.FC<WearAlgorithmDialogProps> = ({ open, onClose }) => {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const stackVertically = useMediaQuery(theme.breakpoints.down('md'));

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      fullScreen={fullScreen}
      scroll="paper"
      aria-labelledby="wear-algorithm-dialog-title"
    >
      <DialogTitle
        id="wear-algorithm-dialog-title"
        sx={{
          position: 'sticky',
          top: 0,
          zIndex: 1,
          bgcolor: 'background.paper',
          borderBottom: 1,
          borderColor: 'divider',
          py: 1.5,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <Typography variant="h5" component="span" fontWeight={700}>
              線耗計算邏輯
            </Typography>
          </Box>
          <IconButton aria-label="關閉線耗計算邏輯" onClick={onClose} edge="end">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ px: { xs: 2, sm: 3 }, py: 0 }}>
        <Typography variant="body2" color="text.secondary" sx={{ pt: 2, maxWidth: '72ch' }}>
          依實際處理次序說明檔案辨識、張力段解析、主線範圍、衝突處理、覆蓋率及保存條件。
        </Typography>
        <Stack divider={<Divider flexItem />}>
          <Box component="section" aria-labelledby="wear-guide-input" sx={{ py: 3 }}>
            <Stack direction="row" spacing={1.25} alignItems="center" sx={{ mb: 1 }}>
              <CheckCircleOutlineIcon color="primary" />
              <Typography id="wear-guide-input" variant="h6">
                開始前先確認
              </Typography>
            </Stack>
            <Typography color="text.secondary" sx={{ mb: 2, maxWidth: '72ch' }}>
              系統先辨識上載檔案所屬路線與 segment，再以 metadata 驗證每筆量測的 Section、Track 及原始 Chainage。Cycle Date 可採用檔案推斷值，也可在預覽前由使用者修正。
            </Typography>

            <Box
              component="ol"
              sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' },
                m: 0,
                p: 0,
                listStyle: 'none',
                borderTop: 1,
                borderBottom: 1,
                borderColor: 'divider',
              }}
            >
              {[
                ['1', '辨識檔案與路線', '讀取 Exception Report，確認 EAL 或 TML，並辨識可處理的 segment。'],
                ['2', '驗證位置資料', '以 Section、Track 及原始 Chainage 對照該路線的 metadata。'],
                ['3', '建立可保存預覽', '解析張力段、分類範圍、整理衝突，再計算聚合及主線覆蓋率。'],
              ].map(([number, title, detail], index) => (
                <Box
                  component="li"
                  key={number}
                  sx={{
                    display: 'flex',
                    gap: 1.25,
                    p: 2,
                    borderRight: { md: index < 2 ? 1 : 0 },
                    borderBottom: { xs: index < 2 ? 1 : 0, md: 0 },
                    borderColor: 'divider',
                  }}
                >
                  <Typography color="primary.main" fontWeight={700} aria-hidden="true">
                    {number}
                  </Typography>
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>{title}</Typography>
                    <Typography variant="body2" color="text.secondary">{detail}</Typography>
                  </Box>
                </Box>
              ))}
            </Box>

            <Alert severity="info" sx={{ mt: 2 }}>
              不要在外部改寫 Chainage、放寬區間或以最近位置代替。位置無法精確解析時，預覽會保留診斷並停止保存。
            </Alert>
          </Box>

          <Box component="section" aria-labelledby="wear-guide-resolution" sx={{ py: 3 }}>
            <Stack direction="row" spacing={1.25} alignItems="center" sx={{ mb: 1 }}>
              <AltRouteIcon color="primary" />
              <Typography id="wear-guide-resolution" variant="h6">
                系統如何判斷
              </Typography>
            </Stack>
            <Typography color="text.secondary" sx={{ mb: 2, maxWidth: '72ch' }}>
              每筆資料先走 strict resolver。只有 strict Section 確認為真正缺口時，才可啟動受限制的 Section transition。
            </Typography>

            <Stack
              direction={{ xs: 'column', md: 'row' }}
              divider={<Divider orientation={stackVertically ? 'horizontal' : 'vertical'} flexItem />}
              sx={{ bgcolor: 'action.hover', borderRadius: 1, mb: 2 }}
            >
              <Box sx={{ p: 2, flex: 1 }}>
                <Typography variant="subtitle2" gutterBottom>先做 strict resolution</Typography>
                <Typography variant="body2" color="text.secondary">
                  以當前 Section、Track、原始 Chainage 及來源資料定位唯一 metadata row。成功後直接使用該列張力段。
                </Typography>
              </Box>
              <Box sx={{ p: 2, flex: 1 }}>
                <Typography variant="subtitle2" gutterBottom>缺口才做 exact transition</Typography>
                <Typography variant="body2" color="text.secondary">
                  必須同 Line、Track、原始 Chainage、完整 ordered source signature 及 source bounds，並只容許一個 source row 與一個 primary TL。
                </Typography>
              </Box>
              <Box sx={{ p: 2, flex: 1 }}>
                <Typography variant="subtitle2" gutterBottom>不唯一便停止</Typography>
                <Typography variant="body2" color="text.secondary">
                  缺少 exact signature、出現碰撞、真正空白或多個 primary TL 時都保留 HTTP 422，不會使用一般 Mainline fallback。
                </Typography>
              </Box>
            </Stack>

            <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
              張力段範圍決策
            </Typography>
            <TableContainer sx={{ mb: 2 }}>
              <Table size="small" aria-label="張力段範圍決策表">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ width: 130 }}>分類</TableCell>
                    <TableCell>判斷方式</TableCell>
                    <TableCell>系統行為</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <TableRow>
                    <TableCell><Chip label="MAINLINE" size="small" color="success" /></TableCell>
                    <TableCell>符合該路線核准的 TL identity 或 series。</TableCell>
                    <TableCell>繼續解析、聚合、覆蓋率、保存及匯出。</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell><Chip label="SIDING" size="small" /></TableCell>
                    <TableCell>符合核准側線規則，`Neutral Section` 亦屬此類。</TableCell>
                    <TableCell>預期排除，不產生結果、衝突、覆蓋缺口或匯出列。</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell><Chip label="UNKNOWN" size="small" color="error" /></TableCell>
                    <TableCell>非空 identity 不符合該路線任何核准規則。</TableCell>
                    <TableCell>Fail closed，診斷列出 Line、sheet row、raw signature 及 identity。</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>

            <Alert severity="warning" sx={{ mb: 2 }}>
              分類是 line-specific 且以 identity 或 series 為準，不能只看 canonical Track。合法 MAINLINE 即使 canonical Track 是 `Siding`，仍會保留並按 physical interval 的 UP 或 DN 方向顯示。
            </Alert>

            <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
              去重、衝突與狀態顏色
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, maxWidth: '80ch' }}>
              系統先按量測 identity 去重。相同 identity 在不同 session 出現不同值時，預覽列出 conflict；使用者接受較低值的決定後，該值才會進入張力段聚合。未接受的 conflict 會阻止保存。
            </Typography>
            <TableContainer>
              <Table size="small" aria-label="線耗狀態門檻表">
                <TableHead>
                  <TableRow>
                    <TableCell>狀態</TableCell>
                    <TableCell>平均最小線耗值</TableCell>
                    <TableCell>用途</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <TableRow>
                    <TableCell><Chip label="正常" size="small" color="success" /></TableCell>
                    <TableCell>&gt; 10.2</TableCell>
                    <TableCell>狀態顯示與篩選。</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell><Chip label="注意" size="small" color="warning" /></TableCell>
                    <TableCell>9.1 至 10.2</TableCell>
                    <TableCell>狀態顯示與篩選。</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell><Chip label="警示" size="small" color="error" /></TableCell>
                    <TableCell>&lt; 9.1</TableCell>
                    <TableCell>狀態顯示與篩選。</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </Box>

          <Box component="section" aria-labelledby="wear-guide-save" sx={{ py: 3 }}>
            <Stack direction="row" spacing={1.25} alignItems="center" sx={{ mb: 1 }}>
              <SaveOutlinedIcon color="primary" />
              <Typography id="wear-guide-save" variant="h6">
                結果如何保存
              </Typography>
            </Stack>
            <Typography color="text.secondary" sx={{ mb: 2, maxWidth: '72ch' }}>
              Cycle Coverage 的 Expected TLs、已完成數量、Diagnostic Gaps 及匯出只計算 MAINLINE。SIDING 不會污染分母或缺口清單，UNKNOWN 則在更早階段阻止預覽完成。
            </Typography>

            <Box sx={{ bgcolor: 'action.hover', borderRadius: 1, p: 2, mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>保存閘門</Typography>
              <Typography variant="body2" color="text.secondary">
                所有位置均已解析、沒有 UNKNOWN、所有 conflict 已接受、preview_digest 仍匹配，而且 data_version 沒有過期，預覽才可保存。任何一項不成立都會顯示 blocking reason。
              </Typography>
            </Box>

            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle2" gutterBottom>原子保存</Typography>
                <Typography variant="body2" color="text.secondary">
                  一個 cycle 的 records、segments、衝突決定及版本資料以單一交易寫入。交易失敗時不會留下部分資料。
                </Typography>
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle2" gutterBottom>保存後匯出</Typography>
                <Typography variant="body2" color="text.secondary">
                  Excel 以已提交的 line group 與 Cycle Date 建立，內容沿用相同的 MAINLINE-only 合約。
                </Typography>
              </Box>
            </Stack>

            <Alert severity="warning">
              `Wire Wear Records` 的新增、修改、儲存格刪除與整列刪除都是 staged changes。橙色標記表示尚未寫入；按「保存變更」後才提交，按「放棄變更」才清除。保存失敗時，待處理內容會保留供修正及重試。
            </Alert>
          </Box>
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 2, py: 1.5, borderTop: 1, borderColor: 'divider' }}>
        <Button onClick={onClose} variant="contained">關閉</Button>
      </DialogActions>
    </Dialog>
  );
};

export default WearAlgorithmDialog;
