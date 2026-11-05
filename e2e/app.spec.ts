import { expect, test } from "@playwright/test";

import { axe, latestCode, login, watchConsole } from "./helpers";

test.describe("explore", () => {
  test("filters live in the URL and update results in place", async ({ page }) => {
    const problems = watchConsole(page);
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Every research deadline");
    const results = page.locator("#results");
    await expect(results.locator("article").first()).toBeVisible();

    await page.getByRole("button", { name: "CORE A*", exact: true }).click();
    await expect(page).toHaveURL(/core=A\*/);
    await expect(page.getByRole("button", { name: "Remove filter: CORE A*" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Explore venues");

    await page.getByRole("searchbox", { name: "Search venues" }).fill("vision");
    await expect(page).toHaveURL(/q=vision/);
    await expect(results.locator("article h3").first()).toContainText(/CVPR|ECCV|ICCV/);

    await page.getByRole("button", { name: "Remove filter: CORE A*" }).click();
    await expect(page).not.toHaveURL(/core=/);
    await page.getByRole("button", { name: "Clear all" }).click();
    await expect(page).not.toHaveURL(/q=/);
    expect(problems).toEqual([]);
  });

  test("table sorts, timeline and calendar render", async ({ page }) => {
    const problems = watchConsole(page);
    await page.goto("/?view=table");
    const table = page.getByRole("table");
    await expect(table).toBeVisible();
    await table.getByRole("button", { name: /^Rank/ }).click();
    await expect(page).toHaveURL(/sort=rank/);
    await expect(table.locator("th[aria-sort]")).toHaveAttribute("aria-sort", "descending");

    await page.getByRole("radio", { name: "Timeline view" }).click();
    await expect(page).toHaveURL(/view=timeline/);
    await expect(page.getByRole("list", { name: "Venue timelines" }).locator("li").first()).toBeVisible();

    await page.getByRole("radio", { name: "Calendar view" }).click();
    await expect(page).toHaveURL(/view=calendar/);
    await expect(page.locator("section[aria-labelledby^=month-]")).toHaveCount(12);
    expect(problems).toEqual([]);
  });

  test("command palette jumps to a venue", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Every research deadline");
    await page.keyboard.press("Control+k");
    const dialog = page.getByRole("dialog", { name: "Search VenuePulse" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("combobox").fill("neurips");
    await dialog
      .getByRole("option", { name: /NeurIPS/ })
      .first()
      .click();
    await expect(page).toHaveURL(/\/venue\/neurips\/$/);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("NeurIPS");
  });
});

test.describe("venue page", () => {
  test("server renders SEO metadata and a 404 for unknown venues", async ({ page, request }) => {
    const html = await (await request.get("/venue/cvpr/")).text();
    expect(html).toContain('<script type="application/ld+json">');
    expect(html).toMatch(/<title>CVPR \d{4} deadlines, rank &amp; submission guide · VenuePulse<\/title>/);
    expect(html).toContain('rel="canonical"');
    const missing = await page.goto("/venue/does-not-exist/");
    expect(missing?.status()).toBe(404);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("couldn’t find that venue");
  });

  test("anonymous visitors can star, take notes and compare", async ({ page }) => {
    const problems = watchConsole(page);
    await page.goto("/venue/cvpr/");
    await expect(page.getByRole("timer").first()).toBeVisible();
    await expect(page.getByText("Embed & API")).toHaveCount(0);

    await page.getByRole("button", { name: "Save to targets" }).click();
    await expect(page.getByRole("button", { name: "Saved to targets" })).toHaveAttribute("aria-pressed", "true");

    await page.getByLabel("Notes about this venue").fill("Use the CVPR 2027 template");
    await expect(page.getByText("Saved", { exact: true })).toBeVisible();

    await page.getByRole("tab", { name: "BibTeX" }).click();
    await expect(page.getByText("@inproceedings{cvpr")).toBeVisible();

    await page.getByRole("button", { name: "Compare", exact: true }).click();
    await page.goto("/venue/iccv/");
    await page.getByRole("button", { name: "Compare", exact: true }).click();
    const tray = page.getByRole("region", { name: "Comparison tray" });
    await tray.getByRole("link", { name: /Compare 2/ }).click();
    await expect(page).toHaveURL(/\/compare\/\?s=cvpr&s=iccv/);
    await expect(page.getByRole("table")).toContainText("h5-index");
    await expect(page.getByText("(best)").first()).toBeAttached();

    await page.goto("/targets/");
    await expect(page.getByRole("heading", { name: "CVPR", exact: false }).first()).toBeVisible();
    await expect(page.getByText("Use the CVPR 2027 template")).toBeVisible();
    expect(problems).toEqual([]);
  });
});

test.describe("accounts", () => {
  test("sign up, keep anonymous stars, log out and back in", async ({ page }) => {
    const problems = watchConsole(page);
    const user = `e2e${Date.now()}`;
    await page.goto("/venue/icml/");
    await page.getByRole("button", { name: "Save to targets" }).click();
    await expect(page.getByRole("button", { name: "Saved to targets" })).toBeVisible();

    await page.goto("/accounts/signup/");
    await page.getByLabel("Username").fill(user);
    await page.getByLabel("Email").fill(`${user}@example.com`);
    await page.getByLabel("Password", { exact: true }).fill("a-Long-pass-123");
    await page.getByLabel("Confirm password").fill("a-Long-pass-123");
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
    await page.getByLabel("Confirmation code").fill(latestCode(`${user}@example.com`));
    await page.getByRole("button", { name: "Verify and create account" }).click();
    await expect(page).toHaveURL(/\/accounts\/profile\/$/);
    await expect(page.getByText("Your email address is confirmed")).toBeVisible();

    await page.getByLabel("Research interests").fill("machine learning, optimization");
    await page.getByRole("button", { name: "Save profile" }).click();
    await expect(page.getByText("Profile saved")).toBeVisible();

    await page.goto("/targets/");
    await expect(page.getByText("ICML").first()).toBeVisible();

    await page.getByRole("button", { name: /Account menu/ }).click();
    await page.getByRole("menuitem", { name: "Log out" }).click();
    await expect(page.getByRole("link", { name: "Log in" })).toBeVisible();

    await login(page, user, "a-Long-pass-123");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/Good (morning|afternoon|evening)/);
    expect(problems).toEqual([]);
  });

  test("reset a forgotten password with an emailed code", async ({ page }) => {
    const problems = watchConsole(page);
    const user = `e2r${Date.now()}`;
    const email = `${user}@example.com`;
    await page.goto("/accounts/signup/");
    await page.getByLabel("Username").fill(user);
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill("a-Long-pass-123");
    await page.getByLabel("Confirm password").fill("a-Long-pass-123");
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
    await page.getByLabel("Confirmation code").fill(latestCode(email));
    await page.getByRole("button", { name: "Verify and create account" }).click();
    await expect(page).toHaveURL(/\/accounts\/profile\/$/);
    await page.getByRole("button", { name: /Account menu/ }).click();
    await page.getByRole("menuitem", { name: "Log out" }).click();
    await expect(page.getByRole("link", { name: "Log in" })).toBeVisible();

    await page.goto("/accounts/password/reset/");
    await page.getByLabel("Email").fill(email);
    await page.getByRole("button", { name: "Send code" }).click();
    await expect(page.getByRole("heading", { name: "Choose a new password" })).toBeVisible();
    await expect(page.getByText(/request a new code in \d+s/)).toBeVisible();
    await page.getByLabel("Code from the email").fill("000000" === latestCode(email) ? "111111" : "000000");
    await page.getByLabel("New password", { exact: true }).fill("Another-pass-456");
    await page.getByLabel("Confirm new password").fill("Another-pass-456");
    await page.getByRole("button", { name: "Set new password" }).click();
    await expect(page.getByText("That code is incorrect. 4 attempts left.")).toBeVisible();
    await page.getByLabel("Code from the email").fill(latestCode(email));
    await page.getByRole("button", { name: "Set new password" }).click();
    await expect(page.getByRole("heading", { name: "Password updated" })).toBeVisible();

    await login(page, user, "Another-pass-456");
    expect(problems.filter((p) => !/status of 400/.test(p))).toEqual([]); // the wrong code above is a deliberate 400
  });

  test("login-only pages redirect anonymous visitors", async ({ page }) => {
    await page.goto("/tracker/");
    await expect(page).toHaveURL(/\/accounts\/login\/\?next=(%2F|\/)tracker(%2F|\/)/);
    await page.getByLabel("Username").fill("demo");
    await page.getByLabel("Password", { exact: true }).fill("wrong-password");
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page.getByRole("alert")).toContainText(/correct username and password/i);
  });
});

test.describe("signed-in features", () => {
  test.beforeEach(async ({ page }) => login(page));

  test("track a submission, tick its checklist and move it on the board", async ({ page }) => {
    const problems = watchConsole(page);
    await page.goto("/tracker/new/?venue=neurips");
    await page.waitForLoadState("networkidle");
    const paper = page.getByLabel("Paper", { exact: true });
    if (await paper.count()) await paper.selectOption("new");
    await page.getByLabel("Paper title").fill("Sparse attention at scale");
    await page.getByRole("button", { name: "Start tracking" }).click();
    await expect(page).toHaveURL(/\/tracker\/s\/\d+\/$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Sparse attention at scale");

    const first = page.locator("[id^=ci-]").first();
    await first.click();
    await expect(first).toHaveAttribute("data-state", "checked");

    await page.goto("/tracker/");
    const card = page.locator("section", { hasText: "Planning" }).getByText("Sparse attention at scale");
    await expect(card).toBeVisible();
    await page.getByRole("button", { name: "Move Sparse attention at scale" }).click();
    await page.getByRole("menuitem", { name: "Writing" }).click();
    await expect(page.locator("section[aria-labelledby=col-writing]")).toContainText("Sparse attention at scale");
    expect(problems).toEqual([]);
  });

  test("lists, reviews and notifications", async ({ page }) => {
    const problems = watchConsole(page);
    await page.goto("/venue/acl/");
    await page.getByLabel("New list name").fill("NLP shortlist");
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await expect(page.getByLabel("NLP shortlist")).toBeChecked();

    await page.getByRole("button", { name: "Share your experience" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("radio", { name: "5 of 5" }).first().click();
    await dialog.getByLabel("Comment").fill("Fast, constructive reviews.");
    await dialog.getByRole("button", { name: "Publish review" }).click();
    await expect(page.getByText("Fast, constructive reviews.")).toBeVisible();

    await page.goto("/accounts/lists/");
    await page.getByRole("link", { name: /NLP shortlist/ }).click();
    await page.getByLabel(/Private — only you/).click();
    await expect(page.getByText(/now public/)).toBeVisible();
    await expect(page.locator("article", { hasText: "ACL" })).toBeVisible();

    await page.goto("/accounts/notifications/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Notifications");
    expect(problems).toEqual([]);
  });

  test("dashboard, profile and settings render without tokens", async ({ page }) => {
    const problems = watchConsole(page);
    await expect(page.getByText("Your next 120 days")).toBeVisible();
    await expect(page.getByText("Calendar feed")).toHaveCount(0);
    await page.goto("/accounts/profile/");
    await expect(page.getByRole("heading", { level: 1, name: "Profile" })).toBeVisible();
    await expect(page.getByText(/API token|Calendar feed/)).toHaveCount(0);
    await page.goto("/accounts/settings/");
    await expect(page.getByRole("link", { name: "Export my data" })).toHaveAttribute("href", "/accounts/settings/export/");
    expect(problems).toEqual([]);
  });
});

test.describe("quality", () => {
  test("theme toggle switches to dark mode and persists", async ({ page }) => {
    await page.goto("/about/");
    await page.getByRole("button", { name: /Change theme/ }).click();
    await page.getByRole("menuitemradio", { name: "Dark" }).click();
    await expect(page.locator("html")).toHaveClass(/dark/);
    await page.reload();
    await expect(page.locator("html")).toHaveClass(/dark/);
  });

  test("no serious accessibility violations on key pages", async ({ page }) => {
    for (const path of ["/", "/venue/cvpr/", "/compare/?s=cvpr&s=iccv", "/insights/", "/plan/?ready=2027-01-15", "/about/", "/api/docs/", "/accounts/login/"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      expect(await axe(page), path).toEqual([]);
    }
    await login(page);
    for (const path of ["/accounts/", "/tracker/", "/accounts/profile/"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      expect(await axe(page), path).toEqual([]);
    }
  });

  test("mobile layout has no horizontal overflow and a working menu", async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    const page = await context.newPage();
    for (const path of ["/", "/venue/cvpr/", "/?view=table", "/compare/?s=cvpr&s=iccv", "/insights/", "/api/docs/"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, path).toBeLessThanOrEqual(0);
    }
    await page.goto("/");
    await page.getByRole("button", { name: "Open menu" }).click();
    await page.getByRole("navigation", { name: "Mobile" }).getByRole("link", { name: "Insights" }).click();
    await expect(page).toHaveURL(/\/insights\/$/);
    await context.close();
  });
});
