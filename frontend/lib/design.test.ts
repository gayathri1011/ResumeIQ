import { describe, expect, it } from "vitest";

import { scoreStrokeHex, scoreTextClass } from "@/lib/design";

describe("design tokens", () => {
  it("maps score thresholds to semantic text classes", () => {
    expect(scoreTextClass(85)).toBe("text-success");
    expect(scoreTextClass(65)).toBe("text-warning");
    expect(scoreTextClass(40)).toBe("text-destructive");
  });

  it("maps score thresholds to stroke colors", () => {
    expect(scoreStrokeHex(85)).toContain("142");
    expect(scoreStrokeHex(40)).toContain("0 72%");
  });
});
