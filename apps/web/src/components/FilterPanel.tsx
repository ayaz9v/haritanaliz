import { ChartColumn, MapPin, X } from "lucide-react";
import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useRegionIndex, useWebConfig } from "@/data/queries";
import { REGION_LEVEL_LABELS } from "@/data/regions";
import { groupCategories } from "@/data/webConfig";
import {
  isMetric,
  isMode,
  METRIC_DESCRIPTIONS,
  METRIC_LABELS,
  METRICS,
  MODE_LABELS,
  MODES,
} from "@/state/filters";
import { useFilterStore } from "@/state/store";
import { CategoryFilter } from "./CategoryFilter";

/** Content of the filter panel (desktop side panel and mobile bottom sheet). */
export function FilterPanel() {
  const mode = useFilterStore((state) => state.mode);
  return (
    <div className="flex flex-col gap-5">
      <ModeSection />
      <RegionSection />
      {mode === "explore" && <MetricSection />}
      <Separator />
      <CategorySection />
      <AnalysisPlaceholder />
    </div>
  );
}

function ModeSection() {
  const mode = useFilterStore((state) => state.mode);
  const setMode = useFilterStore((state) => state.setMode);
  return (
    <section aria-labelledby="mode-heading" className="flex flex-col gap-2">
      <h2 id="mode-heading" className="text-sm font-semibold">
        Mod
      </h2>
      <ToggleGroup
        type="single"
        variant="outline"
        spacing={0}
        value={mode}
        onValueChange={(value) => {
          if (isMode(value)) setMode(value);
        }}
        className="grid w-full grid-cols-2"
      >
        {MODES.map((item) => (
          <ToggleGroupItem key={item} value={item}>
            {MODE_LABELS[item]}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </section>
  );
}

function RegionSection() {
  const regionId = useFilterStore((state) => state.regionId);
  const setRegion = useFilterStore((state) => state.setRegion);
  const { data: index } = useRegionIndex();
  const region = regionId ? index?.regions.find((item) => item.id === regionId) : undefined;
  const sectionRef = useRef<HTMLElement>(null);

  // A region picked in the search box should be visible even if the panel was scrolled.
  useEffect(() => {
    if (regionId) sectionRef.current?.scrollIntoView({ block: "nearest" });
  }, [regionId]);

  return (
    <section ref={sectionRef} aria-labelledby="region-heading" className="flex flex-col gap-2">
      <h2 id="region-heading" className="text-sm font-semibold">
        Bölge
      </h2>
      {regionId ? (
        <div className="flex items-center gap-2 rounded-lg border px-3 py-2">
          <MapPin className="size-4 shrink-0 text-muted-foreground" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium" data-testid="selected-region">
              {region?.name ?? regionId}
            </p>
            {region && (
              <p className="text-xs text-muted-foreground">{REGION_LEVEL_LABELS[region.level]}</p>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setRegion(null)}
            aria-label="Bölge seçimini kaldır"
          >
            <X />
          </Button>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Arama kutusundan bir bölge seçin.</p>
      )}
    </section>
  );
}

function MetricSection() {
  const metric = useFilterStore((state) => state.metric);
  const setMetric = useFilterStore((state) => state.setMetric);
  return (
    <section aria-labelledby="metric-heading" className="flex flex-col gap-2">
      <h2 id="metric-heading" className="text-sm font-semibold">
        Gösterilecek ölçü
      </h2>
      <ToggleGroup
        type="single"
        variant="outline"
        value={metric}
        onValueChange={(value) => {
          if (isMetric(value)) setMetric(value);
        }}
        className="grid w-full grid-cols-2"
      >
        {METRICS.map((item) => (
          <ToggleGroupItem
            key={item}
            value={item}
            className="h-auto min-h-8 px-2 py-1.5 leading-tight whitespace-normal"
          >
            {METRIC_LABELS[item]}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      <p className="text-xs text-muted-foreground">{METRIC_DESCRIPTIONS[metric]}</p>
    </section>
  );
}

function CategorySection() {
  const { data: config, isPending, isError } = useWebConfig();

  // Drop category ids from the URL that this data version does not know.
  useEffect(() => {
    if (!config) return;
    const known = new Set(config.categories.map((category) => category.id));
    const { categories } = useFilterStore.getState();
    const kept = categories.filter((id) => known.has(id));
    if (kept.length !== categories.length) useFilterStore.setState({ categories: kept });
  }, [config]);

  if (isPending) {
    return <p className="text-sm text-muted-foreground">İşletme türleri yükleniyor…</p>;
  }
  if (isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        İşletme türleri yüklenemedi.
      </p>
    );
  }
  return <CategoryFilter sections={groupCategories(config)} />;
}

function AnalysisPlaceholder() {
  const mode = useFilterStore((state) => state.mode);
  return (
    <section
      aria-labelledby="analysis-heading"
      className="flex flex-col gap-1.5 rounded-lg border border-dashed p-3"
    >
      <h2 id="analysis-heading" className="flex items-center gap-2 text-sm font-semibold">
        <ChartColumn className="size-4" aria-hidden />
        {mode === "explore" ? "Analiz paneli" : "Fırsatlı mahalleler"}
      </h2>
      <p className="text-xs text-muted-foreground">
        {mode === "explore"
          ? "Bir bölge seçildiğinde kategori bazında doygunluk tablosu, grafikler, kısa yorum, veri güven düzeyi ve veri tarihi burada gösterilecek."
          : "Bir işletme türü seçildiğinde seçili alandaki en fırsatlı mahalleler burada sıralanacak."}
      </p>
      <p className="text-xs font-medium text-amber-800">Analiz verisi henüz yayınlanmadı.</p>
    </section>
  );
}
