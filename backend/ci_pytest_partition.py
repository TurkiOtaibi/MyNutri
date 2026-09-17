"""Deterministic pytest partitioning and execution evidence for backend CI."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any

import pytest


POSTGRES_SHARDS = 2
POSTGRES_FIXTURES = frozenset(
    {
        "isolated_postgresql_session",
        "plan013_postgresql_session",
        "plan014_postgresql_session",
        "plan015_postgresql_session",
        "plan025_postgresql_database",
        "plan025_postgresql_session",
    }
)
ALLOWED_SKIPS: frozenset[str] = frozenset()


@dataclass
class PartitionState:
    partition: str
    evidence_path: Path
    selected: tuple[str, ...]
    reports: dict[str, list[dict[str, str]]] = field(default_factory=lambda: defaultdict(list))


_state: PartitionState | None = None


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("myNutri backend CI partitioning")
    group.addoption(
        "--ci-backend-partition",
        help="Backend CI partition: plan, unit, postgres-1, or postgres-2.",
    )
    group.addoption(
        "--ci-backend-evidence",
        help="JSON evidence path required when --ci-backend-partition is used.",
    )


def _expected_count(name: str) -> int:
    value = os.environ.get(name)
    if value is None:
        raise pytest.UsageError(f"{name} must be set for backend CI partitioning.")
    try:
        return int(value)
    except ValueError as error:
        raise pytest.UsageError(f"{name} must be an integer, got {value!r}.") from error


def _is_postgres_test(item: pytest.Item) -> bool:
    return item.get_closest_marker("migration") is not None or bool(
        POSTGRES_FIXTURES.intersection(item.fixturenames)
    )


def _build_plan(items: list[pytest.Item]) -> dict[str, Any]:
    nodeids = [item.nodeid.replace("\\", "/") for item in items]
    if len(nodeids) != len(set(nodeids)):
        duplicates = sorted(nodeid for nodeid, count in Counter(nodeids).items() if count > 1)
        raise pytest.UsageError(f"Duplicate node IDs in full backend collection: {duplicates}")

    postgres_nodeids = sorted(
        item.nodeid.replace("\\", "/") for item in items if _is_postgres_test(item)
    )
    postgres_assignment = {
        nodeid: f"postgres-{index % POSTGRES_SHARDS + 1}"
        for index, nodeid in enumerate(postgres_nodeids)
    }
    partitions: dict[str, list[str]] = {
        "unit": [],
        **{f"postgres-{index}": [] for index in range(1, POSTGRES_SHARDS + 1)},
    }
    for nodeid in nodeids:
        partitions[postgres_assignment.get(nodeid, "unit")].append(nodeid)

    expected_full = _expected_count("EXPECTED_BACKEND_TESTS")
    expected_unit = _expected_count("EXPECTED_BACKEND_UNIT_TESTS")
    expected_postgres = _expected_count("EXPECTED_BACKEND_POSTGRES_TESTS")
    errors = []
    if len(nodeids) != expected_full:
        errors.append(f"full collection={len(nodeids)}, expected={expected_full}")
    if len(partitions["unit"]) != expected_unit:
        errors.append(f"unit collection={len(partitions['unit'])}, expected={expected_unit}")
    postgres_total = sum(
        len(partitions[f"postgres-{index}"])
        for index in range(1, POSTGRES_SHARDS + 1)
    )
    if postgres_total != expected_postgres:
        errors.append(f"PostgreSQL collection={postgres_total}, expected={expected_postgres}")

    assigned = [nodeid for partition in partitions.values() for nodeid in partition]
    assigned_counts = Counter(assigned)
    assigned_duplicates = sorted(
        nodeid for nodeid, count in assigned_counts.items() if count != 1
    )
    missing = sorted(set(nodeids) - set(assigned))
    unexpected = sorted(set(assigned) - set(nodeids))
    if missing or unexpected or assigned_duplicates:
        errors.append(
            "partition coverage mismatch: "
            f"missing={len(missing)}, unexpected={len(unexpected)}, "
            f"duplicates={len(assigned_duplicates)}"
        )
    if errors:
        raise pytest.UsageError("Invalid backend CI partition plan: " + "; ".join(errors))

    return {
        "schemaVersion": 1,
        "expected": {
            "full": expected_full,
            "unit": expected_unit,
            "postgres": expected_postgres,
            "postgresShards": POSTGRES_SHARDS,
        },
        "allowedSkips": sorted(ALLOWED_SKIPS),
        "full": nodeids,
        "partitions": partitions,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(
    session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
) -> None:
    del session
    global _state

    partition = config.getoption("--ci-backend-partition")
    evidence_value = config.getoption("--ci-backend-evidence")
    if not partition:
        return
    if not evidence_value:
        raise pytest.UsageError(
            "--ci-backend-evidence is required with --ci-backend-partition."
        )

    plan = _build_plan(items)
    evidence_path = Path(evidence_value)
    if partition == "plan":
        _write_json(evidence_path, plan)
        return
    if partition not in plan["partitions"]:
        valid = ", ".join(["plan", *plan["partitions"]])
        raise pytest.UsageError(f"Unknown backend CI partition {partition!r}; expected {valid}.")

    selected_nodeids = set(plan["partitions"][partition])
    selected_items = [
        item for item in items if item.nodeid.replace("\\", "/") in selected_nodeids
    ]
    deselected_items = [
        item for item in items if item.nodeid.replace("\\", "/") not in selected_nodeids
    ]
    items[:] = selected_items
    config.hook.pytest_deselected(items=deselected_items)
    selected = tuple(item.nodeid.replace("\\", "/") for item in selected_items)
    _state = PartitionState(partition=partition, evidence_path=evidence_path, selected=selected)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if _state is None:
        return
    nodeid = report.nodeid.replace("\\", "/")
    _state.reports[nodeid].append({"phase": report.when, "outcome": report.outcome})


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    del exitstatus
    if _state is None:
        return

    selected = list(_state.selected)
    executed = sorted(_state.reports)
    selected_set = set(selected)
    executed_set = set(executed)
    skipped = sorted(
        nodeid
        for nodeid, reports in _state.reports.items()
        if any(report["outcome"] == "skipped" for report in reports)
    )
    expected_skips = sorted(ALLOWED_SKIPS.intersection(selected_set))
    errors = []

    missing = sorted(selected_set - executed_set)
    unexpected = sorted(executed_set - selected_set)
    if missing or unexpected:
        errors.append(
            f"execution mismatch: missing={len(missing)}, unexpected={len(unexpected)}"
        )

    duplicate_setups = sorted(
        nodeid
        for nodeid, reports in _state.reports.items()
        if sum(report["phase"] == "setup" for report in reports) != 1
    )
    if duplicate_setups:
        errors.append(f"tests without exactly one setup phase={len(duplicate_setups)}")
    if skipped != expected_skips:
        errors.append(f"skip mismatch: actual={skipped}, expected={expected_skips}")

    unsuccessful = []
    for nodeid in selected:
        reports = _state.reports.get(nodeid, [])
        outcomes = {(report["phase"], report["outcome"]) for report in reports}
        if nodeid in ALLOWED_SKIPS:
            if not any(outcome == "skipped" for _, outcome in outcomes):
                unsuccessful.append(nodeid)
        elif not any(phase == "call" and outcome == "passed" for phase, outcome in outcomes):
            unsuccessful.append(nodeid)
        elif any(outcome in {"failed", "skipped"} for _, outcome in outcomes):
            unsuccessful.append(nodeid)
    if unsuccessful:
        errors.append(f"tests without one successful terminal outcome={len(unsuccessful)}")

    payload = {
        "schemaVersion": 1,
        "partition": _state.partition,
        "selected": selected,
        "executed": executed,
        "skipped": skipped,
        "reports": dict(sorted(_state.reports.items())),
        "errors": errors,
    }
    _write_json(_state.evidence_path, payload)

    if errors:
        terminal = session.config.pluginmanager.get_plugin("terminalreporter")
        if terminal is not None:
            terminal.write_sep("=", "backend CI partition verification failed", red=True)
            for error in errors:
                terminal.write_line(f"- {error}", red=True)
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
