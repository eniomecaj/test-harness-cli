"""Turn parsed records into a summary report, and render it for humans or files."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass, field

from .categorize import categorize_reason
from .parser import ParseResult, TestRecord


@dataclass
class ComponentStats:
    """Per-component roll-up, used to find the worst offenders."""

    component_id: str
    total: int = 0
    failures: int = 0

    @property
    def fail_rate(self) -> float:
        return self.failures / self.total if self.total else 0.0


@dataclass
class Report:
    total_tests: int
    passed: int
    failed: int
    malformed_lines: int
    failures_by_category: dict[str, int]
    failures_by_test: dict[str, int]
    worst_components: list[dict] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total_tests if self.total_tests else 0.0


def _count_failures_by(records: list[TestRecord], key) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        if record.passed:
            continue
        value = key(record)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def build_report(parse_result: ParseResult, *, top_n: int = 5) -> Report:
    """Roll parsed records up into a Report."""
    records = parse_result.records
    passed = sum(1 for record in records if record.passed)
    failed = len(records) - passed

    stats: dict[str, ComponentStats] = {}
    for record in records:
        entry = stats.setdefault(
            record.component_id, ComponentStats(component_id=record.component_id)
        )
        entry.total += 1
        if not record.passed:
            entry.failures += 1

    # Worst offender = most failures; ties broken by fail rate, then id, so the
    # ordering is deterministic and the CSV/JSON diff cleanly between runs.
    offenders = sorted(
        (entry for entry in stats.values() if entry.failures),
        key=lambda entry: (-entry.failures, -entry.fail_rate, entry.component_id),
    )[:top_n]

    return Report(
        total_tests=len(records),
        passed=passed,
        failed=failed,
        malformed_lines=len(parse_result.errors),
        failures_by_category=_count_failures_by(
            records, lambda record: categorize_reason(record.reason)
        ),
        failures_by_test=_count_failures_by(records, lambda record: record.test_name),
        worst_components=[
            {
                "component_id": entry.component_id,
                "total": entry.total,
                "failures": entry.failures,
                "fail_rate": round(entry.fail_rate, 4),
            }
            for entry in offenders
        ],
    )


def render_console(report: Report, parse_result: ParseResult) -> str:
    """Human-readable report for stdout."""
    lines = [
        "=" * 56,
        "  BOARD TEST SUMMARY",
        "=" * 56,
        f"  Tests run       : {report.total_tests}",
        f"  Passed          : {report.passed}",
        f"  Failed          : {report.failed}",
        f"  Pass rate       : {report.pass_rate:.1%}",
        f"  Malformed lines : {report.malformed_lines}",
    ]

    lines += ["", "  FAILURES BY CATEGORY", "  " + "-" * 54]
    if report.failures_by_category:
        for category, count in report.failures_by_category.items():
            share = count / report.failed if report.failed else 0.0
            lines.append(f"  {category:<16} {count:>5}  ({share:.1%} of failures)")
    else:
        lines.append("  (none)")

    lines += ["", "  WORST-OFFENDING COMPONENTS", "  " + "-" * 54]
    if report.worst_components:
        lines.append(f"  {'COMPONENT':<16} {'FAIL':>5} {'RUN':>5}  FAIL RATE")
        for entry in report.worst_components:
            lines.append(
                f"  {entry['component_id']:<16} {entry['failures']:>5} "
                f"{entry['total']:>5}  {entry['fail_rate']:.1%}"
            )
    else:
        lines.append("  (none)")

    if parse_result.errors:
        lines += ["", "  MALFORMED LINES (not counted in the totals above)", "  " + "-" * 54]
        for error in parse_result.errors:
            location = f"{error.source_file}:{error.line_number}"
            lines.append(f"  {location} - {error.problem}")
            lines.append(f"      {error.raw_line!r}")

    lines.append("=" * 56)
    return "\n".join(lines)


def to_json(report: Report) -> str:
    payload = asdict(report)
    payload["pass_rate"] = round(report.pass_rate, 4)
    return json.dumps(payload, indent=2)


def to_csv(report: Report) -> str:
    """Flatten the report into one long-format CSV: section, key, value."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["section", "key", "value"])

    writer.writerow(["summary", "total_tests", report.total_tests])
    writer.writerow(["summary", "passed", report.passed])
    writer.writerow(["summary", "failed", report.failed])
    writer.writerow(["summary", "pass_rate", round(report.pass_rate, 4)])
    writer.writerow(["summary", "malformed_lines", report.malformed_lines])

    for category, count in report.failures_by_category.items():
        writer.writerow(["failures_by_category", category, count])

    for test_name, count in report.failures_by_test.items():
        writer.writerow(["failures_by_test", test_name, count])

    for entry in report.worst_components:
        writer.writerow(
            [
                "worst_components",
                entry["component_id"],
                f"{entry['failures']}/{entry['total']} ({entry['fail_rate']:.1%})",
            ]
        )

    return buffer.getvalue()
