import React from 'react';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import '@testing-library/jest-dom';

import CalculationView from '../CalculationView';
import { useCalculationStore } from '../../store/useCalculationStore';

describe('CalculationView', () => {
  beforeEach(() => {
    useCalculationStore.getState().reset();
  });

  test('renders the Stagger workspace with the corrected title', () => {
    render(<CalculationView />);

    expect(screen.getByText('拉出值計算')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Cycle A/i })).toBeInTheDocument();
    expect(screen.getAllByText(/上傳 Exception Report/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/n_Repeated Report/i).length).toBeGreaterThan(0);
  });

  test('supports drag and drop for exception report upload', () => {
    render(<CalculationView />);

    const droppedFile = new File(['excel'], 'dragged-exception-report.xlsx');
    const dropZone = screen.getByTestId('stagger-dropzone');

    fireEvent.drop(dropZone, {
      dataTransfer: {
        files: [droppedFile],
      },
    });

    expect(screen.getByText('dragged-exception-report.xlsx')).toBeInTheDocument();
  });

  test('shows uploaded file chip with remove affordance and removes the active cycle file', () => {
    render(<CalculationView />);

    const uploadedFile = new File(['excel'], 'dragged-exception-report.xlsx');
    fireEvent.drop(screen.getByTestId('stagger-dropzone'), {
      dataTransfer: {
        files: [uploadedFile],
      },
    });

    const chip = screen.getByText('dragged-exception-report.xlsx').closest('.MuiChip-root');
    expect(chip).not.toBeNull();

    fireEvent.click(within(chip as HTMLElement).getByTestId('CancelIcon'));

    expect(screen.queryByText('dragged-exception-report.xlsx')).not.toBeInTheDocument();
    expect(useCalculationStore.getState().cycles[0].uploadedFiles).toHaveLength(0);
  });

  test('can add a new cycle tab', async () => {
    render(<CalculationView />);

    await act(async () => {
      fireEvent.click(screen.getByLabelText(/Add cycle tab/i));
    });

    expect(await screen.findByRole('tab', { name: /Cycle B/i })).toBeInTheDocument();
  });

  test('renders an export button when there are stagger results', () => {
    useCalculationStore.setState((state) => ({
      ...state,
      cycles: state.cycles.map((cycle) => ({
        ...cycle,
        results: [
          {
            id: 'SG-001',
            run_date: '2026-03-01',
            line: 'EAL',
            track: 'up',
            section: 'Mainline',
            task_no: 'U2',
            station_start: 'FOT',
            station_end: 'TAP',
            from_m: 113498,
            to_m: 113500,
            length: 2,
            tension_length: 'H01',
            overlap: null,
            track_type: 'Tangent',
            level: 'L1',
            landmark: null,
            asset_class: 'Stagger',
            threshold_value: 45,
            exception_type: 'Stagger Left',
            max_value: 122,
            max_location: 113498.5,
            chi: 113498.5,
            spt_a: 113490,
            spt_i: 113498.5,
            spt_b: 113510,
            span_ai: 8.5,
            span_ib: 11.5,
            k_eq: 1.23456,
            overall_result: 'pass',
            trace_available: true,
            trace_status: 'complete',
            chi_source: 'maxLocation',
            remark: ['Case A'],
          },
        ],
        traces: [{ case_type: 'A', trace_status: 'complete', reference: { chi: 113498.5 }, spans: {} }],
        selectedResultId: 'SG-001',
      })),
    }));

    render(<CalculationView />);

    expect(screen.getByRole('button', { name: /export excel/i })).toBeInTheDocument();
  });

  test('shows visual-first criteria summary in the trace tab', () => {
    useCalculationStore.setState((state) => ({
      ...state,
      cycles: state.cycles.map((cycle) => ({
        ...cycle,
        detailTab: 1,
        results: [
          {
            id: 'SG-001',
            run_date: '2026-03-01',
            line: 'EAL',
            track: 'up',
            exception_type: 'Stagger Left',
            max_location: 113498.5,
            chi: 113498.5,
            spt_a: 113490,
            spt_i: 113498.5,
            spt_b: 113510,
            span_ai: 8.5,
            span_ib: 11.5,
            k_eq: 1.23456,
            overall_result: 'fail',
            trace_available: true,
            trace_status: 'complete',
            chi_source: 'maxLocation',
            remark: ['Case A'],
          },
        ],
        traces: [
          {
            case_type: 'A',
            trace_status: 'complete',
            reference: { chi: 113498.5, spt_a: 113490, spt_i: 113498.5, spt_b: 113510 },
            spans: {
              ai: { s: 644.96, b: 32.24, p: 275.49, allowable: -333.68, result: 'pass_short_circuit' },
              ib: { s: 729.96, b: 720.43, p: 232.99, allowable: -261.66, result: 'fail' },
            },
            k_eq: 1.23456,
          },
        ],
        selectedResultId: 'SG-001',
      })),
    }));

    render(<CalculationView />);

    expect(screen.getByText(/Criteria comparison/i)).toBeInTheDocument();
    expect(screen.getByText(/Final decision/i)).toBeInTheDocument();
    expect(screen.getAllByText(/S >= 4B/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/P <= Allowable/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/IB did not pass/i)).toBeInTheDocument();
    expect(screen.getByText(/AI P/i)).toBeInTheDocument();
    expect(screen.getByText(/IB P/i)).toBeInTheDocument();
  });
});
