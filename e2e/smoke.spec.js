// @ts-check
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const AXE = fs.readFileSync(path.join(__dirname, "..", "node_modules", "axe-core", "axe.min.js"), "utf8");

/** Fail the test on any console error or CSP violation. */
function watchConsole(page) {
  const problems = [];
  page.on("console", (m) => { if (m.type() === "error") problems.push(m.text()); });
  page.on("pageerror", (e) => problems.push(e.message));
  return problems;
}

async function login(page) {
  await page.goto("/accounts/login/");
  await page.fill("#id_username", "demo");
  await page.fill("#id_password", "demo-pass-123");
  await page.click("form button:has-text('Log in')");
  await expect(page).toHaveURL(/\/accounts\/$/);
}

test("explore filters update results in place with clean, shareable URLs", async ({ page }) => {
  const problems = watchConsole(page);
  await page.goto("/");
  const results = page.locator("#results");
  await expect(results.locator("article").first()).toBeVisible();
  await page.check("input[name=core][value='A*']");
  await expect(page.getByRole("button", { name: "Remove filter: CORE A*" })).toBeVisible();
  await expect(page).toHaveURL(/\?core=A\*$/);
  await page.fill("#q", "vision");
  await expect(page).toHaveURL(/q=vision/);
  await expect(results.locator("article h3").first()).toContainText(/CV|ECCV|ICCV|WACV/);
  await page.getByRole("button", { name: "Remove filter: CORE A*" }).click();
  await expect(page).not.toHaveURL(/core=/);
  expect(problems).toEqual([]);
});

test("view modes: table is sortable, timeline draws Gantt rows", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Table" }).click();
  await expect(page.locator("#results table")).toBeVisible();
  await page.getByRole("button", { name: /^IF/ }).click();
  await expect(page.locator("th[aria-sort='descending']")).toContainText("IF");
  await page.getByRole("button", { name: "Timeline" }).click();
  await expect(page.locator("#results").getByText("Call for papers open")).toBeVisible();
  expect(await page.locator("#results ul > li").count()).toBeGreaterThan(5);
});

test("starring shows a toast and the venue appears in My Targets", async ({ page }) => {
  await page.goto("/venue/cvpr/");
  await page.getByRole("button", { name: "Save CVPR to target venues" }).click();
  await expect(page.getByText("Saved CVPR to My Targets")).toBeVisible();
  await page.goto("/targets/");
  await expect(page.locator("article h3", { hasText: "CVPR" })).toBeVisible();
});

test("compare drawer highlights the best values", async ({ page }) => {
  await page.goto("/?q=cvpr");
  await page.locator("article").first().getByLabel("Compare").check();
  await page.goto("/?q=eccv");
  await page.locator("article").first().getByLabel("Compare").check();
  await page.getByRole("button", { name: "Compare venues" }).click();
  const drawer = page.getByRole("dialog", { name: /Compare venues/ });
  await expect(drawer.locator("table")).toBeVisible();
  await expect(drawer.getByText("(best)").first()).toBeAttached();
});

test("command palette jumps to a venue; theme preference persists", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Control+k");
  await page.keyboard.type("icml");
  await expect(page.locator("#palette-results [role=option]").first()).toContainText("ICML");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/venue\/icml\/$/);
  await page.keyboard.press("d");
  const dark = await page.evaluate(() => document.documentElement.classList.contains("dark"));
  await page.reload();
  expect(await page.evaluate(() => document.documentElement.classList.contains("dark"))).toBe(dark);
});

test("tracker cards can be dragged to another column", async ({ page }) => {
  await login(page);
  await page.goto("/tracker/");
  const card = page.locator("section[aria-labelledby='col-planning'] li[draggable]").first();
  const title = (await card.locator("a").textContent()).trim();
  await card.dragTo(page.locator("section[aria-labelledby='col-writing']"));
  await expect(page.getByText(/Moved “.*” to Writing/)).toBeVisible();
  await expect(page.locator("section[aria-labelledby='col-writing']")).toContainText(title.slice(0, 20));
});

for (const url of ["/", "/?view=timeline", "/venue/cvpr/", "/recommend/?text=graph+learning", "/api/docs/", "/accounts/login/", "/about/", "/privacy/", "/embed/venue/cvpr/"]) {
  test(`no accessibility violations: ${url}`, async ({ page }) => {
    const problems = watchConsole(page);
    await page.goto(url);
    await page.evaluate(AXE); // evaluate() is not subject to the page's CSP
    const violations = await page.evaluate(async () =>
      (await axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] } })).violations.map((v) => `${v.id} (${v.nodes.length})`));
    expect(violations).toEqual([]);
    expect(problems).toEqual([]);
  });
}
