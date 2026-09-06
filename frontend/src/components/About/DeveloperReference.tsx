import React from 'react';
import {
  Alert,
  Box,
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

import type { DiagnosticsResponse } from '../../types/api';
import {
  apiOwnershipRows,
  architectureLayers,
  blockingErrorRows,
  check1YearDecisionRows,
  contractRows,
  guideSourceReferences,
  versionDifferenceLimits,
  verificationRows,
  metadataCanonicalRows,
} from './aboutGuideContent';
import DiagnosticsPanel from './DiagnosticsPanel';
import { GuideFlow } from './GuideVisuals';
import architectureOverview from '../../assets/tov1050-architecture-overview.png';
import dataFlowDiagram from '../../assets/tov1050-data-flow.png';

interface DeveloperReferenceProps {
  diagnostics: DiagnosticsResponse | null;
  diagnosticsLoading: boolean;
  diagnosticsError: string;
}

const sectionSx = { scrollMarginTop: 16, py: 3 } as const;

const DeveloperReference: React.FC<DeveloperReferenceProps> = ({
  diagnostics,
  diagnosticsLoading,
  diagnosticsError,
}) => (
  <Box>
    <Typography variant="h5" component="h2" fontWeight={700} gutterBottom>
      開發者參考
    </Typography>
    <Typography color="text.secondary" sx={{ maxWidth: '76ch', mb: 1 }}>
      說明 runtime 邊界、API 與 state ownership、不可弱化的資料合約、錯誤分類、回歸層與目前執行環境。這裡只記錄已由 production code 或 tests 證實的規則。
    </Typography>

    <Stack divider={<Divider flexItem />}>
      <Box component="section" id="developer-architecture" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>Runtime architecture</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          Desktop shell 與 browser UI 分離；frontend 不直接讀取 SQLite 或 metadata workbook，所有業務資料均通過本機 FastAPI。About guide 本身是 React runtime，不再依賴 iframe 內容。
        </Typography>
        <GuideFlow steps={architectureLayers} label="TOV640 Analyzer runtime layers" desktopColumns={3} />
        <Box
          component="img"
          src={architectureOverview}
          alt="TOV1050 Analyzer architecture: inputs, metadata adapter, full-fidelity detector, chart envelope and Electron React frontend"
          sx={{ display: 'block', width: '100%', maxWidth: 980, height: 'auto', mt: 2, border: 1, borderColor: 'divider' }}
        />
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.75 }}>
          圖中顯示五層 runtime 邊界；告警判定使用完整資料，Graph 才採 envelope 與 zoom LOD。
        </Typography>
        <Typography variant="subtitle1" component="h4" fontWeight={700} sx={{ mt: 3, mb: 1 }}>
          端到端資料流
        </Typography>
        <Box
          component="img"
          src={dataFlowDiagram}
          alt="TOV1050 Analyzer data flow from raw CSV through streaming loader, Chainage metre adapter, metadata mapping, detector and chart payload"
          sx={{ display: 'block', width: '100%', maxWidth: 980, height: 'auto', mb: 2, border: 1, borderColor: 'divider' }}
        />
        <TableContainer>
          <Table size="small" aria-label="端到端資料流">
            <TableHead><TableRow><TableCell>入口</TableCell><TableCell>主要處理</TableCell><TableCell>輸出</TableCell></TableRow></TableHead>
            <TableBody>
              <TableRow><TableCell>.datac</TableCell><TableCell>DataLoader → MetadataManager → ExceptionDetector</TableCell><TableCell>異常表、Boundary、ChartData</TableCell></TableRow>
              <TableRow><TableCell>多期 Exception Reports</TableCell><TableCell>compare → repeated chain → 1 Year check</TableCell><TableCell>Previous N、action、reoccurrence_id</TableCell></TableRow>
              <TableRow><TableCell>Wear complete cycle</TableCell><TableCell>parse → resolver index → scope → conflict → coverage</TableCell><TableCell>preview、cycle records、segments、digest</TableCell></TableRow>
              <TableRow><TableCell>Trend files</TableCell><TableCell>L2 candidate → daily minimum → regression</TableCell><TableCell>trend points、logic_1/2、recommendation</TableCell></TableRow>
              <TableRow><TableCell>Stagger workbook</TableCell><TableCell>candidate → support lookup → span formulas</TableCell><TableCell>results、traces、warnings</TableCell></TableRow>
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      <Box component="section" id="developer-version-difference" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>Version Difference API contract</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          `/api/analyze/version-difference` 接受 Latest 及最多四個 Previous multipart files。Parser 僅讀取 Chainage、height1-4、stagger1-4、wear1-4，Latest 的 normalized prepared representation 會重用於四個 comparisons。
        </Typography>
        <TableContainer sx={{ mb: 2 }}>
          <Table size="small" aria-label="Version Difference API limits">
            <TableHead><TableRow><TableCell>Contract</TableCell><TableCell>Required behavior</TableCell></TableRow></TableHead>
            <TableBody>{versionDifferenceLimits.map((row) => (
              <TableRow key={row.cells[0]}><TableCell>{row.cells[0]}</TableCell><TableCell>{row.cells[1]}</TableCell></TableRow>
            ))}</TableBody>
          </Table>
        </TableContainer>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch' }}>
          Alignment 先以完整資料計算 shift、RMSE、coverage 與 overlap，再以 deterministic shared-index min/max envelope 將圖表 arrays 限制在 8,000 點。response 另外提供 source_points、display_points、downsampled。Dense path 上限為 640,000 normalized ticks；sparse path 受 unique observed ticks × 401 不超過 25,000,000 probes 的 hard budget 保護。
        </Typography>
      </Box>

      <Box component="section" id="developer-tov1050-contract" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>TOV1050 metadata 與分析契約</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          Metadata adapter 將現場 workbook 正規化為 detector canonical model。分析與匯出則以 request 的表格 context 為 source of truth，原始 filename 只保留作 lineage。
        </Typography>
        <TableContainer>
          <Table size="small" aria-label="TOV1050 canonical metadata contract">
            <TableHead><TableRow><TableCell>契約</TableCell><TableCell>Required behavior</TableCell></TableRow></TableHead>
            <TableBody>{metadataCanonicalRows.map((row) => (
              <TableRow key={row.cells[0]}><TableCell>{row.cells[0]}</TableCell><TableCell>{row.cells[1]}</TableCell></TableRow>
            ))}</TableBody>
          </Table>
        </TableContainer>
        <Alert severity="info" sx={{ mt: 2 }}>
          Canonical filename parser 仍保留給標準報表與單元測試；任意合法 CSV basename 不應成為分析的阻擋條件。
        </Alert>
      </Box>

      <Box component="section" id="developer-check-1-year" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>Check 1 Year API 與 staged contract</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          `POST /database/repeated-records/check-1-year` 回傳每列 `check_1_year_status` 與分類 counts：checked、match、auto_verified、review_required、keep_monitoring、unmatched、skipped。counts 總和必須等於 exceptions 數量；Check 階段不寫入 review proposal 的 target。
        </Typography>
        <TableContainer sx={{ mb: 2 }}>
          <Table size="small" aria-label="Check 1 Year API decision matrix">
            <TableHead><TableRow><TableCell>Family／level</TableCell><TableCell>Decision rule</TableCell></TableRow></TableHead>
            <TableBody>{check1YearDecisionRows.map((row) => (
              <TableRow key={row.cells[0]}><TableCell>{row.cells[0]}</TableCell><TableCell>{row.cells[1]}</TableCell></TableRow>
            ))}</TableBody>
          </Table>
        </TableContainer>
        <Alert severity="warning" sx={{ mb: 2 }}>
          review proposal 必須攜帶 target record_id、target exception_id 與 target version。Save to DB 只接受 Save Edit 後的 approved links；target 不存在或 version 不一致回 409，整批 rollback 且保留 frontend staged state。
        </Alert>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch' }}>
          Automatic recurrence append 解析 comma-separated IDs、去重並維持原順序。相同 target 的多個 links 只驗證一次，所有 current exception IDs 於單一 transaction 中一次更新；任何錯誤都不會留下部分 current records 或 historical links。
        </Typography>
      </Box>

      <Box component="section" id="developer-api-state" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>API 與 frontend state ownership</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          Zustand stores 保存 workflow state 與 API 結果，不重新實作 backend 演算法。wire format 的 snake_case 在 API client boundary 映射為 UI-facing camelCase contract。
        </Typography>
        <TableContainer>
          <Table size="small" aria-label="API 與 state ownership matrix">
            <TableHead>
              <TableRow><TableCell>Workflow</TableCell><TableCell>Frontend owner</TableCell><TableCell>API boundary</TableCell><TableCell>Backend owner</TableCell></TableRow>
            </TableHead>
            <TableBody>
              {apiOwnershipRows.map((row) => (
                <TableRow key={row.cells[0]}>{row.cells.map((cell) => <TableCell key={cell}>{cell}</TableCell>)}</TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      <Box component="section" id="developer-contracts" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>不可弱化的資料合約</Typography>
        <Alert severity="warning" sx={{ mb: 2 }}>
          不可轉換 Chainage、擴闊 interval、使用 nearest interval、加入一般 Mainline fallback，或只以 canonical Track 判斷 MAINLINE。
        </Alert>
        <TableContainer>
          <Table size="small" aria-label="資料合約矩陣">
            <TableHead><TableRow><TableCell>Contract</TableCell><TableCell>Required behavior</TableCell></TableRow></TableHead>
            <TableBody>
              {contractRows.map((row) => (
                <TableRow key={row.cells[0]}><TableCell>{row.cells[0]}</TableCell><TableCell>{row.cells[1]}</TableCell></TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2, maxWidth: '76ch' }}>
          TL scope 是 line-specific：MAINLINE 繼續，SIDING 預期排除，UNKNOWN fail closed。`Neutral Section` 是 SIDING；canonical Track 為 `Siding` 的合法 mainline identity 仍按 physical intervals 保留。
        </Typography>
      </Box>

      <Box component="section" id="developer-errors" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>錯誤分類與 diagnostics contract</Typography>
        <TableContainer sx={{ mb: 2 }}>
          <Table size="small" aria-label="Blocking error taxonomy">
            <TableHead><TableRow><TableCell>Blocking error</TableCell><TableCell>Actionable context</TableCell></TableRow></TableHead>
            <TableBody>
              {blockingErrorRows.map((row) => (
                <TableRow key={row.cells[0]}><TableCell>{row.cells[0]}</TableCell><TableCell>{row.cells[1]}</TableCell></TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <Alert severity="info">
          Approved SIDING 是 non-blocking exclusion，不會出現在 results、conflicts、coverage、Expected TLs、Diagnostic Gaps、save 或 export。
        </Alert>
      </Box>

      <Box component="section" id="developer-verification" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>回歸與交付驗證層</Typography>
        <TableContainer>
          <Table size="small" aria-label="驗證層矩陣">
            <TableHead><TableRow><TableCell>Layer</TableCell><TableCell>Coverage</TableCell></TableRow></TableHead>
            <TableBody>
              {verificationRows.map((row) => (
                <TableRow key={row.cells[0]}><TableCell>{row.cells[0]}</TableCell><TableCell>{row.cells[1]}</TableCell></TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <Typography variant="subtitle1" component="h4" fontWeight={700} sx={{ mt: 3, mb: 1 }}>
          維護來源
        </Typography>
        <Box component="ul" sx={{ m: 0, pl: 2.5, columns: { md: 2 }, columnGap: 3 }}>
          {guideSourceReferences.map((source) => (
            <Typography component="li" variant="body2" key={source} sx={{ mb: 0.75, breakInside: 'avoid' }}>
              <code>{source}</code>
            </Typography>
          ))}
        </Box>
      </Box>

      <Box component="section" id="developer-diagnostics" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>目前執行環境</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          此區直接讀取 backend `/api/diagnostics`。載入或連線失敗只影響此面板，不會隱藏任何指南內容。
        </Typography>
        <DiagnosticsPanel diagnostics={diagnostics} loading={diagnosticsLoading} error={diagnosticsError} />
      </Box>
    </Stack>
  </Box>
);

export default DeveloperReference;
