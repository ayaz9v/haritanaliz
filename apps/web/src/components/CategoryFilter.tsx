import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import type { CategorySection } from "@/data/webConfig";
import { useFilterStore } from "@/state/store";

/** Business type multi-select, grouped (single select in opportunity mode). */
export function CategoryFilter({ sections }: { sections: readonly CategorySection[] }) {
  const selected = useFilterStore((state) => state.categories);
  const mode = useFilterStore((state) => state.mode);
  const toggleCategory = useFilterStore((state) => state.toggleCategory);
  const clearCategories = useFilterStore((state) => state.clearCategories);
  const selectedIds = new Set(selected);

  return (
    <section aria-labelledby="category-heading" className="flex flex-col gap-3">
      <div className="flex min-h-6 items-center justify-between gap-2">
        <h2 id="category-heading" className="text-sm font-semibold">
          İşletme türü
        </h2>
        {selected.length > 0 && (
          <Button variant="ghost" size="xs" onClick={clearCategories}>
            Temizle ({selected.length})
          </Button>
        )}
      </div>
      {mode === "opportunity" && (
        <p className="-mt-1 text-xs text-muted-foreground">
          Fırsat aramasında tek bir işletme türü seçilir.
        </p>
      )}
      {sections.map(({ group, categories }) => (
        <div
          key={group.id}
          role="group"
          aria-labelledby={`group-${group.id}`}
          className="flex flex-col gap-2"
        >
          <h3 id={`group-${group.id}`} className="text-xs font-medium text-muted-foreground">
            {group.name}
          </h3>
          <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
            {categories.map((category) => {
              const inputId = `category-${category.id}`;
              return (
                <div key={category.id} className="flex items-center gap-2">
                  <Checkbox
                    id={inputId}
                    checked={selectedIds.has(category.id)}
                    onCheckedChange={() => toggleCategory(category.id)}
                  />
                  <Label htmlFor={inputId} className="text-sm leading-tight font-normal">
                    {category.name}
                  </Label>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </section>
  );
}
