import { readFileSync } from "node:fs";
import { expect, it } from "vitest";

it("uses internal credentials throughout the browser authentication boundary", () => {
  for (const file of ["components/AuthProvider.tsx", "components/AuthShell.tsx", "lib/api.ts", "proxy.ts"]) {
    const source = readFileSync(file, "utf8");
    expect(source).not.toMatch(/createClient|createServerClient|document\.cookie/);
  }
});


it("has no browser provider SDK, configuration, or lifecycle retry boundary", () => {
  const manifest = JSON.parse(readFileSync("package.json", "utf8"));
  expect(Object.keys(manifest.dependencies).sort()).toEqual([
    "@base-ui-components/react", "@tanstack/react-query", "lucide-react", "next", "react", "react-dom"
  ]);
  const sessionBoundary = readFileSync("components/SessionQueryProvider.tsx", "utf8");
  expect(sessionBoundary.match(/process\.env\.[A-Z0-9_]+/g)).toEqual(["process.env.NEXT_PUBLIC_E2E_INSPECTION"]);
  expect(readFileSync("lib/api.ts", "utf8")).not.toMatch(/retry-create|retry-delete/);
});
