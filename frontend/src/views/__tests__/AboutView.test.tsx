import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { fetchDiagnostics } from '../../api/client';
import AboutView from '../AboutView';

vi.mock('../../api/client', () => ({
  fetchDiagnostics: vi.fn(),
}));

const diagnostics = {
  database_path: 'C:\\Smart Maintanence\\TOV1050_Analyzer\\dist\\win-unpacked\\data\\analysis.db',
  database_directory: 'C:\\Smart Maintanence\\TOV1050_Analyzer\\dist\\win-unpacked\\data',
  config_directory: 'C:\\Smart Maintanence\\TOV1050_Analyzer\\config',
  mode: 'portable' as const,
  packaging: {
    recommended_target: 'dir' as const,
    current_target: 'dir',
    single_exe_note: 'Single exe packages must store SQLite data in an external writable folder.',
  },
};

describe('AboutView', () => {
  beforeEach(() => {
    vi.mocked(fetchDiagnostics).mockReset();
    vi.mocked(fetchDiagnostics).mockResolvedValue(diagnostics);
  });

  it('預設顯示操作指南及可及圖表，不再載入 iframe', () => {
    vi.mocked(fetchDiagnostics).mockImplementationOnce(() => new Promise(() => {}));
    const bridgeSpy = vi.fn();
    window.electronAPI = { loadVisualGuideHtml: bridgeSpy } as any;

    render(<AboutView />);

    expect(screen.getByRole('heading', { name: '關於 TOV1050 Analyzer', level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '操作指南' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('heading', { name: '操作指南', level: 2 })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Wear 狀態門檻表' })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'MAINLINE-only coverage 示例表' })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Version Difference limits' })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Check 1 Year decision matrix' })).toBeInTheDocument();
    expect(screen.getByText(/X 軸拖曳或 autorange 會同步所有圖/)).toBeInTheDocument();
    expect(screen.getByText(/review_required 會顯示粉紅 review row/)).toBeInTheDocument();
    expect(screen.queryByTitle(/Visual Guide/i)).not.toBeInTheDocument();
    expect(document.querySelector('iframe')).not.toBeInTheDocument();
    expect(bridgeSpy).not.toHaveBeenCalled();
  });

  it('開發者 diagnostics 載入期間保留穩定 skeleton', () => {
    vi.mocked(fetchDiagnostics).mockImplementationOnce(() => new Promise(() => {}));
    render(<AboutView />);

    fireEvent.click(screen.getByRole('tab', { name: '開發者參考' }));

    expect(screen.getByLabelText('正在載入執行環境診斷')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Runtime architecture' })).toBeInTheDocument();
  });

  it('切換至開發者參考並顯示 diagnostics success', async () => {
    render(<AboutView />);

    fireEvent.click(screen.getByRole('tab', { name: '開發者參考' }));

    expect(screen.getByRole('heading', { name: '開發者參考', level: 2 })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'API 與 state ownership matrix' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Version Difference API contract' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Check 1 Year API 與 staged contract' })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Check 1 Year API decision matrix' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '執行環境診斷' })).toBeInTheDocument();
    expect(screen.getByText(/analysis\.db/i)).toBeInTheDocument();
    expect(fetchDiagnostics).toHaveBeenCalledOnce();
  });

  it('diagnostics 載入失敗時仍保留 guide content', async () => {
    vi.mocked(fetchDiagnostics).mockRejectedValueOnce(new Error('backend unavailable'));
    render(<AboutView />);

    expect(screen.getByRole('heading', { name: '操作指南', level: 2 })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: '開發者參考' }));

    expect(screen.getByRole('heading', { name: 'Runtime architecture' })).toBeInTheDocument();
    expect(await screen.findByText(/無法載入執行環境診斷/)).toBeInTheDocument();
    expect(screen.getByText(/backend unavailable/)).toBeInTheDocument();
  });
});
