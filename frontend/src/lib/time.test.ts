import { compactCountdown, countdown, formatAoE, formatDate, formatDateRange, formatDateTime, relativeTime, urgency } from "./time";

const NOW = Date.parse("2026-11-01T12:00:00Z");

describe("countdown", () => {
  it("splits the remaining time into units", () => {
    expect(countdown("2026-11-03T15:04:05Z", NOW)).toEqual({
      total: 2 * 86400_000 + 3 * 3600_000 + 4 * 60_000 + 5000,
      days: 2,
      hours: 3,
      minutes: 4,
      seconds: 5,
      done: false,
    });
  });

  it("reports passed deadlines as done", () => {
    expect(countdown("2026-10-01T00:00:00Z", NOW).done).toBe(true);
    expect(compactCountdown(countdown("2026-10-01T00:00:00Z", NOW))).toBe("Closed");
  });

  it("drops seconds when days remain", () => {
    expect(compactCountdown(countdown("2026-11-03T15:04:05Z", NOW))).toBe("2d 03h 04m");
    expect(compactCountdown(countdown("2026-11-01T15:04:05Z", NOW))).toBe("03h 04m 05s");
  });
});

describe("urgency", () => {
  it("escalates as the deadline approaches", () => {
    expect(urgency("2026-12-31T00:00:00Z", NOW)).toBe("normal");
    expect(urgency("2026-11-10T00:00:00Z", NOW)).toBe("soon");
    expect(urgency("2026-11-02T00:00:00Z", NOW)).toBe("critical");
    expect(urgency("2026-10-31T00:00:00Z", NOW)).toBe("closed");
    expect(urgency(null, NOW)).toBe("normal");
  });
});

describe("formatting", () => {
  it("shows Anywhere-on-Earth time 12 hours behind UTC", () => {
    expect(formatAoE("2026-11-15T11:59:00Z")).toBe("Nov 14, 2026, 23:59 AoE");
  });

  it("formats instants in the requested zone", () => {
    expect(formatDateTime("2026-11-15T11:59:00Z", "UTC")).toBe("Nov 15, 2026, 11:59");
    expect(formatDateTime("2026-11-15T11:59:00Z", "Asia/Tokyo")).toBe("Nov 15, 2026, 20:59");
    expect(formatDate("2026-11-15T23:30:00Z", "Asia/Dhaka")).toBe("Nov 16, 2026");
  });

  it("treats plain dates as calendar dates", () => {
    expect(formatDate("2027-06-11", "Pacific/Honolulu")).toBe("Jun 11, 2027");
    expect(formatDate(null)).toBe("—");
  });

  it("collapses date ranges", () => {
    expect(formatDateRange("2027-06-11", "2027-06-16")).toBe("Jun 11–16, 2027");
    expect(formatDateRange("2027-06-28", "2027-07-02")).toBe("Jun 28 – Jul 2, 2027");
    expect(formatDateRange("2027-12-30", "2028-01-02")).toBe("Dec 30, 2027 – Jan 2, 2028");
    expect(formatDateRange("2027-06-11", null)).toBe("Jun 11, 2027");
  });

  it("describes relative times", () => {
    expect(relativeTime("2026-11-01T11:00:00Z", NOW)).toBe("1 hour ago");
    expect(relativeTime("2026-11-04T12:00:00Z", NOW)).toBe("in 3 days");
    expect(relativeTime("2026-11-01T11:59:30Z", NOW)).toBe("just now");
  });
});
