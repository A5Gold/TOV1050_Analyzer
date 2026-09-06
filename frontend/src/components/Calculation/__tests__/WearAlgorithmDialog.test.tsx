import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import WearAlgorithmDialog from '../WearAlgorithmDialog';

describe('WearAlgorithmDialog', () => {
  it('以繁體中文顯示輸入、判斷及保存的實際操作流程', () => {
    render(<WearAlgorithmDialog open onClose={() => {}} />);

    expect(screen.getByRole('dialog', { name: '線耗計算邏輯' })).toBeInTheDocument();
    expect(screen.getByText('開始前先確認')).toBeInTheDocument();
    expect(screen.getByText('系統如何判斷')).toBeInTheDocument();
    expect(screen.getByText('結果如何保存')).toBeInTheDocument();
    expect(screen.getByText(/系統先辨識上載檔案.*Section、Track 及原始 Chainage/)).toBeInTheDocument();
    expect(screen.getByText(/strict Section 確認為真正缺口/)).toBeInTheDocument();
    expect(screen.getByText(/同 Line、Track、原始 Chainage/)).toBeInTheDocument();
    expect(screen.getByRole('table', { name: '張力段範圍決策表' })).toBeInTheDocument();
    expect(screen.getByText(/canonical Track 是 `Siding`/)).toBeInTheDocument();
    expect(screen.getByText(/preview_digest 仍匹配/)).toBeInTheDocument();
    expect(screen.getByText(/保存失敗時，待處理內容會保留/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '關閉線耗計算邏輯' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '關閉' })).toBeInTheDocument();
    expect(screen.getByAltText('Wear calculation algorithm flow')).toBeInTheDocument();
  });
});
