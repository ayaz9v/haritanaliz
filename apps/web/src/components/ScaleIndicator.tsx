import { useWebConfig } from "@/data/queries";
import { zoomBandAt } from "@/data/webConfig";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/state/ui";

const zoomFormat = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 1 });

/** Shows which zoom band (and so which layers) the map is in. */
export function ScaleIndicator({ className }: { className?: string }) {
  const zoom = useUiStore((state) => state.zoom);
  const { data: config } = useWebConfig();
  if (zoom === null || !config) return null;

  const band = zoomBandAt(config.zoom_bands, zoom);
  return (
    <div
      className={cn(
        "pointer-events-none rounded-md border bg-background/90 px-2 py-1 text-xs shadow-sm backdrop-blur-sm",
        className,
      )}
      data-testid="scale-indicator"
    >
      <span className="font-medium">{band?.name ?? "Ölçek"}</span>
      <span className="text-muted-foreground"> · yakınlık {zoomFormat.format(zoom)}</span>
    </div>
  );
}
