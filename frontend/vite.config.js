import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import os from 'node:os'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  // OneDrive can lock Vite's generated files inside node_modules on Windows.
  // An OS-temporary cache is disposable and keeps source directories immutable.
  cacheDir: process.env.VITE_CACHE_DIR ?? path.join(os.tmpdir(), 'wildfire-vite-cache'),
  // CI and normal checkouts still emit dist/. A temporary absolute directory
  // lets a OneDrive checkout build without mutating locked generated artifacts.
  build: {
    outDir: process.env.VITE_OUT_DIR ?? 'dist',
  },
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.component.test.jsx'],
    setupFiles: ['./src/testSupport/setup.js'],
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
