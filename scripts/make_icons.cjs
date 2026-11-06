// Genera los PNG de la PWA a partir del logo. Uso (con Playwright disponible): node scripts/make_icons.cjs
const { chromium } = require('playwright');
const path = require('path');
const out = path.join(__dirname, '..', 'web', 'public', 'icons');
const G = (scale, off) => `<g transform="translate(${off} ${off}) scale(${scale})" fill="none" stroke-linecap="round" stroke-linejoin="round" stroke-width="3">
<line x1="2" y1="36" x2="22" y2="32" stroke="#ecebe6"/><polygon points="22,12 22,52 46,32" stroke="#ecebe6"/>
<line x1="40" y1="24" x2="62" y2="10" stroke="#f2b84b"/><line x1="42" y1="28" x2="62" y2="22" stroke="#b7d94c"/>
<line x1="44" y1="32" x2="62" y2="34" stroke="#4fd1a5"/><line x1="44" y1="36" x2="62" y2="46" stroke="#9b8cff"/>
<line x1="42" y1="40" x2="60" y2="58" stroke="#e78ad6"/></g>`;
const svg = (rx, scale, off) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" rx="${rx}" fill="#0e1013"/>${G(scale, off)}</svg>`;
const jobs = [
  ['icon-512.png', 512, svg(112, 6, 64)],
  ['icon-192.png', 192, svg(112, 6, 64)],
  ['maskable-512.png', 512, svg(0, 5, 96)],          // a sangre y con margen de seguridad
  ['apple-touch-icon.png', 180, svg(0, 5.6, 80)],    // iOS aplica sus propias esquinas
];
(async () => {
  const b = await chromium.launch();
  for (const [name, size, markup] of jobs) {
    const p = await b.newPage({ viewport: { width: size, height: size } });
    await p.setContent(`<style>html,body{margin:0;background:transparent}svg{display:block;width:${size}px;height:${size}px}</style>${markup}`);
    await p.screenshot({ path: path.join(out, name), omitBackground: true });
    await p.close();
  }
  await b.close();
})();
