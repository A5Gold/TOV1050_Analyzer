import React, { useEffect, useState, useMemo, useRef } from 'react';
import Plotly from 'plotly.js';
import Plot from 'react-plotly.js';
import { Box, Typography, Paper, FormGroup, FormControlLabel, Checkbox, Button, Chip, CircularProgress } from '@mui/material';
import ClearIcon from '@mui/icons-material/Clear';
import { AnalysisResponse, ExceptionRecord } from '../types/api';
import apiClient from '../api/client';

const LEVEL_COLORS: Record<string, string> = {
  'L1': '#d32f2f', // Red
  'L2': '#ed6c02', // Orange
  'L3': '#0288d1', // Blue
};

interface ChartComponentProps {
  result: AnalysisResponse | null;
  selectedExceptionId: string | null;
  onSelectException: (id: string | null) => void;
  sessionId: string;
}

const ChartComponent = ({ result, selectedExceptionId, onSelectException, sessionId }: ChartComponentProps) => {
  
  const [showMarkers, setShowMarkers] = useState(true);
  const [showThresholds, setShowThresholds] = useState(true);
  const [showLegend, setShowLegend] = useState(true);
  const [layoutState, setLayoutState] = useState<Partial<Plotly.Layout>>({});
  const [chartData, setChartData] = useState<AnalysisResponse['chart_data']>({});
  const [chartResolution, setChartResolution] = useState<AnalysisResponse['chart_resolution']>();
  const [detailLoading, setDetailLoading] = useState(false);
  const chartRef = useRef<any>(null); // Ref to hold the Plotly chart instance

  // Generate a unique axis group ID for this session to prevent infinite loops
  const axisGroup = useMemo(() => `axis-group-${sessionId}`, [sessionId]);

  const selectedException = useMemo(() => {
    if (!result || !selectedExceptionId) return null;
    for (const list of Object.values(result.exceptions)) {
      const found = list.find(e => e.id === selectedExceptionId);
      if (found) return found;
    }
    return null;
  }, [result, selectedExceptionId]);

  useEffect(() => {
    setChartData(result?.chart_data || {});
    setChartResolution(result?.chart_resolution);
  }, [result]);

  // Overview stays compact; fetch raw detail only for the selected exception window.
  useEffect(() => {
    if (!selectedException) {
      setChartData(result?.chart_data || {});
      setChartResolution(result?.chart_resolution);
      setDetailLoading(false);
      return;
    }
    const from = Math.max(0, selectedException.FromM - 100);
    const to = selectedException.ToM + 100;
    let cancelled = false;
    setDetailLoading(true);
    apiClient.get<{ chart_data: AnalysisResponse['chart_data']; chart_resolution: AnalysisResponse['chart_resolution'] }>(
      '/analyze/chart-data',
      {
        params: {
          from_m: from,
          to_m: to,
          max_points: 12000,
          file_path: result?.params.file_path,
          line: result?.params.line,
          client_session_id: sessionId,
        },
      },
    ).then(({ data }) => {
      if (!cancelled) {
        setChartData(data.chart_data);
        setChartResolution(data.chart_resolution);
      }
    }).catch(() => {
      // Keep the overview visible when a detail request is unavailable.
    }).finally(() => {
      if (!cancelled) setDetailLoading(false);
    });
    return () => { cancelled = true; };
  }, [selectedException, result?.params.file_path, result?.params.line, sessionId]);

  // Handle Chart Zoom based on Selection
  useEffect(() => {
    if (selectedException) {
      console.log("Selected:", selectedException);
      const length = selectedException.length;
      const padding = 50; 
      const windowSpan = Math.max(100, length + 2 * padding);
      const center = (selectedException.FromM + selectedException.ToM) / 2;
      
      const newLayout: Partial<Plotly.Layout> = {
        xaxis: {
          range: [center - windowSpan / 2, center + windowSpan / 2],
          title: { text: 'Chainage (m)' },
          anchor: 'y3' as any,
          matches: axisGroup as any,
          showticklabels: true
        },
        uirevision: selectedException.id 
      };
      
      setLayoutState(prev => ({ ...prev, ...newLayout }));
    }
  }, [selectedException, axisGroup]);

  // Clean up plot on unmount
  useEffect(() => {
    return () => {
      // Explicitly purge the plot
      if (chartRef.current && chartRef.current.el) {
        try {
            Plotly.purge(chartRef.current.el);
        } catch (e) {
            console.warn('Failed to purge plot:', e);
        }
      }
    };
  }, []);

  if (!result) {
    return <Typography>No data loaded.</Typography>;
  }

  const chainage = chartData['Chainage'] as number[];
  const traces: Plotly.Data[] = [];

    const addLineTrace = (name: string, yCol: string, row: number) => {
    if (chartData[yCol]) {
      traces.push({
        x: chainage,
        y: chartData[yCol] as number[],
        type: 'scattergl',
        mode: 'lines',
        name: name,
        xaxis: axisGroup, 
        yaxis: row === 1 ? 'y' : `y${row}`,
        line: { width: 1 }
      });
    }
  };

  ['height1', 'height2', 'height3', 'height4'].forEach(c => addLineTrace(c, c, 1));
  ['stagger1', 'stagger2', 'stagger3', 'stagger4'].forEach(c => addLineTrace(c, c, 2));
  ['wear1', 'wear2', 'wear3', 'wear4'].forEach(c => addLineTrace(c, c, 3));

  if (showMarkers) {
    const rowMap: Record<string, number> = {
      'Low Height': 1, 'High Height': 1,
      'Stagger Left': 2, 'Stagger Right': 2,
      'Wire Wear': 3
    };

    Object.entries(result.exceptions).forEach(([type, items]) => {
        if (!items.length) return;
        const targetRow = rowMap[type] || 1;
        const x: number[] = [];
        const y: number[] = [];
        const colors: string[] = [];
        const ids: string[] = [];

        items.forEach(item => {
            x.push(item.maxLocation);
            y.push(item.maxValue);
            colors.push(LEVEL_COLORS[item.level] || 'grey');
            ids.push(item.id);
        });

        traces.push({
            x: x,
            y: y,
            mode: 'markers',
            type: 'scattergl',
            name: `${type} Dots`,
            text: ids, // Added text property for hovertemplate
            xaxis: axisGroup,
            yaxis: targetRow === 1 ? 'y' : `y${targetRow}`,
            marker: {
                size: 8, 
                color: colors,
                symbol: 'circle',
                line: { color: 'white', width: 1 }
            },
            hoverinfo: 'text', // Only show ID on hover
            hovertemplate: '<b>ID: %{text}</b><br>Loc: %{x:.2f}m<br>Val: %{y:.2f}<extra></extra>',
        });
    });
  }

  // Shapes Construction
  const shapes: Partial<Plotly.Shape>[] = [];

  if (selectedException) {
    const center = selectedException.maxLocation;
    const type = selectedException['exception type'];
    const rowMap: Record<string, string> = {
      'Low Height': 'y', 'High Height': 'y',
      'Stagger Left': 'y2', 'Stagger Right': 'y2',
      'Wire Wear': 'y3'
    };
    const yRef = rowMap[type] || 'y';

    // Define domains for paper coordinates to match baseLayout
    // This prevents the highlight rect from stretching the Y-axis range
    const domainMap: Record<string, [number, number]> = {
      'y': [0.70, 1],
      'y2': [0.35, 0.65],
      'y3': [0, 0.30]
    };
    const [domainMin, domainMax] = domainMap[yRef] || [0, 1];

    // 1. Highlight Area (Specific Subplot)
    shapes.push({
      type: 'rect',
      x0: selectedException.FromM,
      x1: selectedException.ToM,
      y0: domainMin, 
      y1: domainMax,
      xref: 'x',
      yref: 'paper',
      fillcolor: 'rgba(200, 200, 200, 0.3)', // Lighter Gray
      line: { width: 0 },
      layer: 'below' // Draw behind data traces
    });
    
    // 2. Vertical Line (At Peak)
    if (showMarkers) {
      shapes.push({
        type: 'line',
        x0: center, x1: center,
        y0: 0, y1: 1,
        xref: 'x', yref: 'paper',
        line: { 
          color: LEVEL_COLORS[selectedException.level] || 'red', 
          width: 2, 
          dash: 'dot' 
        }
      });
    }

    // 3. Threshold Horizontal Line(s) (Full Width)
    if (showThresholds && selectedException['Threshold Value'] !== null) {
      const thresh = Math.abs(selectedException['Threshold Value']);
      const color = LEVEL_COLORS[selectedException.level] || 'red';

      // Use x0=0, x1=1 with xref='paper' to span full width
      const addHLine = (val: number) => {
        shapes.push({
          type: 'line',
          x0: 0, 
          x1: 1,
          y0: val, 
          y1: val,
          xref: 'paper', // Full width of the chart area
          yref: yRef as any,
          line: { 
            color: color, 
            width: 1,
            dash: 'dash'
          },
          opacity: 0.8
        });
      };

      if (type.includes('Stagger')) {
        addHLine(thresh);  // Positive
        addHLine(-thresh); // Negative
      } else {
        addHLine(selectedException['Threshold Value']);
      }
    }
  }

  const baseLayout: Partial<Plotly.Layout> = {
    grid: { rows: 3, columns: 1, pattern: 'independent' },
    margin: { t: 30, r: 20, b: 40, l: 60 },
    // Removed fixed height to allow flexbox resizing
    autosize: true,
    showlegend: showLegend,
    shapes: shapes,
    xaxis: {  
      title: { text: 'Chainage (m)' }, 
      anchor: 'y3' as any, 
      matches: axisGroup as any,
      showticklabels: true 
    },
    yaxis: { title: { text: 'Height (mm)' }, domain: [0.70, 1], showgrid: true },
    yaxis2: { title: { text: 'Stagger (mm)' }, domain: [0.35, 0.65], showgrid: true, matches: undefined },
    yaxis3: { title: { text: 'Wear (mm)' }, domain: [0, 0.30], showgrid: true, matches: undefined },
  };

  const finalLayout = { 
    ...baseLayout, 
    ...layoutState,
    shapes: shapes 
  };

  const chartTitle = `${result.params.date_str}_${result.params.line}_${result.params.section}_${result.params.track}`;

  return (
    <Box sx={{ width: '100%', height: '100%', p: 1, display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1, px: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
          <Typography variant="h6" color="primary" noWrap>{chartTitle}</Typography>
          {chartResolution && <Chip size="small" variant="outlined" label={`${chartResolution.strategy === 'min_max_envelope' ? 'Overview envelope' : 'Raw detail'} · ${chartResolution.returned_points.toLocaleString()} / ${chartResolution.source_points.toLocaleString()} pts`} />}
          {detailLoading && <CircularProgress size={16} aria-label="Loading chart detail" />}
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormGroup row>
            <FormControlLabel 
              control={<Checkbox checked={showMarkers} onChange={(e) => setShowMarkers(e.target.checked)} size="small" />} 
              label="Markers" 
            />
            <FormControlLabel 
              control={<Checkbox checked={showThresholds} onChange={(e) => setShowThresholds(e.target.checked)} size="small" />} 
              label="Thresholds" 
            />
            <FormControlLabel 
              control={<Checkbox checked={showLegend} onChange={(e) => setShowLegend(e.target.checked)} size="small" />} 
              label="Legend" 
            />
          </FormGroup>
          <Button 
            variant="outlined" 
            size="small" 
            startIcon={<ClearIcon />}
            onClick={() => onSelectException(null)}
            disabled={!selectedExceptionId}
          >
            Clear Selection
          </Button>
        </Box>
      </Box>

      <Paper elevation={2} sx={{ p: 1, flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Plot
          ref={chartRef}
          data={traces}
          layout={finalLayout}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler={true}
          config={{ 
            responsive: true,
            modeBarButtonsToRemove: ['select2d', 'lasso2d'],
            displaylogo: false,
            scrollZoom: true // Enable scroll zoom
          }}
          onClick={(data) => {
            if (data.points && data.points.length > 0) {
              const point = data.points[0] as any;
              console.log('Clicked point:', point);
              
              // Only process clicks on Marker traces (Dots)
              if (point.data.mode && point.data.mode.includes('markers')) {
                 // Try to get ID from text property or data array
                 const id = point.text || (point.data && point.data.text && point.data.text[point.pointIndex]);
                 if (id) {
                   onSelectException(id);
                 }
              }
            }
          }}
        />
      </Paper>
    </Box>
  );
};

export default ChartComponent;
