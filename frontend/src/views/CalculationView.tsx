import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  IconButton,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import InsightsOutlinedIcon from '@mui/icons-material/InsightsOutlined';
import UploadFileOutlinedIcon from '@mui/icons-material/UploadFileOutlined';
import WarningAmberOutlinedIcon from '@mui/icons-material/WarningAmberOutlined';
import CheckCircleOutlineOutlinedIcon from '@mui/icons-material/CheckCircleOutlineOutlined';
import RuleFolderOutlinedIcon from '@mui/icons-material/RuleFolderOutlined';
import DownloadOutlinedIcon from '@mui/icons-material/DownloadOutlined';
import CycleTabBar, { CycleTabItem } from '../components/Calculation/CycleTabBar';
import StaggerAlgorithmDialog from '../components/Calculation/StaggerAlgorithmDialog';
import StaggerRawDataPanel from '../components/Calculation/StaggerRawDataPanel';
import { exportStaggerResults } from '../components/Calculation/staggerExport';
import { useCalculationStore } from '../store/useCalculationStore';
import { scrollablePageSx } from '../utils/pageLayout';

const resultColorMap: Record<string, 'success' | 'error' | 'default'> = {
  pass: 'success',
  fail: 'error',
  'n/a': 'default',
};

const statusColorMap: Record<string, 'success' | 'warning'> = {
  complete: 'success',
  partial: 'warning',
};

const stickyColumnSx = {
  position: 'sticky',
  left: 0,
  backgroundColor: 'background.paper',
  zIndex: 4,
  minWidth: 120,
  boxShadow: '1px 0 0 rgba(15, 23, 42, 0.08)',
};

const stickyColumnOffset = (offset: number) => ({
  position: 'sticky',
  left: offset,
  backgroundColor: 'background.paper',
  zIndex: 4,
  boxShadow: '1px 0 0 rgba(15, 23, 42, 0.08)',
});

const formatValue = (value: string | number | null | undefined) => (
  value == null ? '-' : String(value)
);

const formatNumber = (value: number | null | undefined, digits?: number) => {
  if (value == null || Number.isNaN(value)) {
    return '-';
  }
  return typeof digits === 'number' ? value.toFixed(digits) : String(value);
};

const formatTraceNumber = (value: unknown, digits = 2) => (
  typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '-'
);

const isPassingSpanResult = (result: unknown) => {
  const normalized = String(result ?? '').toLowerCase();
  return normalized === 'pass' || normalized === 'pass_short_circuit';
};

const describeFailingCriteria = (spans: Record<string, any> | undefined) => {
  const failedKeys = (['ai', 'ib'] as const).filter((key) => {
    const result = spans?.[key]?.result;
    return result && !isPassingSpanResult(result);
  });

  if (!failedKeys.length) {
    return 'AI and IB passed the stagger criteria. Short-circuit spans may pass by S >= 4B even when P > Allowable.';
  }

  return `${failedKeys.map((key) => key.toUpperCase()).join(' and ')} did not pass the stagger criteria.`;
};

