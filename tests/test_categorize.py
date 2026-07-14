from datetime import datetime

import pytest

from test_harness.categorize import categorize_failures, categorize_reason
from test_harness.parser import TestRecord


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("3v3 rail voltage out of range", "power"),
        ("Brownout detected during load step", "power"),
        ("Overheat at 92C", "thermal"),
        ("I2C bus error on addr 0x48", "communication"),
        ("UART framing error", "communication"),
        ("No response from sensor", "timeout"),
        ("Timed out waiting for handshake", "timeout"),
        ("Firmware checksum mismatch", "firmware"),
        ("Connector not seated", "mechanical"),
        ("Gain out of tolerance", "calibration"),
        ("", "uncategorized"),
        ("   ", "uncategorized"),
        ("Something nobody wrote a keyword for", "uncategorized"),
    ],
)
def test_categorize_reason(reason, expected):
    assert categorize_reason(reason) == expected


def test_categorize_reason_is_case_insensitive():
    assert categorize_reason("FIRMWARE CHECKSUM MISMATCH") == "firmware"


def _record(result: str, reason: str = "") -> TestRecord:
    return TestRecord(
        timestamp=datetime(2026, 7, 14, 9, 0, 0),
        component_id="BRD-0001",
        test_name="rail_check",
        result=result,
        reason=reason,
    )


def test_categorize_failures_ignores_passing_records():
    records = [
        _record("PASS"),
        _record("FAIL", "3v3 rail voltage low"),
        _record("FAIL", "Vcc rail collapsed"),
        _record("FAIL", "Overheat at 92C"),
    ]

    assert categorize_failures(records) == {"power": 2, "thermal": 1}


def test_categorize_failures_sorts_by_count_then_name():
    records = [
        _record("FAIL", "Overheat"),
        _record("FAIL", "I2C bus error"),
        _record("FAIL", "SPI bus error"),
    ]

    assert list(categorize_failures(records)) == ["communication", "thermal"]


def test_no_failures_gives_an_empty_breakdown():
    assert categorize_failures([_record("PASS"), _record("PASS")]) == {}
