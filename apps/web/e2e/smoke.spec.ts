import { expect, test, type Page } from "@playwright/test";

async function openFilters(page: Page, isMobile: boolean) {
  if (isMobile) await page.getByRole("button", { name: /Filtreler/ }).click();
}

function queryParam(page: Page, name: string) {
  return () => new URL(page.url()).searchParams.get(name);
}

test("opens on a map of Türkiye with the data date and attributions", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/");
  await expect(page).toHaveTitle(/haritanaliz/);
  await expect(page.getByRole("heading", { name: "haritanaliz" })).toBeVisible();
  await expect(page.locator('[data-map-status="ready"]')).toBeVisible({ timeout: 30_000 });

  // MapLibre writes the view to the hash as #map=zoom/lat/lng; the centre is inside Türkiye.
  await expect
    .poll(() => {
      const [, lat = NaN, lng = NaN] = new URL(page.url()).hash
        .replace("#map=", "")
        .split("/")
        .map(Number);
      return lat > 36 && lat < 42 && lng > 26 && lng < 45;
    })
    .toBe(true);

  await expect(page.getByTestId("data-date")).toContainText("Veri:");
  await expect(page.getByTestId("data-date")).toContainText("örnek");
  await expect(page.getByTestId("attribution")).toContainText("OpenStreetMap");
  await expect(page.getByTestId("scale-indicator")).toContainText("Türkiye / il ölçeği");
  expect(pageErrors).toEqual([]);
});

test("keeps filter selections in the URL", async ({ page, isMobile }) => {
  await page.goto("/");
  await openFilters(page, isMobile);
  await page.getByRole("checkbox", { name: "Eczane" }).click();
  await page.getByRole("checkbox", { name: "Kafe" }).click();
  await page.getByRole("radio", { name: "Doygunluk" }).click();
  await expect.poll(queryParam(page, "cat")).toBe("cafe,pharmacy");
  await expect.poll(queryParam(page, "metric")).toBe("saturation");

  await page.reload();
  await openFilters(page, isMobile);
  await expect(page.getByRole("checkbox", { name: "Kafe" })).toBeChecked();
  await expect(page.getByRole("radio", { name: "Doygunluk" })).toBeChecked();
});

test("finds provinces regardless of Turkish letters", async ({ page, isMobile }) => {
  await page.goto("/");
  await page.getByRole("combobox", { name: "Bölge ara" }).fill("sanliurfa");
  await page.getByRole("option", { name: /Şanlıurfa/ }).click();
  await expect.poll(queryParam(page, "region")).toBe("il-63");
  if (isMobile) {
    await expect(page.getByTestId("bottom-sheet")).toHaveAttribute("data-expanded", "true");
  }
  await expect(page.getByTestId("selected-region")).toHaveText("Şanlıurfa");
  await expect(page.getByTestId("selected-region")).toBeInViewport();
});
