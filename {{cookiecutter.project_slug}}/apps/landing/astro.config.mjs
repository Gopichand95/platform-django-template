// @ts-check
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'astro/config';
import path from 'path';

// https://astro.build/config
export default defineConfig({
  integrations: [react()],
  output: 'static',
  outDir: './dist',
  build: {
    assets: 'assets',
  },
  base: '/static/',
  vite: {
    plugins: [tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve('./src'),
      },
    },
    server: {
      proxy: {
        '/ph/static': {
          target: 'https://us-assets.i.posthog.com',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/ph/, ''),
        },
        '/ph': {
          target: 'https://us.i.posthog.com',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/ph/, ''),
        },
      },
    },
  },
  server: {
    port: 5174,
  },
});
