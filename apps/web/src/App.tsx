import { AttributionBar } from "@/components/AttributionBar";
import { BottomSheet } from "@/components/BottomSheet";
import { ScaleIndicator } from "@/components/ScaleIndicator";
import { SidePanel } from "@/components/SidePanel";
import { TopBar } from "@/components/TopBar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useIsDesktop } from "@/hooks/useMediaQuery";
import { MapView } from "@/map/MapView";
import { useUrlSync } from "@/state/useUrlSync";

export default function App() {
  useUrlSync();
  const isDesktop = useIsDesktop();

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex h-dvh flex-col overflow-hidden bg-background text-foreground">
        <TopBar />
        <main className="relative flex min-h-0 flex-1">
          {isDesktop && <SidePanel />}
          <div className="relative min-w-0 flex-1">
            {/* On mobile the collapsed bottom sheet (h-14) sits below the map, not over it. */}
            <MapView className={isDesktop ? "inset-0" : "inset-x-0 top-0 bottom-14"} />
            <ScaleIndicator className="absolute top-2 left-2 z-10" />
            {!isDesktop && <BottomSheet />}
          </div>
        </main>
        <AttributionBar />
      </div>
    </TooltipProvider>
  );
}
