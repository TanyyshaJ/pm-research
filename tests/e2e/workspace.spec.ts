import { test, expect } from "@playwright/test";

test("account → project → citation → reload → sign out → sign in", async ({
  page,
}) => {
  const email = `e2e-${Date.now()}@example.com`;
  const password = "development-only-passphrase";
  await page.goto("/");
  await page
    .getByRole("button", { name: "Create an account", exact: true })
    .click();
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Good research starts here." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Create your first project" }).click();
  await page
    .getByLabel("Project name", { exact: true })
    .fill("Freelancer finance discovery");
  await page
    .getByLabel("Research question", { exact: true })
    .fill("How do freelancers manage invoice follow-up?");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "No research brief yet." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Create research plan", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "View synthetic example", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Making invoice follow-up less manual" }),
  ).toBeVisible();
  await expect(
    page.getByText("Sample data, transparent by design."),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "View evidence ev_01", exact: true })
    .first()
    .click();
  const drawer = page.getByRole("dialog");
  await expect(
    drawer.getByRole("heading", { name: "Interview A · independent designer" }),
  ).toBeVisible();
  await expect(
    drawer.getByText("I keep a separate sheet for invoices.", { exact: false }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(drawer).not.toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export sample" }).click();
  expect((await download).suggestedFilename()).toBe(
    "fieldnotes-sample-brief.md",
  );
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Freelancer finance discovery" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Sign out", exact: true })
    .filter({ visible: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Welcome to Fieldnotes." }),
  ).toBeVisible();
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page
    .getByRole("button", { name: "Freelancer finance discovery", exact: true })
    .click();
  await page
    .getByRole("button", { name: "View synthetic example", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Making invoice follow-up less manual" }),
  ).toBeVisible();
});
