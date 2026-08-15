"""Validate the small authoritative-documentation surface without dependencies."""

from __future__ import annotations

import argparse
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


AUTHORITY_FILES = (
    "README.md",
    "AGENTS.md",
    "docs/README.md",
    "docs/1-SYSTEM-PLAN.md",
    "docs/2-ARCHITECTURE-SERVICES.md",
    "docs/CLAUDE_CODE_PROMPTS.md",
)
SUPERSEDED_FILES = (
    "docs/1-SYSTEM-PLAN.md",
    "docs/2-ARCHITECTURE-SERVICES.md",
    "docs/CLAUDE_CODE_PROMPTS.md",
)
BANNER = (
    "> [!CAUTION]",
    "> **SUPERSEDED — DO NOT USE FOR CURRENT IMPLEMENTATION.** See "
    "[the current documentation authority map](README.md).",
)

LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
ASSIGNMENT_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:`)?"
    r"((?:[A-Z][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PRIVATE_KEY|API_KEY|SERVICE_ROLE_KEY))"
    r"|DATABASE_URL|PGPASSWORD)"
    r"(?:`)?\s*[:=]\s*([^\s#]+)"
)
SAFE_VALUE_RE = re.compile(
    r"^(?:$|<[^>]+>|\$\{[^}]+\}|your[-_].*|example.*|placeholder.*|redacted|\*+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Results:
    broken_links: tuple[str, ...]
    secrets: tuple[str, ...]
    banners_found: int

    @property
    def ok(self) -> bool:
        return not self.broken_links and not self.secrets and self.banners_found == len(
            SUPERSEDED_FILES
        )


def _link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return target.split(maxsplit=1)[0]


def _validate(root: Path) -> Results:
    broken_links: list[str] = []
    secrets: list[str] = []
    banners_found = 0

    for relative_name in AUTHORITY_FILES:
        source = root / relative_name
        if not source.is_file():
            broken_links.append(f"{relative_name}: file is missing")
            continue

        text = source.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            target = _link_target(raw_target)
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith(("#", "mailto:")):
                continue
            local_path = unquote(parsed.path)
            destination = (source.parent / local_path).resolve()
            try:
                destination.relative_to(root.resolve())
            except ValueError:
                broken_links.append(f"{relative_name}: link escapes repository: {target}")
                continue
            if not destination.exists():
                broken_links.append(f"{relative_name}: broken link: {target}")

        for match in ASSIGNMENT_RE.finditer(text):
            value = match.group(2).strip("`\"'")
            if not SAFE_VALUE_RE.fullmatch(value):
                line = text.count("\n", 0, match.start()) + 1
                secrets.append(f"{relative_name}:{line}: assigned value for {match.group(1)}")

    for relative_name in SUPERSEDED_FILES:
        source = root / relative_name
        if not source.is_file():
            continue
        nonblank = [line.strip() for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
        if tuple(nonblank[:2]) == BANNER:
            banners_found += 1

    return Results(tuple(broken_links), tuple(secrets), banners_found)


def _print_results(results: Results) -> None:
    print(f"links: {len(results.broken_links)} broken")
    for issue in results.broken_links:
        print(f"  {issue}")
    print(f"secrets: {len(results.secrets)}")
    for issue in results.secrets:
        print(f"  {issue}")
    print(f"superseded banners: {results.banners_found}/{len(SUPERSEDED_FILES)}")


def _write_fixture(root: Path) -> None:
    for relative_name in AUTHORITY_FILES:
        path = root / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative_name in SUPERSEDED_FILES:
            path.write_text("\n".join(BANNER) + "\n\nHistorical archive.\n", encoding="utf-8")
        else:
            path.write_text("# Current\n\n[Valid target](target.md)\n", encoding="utf-8")
            (path.parent / "target.md").write_text("# Target\n", encoding="utf-8")


def _self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="mynutri-doc-validator-") as temporary:
        root = Path(temporary)
        _write_fixture(root)
        assert _validate(root).ok

        readme = root / "README.md"
        readme.write_text("# Current\n\n[Broken](missing.md)\n", encoding="utf-8")
        assert _validate(root).broken_links
        print("self-test: broken-link fixture rejected")
        _write_fixture(root)

        legacy = root / SUPERSEDED_FILES[0]
        legacy.write_text("# Missing banner\n", encoding="utf-8")
        assert _validate(root).banners_found == len(SUPERSEDED_FILES) - 1
        print("self-test: missing-banner fixture rejected")
        _write_fixture(root)

        readme.write_text(
            "# Current\n\n"
            "DATABASE_URL=postgresql://user:password@host/db\n"
            "SUPABASE_SERVICE_ROLE_KEY=not-a-placeholder\n",
            encoding="utf-8",
        )
        assert len(_validate(root).secrets) == 2
        print("self-test: secret-shaped fixture rejected")

    print("self-test: passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()

    results = _validate(args.root.resolve())
    _print_results(results)
    return 0 if results.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
