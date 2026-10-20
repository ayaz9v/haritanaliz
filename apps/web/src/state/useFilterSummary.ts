import { METRIC_LABELS, MODE_LABELS } from "./filters";
import { useFilterStore } from "./store";

/** One-line summary of the filters, e.g. "3 tür · 10.000 kişiye düşen". */
export function useFilterSummary(): string {
  const count = useFilterStore((state) => state.categories.length);
  const metric = useFilterStore((state) => state.metric);
  const mode = useFilterStore((state) => state.mode);
  const types = count > 0 ? `${count} tür` : "Tür seçilmedi";
  return `${types} · ${mode === "opportunity" ? MODE_LABELS.opportunity : METRIC_LABELS[metric]}`;
}
