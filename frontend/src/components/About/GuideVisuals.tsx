import React from 'react';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import {
  Box,
  Chip,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { alpha, useTheme } from '@mui/material/styles';

import type { GuideFlowStep } from './aboutGuideContent';

interface GuideFlowProps {
  steps: GuideFlowStep[];
  label: string;
  desktopColumns?: number;
}

export const GuideFlow: React.FC<GuideFlowProps> = ({ steps, label, desktopColumns = 4 }) => (
  <Box
    component="ol"
    aria-label={label}
    sx={{
      display: 'grid',
      gridTemplateColumns: {
        xs: '1fr',
        sm: 'repeat(2, minmax(0, 1fr))',
        lg: `repeat(${desktopColumns}, minmax(0, 1fr))`,
      },
      m: 0,
      p: '1px',
      listStyle: 'none',
      gap: '1px',
      bgcolor: 'divider',
      borderRadius: 1,
      overflow: 'hidden',
    }}
  >
    {steps.map((step, index) => (
      <Box
        component="li"
        key={step.title}
        sx={{
          display: 'flex',
          gap: 1.25,
          p: 1.5,
          bgcolor: 'background.paper',
          minWidth: 0,
        }}
      >
        <Typography color="primary.main" fontWeight={700} aria-hidden="true">
          {index + 1}
        </Typography>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="subtitle2" component="h4" gutterBottom>{step.title}</Typography>
          <Typography variant="body2" color="text.secondary">{step.detail}</Typography>
        </Box>
      </Box>
    ))}
  </Box>
);

export const ThresholdRangeChart: React.FC = () => (
  <Box component="figure" sx={{ m: 0 }} aria-labelledby="wear-threshold-chart-title">
    <Typography id="wear-threshold-chart-title" variant="subtitle2" component="h4" gutterBottom>
      Wear 平均最小值狀態範圍
    </Typography>
    <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
      真實門檻：9.1 與 10.2。數值愈低代表剩餘線徑愈小。
    </Typography>
    <Box
      aria-hidden="true"
      sx={{
        display: 'grid',
        gridTemplateColumns: '1fr 1.2fr 1fr',
        minHeight: 54,
        overflow: 'hidden',
        borderRadius: 1,
        border: 1,
        borderColor: 'divider',
      }}
    >
      <Box sx={{ display: 'grid', placeItems: 'center', bgcolor: 'error.main', color: 'error.contrastText', px: 1 }}>
        <Typography variant="caption" fontWeight={700}>&lt; 9.1 警示</Typography>
      </Box>
      <Box sx={{ display: 'grid', placeItems: 'center', bgcolor: 'warning.main', color: 'warning.contrastText', px: 1 }}>
        <Typography variant="caption" fontWeight={700}>9.1 至 10.2 注意</Typography>
      </Box>
      <Box sx={{ display: 'grid', placeItems: 'center', bgcolor: 'success.main', color: 'success.contrastText', px: 1 }}>
        <Typography variant="caption" fontWeight={700}>&gt; 10.2 正常</Typography>
      </Box>
    </Box>
    <TableContainer sx={{ mt: 1 }}>
      <Table size="small" aria-label="Wear 狀態門檻表">
        <TableHead>
          <TableRow><TableCell>範圍</TableCell><TableCell>狀態</TableCell><TableCell>作用</TableCell></TableRow>
        </TableHead>
        <TableBody>
          <TableRow><TableCell>&lt; 9.1</TableCell><TableCell>警示</TableCell><TableCell>圖表與記錄顯示紅色狀態。</TableCell></TableRow>
          <TableRow><TableCell>9.1 至 10.2</TableCell><TableCell>注意</TableCell><TableCell>圖表與記錄顯示橙色狀態。</TableCell></TableRow>
          <TableRow><TableCell>&gt; 10.2</TableCell><TableCell>正常</TableCell><TableCell>圖表與記錄顯示綠色狀態。</TableCell></TableRow>
        </TableBody>
      </Table>
    </TableContainer>
  </Box>
);

export const RepeatChainTimeline: React.FC = () => (
  <GuideFlow
    label="Repeat chain 時序"
    desktopColumns={4}
    steps={[
      { title: 'Latest Report', detail: '作為 accumulator，保留最新報表欄位。' },
      { title: 'Previous 1', detail: '同類型、區間交集，而且雙方 peak 都位於交集。' },
      { title: 'Previous 2', detail: '只讓上一輪仍有效的列繼續向舊報表比對。' },
      { title: 'Previous N', detail: '一路存活的列形成 repeated chain。' },
    ]}
  />
);

export const OneYearWindowVisual: React.FC = () => (
  <Box component="figure" sx={{ m: 0 }} aria-labelledby="one-year-window-title">
    <Typography id="one-year-window-title" variant="subtitle2" component="h4" gutterBottom>
      365 日比較窗口
    </Typography>
    <Box sx={{ position: 'relative', pt: 2, pb: 1 }} aria-hidden="true">
      <Box sx={{ position: 'absolute', top: 29, left: 12, right: 12, borderTop: 2, borderColor: 'primary.main' }} />
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', position: 'relative' }}>
        {[
          ['目前日期 - 365 日', '更早紀錄不匹配'],
          ['DB record date', '需同 section、type 及位置'],
          ['目前異常日期', '命中後回寫 action'],
        ].map(([title, detail]) => (
          <Box key={title} sx={{ textAlign: 'center', px: 0.5 }}>
            <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: 'primary.main', mx: 'auto', mb: 1 }} />
            <Typography variant="caption" fontWeight={700} display="block">{title}</Typography>
            <Typography variant="caption" color="text.secondary">{detail}</Typography>
          </Box>
        ))}
      </Box>
    </Box>
    <TableContainer sx={{ mt: 1 }}>
      <Table size="small" aria-label="1 Year 匹配條件表">
        <TableBody>
          <TableRow><TableCell>範圍</TableCell><TableCell>日期 window 為目前日期前 365 日，含起訖邊界；先以 line + track + section 找候選。</TableCell></TableRow>
          <TableRow><TableCell>身份</TableCell><TableCell>family 與 level 必須符合矩陣。Stagger Left／Right 可互配，L3 可配 L3/L2/L1；Low Height／High Height 各自只配同 family 的 L2/L1。</TableCell></TableRow>
          <TableRow><TableCell>位置</TableCell><TableCell>目前 location／chainage 必須落在 target from_m 至 to_m，並保留 section identity。</TableCell></TableRow>
          <TableRow><TableCell>候選</TableCell><TableCell>多候選取最新有效日期；同日以 record_id 由大至小排序並排除 self-match，避免 runtime 狀態影響結果。</TableCell></TableRow>
          <TableRow><TableCell>動作</TableCell><TableCell>非空且非 Pending 的人工 ACTION 回傳 skipped；review proposal 只先 staged，不在 Check 寫 DB。</TableCell></TableRow>
        </TableBody>
      </Table>
    </TableContainer>
  </Box>
);

