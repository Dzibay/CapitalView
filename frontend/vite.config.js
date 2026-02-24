import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
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