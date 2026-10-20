import { CalendarDays, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { formatVersionDate, latestVersion } from "@/data/manifest";
import { useManifest } from "@/data/queries";
import { cn } from "@/lib/utils";

/** Date of the data version in use, read from manifest.json. */
export function DataDateBadge({ className }: { className?: string }) {
  const { data: manifest, isPending, isError } = useManifest();

  if (isPending) {
    return (
      <Badge variant="outline" className={cn("text-muted-foreground", className)}>
        Veri tarihi yükleniyor…
      </Badge>
    );
  }
  if (isError) {
    return (
      <Badge variant="destructive" className={className} role="status">
        <TriangleAlert aria-hidden />
        Veri tarihi alınamadı
      </Badge>
    );
  }

  const version = latestVersion(manifest);
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          tabIndex={0}
          className={cn("h-6 cursor-default gap-1.5 px-2", className)}
          data-testid="data-date"
        >
          <CalendarDays aria-hidden />
          <span>
            Veri:{" "}
            <time dateTime={version.version}>{formatVersionDate(version.version, "short")}</time>
          </span>
          {manifest.sample && (
            <span className="rounded-sm bg-amber-100 px-1 text-[0.7rem] text-amber-900">örnek</span>
          )}
        </Badge>
      </TooltipTrigger>
      <TooltipContent side="bottom" align="end" className="flex-col items-start gap-0.5">
        <span>Veri sürümü: {formatVersionDate(version.version)}</span>
        {manifest.sample ? (
          <span>Örnek manifest: gerçek veri henüz yayınlanmadı.</span>
        ) : (
          version.sources.map((source) => (
            <span key={source.id}>
              {source.name}
              {source.version ? ` (${source.version})` : ""}
            </span>
          ))
        )}
      </TooltipContent>
    </Tooltip>
  );
}
