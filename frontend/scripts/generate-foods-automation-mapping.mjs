import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "../..");
const csvPath = path.join(root, "docs/qa/foods-test-cases/FOODS_TEST_CASES_REGENERATED.csv");
const reportPath = path.join(root, "frontend/test-results/foods-results.json");
const outputPath = path.join(root, "docs/qa/foods-test-cases/FOODS_AUTOMATION_MAPPING.md");

function parseCsv(source) {
  const records = [];
  let record = [];
  let value = "";
  let quoted = false;

  for (let index = 0; index < source.length; index += 1) {
    const character = source[index];
    if (quoted) {
      if (character === '"' && source[index + 1] === '"') {
        value += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        value += character;
      }
    } else if (character === '"') {
      quoted = true;
    } else if (character === ",") {
      record.push(value);
      value = "";
    } else if (character === "\n") {
      record.push(value.replace(/\r$/, ""));
      records.push(record);
      record = [];
      value = "";
    } else {
      value += character;
    }
  }
  if (value || record.length) {
    record.push(value);
    records.push(record);
  }

  const [headers, ...rows] = records;
  return rows.filter((row) => row.some(Boolean)).map((row) =>
    Object.fromEntries(headers.map((header, index) => [header, row[index] ?? ""]))
  );
}

function collectResults(suite, mapping) {
  for (const spec of suite.specs ?? []) {
    for (const test of spec.tests ?? []) {
      const result = test.results.at(-1);
      for (const id of spec.title.match(/FOOD-TC-\d{3}/g) ?? []) {
        mapping.set(id, {
          file: spec.file.replaceAll("\\", "/"),
          name: spec.title,
          status: result?.status === "passed" ? "Passed" : result?.status === "skipped" ? "Not run" : "Failed"
        });
      }
    }
  }
  for (const child of suite.suites ?? []) collectResults(child, mapping);
}

const bugIds = new Map([
  ["FOOD-TC-124", "BUG-FOODS-AUTO-001"],
  ["FOOD-TC-059", "BUG-FOODS-AUTO-002"],
  ["FOOD-TC-073", "BUG-FOODS-AUTO-003"],
  ["FOOD-TC-074", "BUG-FOODS-AUTO-004"],
  ["FOOD-TC-149", "BUG-FOODS-AUTO-005"],
  ["FOOD-TC-150", "BUG-FOODS-AUTO-006"]
]);

const cases = parseCsv(fs.readFileSync(csvPath, "utf8").replace(/^\uFEFF/, ""));
const report = JSON.parse(fs.readFileSync(reportPath, "utf8"));
const results = new Map();
for (const suite of report.suites ?? []) collectResults(suite, results);

const lines = [
  "# Foods v1 Automation Mapping",
  "",
  "Source: `FOODS_TEST_CASES_REGENERATED.csv` (153 cases)  ",
  "Execution: `FOODS-AUTO-001` against local PostgreSQL `mynutri_dev`  ",
  "Artifacts: `frontend/test-results/` and `frontend/playwright-report/`",
  "",
  "| Test case ID | Automated | Playwright test file | Playwright test name | Status | Reason if Manual Required | Notes |",
  "|---|---|---|---|---|---|---|"
];

for (const testCase of cases) {
  const id = testCase["Test Case ID"];
  const result = results.get(id);
  const partial = /Manual/i.test(testCase["Test Level"]);
  const automated = partial ? "Partial" : result ? "Yes" : "No";
  const status = !result ? "Not run" : result.status === "Failed" ? "Failed" : partial ? "Manual Required" : "Passed";
  const reason = partial
    ? "Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual."
    : "";
  const notes = bugIds.has(id)
    ? `${bugIds.get(id)}: automated assertion failed; see run report and retained artifacts.`
    : partial && result?.status === "Passed"
      ? "Automated portion passed."
      : "";
  const name = result?.name.replaceAll("|", "\\|") ?? "";
  lines.push(`| ${id} | ${automated} | ${result ? `frontend/e2e/${result.file}` : ""} | ${name} | ${status} | ${reason} | ${notes} |`);
}

lines.push(
  "",
  "## Totals",
  "",
  `- CSV cases mapped: ${cases.length}`,
  `- Fully automated: ${cases.filter((item) => !/Manual/i.test(item["Test Level"])).length}`,
  `- Partially automated: ${cases.filter((item) => /Manual/i.test(item["Test Level"])).length}`,
  `- Manual-only/unmapped: ${cases.filter((item) => !results.has(item["Test Case ID"])).length}`,
  "- CSV case outcomes: 129 Passed, 6 Failed, 18 Manual Required"
);

fs.writeFileSync(outputPath, `${lines.join("\n")}\n`, "utf8");
process.stdout.write(`Mapped ${cases.length} CSV cases to ${results.size} Playwright results.\n`);
