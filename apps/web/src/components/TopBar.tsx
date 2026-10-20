import { Hexagon, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useIsDesktop } from "@/hooks/useMediaQuery";
import { useUiStore } from "@/state/ui";
import { DataDateBadge } from "./DataDateBadge";
import { RegionSearch } from "./RegionSearch";

export function TopBar() {
  const isDesktop = useIsDesktop();
  const panelOpen = useUiStore((state) => state.panelOpen);
  const togglePanel = useUiStore((state) => state.togglePanel);

  return (
    <header className="z-30 shrink-0 border-b bg-background">
      <div className="flex h-12 items-center gap-2 px-3 md:h-14 md:gap-3 md:px-4">
        {isDesktop && (
          <Button
            variant="ghost"
            size="icon"
            onClick={togglePanel}
            aria-expanded={panelOpen}
            aria-controls="filter-panel"
            aria-label={panelOpen ? "Filtre panelini kapat" : "Filtre panelini aç"}
          >
            {panelOpen ? <PanelLeftClose /> : <PanelLeftOpen />}
          </Button>
        )}
        <h1 className="flex items-center gap-1.5 text-base font-semibold tracking-tight">
          <Hexagon className="size-5 text-teal-700" aria-hidden />
          haritanaliz
        </h1>
        {isDesktop && <RegionSearch className="mx-auto w-full max-w-md" />}
        <DataDateBadge className="ml-auto md:ml-0" />
      </div>
      {!isDesktop && (
        <div className="px-3 pb-2">
          <RegionSearch />
        </div>
      )}
    </header>
  );
}
