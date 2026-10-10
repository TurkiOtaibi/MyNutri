// Full-dependency audit gate with a reviewed, expiring exception list.
// Fails on any advisory not listed in audit-exceptions.json, on any expired
// exception, and on exceptions that no longer match a reported advisory.
// Production dependencies are audited separately with plain `npm audit --omit=dev`.
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export type AuditException = { id: string; package: string; reason: string; tracking: string; expires: string };
type Via = string | { url?: string; name?: string };
export type AuditReport = { vulnerabilities?: Record<string, { via: Via[] }> };

export function advisoriesOf(report: AuditReport): { id: string; package: string }[] {
  const found = new Map<string, { id: string; package: string }>();
  for (const [name, entry] of Object.entries(report.vulnerabilities ?? {})) {
    for (const via of entry.via) {
      if (typeof via === "string") continue;
      const id = via.url?.match(/GHSA(-[a-z0-9]{4}){3}/)?.[0] ?? via.url ?? "unknown";
      found.set(`${id}:${name}`, { id, package: name });
    }
  }
  return [...found.values()];
}

export function evaluateAudit(report: AuditReport, exceptions: AuditException[], today: string) {
  const advisories = advisoriesOf(report);
  const matches = (e: AuditException, a: { id: string; package: string }) => e.id === a.id && e.package === a.package;
  return {
    unlisted: advisories.filter((a) => !exceptions.some((e) => matches(e, a))),
    expired: exceptions.filter((e) => e.expires < today),
    unused: exceptions.filter((e) => !advisories.some((a) => matches(e, a)))
  };
}

function main() {
  const dir = fileURLToPath(new URL(".", import.meta.url));
  const { exceptions } = JSON.parse(readFileSync(`${dir}audit-exceptions.json`, "utf8")) as { exceptions: AuditException[] };
  let raw: string;
  try {
    raw = execFileSync("npm", ["audit", "--json"], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  } catch (error) {
    // npm audit exits non-zero when it finds advisories; its JSON report is still on stdout.
    raw = (error as { stdout?: string }).stdout ?? "";
  }
  const report = JSON.parse(raw) as AuditReport;
  const { unlisted, expired, unused } = evaluateAudit(report, exceptions, new Date().toISOString().slice(0, 10));
  for (const a of unlisted) console.error(`Unlisted advisory ${a.id} in ${a.package}`);
  for (const e of expired) console.error(`Exception ${e.id} (${e.package}) expired on ${e.expires}; see ${e.tracking}`);
  for (const e of unused) console.error(`Exception ${e.id} (${e.package}) no longer matches an advisory; remove it`);
  for (const e of exceptions) if (!expired.includes(e) && !unused.includes(e)) console.log(`Excepted ${e.id} (${e.package}) until ${e.expires}: ${e.reason}`);
  if (unlisted.length || expired.length || unused.length) process.exit(1);
  console.log("Full dependency audit passed.");
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) main();
