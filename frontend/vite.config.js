import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@site': path.resolve(__dirname, 'src/site'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        assetFileNames: 'static/[name]-[hash][extname]',
        chunkFileNames: 'static/[name]-[hash].js',
        entryFileNames: 'static/[name]-[hash].js',
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'icons': ['lucide-vue-next'],
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