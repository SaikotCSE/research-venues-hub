import { render } from "@testing-library/react";

import { VenueMark, monogram } from "./venue-mark";

describe("monogram", () => {
  it("keeps short acronyms and shortens long ones", () => {
    expect(monogram("CVPR")).toBe("CVPR");
    expect(monogram("NeurIPS")).toBe("NEU");
    expect(monogram("USENIX ATC")).toBe("UA");
    expect(monogram("IEEE S&P")).toBe("IS");
    expect(monogram("ICML", 2)).toBe("IC");
    expect(monogram("")).toBe("?");
  });

  it("renders a decorative tile with a stable colour per venue", () => {
    const a = render(<VenueMark acronym="ICLR" />).container.firstElementChild!;
    const b = render(<VenueMark acronym="ICLR" />).container.firstElementChild!;
    expect(a).toHaveAttribute("aria-hidden", "true");
    expect(a.textContent).toBe("ICLR");
    expect(a.className).toBe(b.className);
  });
});
