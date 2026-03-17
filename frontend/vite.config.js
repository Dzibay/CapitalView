import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'chart': ['chart.js'],
          'axios': ['axios']
        }
      }
    }
  },
  server: {
    host: true,
    strictPort: false,      // позволяет использовать любой порт
    allowedHosts: 'all',    // разрешаем все хосты
    origin: 'http://localhost:5173', // можно указать, но обычно не нужно
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      },
    },
  }
})