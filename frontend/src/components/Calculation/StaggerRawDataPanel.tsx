import React, { useEffect, useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import * as XLSX from 'xlsx';
import { Alert, Box, CircularProgress, Paper, Stack, Typography } from '@mui/material';
import type { StaggerResult } from '../../types/api';

interface StaggerRawDataPanelProps {
  file: File | null;
  result: StaggerResult | null;
}

interface ChartPoint {
  chainage: number;
  stagger1: number | null;
  stagger2: number | null;
  stagger3: number | null;
  stagger4: number | null;
}

const CHART_PADDING = 50;

const toNumber = (value: unknown): number | null => {
  if (value == null || value === '') {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

const firstDefined = (...values: unknown[]): number | null => {
  for (const value of values) {
    const numeric = toNumber(value);
    if (numeric != null) {
      return numeric;
    }
  }
  return null;
};

const StaggerRawDataPanel: React.FC<StaggerRawDataPanelProps> = ({ file, result }) => {
  const [points, setPoints] = useState<ChartPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadChartData = async () => {
      if (!file || !result) {
        setPoints([]);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const buffer = await file.arrayBuffer();
        const workbook = XLSX.read(buffer, { type: 'array' });
        const sheet = workbook.Sheets.ChartData;
        if (!sheet) {
          throw new Error('找不到 ChartData 工作表。');
        }

        const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, { defval: null });
        const fromM = result.from_m ?? result.max_location;
        const toM = result.to_m ?? result.max_location;
        const start = Math.min(fromM, toM) - CHART_PADDING;
        const end = Math.max(fromM, toM) + CHART_PADDING;

        const filtered = rows
          .map((row) => ({
            chainage: firstDefined(row.Chainage, row.chainage),
            stagger1: firstDefined(row.stagger1, row.STG1),
            stagger2: firstDefined(row.stagger2, row.STG2),
            stagger3: firstDefined(row.stagger3, row.STG3),
            stagger4: firstDefined(row.stagger4, row.STG4),
          }))
          .filter((row): row is ChartPoint => row.chainage != null)
          .filter((row) => row.chainage >= start && row.chainage <= end);

        if (!cancelled) {
          setPoints(filtered);
        }
      } catch (loadError: any) {
        if (!cancelled) {
          setPoints([]);
          setError(loadError.message || '無法讀取 Raw Data。');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadChartData();

    return () => {
      cancelled = true;
    };
  }, [file, result]);

  const traces = useMemo<Plotly.Data[]>(() => {
    if (!points.length) {
      return [];
    }

    const chainage = points.map((point) => point.chainage);
    const series = [
      { key: 'stagger1', name: 'Stagger 1', color: '#1d4ed8' },
      { key: 'stagger2', name: 'Stagger 2', color: '#0891b2' },
      { key: 'stagger3', name: 'Stagger 3', color: '#16a34a' },
      { key: 'stagger4', name: 'Stagger 4', color: '#ea580c' },
    ] as const;

    return series.map((item) => ({
      x: chainage,
      y: points.map((point) => point[item.key]),
      type: 'scatter',
      mode: 'lines',
      name: item.name,
      line: { color: item.color, width: 2 },
    }));
  }, [points]);

  if (!result) {
    return (
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="body2" color="text.secondary">
          請先在摘要表選擇一筆結果，再查看對應的 Raw Data。
        </Typography>
      </Paper>
    );
  }

  if (isLoading) {
    return (
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <CircularProgress size={18} />
          <Typography variant="body2">正在讀取 ChartData...</Typography>
        </Stack>
      </Paper>
    );
  }

  if (error) {
    return <Alert severity="warning">{error}</Alert>;
  }

  if (!points.length) {
    return (
      <Alert severity="info">
        在指定的 Chainage 範圍內找不到可繪圖的 stagger 資料。請確認 ChartData 工作表包含 chainage 與 stagger 欄位。
      </Alert>
    );
  }

  const fromM = result.from_m ?? result.max_location;
  const toM = result.to_m ?? result.max_location;
  const alarmStart = Math.min(fromM, toM);
  const alarmEnd = Math.max(fromM, toM);

  return (
    <Stack spacing={2}>
      <Alert severity="info">
        目前顯示 {alarmStart - CHART_PADDING}m 到 {alarmEnd + CHART_PADDING}m 的區間，紅色區塊代表 alarm range，虛線代表 MaxLocation。
      </Alert>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Box sx={{ height: 420 }}>
          <Plot
            data={traces}
            layout={{
              title: {
                text: `${result.id} - Stagger vs Chainage`,
                font: { size: 14 },
                x: 0.02,
                xanchor: 'left',
              },
              margin: { t: 72, r: 24, b: 52, l: 64 },
              xaxis: { title: { text: 'Chainage (m)' } },
              yaxis: { title: { text: 'Stagger' } },
              legend: { orientation: 'h', y: -0.18 },
              shapes: [
                {
                  type: 'rect',
                  x0: alarmStart,
                  x1: alarmEnd,
                  y0: 0,
                  y1: 1,
                  xref: 'x',
                  yref: 'paper',
                  fillcolor: 'rgba(220, 38, 38, 0.18)',
                  line: { color: '#dc2626', width: 1.5 },
                  layer: 'below',
                },
                {
                  type: 'line',
                  x0: result.max_location,
                  x1: result.max_location,
                  y0: 0,
                  y1: 1,
                  xref: 'x',
                  yref: 'paper',
                  line: { color: '#dc2626', width: 2, dash: 'dash' },
                },
              ],
              annotations: [
                {
                  x: (alarmStart + alarmEnd) / 2,
                  y: 1.12,
                  xref: 'x',
                  yref: 'paper',
                  text: 'Alarm Range',
                  showarrow: false,
                  font: { color: '#b91c1c', size: 12 },
                  bgcolor: 'rgba(255,255,255,0.78)',
                },
                {
                  x: result.max_location,
                  y: 1.02,
                  xref: 'x',
                  yref: 'paper',
                  text: 'MaxLocation',
                  showarrow: true,
                  arrowhead: 2,
                  ay: -42,
                  ax: 24,
                },
              ],
            }}
            config={{ responsive: true, displaylogo: false }}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler
          />
        </Box>
      </Paper>
    </Stack>
  );
};

export default StaggerRawDataPanel;
