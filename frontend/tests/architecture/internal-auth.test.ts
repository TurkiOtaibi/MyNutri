import { readFileSync } from "node:fs";
import { expect, it } from "vitest";

it("uses internal credentials throughout the browser authentication boundary", () => {
  for (const file of ["components/AuthProvider.tsx", "components/AuthShell.tsx", "lib/api.ts", "proxy.ts"]) {
    const source = readFileSync(file, "utf8");
    expect(source).not.toMatch(/createClient|createServerClient|supabase\.auth|document\.cookie/);
  }
});
