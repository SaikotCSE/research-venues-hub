import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

import { type Page, expect } from "@playwright/test";

const require = createRequire(import.meta.url);
const AXE = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");

/** Collect console errors, uncaught exceptions and CSP violations for the test to assert on. */
export function watchConsole(page: Page) {
  const problems: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error" && !/status of 404/.test(m.text())) problems.push(m.text());
  });
  page.on("pageerror", (e) => problems.push(e.message));
  return problems;
}

export async function login(page: Page, username = "demo", password = "demo-pass-123") {
  await page.goto("/accounts/login/");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/accounts\/$/);
}

/** Run axe-core and return serious/critical violations (WCAG 2.1 A/AA). */
export async function axe(page: Page) {
  await page.evaluate(AXE); // evaluated over CDP, so the page's strict CSP stays untouched
  return page.evaluate(async () => {
    // @ts-expect-error injected global
    const result = await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] } });
    return result.violations
      .filter((v: { impact: string }) => v.impact === "serious" || v.impact === "critical")
      .map(
        (v: { id: string; nodes: { target: string[] }[] }) =>
          `${v.id}: ${v.nodes
            .map((n) => n.target.join(" "))
            .slice(0, 3)
            .join(", ")}`,
      );
  });
}
