import { ScrollArea } from "@/components/ui/scroll-area";
import { useUiStore } from "@/state/ui";
import { FilterPanel } from "./FilterPanel";

/** Desktop: collapsible filter panel next to the map. */
export function SidePanel() {
  const open = useUiStore((state) => state.panelOpen);
  return (
    <aside
      id="filter-panel"
      aria-label="Filtreler ve analiz"
      hidden={!open}
      className="w-80 shrink-0 border-r bg-background"
    >
      <ScrollArea className="h-full">
        <div className="p-4">
          <FilterPanel />
        </div>
      </ScrollArea>
    </aside>
  );
}
