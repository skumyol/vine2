import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: process.env.VITE_PORT ? parseInt(process.env.VITE_PORT) : 5173,
    proxy: {
      '/api': {
        target: process.env.VINO_BACKEND_URL || 'http://127.0.0.1:18000',
        changeOrigin: true,
      },
      '/health': {
        target: process.env.VINO_BACKEND_URL || 'http://127.0.0.1:18000',
        changeOrigin: true,
      },
    },
  },
})
