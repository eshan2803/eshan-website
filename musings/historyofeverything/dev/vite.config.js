import { defineConfig } from 'vite';

export default defineConfig({
  base: './', // Use relative paths for assets so it runs anywhere (e.g. GitHub Pages subfolder)
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
});
