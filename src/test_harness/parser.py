"""Parsing of raw test log files into TestRecord objects.

Log line format (pipe-delimited, whitespace around fields is ignored)::

    2026-07-14T09:12:03 | BRD-00123 | i2c_bus_scan | FAIL | Timeout on addr 0x48

The trailing reason field is only expected on FAIL lines. Blank lines and
lines starting with '#' are comments and are skipped silently. Anything else
that does not fit the format is recorded as a ParseError rather than raising,
because a single corrupt line in a shift's worth of logs should not sink the
whole report.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

FIELD_SEP = "|"
PASS = "PASS"
FAIL = "FAIL"
VALID_RESULTS = (PASS, FAIL)


@dataclass(frozen=True)
class TestRecord:
    """A single board-level test result."""

    timestamp: datetime
    component_id: str
    test_name: str
    result: str
    reason: str = ""
    source_file: str = ""
    line_number: int = 0

    @property
    def passed(self) -> bool:
        return self.result == PASS


@dataclass(frozen=True)
class ParseError:
    """A line we could not turn into a TestRecord, kept for the report."""

    source_file: str
    line_number: int
    raw_line: str
    problem: str


@dataclass
class ParseResult:
    """Everything a parse run produced: the good rows and the bad ones."""

    records: list[TestRecord]
    errors: list[ParseError]

    @property
    def total_lines(self) -> int:
        return len(self.records) + len(self.errors)


def parse_line(
    line: str, *, source_file: str = "", line_number: int = 0
) -> TestRecord | ParseError:
    """Parse one log line. Never raises -- bad input comes back as a ParseError."""
    fields = [field.strip() for field in line.split(FIELD_SEP)]

    if len(fields) < 4:
        return ParseError(
            source_file=source_file,
            line_number=line_number,
            raw_line=line.strip(),
            problem=f"expected at least 4 fields, found {len(fields)}",
        )

    raw_timestamp, component_id, test_name, result = fields[:4]
    reason = fields[4].strip() if len(fields) > 4 else ""

    try:
        timestamp = datetime.fromisoformat(raw_timestamp)
    except ValueError:
        return ParseError(
            source_file=source_file,
            line_number=line_number,
            raw_line=line.strip(),
            problem=f"unreadable timestamp: {raw_timestamp!r}",
        )

    if not component_id:
        return ParseError(
            source_file=source_file,
            line_number=line_number,
            raw_line=line.strip(),
            problem="missing component id",
        )

    if not test_name:
        return ParseError(
            source_file=source_file,
            line_number=line_number,
            raw_line=line.strip(),
            problem="missing test name",
        )

    result = result.upper()
    if result not in VALID_RESULTS:
        return ParseError(
            source_file=source_file,
            line_number=line_number,
            raw_line=line.strip(),
            problem=f"result must be PASS or FAIL, found {result!r}",
        )

    return TestRecord(
        timestamp=timestamp,
        component_id=component_id,
        test_name=test_name,
        result=result,
        reason=reason,
        source_file=source_file,
        line_number=line_number,
    )


def parse_text(text: str, *, source_file: str = "") -> ParseResult:
    """Parse the full contents of one log file."""
    records: list[TestRecord] = []
    errors: list[ParseError] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        parsed = parse_line(line, source_file=source_file, line_number=line_number)
        if isinstance(parsed, TestRecord):
            records.append(parsed)
        else:
            errors.append(parsed)

    return ParseResult(records=records, errors=errors)


def parse_file(path: Path) -> ParseResult:
    """Parse a single log file from disk."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_text(text, source_file=path.name)


def parse_path(path: Path, *, pattern: str = "*.log") -> ParseResult:
    """Parse a log file, or every matching log file in a directory."""
    if path.is_dir():
        paths: Iterable[Path] = sorted(path.glob(pattern))
    else:
        paths = [path]

    records: list[TestRecord] = []
    errors: list[ParseError] = []
    for log_path in paths:
        result = parse_file(log_path)
        records.extend(result.records)
        errors.extend(result.errors)

    return ParseResult(records=records, errors=errors)
