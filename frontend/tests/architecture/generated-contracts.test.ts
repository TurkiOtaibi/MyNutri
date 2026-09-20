import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

const root = resolve(import.meta.dirname, "../..");
const contractsPath = resolve(root, "lib/generated/openapi.ts");
const read = (path: string) => readFileSync(path);

describe("generated OpenAPI contracts", () => {
  it("contains no runtime client or machine-specific output", () => {
    const source = read(contractsPath).toString("utf8");
    for (const retiredContract of [
      "NutritionPatternAnalysisResponseV2",
      "WeeklyPriorityResultV1",
      "BehaviorGoalResponseV1",
      "export namespace Progress",
      "nutrition_snapshot",
      "snapshot_schema_version",
      "FoodDeleteResponse",
      "archived_at",
      "ArchiveFoodAdminFoods",
      "RestoreFoodAdminFoods",
      "export namespace AdminFoods",
      "FoodCreateV3",
      "FoodUpdateV3",
      "FoodResponseV3",
      "uncategorized_count",
    ]) {
      expect(source).not.toContain(retiredContract);
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
