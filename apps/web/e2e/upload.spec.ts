import { test, expect } from "@playwright/test";

// Smoke coverage for the core pipeline navigation: upload source media,
// browse runs, and the full-bucket file explorer. (Driving a real detection
// run end-to-end requires B2 credentials + the CV runtime, so it is exercised
// manually — see docs/app-workflows.md.)
test.describe("Pipeline navigation", () => {
  test("should display the upload page", async ({ page }) => {
    await page.goto("/upload");
    await expect(page).toHaveURL(/upload/);
  });

  test("should display the runs library", async ({ page }) => {
    await page.goto("/runs");
    await expect(page).toHaveURL(/runs/);
    await expect(page.getByRole("heading", { name: "Runs" })).toBeVisible();
  });

  test("should navigate to files page", async ({ page }) => {
    await page.goto("/files");
    await expect(page).toHaveURL(/files/);
  });

  test("should display the dashboard", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
  });
});
