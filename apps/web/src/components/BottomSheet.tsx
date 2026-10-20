import { ChevronUp, SlidersHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { useFilterSummary } from "@/state/useFilterSummary";
import { useUiStore } from "@/state/ui";
import { FilterPanel } from "./FilterPanel";

/**
 * Mobile: filters in a bottom sheet over the map. Collapsed it shows a one-line summary;
 * it is not modal, so the map stays usable around it.
 */
export function BottomSheet() {
  const expanded = useUiStore((state) => state.sheetExpanded);
  const setExpanded = useUiStore((state) => state.setSheetExpanded);
  const summary = useFilterSummary();

  return (
    <section
      aria-label="Filtreler ve analiz"
      className={cn(
        "absolute inset-x-0 bottom-0 z-20 flex flex-col rounded-t-2xl border-t bg-background shadow-[0_-8px_24px_-12px_rgb(0_0_0/0.3)] transition-[height] duration-300 ease-out motion-reduce:transition-none",
        expanded ? "h-[75%]" : "h-14",
      )}
      data-testid="bottom-sheet"
      data-expanded={expanded}
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-controls="filter-sheet-content"
        className="flex h-14 w-full shrink-0 flex-col items-center gap-1.5 rounded-t-2xl px-4 pt-2 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <span aria-hidden className="h-1 w-10 rounded-full bg-muted-foreground/30" />
        <span className="flex w-full items-center gap-2 text-sm">
          <SlidersHorizontal className="size-4 shrink-0" aria-hidden />
          <span className="font-medium">Filtreler</span>
          <span className="truncate text-muted-foreground">{summary}</span>
          <ChevronUp
            className={cn("ml-auto size-4 shrink-0 transition-transform", expanded && "rotate-180")}
            aria-hidden
          />
        </span>
      </button>
      <div
        id="filter-sheet-content"
        hidden={!expanded}
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pt-2 pb-6"
      >
        <FilterPanel />
      </div>
    </section>
  );
}
