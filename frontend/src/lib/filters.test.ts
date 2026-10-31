import { activeFilterCount, clearFilters, currentView, exportQuery, removeChip, setValue, toggleValue } from "./filters";

describe("explore filter helpers", () => {
  it("toggles repeatable values and resets the page", () => {
    let p = new URLSearchParams("core=A&page=3");
    p = toggleValue(p, "core", "A*");
    expect(p.getAll("core")).toEqual(["A", "A*"]);
    expect(p.has("page")).toBe(false);
    p = toggleValue(p, "core", "A");
    expect(p.getAll("core")).toEqual(["A*"]);
  });

  it("sets and clears single values", () => {
    let p = setValue(new URLSearchParams(), "status", "open");
    expect(p.get("status")).toBe("open");
    p = setValue(p, "status", null);
    expect(p.has("status")).toBe(false);
  });

  it("removes a single chip and keeps the rest", () => {
    const p = removeChip(new URLSearchParams("type=Conference&type=Journal&q=vision"), "type", "Journal");
    expect(p.toString()).toBe("q=vision&type=Conference");
  });

  it("counts active filters and keeps view/sort on reset", () => {
    const p = new URLSearchParams("view=table&sort=rank&q=nlp&core=A&core=B&oa=1");
    expect(activeFilterCount(p)).toBe(4);
    expect(clearFilters(p).toString()).toBe("view=table&sort=rank");
    expect(currentView(p)).toBe("table");
    expect(currentView(new URLSearchParams("view=bogus"))).toBe("grid");
  });

  it("strips view and page from export links", () => {
    expect(exportQuery(new URLSearchParams("view=calendar&page=2&core=A*"))).toBe("core=A*");
  });
});
