# Product

## Register

product

## Platform

web

## Runtime

Windows Electron desktop application with a React/Vite web UI. The backend runs as a local FastAPI process in development and as a packaged PyInstaller process in the portable build.

## Users

主要使用者是鐵路接觸網維護與工程分析人員。他們在 Windows desktop 環境中進行檢修、比對歷史資料、確認異常與整理報表，需要快速讀取大量量測資料並保留可追溯的分析脈絡。

## Product Purpose

TOV1050 Analyzer 將 TOV1050 CSV 原始量測、line/session metadata、Exception Reports、重複異常與 SQLite 紀錄串接，完成接觸網高度、線材磨耗、stagger、趨勢與報表分析；異常判定重用已驗證的 TOV640 detector contract。

成功的結果是使用者能在同一個工作流程中確認資料品質、理解趨勢、處理例外與衝突、保存可重建的分析結果，並產出正確且可審核的維護報告。

## Positioning

這是一個面向鐵路維護工作的高密度 Windows 分析工作台，將原始量測轉成可追溯的維護決策。它的差異在於嚴格 metadata/section resolution、mainline scope、preview/save digest、optimistic version 與 atomic persistence，而不是展示型或行銷型體驗。

## Brand Personality

專業、克制、可核查。介面應讓使用者感到穩定、清楚且適合長時間重複操作。

## Anti-references

避免行銷 landing page 的英雄區塊、裝飾性卡片堆疊、過度圓角、低對比文字、僅靠顏色傳達狀態，以及會掩蓋原始數值或錯誤脈絡的視覺效果。

## Design Principles

- 先保留資料與決策脈絡，再追求視覺簡潔。
- 讓異常、驗證結果與下一步操作可被快速掃描。
- 沿用既有 MUI/Plotly 語彙，避免為單一畫面引入不一致的互動模式。
- 匯入、分析、比較與匯出流程都要有明確的 loading、empty、error 與完成狀態。
- 所有 preview/save/sync 都以後端重建、digest/version 驗證與交易邊界維持資料正確性。
- 不以 nearest interval、模糊 fallback 或靜默修正掩蓋 metadata drift；無法唯一解析時要 fail closed 並提供可操作診斷。

## Accessibility & Inclusion

維持可鍵盤操作、清楚的焦點狀態與足夠的文字對比；不可只用顏色區分成功、警告與錯誤。尊重使用者的 reduced-motion 設定。
