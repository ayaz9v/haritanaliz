import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import type { CategorySection } from "@/data/webConfig";
import { DEFAULT_FILTERS } from "@/state/filters";
import { useFilterStore } from "@/state/store";
import { CategoryFilter } from "./CategoryFilter";

const sections: CategorySection[] = [
  {
    group: { id: "food_drink", name: "Yeme-içme" },
    categories: [
      { id: "restaurant", name: "Restoran", group: "food_drink" },
      { id: "cafe", name: "Kafe", group: "food_drink" },
    ],
  },
  {
    group: { id: "health", name: "Sağlık" },
    categories: [{ id: "pharmacy", name: "Eczane", group: "health" }],
  },
];

beforeEach(() => {
  useFilterStore.setState(DEFAULT_FILTERS);
});

describe("CategoryFilter", () => {
  it("renders grouped checkboxes", () => {
    render(<CategoryFilter sections={sections} />);
    expect(screen.getByRole("group", { name: "Yeme-içme" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Sağlık" })).toBeInTheDocument();
    expect(screen.getAllByRole("checkbox")).toHaveLength(3);
  });

  it("updates the store when categories are toggled and cleared", async () => {
    const user = userEvent.setup();
    render(<CategoryFilter sections={sections} />);

    await user.click(screen.getByRole("checkbox", { name: "Kafe" }));
    await user.click(screen.getByLabelText("Eczane"));
    expect(useFilterStore.getState().categories).toEqual(["cafe", "pharmacy"]);
    expect(screen.getByRole("checkbox", { name: "Kafe" })).toBeChecked();

    await user.click(screen.getByRole("button", { name: "Temizle (2)" }));
    expect(useFilterStore.getState().categories).toEqual([]);
    expect(screen.getByRole("checkbox", { name: "Kafe" })).not.toBeChecked();
  });

  it("selects a single type in opportunity mode", async () => {
    useFilterStore.setState({ mode: "opportunity" });
    const user = userEvent.setup();
    render(<CategoryFilter sections={sections} />);

    expect(screen.getByText("Fırsat aramasında tek bir işletme türü seçilir.")).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", { name: "Kafe" }));
    await user.click(screen.getByRole("checkbox", { name: "Restoran" }));
    expect(useFilterStore.getState().categories).toEqual(["restaurant"]);
  });
});
