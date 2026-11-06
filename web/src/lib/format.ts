const BASE = import.meta.env.BASE_URL.replace(/\/$/, '');

/** Ruta interna respetando la subruta /PrismaNews/. */
export const href = (p = '') => `${BASE}/${p.replace(/^\//, '')}`;

const TZ = 'Europe/Madrid';
export const fmtDate = (iso: string) =>
  new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: TZ }).format(
    new Date(iso),
  );
export const fmtLong = (iso: string) =>
  new Intl.DateTimeFormat('es-ES', { dateStyle: 'long', timeStyle: 'short', timeZone: TZ }).format(new Date(iso));

/**
 * Colores por medio: tono estable por hash, sin rojo ni azul puros (para no sugerir orientación política).
 * El color solo sirve para distinguir medios entre sí.
 */
const HUES = [30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180, 195, 270, 285, 300, 315, 330, 340];
export function sourceHue(slug: string): { h: number; alt: boolean } {
  let x = 5381;
  for (const c of slug) x = (x * 33) ^ c.charCodeAt(0);
  const i = Math.abs(x) % (HUES.length * 2);
  return { h: HUES[i % HUES.length], alt: i >= HUES.length };
}
export const slugify = (s: string) =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
export const colorVars = (name: string) => {
  const { h, alt } = sourceHue(slugify(name));
  return `--h:${h};--ld:${alt ? 0.62 : 0.78};--ll:${alt ? 0.42 : 0.56}`;
};
export const trendLabel = { sube: 'Sube la cobertura', baja: 'Baja la cobertura', estable: 'Cobertura estable' } as const;
export const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
