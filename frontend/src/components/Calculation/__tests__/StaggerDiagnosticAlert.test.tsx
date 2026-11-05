import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom';
import StaggerDiagnosticAlert from '../StaggerDiagnosticAlert';
import { apiErrorDiagnostic } from '../../../api/errorMessage';

const diagnostic = apiErrorDiagnostic({ response: { status: 422, data: { detail: {
  code: 'STAGGER_CONFIG_UNAVAILABLE', message: 'Unavailable',
  context: { line: 'AEL', branch: 'Mainline', direction: 'UP' },
  missing_configuration: ['approved branch support metadata', 'approved Keq strategy/coefficients'],
} } } }, 'AEL_report.xlsx')!;

describe('StaggerDiagnosticAlert', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('shows the identified scope and lets users copy filename, code, and configuration gaps', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    render(<StaggerDiagnosticAlert diagnostic={diagnostic} />);
    expect(screen.getByRole('alert')).toHaveTextContent('AEL／Mainline／UP');
    expect(screen.getByText('檔案：AEL_report.xlsx')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '複製診斷詳情' }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('已複製診斷詳情'));
    expect(JSON.parse(writeText.mock.calls[0][0])).toMatchObject({ filename: 'AEL_report.xlsx', code: 'STAGGER_CONFIG_UNAVAILABLE', context: diagnostic.context });
  });

  it('keeps selectable text available when clipboard access fails', async () => {
    vi.stubGlobal('navigator', { clipboard: { writeText: vi.fn().mockRejectedValue(new Error('Denied')) } });
    render(<StaggerDiagnosticAlert diagnostic={diagnostic} />);
    fireEvent.click(screen.getByRole('button', { name: '複製診斷詳情' }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('請在下方選取診斷詳情後複製'));
    expect((screen.getByLabelText('可複製診斷詳情') as HTMLTextAreaElement).value).toContain('AEL_report.xlsx');
  });
});
