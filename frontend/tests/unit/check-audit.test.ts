import { describe, expect, it } from "vitest";
import { evaluateAudit, type AuditException, type AuditReport } from "@/scripts/check-audit";

const braces: AuditException = {
  id: "GHSA-vfj7-8cjw-p6xm", package: "braces", reason: "dev only", tracking: "#1", expires: "2026-11-09"
};
const report: AuditReport = {
  vulnerabilities: {
    braces: { via: [{ url: "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm" }] },
    micromatch: { via: ["braces"] }
  }
};

describe("full dependency audit gate", () => {
  it("passes when every advisory is excepted and unexpired", () => {
    expect(evaluateAudit(report, [braces], "2026-10-10")).toEqual({ unlisted: [], expired: [], unused: [] });
  });

  it("fails on any advisory that is not excepted", () => {
    const withSharp: AuditReport = { vulnerabilities: { ...report.vulnerabilities, sharp: { via: [{ url: "https://github.com/advisories/GHSA-wq5f-xc86-pv6w" }] } } };
    expect(evaluateAudit(withSharp, [braces], "2026-10-10").unlisted).toEqual([{ id: "GHSA-wq5f-xc86-pv6w", package: "sharp" }]);
  });

  it("does not let an exception cover the same advisory in another package", () => {
    const elsewhere: AuditReport = { vulnerabilities: { other: { via: [{ url: "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm" }] } } };
    expect(evaluateAudit(elsewhere, [braces], "2026-10-10").unlisted).toHaveLength(1);
  });

  it("fails once an exception expires", () => {
    expect(evaluateAudit(report, [braces], "2026-11-10").expired).toEqual([braces]);
  });

  it("flags an exception that no longer matches a reported advisory", () => {
    expect(evaluateAudit({ vulnerabilities: {} }, [braces], "2026-10-10").unused).toEqual([braces]);
  });
});
