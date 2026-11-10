/** Secciones de la web: las dos ediciones y los temas. */
export type Edition = 'espana' | 'canarias' | 'tecnologia' | 'finanzas';
export interface Article {
  id: string;
  source: string;
  scope: 'nacional' | 'canario';
  title: string;
  url: string;
  published: string;
  author: string | null;
  summary: string | null;
  image: string | null;
}
export interface Group {
  id: string;
  headline: string;
  headline_source: string;
  image: string | null;
  editions: Edition[];
  source_count: number;
  sources: string[];
  article_count: number;
  first_published: string;
  last_published: string;
  trend: { state: 'sube' | 'baja' | 'estable'; recent: number; previous: number };
  articles: Article[];
}
export interface SourceInfo { name: string; slug: string; scope: 'nacional' | 'canario' }
export interface Data {
  schema_version: number;
  generated_at: string;
  window_hours: number;
  history_days: number;
  sources: SourceInfo[];
  groups: Group[];
}
