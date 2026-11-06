// Mejoras progresivas: tema, fechas relativas, imágenes rotas y service worker.
const root = document.documentElement;

// Tema: automático -> claro -> oscuro
const btn = document.getElementById('theme-toggle');
btn?.addEventListener('click', () => {
  const cur = root.dataset.theme;
  const next = cur === undefined ? 'light' : cur === 'light' ? 'dark' : undefined;
  if (next) root.dataset.theme = next; else delete root.dataset.theme;
  try { next ? localStorage.setItem('prisma-theme', next) : localStorage.removeItem('prisma-theme'); } catch {}
  btn.setAttribute('title', `Tema: ${next === 'light' ? 'claro' : next === 'dark' ? 'oscuro' : 'automático'}`);
});

// Fechas relativas ("hace 2 h")
const rtf = new Intl.RelativeTimeFormat('es', { numeric: 'auto' });
function relative(iso: string) {
  const diff = (new Date(iso).getTime() - Date.now()) / 1000;
  const abs = Math.abs(diff);
  if (abs < 60) return 'ahora mismo';
  if (abs < 3600) return rtf.format(Math.round(diff / 60), 'minute');
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), 'hour');
  return rtf.format(Math.round(diff / 86400), 'day');
}
document.querySelectorAll<HTMLTimeElement>('time[data-rel]').forEach((t) => {
  const iso = t.getAttribute('datetime');
  if (iso) { t.title = t.textContent ?? ''; t.textContent = relative(iso); }
});

// Imágenes enlazadas que fallan: se ocultan y queda el fondo de espectro
document.addEventListener('error', (e) => {
  const el = e.target as HTMLElement;
  if (el instanceof HTMLImageElement && el.hasAttribute('data-hide-on-error')) el.style.visibility = 'hidden'; // conserva el hueco: sin saltos de maquetación
}, true);

// Service worker (solo en producción) con la subruta correcta
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  const base = root.dataset.base ?? '/';
  navigator.serviceWorker.register(`${base}sw.js`, { scope: base }).then(() => navigator.serviceWorker.ready).then((reg) => {
    // Tras la primera visita, guarda los recursos de la página actual para verla sin conexión
    const urls = [location.href, ...performance.getEntriesByType('resource').map((r) => r.name)];
    reg.active?.postMessage({ type: 'cache-urls', urls });
  }).catch(() => {});
}
