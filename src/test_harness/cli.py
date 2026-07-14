"""Command-line entry point for test-harness-cli."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .parser import parse_path
from .report import build_report, render_console, to_csv, to_json

EXIT_OK = 0
EXIT_BELOW_THRESHOLD = 1
EXIT_NO_INPUT = 2


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="test-harness",
        description="Parse board-level test logs and summarize pass rate and failures.",
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        type=Path,
        help="Log file, or a directory of log files.",
    )
    parser.add_argument(
        "--pattern",
        default="*.log",
        help="Glob used when --input is a directory (default: %(default)s).",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=("json", "csv"),
        help="Export format. Requires --output.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write the export to this file. Requires --format.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="How many worst-offending components to list (default: %(default)s).",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        metavar="PCT",
        help="Exit non-zero if the pass rate falls below this percentage, e.g. 95.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress the console report (useful when only exporting).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if bool(args.format) != bool(args.output):
        parser.error("--format and --output must be used together")

    if not args.input.exists():
        print(f"error: input path does not exist: {args.input}", file=sys.stderr)
        return EXIT_NO_INPUT

    parse_result = parse_path(args.input, pattern=args.pattern)
    if not parse_result.records and not parse_result.errors:
        print(f"error: no log lines found in {args.input}", file=sys.stderr)
        return EXIT_NO_INPUT

    report = build_report(parse_result, top_n=args.top)

    if not args.quiet:
        print(render_console(report, parse_result))

    if args.output:
        rendered = to_json(report) if args.format == "json" else to_csv(report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"\nReport written to {args.output}")

    if args.fail_under is not None and report.pass_rate * 100 < args.fail_under:
        print(
            f"\nFAIL: pass rate {report.pass_rate:.1%} is below the "
            f"{args.fail_under:.1f}% threshold",
            file=sys.stderr,
        )
        return EXIT_BELOW_THRESHOLD

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