const CalculationView: React.FC = () => {
  const {
    cycles,
    activeCycleId,
    setActiveCycle,
    createCycle,
    closeCycle,
    setUploadedFile,
    removeUploadedFile,
    setRepeatedFile,
    setSelectedResult,
    analyze,
    setDetailTab,
    resetActiveCycle,
  } = useCalculationStore();

  const [algoOpen, setAlgoOpen] = useState(false);
  const [isMainDragOver, setIsMainDragOver] = useState(false);
  const [isRepeatedDragOver, setIsRepeatedDragOver] = useState(false);
  const mainInputRef = useRef<HTMLInputElement>(null);
  const repeatedInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const preventBrowserDrop = (event: DragEvent) => {
      event.preventDefault();
    };
    window.addEventListener('dragover', preventBrowserDrop);
    window.addEventListener('drop', preventBrowserDrop);
    return () => {
      window.removeEventListener('dragover', preventBrowserDrop);
      window.removeEventListener('drop', preventBrowserDrop);
    };
  }, []);

  const activeCycle = cycles.find((cycle) => cycle.id === activeCycleId) ?? cycles[0];
  const selectedResult = activeCycle.results.find((result) => result.id === activeCycle.selectedResultId) ?? activeCycle.results[0] ?? null;
  const selectedTraceIndex = selectedResult
    ? activeCycle.results.findIndex((result) => result.id === selectedResult.id)
    : -1;
  const selectedTrace = selectedTraceIndex >= 0 ? activeCycle.traces[selectedTraceIndex] ?? null : null;

  const cycleTabs: CycleTabItem[] = useMemo(
    () => cycles.map((cycle) => ({ id: cycle.id, label: cycle.name })),
    [cycles],
  );

  const summaryCards = [
    {
      label: '已上傳檔案',
      value: (activeCycle.uploadedFiles.length ? 1 : 0) + (activeCycle.repeatedFile ? 1 : 0),
      icon: <UploadFileOutlinedIcon fontSize="small" />,
    },
    {
      label: '結果數',
      value: activeCycle.results.length,
      icon: <CheckCircleOutlineOutlinedIcon fontSize="small" />,
    },
    {
      label: '部分 Trace',
      value: activeCycle.results.filter((result) => result.trace_status === 'partial').length,
      icon: <WarningAmberOutlinedIcon fontSize="small" />,
    },
    {
      label: '分析模式',
      value: activeCycle.repeatedFile ? 'Case A / B' : 'Case A',
      icon: <RuleFolderOutlinedIcon fontSize="small" />,
    },
  ];

  const handleMainDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsMainDragOver(false);
    const droppedFile = event.dataTransfer.files?.[0];
    if (droppedFile) {
      setUploadedFile(droppedFile);
    }
  };

  const handleRepeatedDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsRepeatedDragOver(false);
    const droppedFile = event.dataTransfer.files?.[0];
    if (droppedFile) {
      setRepeatedFile(droppedFile);
    }
  };

  const handleSelectResult = (resultId: string, tab?: number) => {
    setSelectedResult(resultId);
    if (typeof tab === 'number') {
      setDetailTab(tab);
    }
  };

  const handleAnalyzeClick = () => {
    void analyze().catch(() => {
      // Store state already captures the user-facing error message.
    });
  };

  return (
    <Box sx={scrollablePageSx}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2 }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>
            拉出值計算
          </Typography>
          <Typography variant="body2" color="text.secondary">
            以 cycle 為單位上傳 Exception Report，檢視結果摘要、trace 與局部 Raw Data，方便逐筆追蹤拉出值判定過程。
          </Typography>
        </Box>
        <Tooltip title="說明拉出值判定演算法">
          <IconButton aria-label="Explain the algorithm" onClick={() => setAlgoOpen(true)} color="primary">
            <InfoOutlinedIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {activeCycle.error && <Alert severity="error">{activeCycle.error}</Alert>}
      {activeCycle.warnings.map((warning) => (
        <Alert key={warning} severity="warning">{warning}</Alert>
      ))}

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Stack spacing={1.5}>
            <Alert severity="success" variant="outlined">
              <strong>Case A：</strong>只使用 Exception Report 的 Summary 與 ChartData 計算。
            </Alert>
            <Alert severity={activeCycle.repeatedFile ? 'info' : 'warning'} variant="outlined">
              <strong>Case B：</strong>額外上傳 n_Repeated Report，系統會結合 repeated data 補足候選支點與判定依據。
            </Alert>
          </Stack>

          <Grid container spacing={2}>
            <Grid item xs={12} md={7}>
              <Box
                data-testid="stagger-dropzone"
                onClick={() => mainInputRef.current?.click()}
                onDrop={handleMainDrop}
                onDragOver={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  setIsMainDragOver(true);
                }}
                onDragLeave={() => setIsMainDragOver(false)}
                sx={{
                  border: '2px dashed',
                  borderColor: isMainDragOver ? 'primary.main' : 'divider',
                  borderRadius: 2,
                  p: 3,
                  bgcolor: isMainDragOver ? 'action.hover' : 'background.paper',
                  cursor: 'pointer',
                  transition: 'border-color 150ms ease, background-color 150ms ease',
                }}
              >
                <Stack spacing={1}>
                  <Typography variant="subtitle1" fontWeight={700}>上傳 Exception Report</Typography>
                  <Typography variant="body2" color="text.secondary">
                    拖放或點擊上傳 `.xlsx` 檔案。系統會讀取 workbook 內的 Summary 與 ChartData 工作表進行拉出值分析。
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    必要工作表：Summary、ChartData；必要欄位包含 stagger1 至 stagger4 與 Chainage。
                  </Typography>
                </Stack>
                <input
                  ref={mainInputRef}
                  type="file"
                  accept=".xlsx"
                  hidden
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) {
                      setUploadedFile(file);
                    }
                    event.target.value = '';
                  }}
                />
              </Box>
            </Grid>

            <Grid item xs={12} md={5}>
              <Box
                data-testid="stagger-repeated-dropzone"
                onClick={() => repeatedInputRef.current?.click()}
                onDrop={handleRepeatedDrop}
                onDragOver={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  setIsRepeatedDragOver(true);
                }}
                onDragLeave={() => setIsRepeatedDragOver(false)}
                sx={{
                  border: '2px dashed',
                  borderColor: isRepeatedDragOver ? 'secondary.main' : 'divider',
                  borderRadius: 2,
                  p: 3,
                  bgcolor: isRepeatedDragOver ? 'action.hover' : 'background.paper',
                  cursor: 'pointer',
                  transition: 'border-color 150ms ease, background-color 150ms ease',
                }}
              >
                <Stack spacing={1}>
                  <Typography variant="subtitle1" fontWeight={700}>上傳 n_Repeated Report（選填）</Typography>
                  <Typography variant="body2" color="text.secondary">
                    用於 Case B。當需要補充 Stagger Left / Stagger Right 的 repeated data 時，請一併提供此報表。
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    未提供時仍可執行 Case A；提供後會以 repeated data 補強 stagger candidate 判定。
                  </Typography>
                </Stack>
                <input
                  ref={repeatedInputRef}
                  type="file"
                  accept=".xlsx"
                  hidden
                  onChange={(event) => {
                    setRepeatedFile(event.target.files?.[0] ?? null);
                    event.target.value = '';
                  }}
                />
              </Box>
            </Grid>
          </Grid>

          <CycleTabBar
            tabs={cycleTabs}
            activeId={activeCycleId}
            onChange={setActiveCycle}
            onAdd={createCycle}
            onClose={closeCycle}
            onReset={resetActiveCycle}
            resetLabel="重設目前 Cycle"
          />

          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ alignItems: 'center' }}>
            {activeCycle.uploadedFiles.map((file) => (
              <Chip
                key={file.name}
                label={file.name}
                size="small"
                color="primary"
                variant="outlined"
                onDelete={() => removeUploadedFile(file.name)}
              />
            ))}
            {activeCycle.repeatedFile && (
              <Chip
                label={`n_Repeated: ${activeCycle.repeatedFile.name}`}
                size="small"
                color="secondary"
                variant="outlined"
                onDelete={() => setRepeatedFile(null)}
              />
            )}
            <Button
              variant="contained"
              onClick={handleAnalyzeClick}
              disabled={!activeCycle.uploadedFiles.length || activeCycle.isLoading}
            >
              {activeCycle.isLoading ? '分析中...' : '開始分析'}
            </Button>
            <Button variant="outlined" onClick={() => mainInputRef.current?.click()}>
              上傳主檔
            </Button>
            <Button variant="outlined" onClick={() => repeatedInputRef.current?.click()}>
              上傳 n_Repeated
            </Button>
            <Button
              variant="outlined"
              startIcon={<DownloadOutlinedIcon />}
              onClick={() => exportStaggerResults(activeCycle.results)}
              disabled={activeCycle.results.length === 0}
            >
              Export Excel
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Grid container spacing={2}>
        {summaryCards.map((card) => (
          <Grid item xs={12} sm={6} md={3} key={card.label}>
            <Card variant="outlined" sx={{ height: '100%' }}>
              <CardContent sx={{ p: 2 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  {card.icon}
                  <Typography variant="caption" color="text.secondary">{card.label}</Typography>
                </Stack>
                <Typography variant="h5" fontWeight={700} sx={{ mt: 1 }}>
                  {card.value}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Paper sx={{ p: 2 }}>
        <Tabs value={activeCycle.detailTab} onChange={(_, value) => setDetailTab(value)} sx={{ mb: 2 }}>
          <Tab label="摘要" />
          <Tab label="追蹤" />
          <Tab label="原始資料" />
        </Tabs>

        {activeCycle.detailTab === 0 && (
          <Stack spacing={2}>
            <Alert severity="info">
              <strong>摘要</strong>會列出每筆結果、關鍵識別欄位、K_eq 與狀態。可透過「追蹤」或「原始資料」檢視所選 ID。
            </Alert>

            {!activeCycle.results.length ? (
              <Paper variant="outlined" sx={{ p: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  尚無拉出值結果。
                </Typography>
              </Paper>
            ) : (
              <Paper variant="outlined" sx={{ overflowX: 'auto' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={stickyColumnSx}>ID</TableCell>
                      <TableCell sx={stickyColumnOffset(120)}>結果</TableCell>
                      <TableCell sx={stickyColumnOffset(210)}>狀態</TableCell>
                      <TableCell align="right" sx={stickyColumnOffset(300)}>操作</TableCell>
                      <TableCell>執行日期</TableCell>
                      <TableCell>綫別</TableCell>
                      <TableCell>股道</TableCell>
                      <TableCell>區段</TableCell>
                      <TableCell>工作單號</TableCell>
                      <TableCell>起點站</TableCell>
                      <TableCell>終點站</TableCell>
                      <TableCell>FromM</TableCell>
                      <TableCell>ToM</TableCell>
                      <TableCell>長度</TableCell>
                      <TableCell>異常類型</TableCell>
                      <TableCell>最大值</TableCell>
                      <TableCell>最大位置</TableCell>
                      <TableCell>張力長度</TableCell>
                      <TableCell>軌道類型</TableCell>
                      <TableCell>等級</TableCell>
                      <TableCell>類別</TableCell>
                      <TableCell>門檻值</TableCell>
                      <TableCell>K_eq</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {activeCycle.results.map((result) => (
                      <TableRow
                        key={result.id}
                        hover
                        selected={result.id === selectedResult?.id}
                        onClick={() => handleSelectResult(result.id)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell sx={stickyColumnSx}>{result.id}</TableCell>
                        <TableCell sx={stickyColumnOffset(120)}>
                          <Chip size="small" label={result.overall_result} color={resultColorMap[result.overall_result]} />
                        </TableCell>
                        <TableCell sx={stickyColumnOffset(210)}>
                          <Chip
                            size="small"
                            label={result.trace_status ?? '-'}
                            color={statusColorMap[result.trace_status ?? 'partial'] ?? 'warning'}
                            variant={result.trace_status === 'complete' ? 'filled' : 'outlined'}
                          />
                        </TableCell>
                        <TableCell align="right" sx={stickyColumnOffset(300)}>
                          <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                            <Tooltip title="開啟追蹤">
                              <IconButton
                                size="small"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  handleSelectResult(result.id, 1);
                                }}
                              >
                                <InsightsOutlinedIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="開啟原始資料">
                              <IconButton
                                size="small"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  handleSelectResult(result.id, 2);
                                }}
                              >
                                <VisibilityOutlinedIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Stack>
                        </TableCell>
                        <TableCell>{formatValue(result.run_date)}</TableCell>
                        <TableCell>{formatValue(result.line)}</TableCell>
                        <TableCell>{formatValue(result.track)}</TableCell>
                        <TableCell>{formatValue(result.section)}</TableCell>
                        <TableCell>{formatValue(result.task_no)}</TableCell>
                        <TableCell>{formatValue(result.station_start)}</TableCell>
                        <TableCell>{formatValue(result.station_end)}</TableCell>
                        <TableCell>{formatNumber(result.from_m)}</TableCell>
                        <TableCell>{formatNumber(result.to_m)}</TableCell>
                        <TableCell>{formatNumber(result.length)}</TableCell>
                        <TableCell>{result.exception_type}</TableCell>
                        <TableCell>{formatNumber(result.max_value)}</TableCell>
                        <TableCell>{formatNumber(result.max_location)}</TableCell>
                        <TableCell>{formatValue(result.tension_length)}</TableCell>
                        <TableCell>{formatValue(result.track_type)}</TableCell>
                        <TableCell>{formatValue(result.level)}</TableCell>
                        <TableCell>{formatValue(result.asset_class)}</TableCell>
                        <TableCell>{formatNumber(result.threshold_value)}</TableCell>
                        <TableCell>{formatNumber(result.k_eq, 3)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Paper>
            )}

            {selectedResult && selectedTrace?.trace_status === 'partial' && (
              <Alert severity="warning">
                部分 Trace 代表計算流程無法解析所有必要支點參照。當 Spt_A / Spt_I / Spt_B 或 span 輸入不完整時，
                <strong> Result = n/a</strong>、<strong>K_eq = -</strong> 與 <strong>Status = partial</strong> 屬於預期結果。
              </Alert>
            )}
          </Stack>
        )}

        {activeCycle.detailTab === 1 && (
          <Stack spacing={2}>
            <Alert severity="info">
              <strong>追蹤</strong>會顯示所選 ID 的判定過程，包含 K_eq、Ch_I、支點參照與 AI / IB 跨距檢查。
            </Alert>

            {!selectedResult || !selectedTrace ? (
              <Paper variant="outlined" sx={{ p: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  請先在摘要表選擇一筆 ID。
                </Typography>
              </Paper>
            ) : (
              <>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Stack spacing={2}>
                    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
                      <Paper variant="outlined" sx={{ p: 1.5, minWidth: 220 }}>
                        <Typography variant="caption" color="text.secondary">Final decision</Typography>
                        <Typography
                          variant="h5"
                          fontWeight={700}
                          color={selectedResult.overall_result === 'pass' ? 'success.main' : selectedResult.overall_result === 'fail' ? 'error.main' : 'text.secondary'}
                        >
                          {selectedResult.overall_result.toUpperCase()}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {describeFailingCriteria(selectedTrace.spans)}
                        </Typography>
                      </Paper>

                      <Paper variant="outlined" sx={{ p: 1.5, flex: 1 }}>
                        <Typography variant="caption" color="text.secondary">Formula</Typography>
                        <Typography variant="subtitle1" fontWeight={700}>S &gt;= 4B and P &lt;= Allowable</Typography>
                        <Typography variant="body2" color="text.secondary">
                          Each span first checks the short-circuit criterion S &gt;= 4B. When it is not met, P must be no greater than Allowable.
                        </Typography>
                      </Paper>
                    </Stack>

                    <Box>
                      <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
                        Criteria comparison
                      </Typography>
                      <Grid container spacing={1.5}>
                        {(['ai', 'ib'] as const).map((key) => {
                          const span = selectedTrace.spans?.[key];
                          const threshold = typeof span?.b === 'number' ? 4 * span.b : null;
                          const sValue = typeof span?.s === 'number' ? span.s : null;
                          const pValue = typeof span?.p === 'number' ? span.p : null;
                          const allowable = typeof span?.allowable === 'number' ? span.allowable : null;
                          const maxValue = Math.max(sValue ?? 0, threshold ?? 0, Math.abs(pValue ?? 0), Math.abs(allowable ?? 0), 1);
                          const sWidth = `${Math.max(6, ((sValue ?? 0) / maxValue) * 100)}%`;
                          const thresholdWidth = `${Math.max(6, ((threshold ?? 0) / maxValue) * 100)}%`;
                          const pWidth = `${Math.max(6, (Math.abs(pValue ?? 0) / maxValue) * 100)}%`;
                          const allowableWidth = `${Math.max(6, (Math.abs(allowable ?? 0) / maxValue) * 100)}%`;
                          const passed = isPassingSpanResult(span?.result);
                          const pPassed = pValue != null && allowable != null ? pValue <= allowable : false;

                          return (
                            <Grid item xs={12} md={6} key={key}>
                              <Paper variant="outlined" sx={{ p: 1.5 }}>
                                <Stack spacing={1}>
                                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                                    <Typography variant="subtitle2" fontWeight={700}>{key.toUpperCase()}</Typography>
                                    <Chip
                                      size="small"
                                      color={passed ? 'success' : 'error'}
                                      label={passed ? 'Pass' : 'Fail'}
                                      variant="outlined"
                                    />
                                  </Stack>
                                  <Box>
                                    <Stack direction="row" spacing={1} alignItems="center">
                                      <Typography variant="caption" sx={{ width: 28 }}>S</Typography>
                                      <Box sx={{ flex: 1, bgcolor: 'action.hover', borderRadius: 1, overflow: 'hidden' }}>
                                        <Box sx={{ width: sWidth, height: 10, bgcolor: 'primary.main' }} />
                                      </Box>
                                      <Typography variant="caption" sx={{ width: 64, textAlign: 'right' }}>{formatTraceNumber(sValue)}</Typography>
                                    </Stack>
                                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.75 }}>
                                      <Typography variant="caption" sx={{ width: 28 }}>4B</Typography>
                                      <Box sx={{ flex: 1, bgcolor: 'action.hover', borderRadius: 1, overflow: 'hidden' }}>
                                        <Box sx={{ width: thresholdWidth, height: 10, bgcolor: passed ? 'success.main' : 'error.main' }} />
                                      </Box>
                                    <Typography variant="caption" sx={{ width: 64, textAlign: 'right' }}>{formatTraceNumber(threshold)}</Typography>
                                  </Stack>
                                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1.25 }}>
                                    <Typography variant="caption" sx={{ width: 28 }}>{key.toUpperCase()} P</Typography>
                                    <Box sx={{ flex: 1, bgcolor: 'action.hover', borderRadius: 1, overflow: 'hidden' }}>
                                      <Box sx={{ width: pWidth, height: 10, bgcolor: pPassed ? 'success.main' : 'warning.main' }} />
                                    </Box>
                                    <Typography variant="caption" sx={{ width: 64, textAlign: 'right' }}>{formatTraceNumber(pValue)}</Typography>
                                  </Stack>
                                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.75 }}>
                                    <Typography variant="caption" sx={{ width: 28 }}>Allow</Typography>
                                    <Box sx={{ flex: 1, bgcolor: 'action.hover', borderRadius: 1, overflow: 'hidden' }}>
                                      <Box sx={{ width: allowableWidth, height: 10, bgcolor: pPassed ? 'success.main' : 'error.main' }} />
                                    </Box>
                                    <Typography variant="caption" sx={{ width: 64, textAlign: 'right' }}>{formatTraceNumber(allowable)}</Typography>
                                  </Stack>
                                  </Box>
                                  <Typography variant="body2" color="text.secondary">
                                    {key.toUpperCase()}: {formatTraceNumber(sValue)} {sValue != null && threshold != null && sValue >= threshold ? '>=' : '<'} {formatTraceNumber(threshold)}
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    P &lt;= Allowable: {formatTraceNumber(pValue)} {pPassed ? '<=' : '>'} {formatTraceNumber(allowable)}
                                  </Typography>
                                </Stack>
                              </Paper>
                            </Grid>
                          );
                        })}
                      </Grid>
                    </Box>
                  </Stack>
                </Paper>

                <Grid container spacing={2}>
                <Grid item xs={12} md={5}>
                  <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                    <Stack spacing={1}>
                      <Typography variant="subtitle1" fontWeight={700}>參考摘要</Typography>
                      <Typography variant="body2">案例：{selectedTrace.case_type ?? '-'}</Typography>
                      <Typography variant="body2">Ch_I 來源：{selectedTrace.chi_source ?? '-'}</Typography>
                      <Typography variant="body2">追蹤狀態：{selectedTrace.trace_status ?? '-'}</Typography>
                      <Typography variant="body2">K_eq: {selectedTrace.k_eq ?? '-'}</Typography>
                      <Typography variant="body2">Ch_I: {selectedTrace.reference?.chi ?? '-'}</Typography>
                      <Typography variant="body2">Spt_A / Spt_I / Spt_B: {selectedTrace.reference?.spt_a ?? '-'} / {selectedTrace.reference?.spt_i ?? '-'} / {selectedTrace.reference?.spt_b ?? '-'}</Typography>
                    </Stack>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={7}>
                  <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                    <Stack spacing={1.5}>
                      <Typography variant="subtitle1" fontWeight={700}>跨距檢查</Typography>
                      {(['ai', 'ib'] as const).map((key) => {
                        const span = selectedTrace.spans?.[key];
                        return (
                          <Paper key={key} variant="outlined" sx={{ p: 1.5 }}>
                            <Typography variant="subtitle2" fontWeight={700}>
                              跨距 {key.toUpperCase()}
                            </Typography>
                            <Typography variant="body2">
                              條件：S{key.toUpperCase()} {typeof span?.b === 'number' && typeof span?.s === 'number'
                                ? `${span.s.toFixed(2)} ${span.s >= 4 * span.b ? '>=' : '<'} ${(4 * span.b).toFixed(2)}`
                                : '-'}
                            </Typography>
                            <Typography variant="body2">B: {typeof span?.b === 'number' ? span.b.toFixed(2) : '-'}</Typography>
                            <Typography variant="body2">P: {typeof span?.p === 'number' ? span.p.toFixed(2) : '-'}</Typography>
                            <Typography variant="body2">允許值：{typeof span?.allowable === 'number' ? span.allowable.toFixed(2) : '-'}</Typography>
                            <Typography variant="body2">結果：{span?.result ?? '-'}</Typography>
                          </Paper>
                        );
                      })}
                    </Stack>
                  </Paper>
                </Grid>
                </Grid>
              </>
            )}
          </Stack>
        )}

        {activeCycle.detailTab === 2 && (
          <Stack spacing={2}>
            <Alert severity="info">
              <strong>原始資料</strong>會繪製所選 ID 在 `FromM - 50m` 到 `ToM + 50m` 範圍內的資料，方便檢視局部 Stagger 與 Chainage。
            </Alert>
            <StaggerRawDataPanel
              file={activeCycle.uploadedFiles[0] ?? null}
              result={selectedResult}
            />
          </Stack>
        )}
      </Paper>

      <StaggerAlgorithmDialog open={algoOpen} onClose={() => setAlgoOpen(false)} />
    </Box>
  );
};

export default CalculationView;
