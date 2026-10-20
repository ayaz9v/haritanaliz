import { describe, expect, it, vi } from "vitest";
import { applyTurkishLabels, TURKISH_LABEL } from "./labels";

describe("applyTurkishLabels", () => {
  it("replaces name labels and keeps other symbol and non-symbol layers", () => {
    const layout: Record<string, unknown> = {
      label_city: ["coalesce", ["get", "name_en"], ["get", "name"]],
      highway_shield: ["to-string", ["get", "ref"]],
      poi_icon: undefined,
    };
    const map = {
      getStyle: () => ({
        layers: [
          { id: "water", type: "fill" },
          { id: "label_city", type: "symbol" },
          { id: "highway_shield", type: "symbol" },
          { id: "poi_icon", type: "symbol" },
        ],
      }),
      getLayoutProperty: (id: string) => layout[id],
      setLayoutProperty: vi.fn(),
    };

    applyTurkishLabels(map as unknown as Parameters<typeof applyTurkishLabels>[0]);

    expect(map.setLayoutProperty).toHaveBeenCalledTimes(1);
    expect(map.setLayoutProperty).toHaveBeenCalledWith("label_city", "text-field", TURKISH_LABEL);
  });
});
