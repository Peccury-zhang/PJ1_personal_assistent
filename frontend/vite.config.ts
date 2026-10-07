import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 开发态：前端跑在 5173，/api 代理到后端 8765
// 生产态：vite build 输出到 ../web，由 FastAPI 托管（同源，/api 直连）
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8765', changeOrigin: true }
    }
  },
  build: {
    outDir: '../web',
    emptyOutDir: true,
    chunkSizeWarningLimit: 2000
  }
})
