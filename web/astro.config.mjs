import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

// El sitio se sirve bajo /PrismaNews/ (GitHub Pages de proyecto).
export default defineConfig({
  site: 'https://xacoy.github.io',
  base: '/PrismaNews',
  trailingSlash: 'always',
  output: 'static',
  build: { assets: '_astro' },
  vite: { plugins: [tailwindcss()] },
});
