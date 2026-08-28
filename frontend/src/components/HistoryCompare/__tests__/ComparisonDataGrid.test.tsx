import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import * as ComparisonModule from '../ComparisonDataGrid';
import { transformData } from '../ComparisonDataGrid';
import ComparisonDataGrid from '../ComparisonDataGrid';
import { ExceptionRecord } from '../../../types/api';

// Mock MUI DataGrid to avoid complex rendering issues in tests
vi.mock('@mui/x-data-grid', async () => {
    const actual = await vi.importActual('@mui/x-data-grid');
    return {
        ...actual,
        DataGrid: ({ rows }: { rows: any[] }) => (
            <div data-testid="mock-datagrid">
                {rows.length === 0 ? (
                    <div data-testid="empty-state">No data to display</div>
                ) : (
                    rows.map((row: any) => (
                        <div key={row.id} data-testid={`row-${row.id}`}>
                            {row.id}
                        </div>
                    ))
                )}
            </div>
        ),
    };
});

describe('ComparisonDataGrid Logic', () => {
    describe('transformData', () => {
        it('should correctly parse "Previous ID" CSV string', () => {
            const input: ExceptionRecord[] = [{
                id: '1',
                'exception type': 'Test',
                level: 'L1',
                FromM: 100,
                ToM: 110,
                length: 10,
                maxValue: 5,
                maxLocation: 105,
                Landmark: 'Platform(FOT)',
                'Tension Length': 'TL1',
                'Track Type': 'T1',
                Overlap: null,
                Class: 'both',
                'Threshold Value': 5,
                Section: 'S1',
                // @ts-expect-error - Dynamic property for testing
                'Previous ID': 'prev1, prev2'
            }];
            
            const result = transformData(input);
            expect(result[0].prev_0).toBe('prev1');
            expect(result[0].prev_1).toBe('prev2');
        });

        it('should correctly parse "Previous {N}" keys', () => {
             const input: any[] = [{
                id: '1',
                'Previous 1': 'prevA',
                'Previous 2': 'prevB'
            }];
            
            const result = transformData(input);
            expect(result[0].prev_0).toBe('prevA');
            expect(result[0].prev_1).toBe('prevB');
        });
        
        it('should default action to "Pending" if missing', () => {
             const input: ExceptionRecord[] = [{
                id: '1',
                'exception type': 'Test',
                level: 'L1',
                FromM: 100,
                ToM: 110,
                length: 10,
                maxValue: 5,
                maxLocation: 105,
                Landmark: 'Platform(HUH)',
                'Tension Length': 'TL1',
                'Track Type': 'T1',
                Overlap: null,
                Class: 'KSL',
                'Threshold Value': 5,
                Section: 'RAC'
            }];
            
            const result = transformData(input);
            expect(result[0].action).toBe('Pending');
        });

        it('should return empty array when input is empty', () => {
            const input: ExceptionRecord[] = [];
            const result = transformData(input);
            expect(result).toEqual([]);
            expect(result.length).toBe(0);
        });

        it('should NOT return MOCK_DATA when input is empty', () => {
            const input: ExceptionRecord[] = [];
            const result = transformData(input);
            // MOCK_DATA has ids starting with 'mock-'
            const hasMockData = result.some(row => 
                row.id?.toString().startsWith('mock-')
            );
            expect(hasMockData).toBe(false);
        });
    });

    describe('Q1 compact column sizing', () => {
        it('uses compact widths for short identifier columns', () => {
            const columns = (ComparisonModule as any).__TEST_ONLY__?.baseColumns ?? [];

            const idColumn = columns.find((column: { field: string }) => column.field === 'id');
            const levelColumn = columns.find((column: { field: string }) => column.field === 'level');
            const trackTypeColumn = columns.find((column: { field: string }) => column.field === 'Track Type');

            expect(idColumn).toMatchObject({
                field: 'id',
                minWidth: expect.any(Number),
            });
            expect(idColumn.width).toBeLessThanOrEqual(180);
            expect(levelColumn.width).toBeLessThanOrEqual(80);
            expect(trackTypeColumn.width).toBeLessThanOrEqual(100);
        });
    });

    // Bug-001: TML 資料無法產生比較表格
    describe('Bug-001: Empty data handling', () => {
        it('should display empty state when data is empty array', () => {
            render(<ComparisonDataGrid data={[]} />);
            
            // Should NOT have mock data rows
            const mockRows = screen.queryAllByTestId(/^row-mock-/);
            expect(mockRows.length).toBe(0);
        });

        it('should display empty state when data is undefined', () => {
            // @ts-expect-error - Testing undefined case
            render(<ComparisonDataGrid data={undefined} />);
            
            // Should NOT have mock data rows
            const mockRows = screen.queryAllByTestId(/^row-mock-/);
            expect(mockRows.length).toBe(0);
        });

        it('should display actual data when provided', () => {
            const realData: ExceptionRecord[] = [{
                id: 'real-exception-1',
                'exception type': 'Low Height',
                level: 'L2',
                FromM: 5000,
                ToM: 5010,
                length: 10,
                maxValue: 4.5,
                maxLocation: 5005,
                Landmark: null,
                'Tension Length': 'TL-50',
                'Track Type': 'Tangent',
                Overlap: 'Y',
                Class: 'SCL',
                'Threshold Value': 5.0,
                Section: 'Mainline'
            }];
            
            render(<ComparisonDataGrid data={realData} />);
            
            // Should have real data row
            const realRow = screen.queryByTestId('row-real-exception-1');
            expect(realRow).toBeTruthy();
            
            // Should NOT have mock data rows
            const mockRows = screen.queryAllByTestId(/^row-mock-/);
            expect(mockRows.length).toBe(0);
        });
    });
});
