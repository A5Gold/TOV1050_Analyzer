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
  measurementFlow,
  dualSystemCleaningRows,
  chartContractRows,
} from './aboutGuideContent';
import DiagnosticsPanel from './DiagnosticsPanel';
import { GuideFlow } from './GuideVisuals';

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
        <GuideFlow steps={architectureLayers} label="雙系統 Analyzer runtime layers" desktopColumns={3} />
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.75 }}>
          正常分析使用完整的中位代表資料偵測例外並匯出；只有圖表 payload 使用 envelope。Raw overview 是獨立模式，不進行例外偵測。
        </Typography>
        <Typography variant="subtitle1" component="h4" fontWeight={700} sx={{ mt: 3, mb: 1 }}>
          端到端資料流
        </Typography>
        <GuideFlow steps={measurementFlow} label="共同量測與分析資料流" desktopColumns={4} />
        <TableContainer>
          <Table size="small" aria-label="端到端資料流">
            <TableHead><TableRow><TableCell>入口</TableCell><TableCell>主要處理</TableCell><TableCell>輸出</TableCell></TableRow></TableHead>
            <TableBody>
              <TableRow><TableCell>.datac / .csv</TableCell><TableCell>格式 loader → context/metadata → median → detector</TableCell><TableCell>同 revision 異常表、Boundary、ChartData、_Metadata</TableCell></TableRow>
              <TableRow><TableCell>多期 Exception Reports</TableCell><TableCell>compare → repeated chain → 1 Year check</TableCell><TableCell>Previous N、action、reoccurrence_id</TableCell></TableRow>
              <TableRow><TableCell>Wear complete cycle</TableCell><TableCell>parse → resolver index → scope → conflict → coverage</TableCell><TableCell>preview、cycle records、segments、digest</TableCell></TableRow>
              <TableRow><TableCell>Trend files</TableCell><TableCell>L2 candidate → daily minimum → regression</TableCell><TableCell>trend points、logic_1/2、recommendation</TableCell></TableRow>
              <TableRow><TableCell>Stagger workbook</TableCell><TableCell>ReportContext → capability preflight → candidate/support/span</TableCell><TableCell>已配置 results/traces；未配置明確列缺項</TableCell></TableRow>
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
        <Typography variant="h6" component="h3" gutterBottom>雙系統 metadata 與分析契約</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '76ch', mb: 2 }}>
          路線 registry 有九個 parent Line。LMC 是 EAL 分支、TKS 是 TKL 分支、DRL branch UT 對應 legacy Mainline；branch UT 與 direction UT 分別保存。Metadata adapter 將各格式 workbook 正規化為 detector model；原始資料採表單 context，下游採 workbook context，衝突不可由 filename 靜默覆蓋。
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

      <Box component="section" id="developer-cleaning" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>格式清洗與中位實測樣本</Typography>
        <TableContainer><Table size="small" aria-label="DATAC CSV cleaning differences">
          <TableHead><TableRow><TableCell>規則</TableCell><TableCell>TOV640 DATAC</TableCell><TableCell>TOV1050 CSV</TableCell></TableRow></TableHead>
          <TableBody>{dualSystemCleaningRows.map(row => (
            <TableRow key={row.cells[0]}>{row.cells.map(cell => <TableCell key={cell}>{cell}</TableCell>)}</TableRow>
          ))}</TableBody>
        </Table></TableContainer>
        <Typography variant="body2" sx={{ mt: 2, maxWidth: '76ch' }}>
          same_chainage_median_sample_v1 按採集次序建立相鄰、精確同 chainage 群，遇 context／pass／segment／來源連續性改變便分群；非相鄰重訪不合併。每 channel 排除 nonfinite 後選真實中位樣本，偶數在中間兩個來源樣本取採集較早者，不求平均。保留 channel_source_row、sample counter、valid_count 及群樣本數；各 channel 可以來自不同列。
        </Typography>
        <Typography variant="body2" sx={{ mt: 1.5, maxWidth: '76ch' }}>
          Detector、threshold crossing、peak、Excel 與 ChartData 消費同一份代表資料；min/max envelope 只縮小 UI payload。來源行數、清洗保留行數、代表群數、圖表顯示點數是不同指標，不能共用同一個 raw_row_count 解讀。
        </Typography>
      </Box>

      <Box component="section" id="developer-chart" sx={sectionSx}>
        <Typography variant="h6" component="h3" gutterBottom>圖表、背景工作與快照生命週期</Typography>
        <TableContainer><Table size="small" aria-label="Chart snapshot and cache contract">
          <TableHead><TableRow><TableCell>邊界</TableCell><TableCell>行為</TableCell></TableRow></TableHead>
          <TableBody>{chartContractRows.map(row => (
            <TableRow key={row.cells[0]}><TableCell>{row.cells[0]}</TableCell><TableCell>{row.cells[1]}</TableCell></TableRow>
          ))}</TableBody>
        </Table></TableContainer>
        <Typography variant="body2" sx={{ mt: 2, maxWidth: '76ch' }}>
          分析及報表匯出以 background job 回報 stage/progress；匯出只提交 client_session_id、analysis_revision 及 mode，由後端快照重建完整報表。detail 的有限 range 正規化後與 chart_domain 取交集；UI debounce 250ms、AbortController 與 generation guard 隔離舊回覆。後端數值索引每 revision 準備一次，window cache 有界。Raw 快取過期需重讀完整來源，detail timeout 為 120 秒並提供載入提示與取消；median 維持 30 秒。冷／熱效能須分開量度。
        </Typography>
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
          原始座標只在格式 adapter 轉成公尺一次；下游不可重複換算、擴闊 interval、使用 nearest interval、加入一般 Mainline fallback，或只以 canonical Track 判斷 MAINLINE。
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
