import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        walkthrough: resolve(__dirname, 'walkthrough.html'),
      },
    },
  },
  resolve: {
    alias: { '@': resolve(__dirname, 'src') }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://127.0.0.1:18789',
      '/ws': { target: 'ws://127.0.0.1:18789', ws: true },
      '/health': 'http://127.0.0.1:18789',
    }
  }
})
