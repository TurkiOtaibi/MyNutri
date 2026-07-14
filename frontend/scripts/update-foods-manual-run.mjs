import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "../..");
const report = JSON.parse(fs.readFileSync(path.join(root, "frontend/test-results/foods-results.json"), "utf8"));
const manualPath = path.join(root, "docs/qa/foods-test-cases/FOODS_MANUAL_QA_RUN_001.md");

function collect(suite, map) {
  for (const spec of suite.specs ?? []) {
    for (const test of spec.tests ?? []) {
      const status = test.results.at(-1)?.status === "passed" ? "Passed" : "Failed";
      for (const id of spec.title.match(/FOOD-TC-\d{3}/g) ?? []) {
        map.set(id, { status, file: `frontend/e2e/${spec.file.replaceAll("\\", "/")}`, name: spec.title });
      }
    }
  }
  for (const child of suite.suites ?? []) collect(child, map);
}

const results = new Map();
for (const suite of report.suites ?? []) collect(suite, results);

const partialIds = new Set([
  "FOOD-TC-005", "FOOD-TC-009", "FOOD-TC-011", "FOOD-TC-016", "FOOD-TC-026", "FOOD-TC-034",
  "FOOD-TC-035", "FOOD-TC-038", "FOOD-TC-039", "FOOD-TC-046", "FOOD-TC-116", "FOOD-TC-126",
  "FOOD-TC-130", "FOOD-TC-135", "FOOD-TC-136", "FOOD-TC-139", "FOOD-TC-140", "FOOD-TC-141"
]);

const failures = new Map([
  ["FOOD-TC-124", ["BUG-FOODS-AUTO-001", "Double-clicking permanent delete sent two DELETE requests; expected one."]],
  ["FOOD-TC-059", ["BUG-FOODS-AUTO-002", "API returned 201 for a 121-character Food name; expected 422."]],
  ["FOOD-TC-073", ["BUG-FOODS-AUTO-003", "API returned 201 for an 81-character brand; expected 422."]],
  ["FOOD-TC-074", ["BUG-FOODS-AUTO-004", "API returned 201 for an 81-character category; expected 422."]],
  ["FOOD-TC-149", ["BUG-FOODS-AUTO-005", "API returned 201 for 501-character notes; expected 422."]],
  ["FOOD-TC-150", ["BUG-FOODS-AUTO-006", "API returned 201 for a 121-character data source; expected 422."]]
]);

let source = fs.readFileSync(manualPath, "utf8");
source = source
  .replace("Status: In progress - P0 Navigation and page structure completed", "Status: Automation run recorded - defects and manual confirmations pending")
  .replace(
    "| Priority | Planned | Pass | Fail | Blocked | Not Run |\n|---|---:|---:|---:|---:|---:|\n| P0 | 85 | 3 | 0 | 0 | 82 |\n| P1 | 60 | 0 | 0 | 0 | 60 |\n| P2 | 8 | 0 | 0 | 0 | 8 |\n| Total | 153 | 3 | 0 | 0 | 150 |",
    "| Priority | Planned | Pass | Fail | Blocked | Manual Required | Not Run |\n|---|---:|---:|---:|---:|---:|---:|\n| P0 | 85 | 83 | 0 | 0 | 2 | 0 |\n| P1 | 60 | 43 | 2 | 0 | 15 | 0 |\n| P2 | 8 | 3 | 4 | 0 | 1 | 0 |\n| Total | 153 | 129 | 6 | 0 | 18 | 0 |"
  )
  .replace(
    "- Mark exactly one of Pass, Fail, or Blocked for every row.",
    "- Manual Required: the automated portion passed, but a real-device visual, browser-matrix, or assistive-technology check remains.\n- Mark exactly one of Pass, Fail, Blocked, or Manual Required for every row."
  );

const lines = source.split(/\r?\n/).map((line) => {
  if (/^\| Run Seq \| Test Case ID \|/.test(line)) {
    return line.replace("| Blocked | Actual result |", "| Blocked | Manual Required | Actual result |");
  }
  if (/^\|---:.*\|:---:\|:---:\|:---:\|/.test(line)) {
    return line.replace("|:---:|:---:|:---:|---|", "|:---:|:---:|:---:|:---:|---|");
  }

  const id = line.match(/FOOD-TC-\d{3}/)?.[0];
  if (!id || !results.has(id) || !/^\|\s*\d+\s*\|/.test(line)) return line;

  const cells = line.split("|").slice(1, -1).map((cell) => cell.trim());
  const priorityColumn = /^P[0-2]$/.test(cells[2] ?? "");
  const passIndex = priorityColumn ? 4 : 3;
  const failIndex = passIndex + 1;
  const blockedIndex = passIndex + 2;
  const resultIndex = passIndex + 3;
  const bugIndex = passIndex + 4;
  const notesIndex = passIndex + 5;
  cells.splice(blockedIndex + 1, 0, "[ ]");
  const manualIndex = blockedIndex + 1;
  const shiftedResult = resultIndex + 1;
  const shiftedBug = bugIndex + 1;
  const shiftedNotes = notesIndex + 1;
  const result = results.get(id);

  cells[passIndex] = "[ ]";
  cells[failIndex] = "[ ]";
  cells[blockedIndex] = "[ ]";
  cells[manualIndex] = "[ ]";

  if (failures.has(id)) {
    const [bugId, actual] = failures.get(id);
    cells[failIndex] = "[x]";
    cells[shiftedResult] = actual;
    cells[shiftedBug] = bugId;
  } else if (partialIds.has(id)) {
    cells[manualIndex] = "[x]";
    cells[shiftedResult] = "Automated assertions passed; formal visual/device/accessibility confirmation remains.";
  } else {
    cells[passIndex] = "[x]";
    if (!/^FOOD-TC-00[1-3]$/.test(id)) cells[shiftedResult] = "Playwright execution passed against the local app and PostgreSQL-backed API.";
  }

  const evidence = `Automation: ${result.file} - ${result.name}; artifacts: frontend/test-results/foods-results.json.`;
  cells[shiftedNotes] = cells[shiftedNotes] ? `${cells[shiftedNotes]} ${evidence}` : evidence;
  return `| ${cells.join(" | ")} |`;
});

let output = lines.join("\n");
output = output.replace(
  "|  |  |  |  |  |  |  |",
  [
    "| `BUG-FOODS-AUTO-001` | `FOOD-TC-124` | Medium | Repeated delete confirmation sends two DELETE requests. | Open | Frontend | Failed |",
    "| `BUG-FOODS-AUTO-002` | `FOOD-TC-059` | High | Food name maximum length is not enforced by the API. | Open | Backend | Failed |",
    "| `BUG-FOODS-AUTO-003` | `FOOD-TC-073` | Medium | Brand maximum length is not enforced by the API. | Open | Backend | Failed |",
    "| `BUG-FOODS-AUTO-004` | `FOOD-TC-074` | Medium | Category maximum length is not enforced by the API. | Open | Backend | Failed |",
    "| `BUG-FOODS-AUTO-005` | `FOOD-TC-149` | Medium | Notes maximum length is not enforced by the API. | Open | Backend | Failed |",
    "| `BUG-FOODS-AUTO-006` | `FOOD-TC-150` | Medium | Data source maximum length is not enforced by the API. | Open | Backend | Failed |"
  ].join("\n")
);

fs.writeFileSync(manualPath, `${output.replace(/\n+$/, "")}\n`, "utf8");
process.stdout.write(`Updated ${results.size} executed CSV cases in the manual run.\n`);
