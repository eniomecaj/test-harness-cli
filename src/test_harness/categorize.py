"""Bucket free-text failure reasons into a small set of engineering categories.

Real test-floor logs have free-text failure reasons written by whoever wrote
the test script, so the same physical fault shows up a dozen different ways.
Matching on keywords collapses them into categories an engineer can act on.
Order matters: the first category with a keyword hit wins, so the more specific
categories are listed before the more general ones.
"""

from __future__ import annotations

from .parser import TestRecord

UNCATEGORIZED = "uncategorized"

# category -> keywords that imply it (matched case-insensitively as substrings)
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "power": ("voltage", "vcc", "rail", "brownout", "undervolt", "overcurrent", "power"),
    "thermal": ("thermal", "overheat", "temperature", "temp exceeded", "throttl"),
    "communication": ("i2c", "spi", "uart", "can bus", "nack", "bus error"),
    "timeout": ("timeout", "timed out", "no response", "deadline"),
    "firmware": ("firmware", "checksum", "crc", "flash", "bootloader"),
    "mechanical": ("connector", "solder", "short circuit", "open circuit", "not seated"),
    "calibration": ("calibration", "out of tolerance", "drift", "offset", "out of spec"),
}


def categorize_reason(reason: str) -> str:
    """Return the failure category for a free-text reason string."""
    text = reason.lower()
    if not text.strip():
        return UNCATEGORIZED

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category

    return UNCATEGORIZED


def categorize_failures(records: list[TestRecord]) -> dict[str, int]:
    """Count failures by category. Passing records are ignored."""
    counts: dict[str, int] = {}
    for record in records:
        if record.passed:
            continue
        category = categorize_reason(record.reason)
        counts[category] = counts.get(category, 0) + 1

    # Highest count first, then alphabetically so output is stable.
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
