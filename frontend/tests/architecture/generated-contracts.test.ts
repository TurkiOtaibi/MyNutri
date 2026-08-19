import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

const root = resolve(import.meta.dirname, "../..");
const schemaPath = resolve(root, "openapi.json");
const contractsPath = resolve(root, "lib/generated/openapi.ts");
const read = (path: string) => readFileSync(path);
const digest = (value: Buffer) => createHash("sha256").update(value).digest("hex");

describe("generated OpenAPI contracts", () => {
  it("regenerates deterministically from the local Backend schema", () => {
    const before = [read(schemaPath), read(contractsPath)];
    const npmCli = process.env.npm_execpath;
    expect(npmCli).toBeTruthy();
    execFileSync(process.execPath, [npmCli!, "run", "generate:api"], {
      cwd: root,
      stdio: "pipe",
    });
    const after = [read(schemaPath), read(contractsPath)];
    expect(after.map(digest)).toEqual(before.map(digest));
    expect(after).toEqual(before);
  }, 120_000);

  it("contains generated transport contracts without a runtime client", () => {
    const source = read(contractsPath).toString("utf8");
    for (const contract of [
      "AccountResponse",
      "ProfileResponse",
      "NutritionRegistryResponse",
      "DiaryEntryResponse",
      "FoodResponse",
      "AdminUserDetail",
      "WeeklyPriorityAnalysisInputV1",
      "NutritionPatternAnalysisResponseV1",
      "export namespace Diary",
      "export namespace Foods",
      "export namespace Progress",
    ]) {
      expect(source).toContain(contract);
    }
    expect(source).not.toMatch(/class (?:Api|HttpClient)|\bfetch\(|\baxios\b|request</);
    expect(source).not.toMatch(/[A-Z]:\\|\/home\/|\/Users\//);
  });

  it("is semantically valid under the repository TypeScript compiler", () => {
    const source = read(contractsPath)
      .toString("utf8")
      .replace("// @ts-nocheck\n", "");
    const options: ts.CompilerOptions = {
      strict: true,
      noEmit: true,
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.ESNext,
      skipLibCheck: true,
    };
    const host = ts.createCompilerHost(options);
    const original = host.getSourceFile.bind(host);
    host.getSourceFile = (fileName, languageVersion, ...rest) =>
      resolve(fileName) === contractsPath
        ? ts.createSourceFile(fileName, source, languageVersion, true)
        : original(fileName, languageVersion, ...rest);
    const program = ts.createProgram([contractsPath], options, host);
    expect(ts.getPreEmitDiagnostics(program)).toEqual([]);
  });
});
