import { expect, test } from "@playwright/test";
import path from "node:path";

// Visual check, not an assertion-heavy test: `npm run screenshots` saves the images to
// SCREENSHOT_DIR (default: ./screenshots, which git ignores).
const outDir = process.env.SCREENSHOT_DIR ?? "screenshots";

test("@screenshot home and filters", async ({ page, isMobile }, testInfo) => {
  const shot = (name: string) =>
    page.screenshot({ path: path.join(outDir, `${testInfo.project.name}-${name}.png`) });

  await page.goto("/");
  await expect(page.locator('[data-map-status="ready"]')).toBeVisible({ timeout: 30_000 });
  await page.waitForLoadState("networkidle");
  await shot("1-home");

  if (isMobile) await page.getByRole("button", { name: /Filtreler/ }).click();
  await page.getByRole("checkbox", { name: "Kafe" }).click();
  await page.getByRole("checkbox", { name: "Eczane" }).click();
  await page.getByRole("combobox", { name: "Bölge ara" }).fill("izmir");
  await expect(page.getByRole("option", { name: /İzmir/ })).toBeVisible();
  await shot("2-search");

  await page.getByRole("option", { name: /İzmir/ }).click();
  await page.waitForTimeout(400); // let the bottom sheet finish its transition
  await shot("3-filters");
});
