import React from 'react';
import {
  Alert,
  Box,
  Chip,
  Divider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';

import {
  blockingErrorRows,
  check1YearDecisionRows,
  check1YearStatuses,
  operatorWorkflowSteps,
  versionDifferenceLimits,
  versionDifferenceRoles,
  tov1050InputRows,
} from './aboutGuideContent';
import {
  CoverageExample,
  GuideFlow,
  OneYearWindowVisual,
  RepeatChainTimeline,
  StagedChangesVisual,
  StaggerSpanVisual,
  ThresholdRangeChart,
  WearResolutionVisual,
} from './GuideVisuals';
import operatorWorkflowDiagram from '../../assets/tov1050-operator-workflow.png';

const sectionSx = { scrollMarginTop: 16, py: 3 } as const;

const OperatorGuide: React.FC = () => (
  <Box>
    <Typography variant="h5" component="h2" fontWeight={700} gutterBottom>
      操作指南
    </Typography>
    <Typography color="text.secondary" sx={{ maxWidth: '76ch', mb: 1 }}>
      按實際工作次序由匯入、位置對齊及六類判斷，走到 conflict、coverage、保存、匯出與錯誤診斷。所有計算規則仍以 backend 與測試為準。
    </Typography>

    <Stack divider={<Divider flexItem />}>
      <Box component="section" id="operator-workflow" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>從資料到行動</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          選檔後先確認 Line、日期與 metadata 範圍。預覽是作出保存決定的必要步驟，不應直接略過 conflict、blocking reason 或 trace。
        </Typography>
        <GuideFlow steps={operatorWorkflowSteps} label="TOV640 Analyzer 操作流程" desktopColumns={5} />
        <Box
          component="img"
          src={operatorWorkflowDiagram}
          alt="TOV1050 Exception Generator operator workflow from selecting a run preset through reviewing Graph and Table and exporting a report"
          sx={{ display: 'block', width: '100%', maxWidth: 980, height: 'auto', mt: 2, border: 1, borderColor: 'divider' }}
        />
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.75 }}>
          Run preset 僅提供快速填入；特殊案例仍可直接編輯 Track、Station 與 Task 欄位。
        </Typography>
      </Box>

      <Box component="section" id="operator-tov1050-input" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>TOV1050 輸入與輸出</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          原始量測 CSV 的檔名可能來自設備或現場流程，不一定是報表名稱。請在輸入表格確認業務參數；系統會用這些參數分析與產生可供其他模組使用的輸出檔名。
        </Typography>
        <TableContainer>
          <Table size="small" aria-label="TOV1050 input and output contract">
            <TableHead><TableRow><TableCell>項目</TableCell><TableCell>行為</TableCell></TableRow></TableHead>
            <TableBody>{tov1050InputRows.map((row) => (
              <TableRow key={row.cells[0]}><TableCell>{row.cells[0]}</TableCell><TableCell>{row.cells[1]}</TableCell></TableRow>
            ))}</TableBody>
          </Table>
        </TableContainer>
        <Alert severity="warning" sx={{ mt: 2 }}>
          若缺少日期、Line、Direction、Session 或 Station range，請先補齊表格欄位；不要嘗試修改原始 CSV 檔名來繞過提示。
        </Alert>
      </Box>

      <Box component="section" id="operator-version-difference" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>Version Difference</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          用固定 cycle role 比較最多五份 ChartData 報表。先上傳 Latest，再依 Previous 1 至 Previous 4 的時間順序加入檔案；缺少 Previous 或 metric 時保留 partial result，不以猜測值補齊。
        </Typography>
        <GuideFlow steps={versionDifferenceRoles} label="Version Difference cycle 與軸線規則" desktopColumns={4} />
        <TableContainer sx={{ mt: 2 }}>
          <Table size="small" aria-label="Version Difference limits">
            <TableHead><TableRow><TableCell>項目</TableCell><TableCell>限制與行為</TableCell></TableRow></TableHead>
            <TableBody>{versionDifferenceLimits.map((row) => (
              <TableRow key={row.cells[0]}><TableCell>{row.cells[0]}</TableCell><TableCell>{row.cells[1]}</TableCell></TableRow>
            ))}</TableBody>
          </Table>
        </TableContainer>
        <Alert severity="info" sx={{ mt: 2 }}>
          X 軸拖曳或 autorange 會同步所有圖；Y 軸縮放只影響目前圖。Reset zoom 會清除共用 X 與全部 Y；切換 metric 或 response 會重新建立軸線狀態。
        </Alert>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5, maxWidth: '76ch' }}>
          400 表示檔案格式或 workbook 無法讀取，413 表示 bytes 超限，422 表示缺少 Chainage、超過列數或 alignment 工作量限制。錯誤訊息會標示檔案角色，請依 detail 修正後重試。
        </Typography>
      </Box>

      <Box component="section" id="operator-threshold" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>Threshold 異常判定</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          原始量測先按 chainage 取得最壞值，再對照 metadata threshold。Low Height 與 Wire Wear 值愈低愈嚴重，High Height 值愈高愈嚴重；Stagger 依 Tangent 或 Curve threshold 比左右絕對值。
        </Typography>
        <TableContainer sx={{ mb: 2 }}>
          <Table size="small" aria-label="Threshold 判斷次序">
            <TableHead><TableRow><TableCell>類型</TableCell><TableCell>Gatekeeper</TableCell><TableCell>等級次序</TableCell></TableRow></TableHead>
            <TableBody>
              <TableRow><TableCell>Low Height / Wire Wear</TableCell><TableCell>row value &lt;= max(L1, L2)</TableCell><TableCell>先 L1，再 L2</TableCell></TableRow>
              <TableRow><TableCell>High Height</TableCell><TableCell>row value &gt;= min(L1, L2)</TableCell><TableCell>先 L1，再 L2</TableCell></TableRow>
              <TableRow><TableCell>Stagger Left / Right</TableCell><TableCell>跨過最外層 L1/L2/L3</TableCell><TableCell>先 L1，再 L2，最後 L3</TableCell></TableRow>
            </TableBody>
          </Table>
        </TableContainer>
        <ThresholdRangeChart />
      </Box>

      <Box component="section" id="operator-repeat" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>Repeat 配對</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          Repeat 必須同 exception type、區間有交集，而且最新與舊報表的兩個 peak 都落在交集。最新報表作為 accumulator，只有每一輪仍匹配的列才會延伸到 Previous N。
        </Typography>
        <RepeatChainTimeline />
        <Alert severity="info" sx={{ mt: 2 }}>
          區間有交集但任一 peak 飄出交集時，該列不會進入 repeated chain。
        </Alert>
      </Box>

      <Box component="section" id="operator-year" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>1 Year 追蹤</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          Check 1 Year 只在目前異常日期前 365 日（含兩端）尋找同 line、track、section、family、level 與位置的候選。Stagger Left／Right 可互配，Low Height／High Height 不可互配；已有非 Pending ACTION 不會被靜默改寫。
        </Typography>
        <OneYearWindowVisual />
        <Typography variant="subtitle1" component="h4" fontWeight={700} sx={{ mt: 3, mb: 1 }}>
          Decision matrix
        </Typography>
        <TableContainer>
          <Table size="small" aria-label="Check 1 Year decision matrix">
            <TableHead><TableRow><TableCell>Family／level</TableCell><TableCell>規則</TableCell></TableRow></TableHead>
            <TableBody>{check1YearDecisionRows.map((row) => (
              <TableRow key={row.cells[0]}><TableCell>{row.cells[0]}</TableCell><TableCell>{row.cells[1]}</TableCell></TableRow>
            ))}</TableBody>
          </Table>
        </TableContainer>
        <GuideFlow steps={check1YearStatuses} label="Check 1 Year 結果分類" desktopColumns={4} />
        <Alert severity="warning" sx={{ mt: 2 }}>
          review_required 會顯示粉紅 review row、橙色 proposed 欄位及 warning icon。先用 Save Edit 接受 staged changes，再用 Save to DB 寫入；Discard 只恢復本次 proposal，不會寫入資料庫。
        </Alert>
      </Box>

      <Box component="section" id="operator-wear" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>Wear 預覽、分類與覆蓋率</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          Analysis 接受 EAL 或 TML complete-cycle 檔案。位置解析、張力段 scope、identity 去重與 conflict acceptance 完成後，才產生 cycle records 與 MAINLINE-only coverage。
        </Typography>
        <Stack spacing={3}>
          <WearResolutionVisual />
          <CoverageExample />
        </Stack>
      </Box>

      <Box component="section" id="operator-trend-stagger" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>Trend 與 Stagger</Typography>
        <Typography variant="subtitle1" component="h4" fontWeight={700} gutterBottom>Wire Wear L2 Trend</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 1.5 }}>
          Trend 只分析最新週期、ACTION 空白的 L2 Wire Wear 候選；Case B 另要求 ID 出現在 n_Repeated。每個日期在區間內取 wear_min 最小值，再做線性回歸。
        </Typography>
        <TableContainer sx={{ mb: 3 }}>
          <Table size="small" aria-label="Trend recommendation 決策表">
            <TableHead><TableRow><TableCell>條件</TableCell><TableCell>Recommendation</TableCell></TableRow></TableHead>
            <TableBody>
              <TableRow><TableCell>fitted value &gt; 10.2</TableCell><TableCell>no action required</TableCell></TableRow>
              <TableRow><TableCell>fitted value &lt;= 10.2，且與最新值相差 &gt; 0.2</TableCell><TableCell>verify on site</TableCell></TableRow>
              <TableRow><TableCell>fitted value &lt;= 10.2，且與最新值相差 &lt;= 0.2</TableCell><TableCell>confirmed valid L2</TableCell></TableRow>
            </TableBody>
          </Table>
        </TableContainer>
        <Typography variant="subtitle1" component="h4" fontWeight={700} gutterBottom>Stagger span</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 1.5 }}>
          Stagger 只選 L1/L2 的 Left 或 Right 候選。Case B 必須 repeated summary 有相同 ID；系統再以 chi 找 SPT A、I、B，計算 AI 與 IB span，並保留完整或 partial trace。
        </Typography>
        <StaggerSpanVisual />
      </Box>

      <Box component="section" id="operator-save" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>保存、匯出與拒絕診斷</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          Wear cycle 只有在位置已解析、UNKNOWN 為零、conflict 全部接受、preview_digest 與 data_version 仍有效時才可原子保存。保存後的 Excel 與 sync package 使用同一已提交資料。
        </Typography>
        <Stack spacing={3}>
          <StagedChangesVisual />
          <Box>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="subtitle2" component="h4">常見 blocking reason</Typography>
              <Chip label="不會自動 fallback" size="small" variant="outlined" />
            </Stack>
            <TableContainer>
              <Table size="small" aria-label="常見 blocking reason 與處理方法">
                <TableHead><TableRow><TableCell>問題</TableCell><TableCell>處理方法</TableCell></TableRow></TableHead>
                <TableBody>
                  {blockingErrorRows.map((row) => (
                    <TableRow key={row.cells[0]}><TableCell>{row.cells[0]}</TableCell><TableCell>{row.cells[1]}</TableCell></TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        </Stack>
      </Box>
    </Stack>
  </Box>
);

export default OperatorGuide;
