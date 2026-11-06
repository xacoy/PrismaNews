import type { APIRoute } from 'astro';

// Se genera en el build para respetar la subruta (/PrismaNews/ hoy, otra si algún día hay dominio propio).
export const GET: APIRoute = () => {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '') + '/';
  const manifest = {
    id: base,
    name: 'Prisma · qué medios cubren cada noticia',
    short_name: 'Prisma',
    description: 'Titulares de distintos medios agrupados por noticia. Sin etiquetas ni puntuaciones.',
    lang: 'es',
    dir: 'ltr',
    start_url: `${base}?source=pwa`,
    scope: base,
    display: 'standalone',
    orientation: 'portrait-primary',
    background_color: '#0e1013',
    theme_color: '#0e1013',
    categories: ['news'],
    icons: [
      { src: `${base}icons/icon-192.png`, sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: `${base}icons/icon-512.png`, sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: `${base}icons/maskable-512.png`, sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
    shortcuts: [{ name: 'Canarias', url: `${base}canarias/`, icons: [{ src: `${base}icons/icon-192.png`, sizes: '192x192' }] }],
  };
  return new Response(JSON.stringify(manifest), { headers: { 'Content-Type': 'application/manifest+json' } });
};
