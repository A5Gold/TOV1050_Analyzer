import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './', // Use relative paths for Electron file:// protocol
  define: {
    // Polyfill process for browser compatibility
    'process.env': {},
    'process.version': JSON.stringify('').split('"').join("'"), // Avoid JSON.stringify quotes
    'process.platform': JSON.stringify('browser'),
    'process.browser': true,
  },
  resolve: {
    alias: {
      buffer: 'buffer/',
      stream: 'stream-browserify',
      util: 'util/',
    },
  },
  server: {
    // The launcher sets TOV1050_DEV_PORT when the default port is occupied.
    port: Number(process.env.TOV1050_DEV_PORT || 5174),
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        timeout: 300000,
        proxyTimeout: 300000,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    exclude: ['**/node_modules/**', '**/tests/**'],
    css: true,
    server: {
      deps: {
        inline: [/@mui\//],
      },
    },
  },
} as any)
