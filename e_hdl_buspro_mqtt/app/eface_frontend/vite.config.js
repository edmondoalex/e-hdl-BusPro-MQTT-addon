import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  base: '/static/eface/',
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://127.0.0.1:8124',
      '/ws': {
        target: 'ws://127.0.0.1:8124',
        ws: true
      }
    }
  },
  build: {
    emptyOutDir: true,
    sourcemap: false
  }
})
