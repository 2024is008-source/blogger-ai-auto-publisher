import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Base path defaults to './' so GitHub Pages works on both user and project sites.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
});
