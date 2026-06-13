import { fileURLToPath, URL } from 'node:url';

import vue from '@vitejs/plugin-vue';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-vue': ['vue', 'vue-router', 'pinia'],
          'vendor-element': ['element-plus', '@element-plus/icons-vue'],
          'vendor-echarts': ['echarts', 'vue-echarts'],
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5373,
    proxy: {
      '/api': {
        target: 'http://localhost:5380',
        changeOrigin: true,
      },
    },
  },
});
