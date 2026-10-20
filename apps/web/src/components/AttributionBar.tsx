import { Fragment } from "react";
import { BASEMAP_ATTRIBUTIONS, DATA_ATTRIBUTIONS, type Attribution } from "@/data/attributions";

function AttributionLinks({ items }: { items: readonly Attribution[] }) {
  return items.map((item, index) => (
    <Fragment key={item.id}>
      {index > 0 && <span aria-hidden>·</span>}
      <a
        href={item.href}
        target="_blank"
        rel="noopener noreferrer"
        className="underline-offset-2 hover:text-foreground hover:underline"
      >
        {item.label}
      </a>
    </Fragment>
  ));
}

/** Always-visible attribution of the base map and the data sources. */
export function AttributionBar() {
  return (
    <footer
      aria-label="Veri atıfları"
      className="z-30 shrink-0 border-t bg-background px-3 py-1 text-[11px] leading-4 text-muted-foreground"
      data-testid="attribution"
    >
      <p className="flex flex-wrap items-center gap-x-1.5">
        <span className="font-medium text-foreground/80">Altlık:</span>
        <AttributionLinks items={BASEMAP_ATTRIBUTIONS} />
        <span aria-hidden className="px-0.5">
          |
        </span>
        <span className="font-medium text-foreground/80">Veri:</span>
        <AttributionLinks items={DATA_ATTRIBUTIONS} />
      </p>
    </footer>
  );
}
