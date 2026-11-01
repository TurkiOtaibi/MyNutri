import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { expect, it } from "vitest";

it("keeps ESLint's legacy React glob rule effective with the patched matcher", () => {
  const root = resolve(import.meta.dirname, "../..");
  const rule = "react/forbid-component-props";
  const options = { forbid: [{ propName: "color", disallowedForPatterns: ["Trial*"] }] };
  const run = spawnSync(process.execPath, [
    resolve(root, "node_modules/eslint/bin/eslint.js"),
    "--stdin", "--stdin-filename", "components/GlobExample.tsx", "--format", "json",
    "--rule", JSON.stringify({ [rule]: ["error", options] }),
  ], {
    cwd: root,
    encoding: "utf8",
    input: [
      "const TrialButton = () => null;",
      "const OtherButton = () => null;",
      "export default function Example() {",
      "  return <><TrialButton color='red' /><OtherButton color='red' /></>;",
      "}",
    ].join("\n"),
  });
  expect(run.status, run.stderr).toBe(1);
  const [result] = JSON.parse(run.stdout);
  expect(result.messages.filter((issue: { ruleId: string }) => issue.ruleId === rule)).toHaveLength(1);
  expect(result.errorCount).toBe(1);
}, 30_000);
