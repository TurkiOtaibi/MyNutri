import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("macro progress bar CSS", () => {
  it("sizes the fill with width and min-width, not max(), so iOS Safari keeps percentages", () => {
    const css = readFileSync(resolve(process.cwd(), "features/diary/diary.module.css"), "utf8");
    const rule = css.match(/:global\(\.macro-progress-track\):global\(\.has-progress\) > span \{([^}]*)\}/)?.[1] ?? "";
    expect(rule).toContain("width: var(--macro-progress);");
    expect(rule).toContain("min-width: var(--macro-min-progress);");
    expect(css).not.toMatch(/max\([^)]*--macro-(min-)?progress/);
  });
});
