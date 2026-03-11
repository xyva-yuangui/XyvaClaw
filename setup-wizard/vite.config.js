import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 19091,
    proxy: {
      '/api': 'http://localhost:19090',
    },
  },
  build: {
    outDir: 'dist',
  },
});
