import type { Article, Group } from './types';

/** Una diapositiva por medio: primero el titular representativo del grupo, luego el resto por orden alfabético. */
export function buildSlides(g: Group): Article[] {
  const sorted = [...g.articles].sort((a, b) => a.published.localeCompare(b.published));
  const bySource = new Map<string, Article>();
  for (const a of sorted) if (!bySource.has(a.source)) bySource.set(a.source, a);
  const rep = g.articles.find((a) => a.title === g.headline && a.source === g.headline_source) ?? sorted[0];
  const others = [...bySource.values()]
    .filter((a) => a.source !== rep.source)
    .sort((a, b) => a.source.localeCompare(b.source, 'es'));
  return [rep, ...others];
}
