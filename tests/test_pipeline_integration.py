"""End-to-end: run the CLI over the sample log and check the exported report.

The sample log in tests/data/sample_run.log holds 12 well-formed records
(6 pass, 6 fail) plus 4 deliberately broken lines, so the expected numbers
below are hand-checked rather than derived from the code under test.
"""

import json
from pathlib import Path

import pytest

from test_harness.cli import main

SAMPLE_LOG = Path(__file__).parent / "data" / "sample_run.log"


@pytest.fixture
def report(tmp_path):
    """Run the full pipeline once and hand the parsed JSON export to each test."""
    output = tmp_path / "report.json"
    exit_code = main(
        ["--input", str(SAMPLE_LOG), "--format", "json", "--output", str(output), "--quiet"]
    )

    assert exit_code == 0
    return json.loads(output.read_text(encoding="utf-8"))


def test_totals_and_pass_rate(report):
    assert report["total_tests"] == 12
    assert report["passed"] == 6
    assert report["failed"] == 6
    assert report["pass_rate"] == 0.5


def test_broken_lines_are_counted_but_do_not_break_the_run(report):
    assert report["malformed_lines"] == 4


def test_failure_categories(report):
    assert report["failures_by_category"] == {
        "communication": 1,
        "firmware": 1,
        "power": 1,
        "thermal": 1,
        "timeout": 1,
        "uncategorized": 1,
    }


def test_worst_offending_component_is_listed_first(report):
    worst = report["worst_components"][0]

    assert worst["component_id"] == "BRD-0003"
    assert worst["failures"] == 3
    assert worst["total"] == 4
    assert worst["fail_rate"] == 0.75


def test_clean_boards_are_not_listed_as_offenders(report):
    listed = {entry["component_id"] for entry in report["worst_components"]}

    assert "BRD-0004" not in listed


def test_console_output_names_the_worst_offender(capsys):
    exit_code = main(["--input", str(SAMPLE_LOG)])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert "Pass rate       : 50.0%" in stdout
    assert "BRD-0003" in stdout
    assert "MALFORMED LINES" in stdout


def test_csv_export(tmp_path):
    output = tmp_path / "report.csv"

    exit_code = main(
        ["--input", str(SAMPLE_LOG), "--format", "csv", "--output", str(output), "--quiet"]
    )
    rows = output.read_text(encoding="utf-8").splitlines()

    assert exit_code == 0
    assert rows[0] == "section,key,value"
    assert "summary,total_tests,12" in rows
    assert "summary,pass_rate,0.5" in rows


def test_fail_under_threshold_sets_a_nonzero_exit_code():
    # 50% pass rate is well under 95%, so this is the CI gate tripping.
    assert main(["--input", str(SAMPLE_LOG), "--fail-under", "95", "--quiet"]) == 1
    assert main(["--input", str(SAMPLE_LOG), "--fail-under", "10", "--quiet"]) == 0


def test_missing_input_path_exits_with_code_2(tmp_path):
    assert main(["--input", str(tmp_path / "nope.log"), "--quiet"]) == 2


def test_directory_input_reads_every_log_file(tmp_path):
    (tmp_path / "a.log").write_text(
        "2026-07-14T09:00:01 | BRD-0001 | psu | PASS\n", encoding="utf-8"
    )
    (tmp_path / "b.log").write_text(
        "2026-07-14T09:00:02 | BRD-0002 | psu | FAIL | Overheat\n", encoding="utf-8"
    )
    (tmp_path / "ignore.txt").write_text("garbage that must not be read\n", encoding="utf-8")
    output = tmp_path / "report.json"

    main(["--input", str(tmp_path), "--format", "json", "--output", str(output), "--quiet"])
    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["total_tests"] == 2
    assert report["malformed_lines"] == 0
