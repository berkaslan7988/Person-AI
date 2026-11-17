import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Build output goes to ../static, which the Python server serves.
export default defineConfig({
  plugins: [react()],
  build: { outDir: '../static', emptyOutDir: false, assetsDir: 'assets', chunkSizeWarningLimit: 900 },
  server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:8550' } },
})
