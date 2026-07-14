from datetime import datetime

import pytest

from test_harness.parser import ParseError, TestRecord, parse_line, parse_text


def test_parses_a_passing_line():
    parsed = parse_line("2026-07-14T09:00:01 | BRD-0001 | power_on_self_test | PASS")

    assert isinstance(parsed, TestRecord)
    assert parsed.timestamp == datetime(2026, 7, 14, 9, 0, 1)
    assert parsed.component_id == "BRD-0001"
    assert parsed.test_name == "power_on_self_test"
    assert parsed.passed is True
    assert parsed.reason == ""


def test_parses_a_failing_line_with_a_reason():
    parsed = parse_line("2026-07-14T09:00:05 | BRD-0001 | i2c_bus_scan | FAIL | Bus error 0x48")

    assert isinstance(parsed, TestRecord)
    assert parsed.passed is False
    assert parsed.reason == "Bus error 0x48"


def test_result_is_case_insensitive():
    parsed = parse_line("2026-07-14T09:00:01 | BRD-0001 | psu | pass")

    assert isinstance(parsed, TestRecord)
    assert parsed.result == "PASS"


@pytest.mark.parametrize(
    ("line", "expected_problem"),
    [
        ("2026-07-14T09:04:00 | BRD-0005 | rail_check", "expected at least 4 fields"),
        ("this line is not a log line at all", "expected at least 4 fields"),
        ("2026-07-14T09:05:00 | BRD-0005 | rail_check | MAYBE", "result must be PASS or FAIL"),
        ("not-a-timestamp | BRD-0006 | fw | FAIL | x", "unreadable timestamp"),
        ("2026-07-14T09:05:00 |  | rail_check | PASS", "missing component id"),
        ("2026-07-14T09:05:00 | BRD-0005 |  | PASS", "missing test name"),
    ],
)
def test_bad_lines_become_parse_errors_instead_of_raising(line, expected_problem):
    parsed = parse_line(line, source_file="run.log", line_number=7)

    assert isinstance(parsed, ParseError)
    assert expected_problem in parsed.problem
    assert parsed.source_file == "run.log"
    assert parsed.line_number == 7


def test_blank_lines_and_comments_are_skipped():
    text = "\n".join(
        [
            "# a comment",
            "",
            "   ",
            "2026-07-14T09:00:01 | BRD-0001 | psu | PASS",
        ]
    )

    result = parse_text(text, source_file="run.log")

    assert len(result.records) == 1
    assert result.errors == []


def test_parse_text_keeps_good_records_alongside_bad_lines():
    text = "\n".join(
        [
            "2026-07-14T09:00:01 | BRD-0001 | psu | PASS",
            "garbage",
            "2026-07-14T09:00:02 | BRD-0002 | psu | FAIL | Overheat",
        ]
    )

    result = parse_text(text, source_file="run.log")

    assert len(result.records) == 2
    assert len(result.errors) == 1
    assert result.errors[0].line_number == 2
    assert result.total_lines == 3
