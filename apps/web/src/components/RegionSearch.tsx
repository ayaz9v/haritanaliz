import { useMemo, useState } from "react";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from "@/components/ui/command";
import { useManifest, useRegionIndex } from "@/data/queries";
import { REGION_LEVEL_LABELS } from "@/data/regions";
import { searchByName } from "@/lib/turkish";
import { cn } from "@/lib/utils";
import { useFilterStore } from "@/state/store";
import { useUiStore } from "@/state/ui";

/**
 * Region search (il → ilçe → mahalle/köy) with Turkish-aware matching. Until boundary data
 * is published, the sample index only contains the 81 provinces.
 */
export function RegionSearch({ className }: { className?: string }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const { data: index, isPending, isError } = useRegionIndex();
  const isSample = useManifest().data?.sample ?? false;
  const setRegion = useFilterStore((state) => state.setRegion);

  const results = useMemo(() => (index ? searchByName(index.regions, query) : []), [index, query]);
  const showList = open && query.trim().length > 0;

  const select = (regionId: string) => {
    setRegion(regionId);
    setQuery("");
    setOpen(false);
    useUiStore.getState().revealPanel();
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
  };

  return (
    <Command
      shouldFilter={false}
      loop
      label="Bölge ara"
      className={cn("relative h-auto overflow-visible bg-transparent p-0", className)}
    >
      <CommandInput
        value={query}
        onValueChange={(value) => {
          setQuery(value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setQuery("");
            setOpen(false);
          }
        }}
        placeholder="İl, ilçe veya mahalle ara"
      />
      {showList && (
        <CommandList
          // Keep focus in the input so that a click selects instead of blurring first.
          onMouseDown={(event) => event.preventDefault()}
          className="absolute inset-x-0 top-full z-50 mt-1 rounded-lg border bg-popover p-1 text-popover-foreground shadow-lg"
        >
          {isPending && (
            <p className="py-4 text-center text-sm text-muted-foreground">Yükleniyor…</p>
          )}
          {isError && (
            <p role="alert" className="py-4 text-center text-sm text-destructive">
              Bölge listesi yüklenemedi.
            </p>
          )}
          {index && <CommandEmpty>Sonuç bulunamadı.</CommandEmpty>}
          {results.length > 0 && (
            <CommandGroup heading={isSample ? "Örnek veri: şimdilik yalnızca iller" : undefined}>
              {results.map((region) => (
                <CommandItem key={region.id} value={region.id} onSelect={() => select(region.id)}>
                  {region.name}
                  <CommandShortcut className="tracking-normal">
                    {REGION_LEVEL_LABELS[region.level]}
                  </CommandShortcut>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
        </CommandList>
      )}
    </Command>
  );
}