export const WearResolutionVisual: React.FC = () => (
  <Box component="figure" sx={{ m: 0 }} aria-labelledby="wear-resolution-title">
    <Typography id="wear-resolution-title" variant="subtitle2" component="h4" gutterBottom>
      Wear 解析與範圍決策
    </Typography>
    <GuideFlow
      label="Wear 解析流程"
      desktopColumns={4}
      steps={[
        { title: 'Strict Section', detail: '先以 Section、Track 與原始 Chainage 找唯一 row。' },
        { title: 'Exact transition', detail: '只有 strict gap 才比對同 Line、Track、Chainage 與 ordered source signature。' },
        { title: 'Scope classifier', detail: '依 line-specific TL identity 或 series 分成 MAINLINE、SIDING、UNKNOWN。' },
        { title: 'Preview gate', detail: '去重、接受 conflict、計算 MAINLINE-only coverage，再建立 digest 與版本。' },
      ]}
    />
    <TableContainer sx={{ mt: 1 }}>
      <Table size="small" aria-label="Wear 張力段分類表">
        <TableHead>
          <TableRow><TableCell>分類</TableCell><TableCell>結果</TableCell></TableRow>
        </TableHead>
        <TableBody>
          <TableRow><TableCell><Chip label="MAINLINE" size="small" color="success" /></TableCell><TableCell>進入結果、coverage、保存與匯出。</TableCell></TableRow>
          <TableRow><TableCell><Chip label="SIDING" size="small" /></TableCell><TableCell>預期排除，不產生 conflict 或 gap。</TableCell></TableRow>
          <TableRow><TableCell><Chip label="UNKNOWN" size="small" color="error" /></TableCell><TableCell>Fail closed，HTTP 422 並顯示可行動診斷。</TableCell></TableRow>
        </TableBody>
      </Table>
    </TableContainer>
  </Box>
);

