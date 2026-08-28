import React, { useEffect, useState, useMemo, useRef } from 'react';
import Plotly from 'plotly.js';
import Plot from 'react-plotly.js';
import { Box, Typography, Paper, Button, FormGroup, FormControlLabel, Checkbox, Grid, Chip } from '@mui/material';
import ClearIcon from '@mui/icons-material/Clear';
import { ExceptionRecord } from '../../types/api';

interface ComparisonChartProps {
  chartData: (Record<string, (number | null)[]> | null)[] | undefined;
  selectedRow: ExceptionRecord | null;
  onClearSelection: () => void;
  sessionId: string;
}

// User-defined Palette
const CYCLE_COLORS = ['#d62728', '#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd']; // Red, Blue, Green, Orange, Purple

const ComparisonChart = ({ chartData, selectedRow, onClearSelection, sessionId }: ComparisonChartProps) => {
  const [layoutState, setLayoutState] = useState<Partial<Plotly.Layout>>({});
  const [showLegends, setShowLegends] = useState(true);
  const [showMaxLabel, setShowMaxLabel] = useState(true);
  const [showValidArea, setShowValidArea] = useState(true);
  const [showExceptionArea, setShowExceptionArea] = useState(true);
  const chartRef = useRef<any>(null);

  const axisGroup = useMemo(() => `axis-group-compare-${sessionId}`, [sessionId]);

  // Handle Zoom on Selection
  useEffect(() => {
    if (selectedRow) {
      const length = selectedRow.length || 10;
      const padding = 50; 
      const windowSpan = Math.max(100, length + 2 * padding);
      const center = (selectedRow.FromM + selectedRow.ToM) / 2;
      
      const newLayout: Partial<Plotly.Layout> = {
        xaxis: {
          range: [center - windowSpan / 2, center + windowSpan / 2],
          title: { text: 'Chainage (m)' },
          anchor: 'free', 
          position: 0,
          matches: axisGroup as any,
          showticklabels: true
        },
        uirevision: selectedRow.id 
      };
      setLayoutState(prev => ({ ...prev, ...newLayout }));
    }
  }, [selectedRow, axisGroup]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (chartRef.current && chartRef.current.el) {
        try { Plotly.purge(chartRef.current.el); } catch (e) { console.warn(e); }
      }
    };
  }, []);

  if (!chartData || chartData.length === 0) {
      return (
          <Box sx={{ p: 2, textAlign: 'center', color: 'text.secondary', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <Typography variant="body1">No Chart Data Available.</Typography>
              <Typography variant="caption">Ensure uploaded reports contain "ChartData" sheet.</Typography>
          </Box>
      );
  }

  if (!selectedRow) {
      return (
          <Box sx={{ p: 2, textAlign: 'center', color: 'text.secondary', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <Typography variant="h6" gutterBottom>No Exception Selected</Typography>
              <Typography variant="body2">Please click the "View Chart" icon in the table to compare details.</Typography>
          </Box>
      );
  }

  const traces: Plotly.Data[] = [];
  const shapes: Partial<Plotly.Shape>[] = [];

  // 1. Determine Traces to Show based on Type
  let showHeight = true;
  let showStagger = true;
  let showWear = true;

  if (selectedRow) {
      // Fix Issue 2: Handle key casing mismatch ('exception type' vs 'Exception Type')
      const row = selectedRow as any;
      const type = (row['exception type'] || row['Exception Type'] || "").toLowerCase();
      if (type.includes("stagger")) {
          showHeight = false;
          showWear = false;
      } else if (type.includes("height")) {
          showStagger = false;
          showWear = false;
      } else if (type.includes("wear")) {
          showHeight = false;
          showStagger = false;
      }
  }

  // 2. Iterate Cycles to Build Traces and Shapes
  chartData.forEach((data, i) => {
      if (!data) return;
      
      const x = data['Chainage'] as number[];
      if (!x) return;

      const cycleColor = CYCLE_COLORS[i % CYCLE_COLORS.length];
      const yAxisName = i === 0 ? 'y' : `y${i + 1}`;
      const suffix = i === 0 ? 'Latest' : `Prev ${i}`;

      // --- Add Waveforms ---
      const addTrace = (col: string, name: string, subIdx: number) => {
          if (data[col]) {
              // Color Logic: Cycle Color (Base) + Saturation/Opacity (Wire 1-4)
              // height1 -> subIdx=0 (Solid, 1.0)
              // height2 -> subIdx=1 (Dash, 0.8)
              // height3 -> subIdx=2 (Dot, 0.6)
              // height4 -> subIdx=3 (DashDot, 0.4)
              
              const opacity = 1.0 - (subIdx * 0.2); // 1.0, 0.8, 0.6, 0.4
              // For rgba, we need to convert hex cycleColor to rgb
              // But ploty supports 'rgba(r,g,b,a)'.
              // Hack: Use `opacity` prop on trace? No, that affects whole trace.
              // Let's use Line Dash for distinction as well.
              const dashStyles: Array<'solid' | 'dash' | 'dot' | 'dashdot'> = ['solid', 'dash', 'dot', 'dashdot'];
              
              traces.push({
                  x: x,
                  y: data[col] as number[],
                  type: 'scattergl',
                  mode: 'lines',
                  name: `${name} (${suffix})`,
                  xaxis: 'x', // Shared X
                  yaxis: yAxisName,
                  line: { 
                      width: 1.5, 
                      color: cycleColor, 
                      dash: dashStyles[subIdx % 4] 
                  },
                  opacity: opacity, // Vary opacity for "Different saturation" feel
                  hoverinfo: 'y+name'
              });
          }
      };

      if (showHeight) ['height1', 'height2', 'height3', 'height4'].forEach((c, idx) => addTrace(c, `Height ${idx+1}`, idx));
      if (showStagger) ['stagger1', 'stagger2', 'stagger3', 'stagger4'].forEach((c, idx) => addTrace(c, `Stagger ${idx+1}`, idx));
      if (showWear) ['wear1', 'wear2', 'wear3', 'wear4'].forEach((c, idx) => addTrace(c, `Wear ${idx+1}`, idx));

      // --- Add Markers (Triangle) ---
      if (selectedRow) {
          let maxLoc, maxVal, fromM, toM;

          if (i === 0) {
              // Latest
              maxLoc = selectedRow.maxLocation;
              maxVal = selectedRow.maxValue;
              fromM = selectedRow.FromM;
              toM = selectedRow.ToM;
          } else {
              // Previous
              // Note: Typescript might complain about dynamic access, assume any
              const row = selectedRow as any;
              maxLoc = row[`Previous ${i}_maxLocation`];
              maxVal = row[`Previous ${i}_maxValue`];
              fromM = row[`Previous ${i}_FromM`];
              toM = row[`Previous ${i}_ToM`];
          }

          if (maxLoc !== undefined && maxVal !== undefined && showMaxLabel) {
              // Removed Trace Push (Issue 2: Prevent 'trace X' legend and Y-axis 0 scaling)
              // Only using Annotations (configured below)
          }

          // --- Add Exception Area (Rounded Rect) ---
          if (fromM !== undefined && toM !== undefined && showExceptionArea) {
              shapes.push({
                  type: 'rect',
                  x0: fromM,
                  x1: toM,
                  y0: 0, 
                  y1: 1, 
                  xref: 'x', 
                  yref: `${yAxisName} domain` as any, // Use domain reference to cover full subplot height
                  fillcolor: cycleColor,
                  opacity: 0.1, // Issue 2: More Transparency
                  line: { width: 0 },
                  layer: 'below'
              });
          }
      }
  });

  // --- Add Valid Match Area (Green Vertical Zone) ---
  if (selectedRow && showValidArea) {
      shapes.push({
          type: 'rect',
          x0: selectedRow.FromM,
          x1: selectedRow.ToM,
          y0: 0,
          y1: 1,
          xref: 'x',
          yref: 'paper', // Covers all subplots
          fillcolor: 'rgba(200, 200, 200, 0.2)', // Grey (Issue 2: Not Green)
          line: { color: 'grey', width: 1, dash: 'dash' },
          layer: 'below'
      });
  }

    // 3. Configure Layout Grid
    const nCharts = chartData.length;
    // Calculate domains manually for better control
    // e.g. 2 charts: [0.55, 1], [0, 0.45]
    const gap = 0.05;
    const heightPerChart = (1 - (nCharts - 1) * gap) / nCharts;

    const layoutYAxes: any = {};
    const annotations: Partial<Plotly.Annotations>[] = [];

    // Identify the bottom-most axis name for X-axis anchoring
    // The loop assigns 'yaxis' (i=0, top) ... 'yaxisN' (i=N-1, bottom)
    const bottomAxisId = nCharts === 1 ? 'y' : `y${nCharts}`;

    for (let i = 0; i < nCharts; i++) {
        const start = 1 - (i + 1) * heightPerChart - i * gap;
        const end = start + heightPerChart;
        const key = i === 0 ? 'yaxis' : `yaxis${i + 1}`;
        
        layoutYAxes[key] = {
            domain: [start, end],
            title: i === 0 ? 'Latest' : `Prev ${i}`,
            showgrid: true
        };

        // Add MaxLocation Triangle Annotation (at bottom of this subplot)
        if (selectedRow && showMaxLabel) {
            let maxLoc, fromM, toM;
            if (i === 0) {
                maxLoc = selectedRow.maxLocation;
                fromM = selectedRow.FromM;
                toM = selectedRow.ToM;
            } else {
                const row = selectedRow as any;
                maxLoc = row[`Previous ${i}_maxLocation`];
                fromM = row[`Previous ${i}_FromM`];
                toM = row[`Previous ${i}_ToM`];
            }

            if (maxLoc !== undefined) {
                const cycleColor = CYCLE_COLORS[i % CYCLE_COLORS.length];
                annotations.push({
                    x: maxLoc,
                    y: start, // Bottom of the subplot domain
                    xref: 'x',
                    yref: 'paper',
                    showarrow: true,
                    arrowhead: 2, // Triangle
                    arrowcolor: cycleColor,
                    ax: 0,
                    ay: -20, // Point up (taller arrow to be visible)
                    text: 'Max',
                    font: { color: cycleColor, size: 10 },
                    bgcolor: 'rgba(255,255,255,0.6)' // Ensure text is readable
                });
            }
        }
    }

    // Update layout x-axis to be anchored to the bottom chart
    const layout: Partial<Plotly.Layout> = {
      // grid: { rows: nCharts, columns: 1, pattern: 'independent' }, // REMOVED: Conflict with manual domains
      margin: { t: 30, r: 20, b: 40, l: 60 },
      autosize: true,
      showlegend: showLegends,
      shapes: shapes,
      annotations: annotations,
      xaxis: { 
        title: 'Chainage (m)', 
        anchor: 'free', // Force anchor to free to position manually
        position: 0,    // Position at the very bottom
        side: 'bottom',
        showticklabels: true 
      },
      ...layoutYAxes,
      legend: { orientation: 'h', x: 0.5, y: -0.1, xanchor: 'center', yanchor: 'top' }, // Issue 2: Move legend to bottom
      ...layoutState
    };

  return (
    <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
        {selectedRow && (
            <Paper elevation={0} sx={{ p: 1.5, m: 1, mb: 0, bgcolor: 'background.default' }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid item xs="auto">
                        <Typography variant="caption" color="text.secondary" display="block">Latest Cycle ID</Typography>
                        <Typography variant="body2" fontWeight="bold">{selectedRow.id}</Typography>
                    </Grid>
                    <Grid item xs="auto">
                        <Typography variant="caption" color="text.secondary" display="block">Exception Type</Typography>
                        <Typography variant="body2">{(selectedRow as any)['exception type'] || '-'}</Typography>
                    </Grid>
                    <Grid item xs="auto">
                        <Typography variant="caption" color="text.secondary" display="block">Level</Typography>
                        <Chip label={selectedRow.level || '-'} size="small" color="default" />
                    </Grid>
                    <Grid item xs="auto">
                        <Typography variant="caption" color="text.secondary" display="block">MaxValue</Typography>
                        <Typography variant="body2">{selectedRow.maxValue ?? '-'}</Typography>
                    </Grid>
                    <Grid item xs="auto">
                        <Typography variant="caption" color="text.secondary" display="block">MaxLocation</Typography>
                        <Typography variant="body2">{selectedRow.maxLocation ?? '-'}</Typography>
                    </Grid>
                    <Grid item xs="auto">
                        <Typography variant="caption" color="text.secondary" display="block">Length</Typography>
                        <Typography variant="body2">{selectedRow.length ?? '-'}</Typography>
                    </Grid>
                </Grid>
            </Paper>
        )}
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, px: 2, py: 0.5 }}>
             {/* Removed Focus Text */}
            <FormGroup row>
                <FormControlLabel control={<Checkbox checked={showLegends} onChange={e => setShowLegends(e.target.checked)} size="small" />} label="Legends" />
                <FormControlLabel control={<Checkbox checked={showMaxLabel} onChange={e => setShowMaxLabel(e.target.checked)} size="small" />} label="Max Label" />
                <FormControlLabel control={<Checkbox checked={showValidArea} onChange={e => setShowValidArea(e.target.checked)} size="small" />} label="Valid Area" />
                <FormControlLabel control={<Checkbox checked={showExceptionArea} onChange={e => setShowExceptionArea(e.target.checked)} size="small" />} label="Exc. Area" />
            </FormGroup>
            <Button size="small" onClick={onClearSelection} disabled={!selectedRow} startIcon={<ClearIcon />}>
                Reset Zoom
            </Button>
        </Box>
        <Paper elevation={0} sx={{ flex: 1, minHeight: 0 }}>
             <Plot
                ref={chartRef}
                data={traces}
                layout={layout}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler={true}
                config={{ responsive: true, scrollZoom: true, displaylogo: false }}
             />
        </Paper>
    </Box>
  );
};

export default ComparisonChart;
