export const METRICS = ["count", "per10k", "saturation", "opportunity"] as const;
export type Metric = (typeof METRICS)[number];

export const METRIC_LABELS: Record<Metric, string> = {
  count: "Sayı",
  per10k: "10.000 kişiye düşen",
  saturation: "Doygunluk",
  opportunity: "Fırsat",
};

export const METRIC_DESCRIPTIONS: Record<Metric, string> = {
  count: "Bölgedeki işletme sayısı.",
  per10k: "Nüfusa göre yoğunluk: her 10.000 kişiye düşen işletme sayısı.",
  saturation: "Gözlenen sayının modelin beklediği sayıyla karşılaştırması: fazla, dengeli, eksik.",
  opportunity: "Eksiklik, erişilebilirlik ve talebin ağırlıklı birleşimi.",
};

export const MODES = ["explore", "opportunity"] as const;
export type Mode = (typeof MODES)[number];

export const MODE_LABELS: Record<Mode, string> = {
  explore: "Bölge analizi",
  opportunity: "Fırsat arama",
};

export interface Filters {
  /** Selected category ids, sorted. Opportunity mode allows at most one. */
  categories: string[];
  metric: Metric;
  regionId: string | null;
  mode: Mode;
}

export const DEFAULT_FILTERS: Filters = {
  categories: [],
  metric: "per10k",
  regionId: null,
  mode: "explore",
};

export function isMetric(value: unknown): value is Metric {
  return (METRICS as readonly unknown[]).includes(value);
}

export function isMode(value: unknown): value is Mode {
  return (MODES as readonly unknown[]).includes(value);
}

/** Sorts and de-duplicates categories; opportunity mode keeps only the first one. */
export function normalizeFilters(filters: Filters): Filters {
  const categories = [...new Set(filters.categories)].sort();
  return {
    categories: filters.mode === "opportunity" ? categories.slice(0, 1) : categories,
    metric: filters.metric,
    regionId: filters.regionId,
    mode: filters.mode,
  };
}

export function pickFilters({ categories, metric, regionId, mode }: Filters): Filters {
  return { categories, metric, regionId, mode };
}