export const CoverageExample: React.FC = () => (
  <Box component="figure" sx={{ m: 0 }} aria-labelledby="coverage-example-title">
    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
      <Typography id="coverage-example-title" variant="subtitle2" component="h4">MAINLINE-only coverage</Typography>
      <Chip label="示例" size="small" variant="outlined" />
    </Stack>
    <Box
      aria-hidden="true"
      sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 1, mb: 1 }}
    >
      <Box sx={{ p: 1.25, textAlign: 'center', bgcolor: 'success.main', color: 'success.contrastText', borderRadius: 1 }}>H01 已完成</Box>
      <Box sx={{ p: 1.25, textAlign: 'center', bgcolor: 'success.main', color: 'success.contrastText', borderRadius: 1 }}>H02 已完成</Box>
      <Box sx={{ p: 1.25, textAlign: 'center', bgcolor: 'warning.main', color: 'warning.contrastText', borderRadius: 1 }}>H03 缺口</Box>
    </Box>
    <TableContainer>
      <Table size="small" aria-label="MAINLINE-only coverage 示例表">
        <TableBody>
          <TableRow><TableCell>Expected TLs</TableCell><TableCell>H01、H02、H03，共 3 個 MAINLINE TL。</TableCell></TableRow>
          <TableRow><TableCell>已完成</TableCell><TableCell>H01、H02，共 2 個。</TableCell></TableRow>
          <TableRow><TableCell>Coverage</TableCell><TableCell>2 / 3 = 66.7%（示例）。</TableCell></TableRow>
          <TableRow><TableCell>排除</TableCell><TableCell>任何 SIDING TL 不進入分母或 Diagnostic Gaps。</TableCell></TableRow>
        </TableBody>
      </Table>
    </TableContainer>
  </Box>
);

export const StagedChangesVisual: React.FC = () => {
  const theme = useTheme();
  const pendingBackground = alpha(theme.palette.warning.main, theme.palette.mode === 'dark' ? 0.24 : 0.12);
  const pendingBorder = alpha(theme.palette.warning.main, theme.palette.mode === 'dark' ? 0.74 : 0.56);

  return (
    <Box component="figure" sx={{ m: 0 }} aria-labelledby="staged-changes-title">
      <Typography id="staged-changes-title" variant="subtitle2" component="h4" gutterBottom>
        Wire Wear Records 待提交狀態
      </Typography>
      <Stack spacing={0.75}>
        {[
          { label: '待新增', Icon: AddCircleOutlineIcon, detail: '新日期與新數值尚未寫入。' },
          { label: '待更新', Icon: EditOutlinedIcon, detail: '原值已修改，保存前仍可放棄。' },
          { label: '待刪除', Icon: DeleteOutlineIcon, detail: '值保留刪除線，整列刪除會連續標記。' },
        ].map(({ label, Icon, detail }) => (
          <Box
            key={label}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              p: 1,
              bgcolor: pendingBackground,
              border: 1,
              borderColor: pendingBorder,
              borderRadius: 1,
            }}
          >
            <Icon color="warning" fontSize="small" />
            <Typography variant="body2" fontWeight={700}>{label}</Typography>
            <Typography variant="body2" color="text.secondary">{detail}</Typography>
          </Box>
        ))}
      </Stack>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
        保存失敗時以上狀態及操作會保留，供修正後重試。
      </Typography>
    </Box>
  );
};

export const StaggerSpanVisual: React.FC = () => (
  <Box component="figure" sx={{ m: 0 }} aria-labelledby="stagger-span-title">
    <Typography id="stagger-span-title" variant="subtitle2" component="h4" gutterBottom>
      Stagger 支點與 span 判斷
    </Typography>
    <Box sx={{ position: 'relative', py: 2.5, px: 2 }} aria-hidden="true">
      <Box sx={{ position: 'absolute', top: '50%', left: 28, right: 28, borderTop: 3, borderColor: 'primary.main' }} />
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', position: 'relative' }}>
        {['SPT A', 'SPT I', 'SPT B'].map((support) => (
          <Box key={support} sx={{ textAlign: 'center' }}>
            <Box sx={{ width: 14, height: 14, borderRadius: '50%', bgcolor: 'primary.main', mx: 'auto', mb: 1 }} />
            <Typography variant="caption" fontWeight={700}>{support}</Typography>
          </Box>
        ))}
      </Box>
    </Box>
    <TableContainer>
      <Table size="small" aria-label="Stagger span 判斷表">
        <TableHead><TableRow><TableCell>條件</TableCell><TableCell>結果</TableCell></TableRow></TableHead>
        <TableBody>
          <TableRow><TableCell>SPT A、I 或 B 缺失</TableCell><TableCell>partial trace + n/a</TableCell></TableRow>
          <TableRow><TableCell>s &gt;= 4b</TableCell><TableCell>pass_short_circuit</TableCell></TableRow>
          <TableRow><TableCell>p &lt;= allowable</TableCell><TableCell>pass</TableCell></TableRow>
          <TableRow><TableCell>p &gt; allowable</TableCell><TableCell>fail</TableCell></TableRow>
          <TableRow><TableCell>任一 span fail</TableCell><TableCell>overall fail</TableCell></TableRow>
        </TableBody>
      </Table>
    </TableContainer>
  </Box>
);
