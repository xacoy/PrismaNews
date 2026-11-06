import fs from 'node:fs';
import path from 'node:path';
import type { Data, Group } from './types';

/** Lee los datos generados por el pipeline (public/data) o, si no existen, la muestra de desarrollo. */
function load(): Data {
  const real = path.join(process.cwd(), 'public', 'data', 'groups.json');
  const sample = path.join(process.cwd(), 'src', 'data', 'sample-groups.json');
  const file = fs.existsSync(real) ? real : sample;
  return JSON.parse(fs.readFileSync(file, 'utf-8')) as Data;
}

export const data = load();
export const generatedAt = new Date(data.generated_at);

/** Grupos con actividad dentro de la ventana de la portada (el resto queda como histórico). */
export function frontPageGroups(edition: 'espana' | 'canarias'): Group[] {
  const cutoff = generatedAt.getTime() - data.window_hours * 3600_000;
  return data.groups
    .filter((g) => g.editions.includes(edition) && new Date(g.last_published).getTime() >= cutoff)
    .sort(
      (a, b) =>
        b.source_count - a.source_count ||
        new Date(b.last_published).getTime() - new Date(a.last_published).getTime(),
    );
}

export function groupsBySource() {
  const map = new Map<string, Group[]>();
  for (const g of data.groups) for (const s of g.sources) (map.get(s) ?? map.set(s, []).get(s)!).push(g);
  return map;
}
