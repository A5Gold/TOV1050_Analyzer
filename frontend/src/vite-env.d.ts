/// <reference types="vite/client" />

interface Window {
  electronAPI: {
    openFile: () => Promise<string | null>;
    saveFile: (
      data: ArrayBuffer,
      defaultName: string,
    ) => Promise<{ success: boolean; filePath?: string; error?: string }>;
  };
}
