// End-to-end browser tests. Run: npm run e2e   (starts a throwaway Django server on :8090)
const { defineConfig, devices } = require("@playwright/test");

const python = process.env.PYTHON || "python";
const env = { ...process.env, DJANGO_SETTINGS_MODULE: "config.settings.local", DATABASE_URL: "sqlite:///e2e.sqlite3", RATELIMIT_ENABLED: "0" };

module.exports = defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: { baseURL: "http://127.0.0.1:8090", trace: "retain-on-failure", ...devices["Desktop Chrome"] },
  webServer: {
    command: `rm -f e2e.sqlite3 && ${python} manage.py migrate -v0 && ${python} manage.py seed_venues -v0 && ${python} manage.py seed_demo --password demo-pass-123 && ${python} manage.py runserver 127.0.0.1:8090 --noreload`,
    url: "http://127.0.0.1:8090/healthz",
    env,
    timeout: 120_000,
    reuseExistingServer: false,
  },
});
