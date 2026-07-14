# test-harness-cli

[![CI](https://github.com/eniomecaj/test-harness-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/eniomecaj/test-harness-cli/actions/workflows/ci.yml)

A CLI tool that chews through board-level test logs and tells you what's actually
going wrong. It reads pass/fail records, works out the pass rate, buckets the
failures by type, and calls out which components are causing the most trouble.

This is basically how a real test floor works. A station runs a fixed battery of
tests on each board and logs a pass or fail with a reason. By the end of a shift
you've got a pile of lines and someone has to turn that into an actual answer to
"what is going wrong on the line." Test floor logs are never clean either, a station
resets mid write, a field goes missing, some operator script spits out a weird
result string. So instead of dying on the first bad line, the tool just flags it and
keeps going.

## Log format

Pipe-delimited, one test result per line. The reason field is only expected on `FAIL`
lines. Blank lines and `#` comments are ignored.

```
timestamp | component_id | test_name | PASS/FAIL | reason (fail only)

2026-07-14T09:00:01 | BRD-0001 | power_on_self_test | PASS
2026-07-14T09:00:05 | BRD-0001 | i2c_bus_scan       | FAIL | I2C bus error on addr 0x48
```

Failure reasons get bucketed by keyword into `power`, `thermal`, `communication`,
`timeout`, `firmware`, `mechanical`, `calibration`, or `uncategorized`
(see [`categorize.py`](src/test_harness/categorize.py)).

## Run it locally

```bash
./scripts/setup.sh          # create .venv, install the package + dev deps
./scripts/run_pipeline.sh   # generate sample logs -> run the CLI -> write a report
```

`run_pipeline.sh` is the one-command version. Run it and it generates sample logs,
runs the CLI, and prints the summary to the console while also writing
`reports/summary.json`.

Or drive the CLI yourself:

```bash
source .venv/bin/activate                       # .venv/Scripts/activate on Windows

test-harness --input sample_logs/                                  # console report
test-harness --input sample_logs/ --format json --output out.json  # JSON export
test-harness --input sample_logs/ --format csv  --output out.csv   # CSV export
test-harness --input sample_logs/ --fail-under 95                  # exit 1 if pass rate < 95%
test-harness --help
```

`--fail-under` is the bit that actually makes this useful as a gate. It exits
non-zero if the pass rate drops below whatever threshold you set, so a CI job or a
shift script can fail loudly on it.

Exit codes: `0` OK, `1` pass rate below `--fail-under`, `2` no usable input.

## Run it in Docker

There's a small sample log baked into the image, so it does something useful even
with no arguments:

```bash
docker build -t test-harness .
docker run --rm test-harness --input sample_logs/
```

Got your own logs? Mount them in:

```bash
docker run --rm -v "$(pwd)/sample_logs:/data" test-harness --input /data
```

## Run the tests

```bash
source .venv/bin/activate
pytest -v          # unit tests + one end-to-end pipeline test
ruff check .       # lint
```

Unit tests cover parsing and failure categorization. The integration test
(`tests/test_pipeline_integration.py`) runs the whole CLI over
`tests/data/sample_run.log` and checks the exported report is correct. That sample
log has four broken lines on purpose: a truncated record, a line that isn't a log
line at all, a bogus result value, and a timestamp that won't parse. So the tests
actually prove the tool survives bad input and still gets the good lines right.

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) fires on every push and pull
request to `main`. Checks out the repo, sets up Python, installs everything, lints
with ruff, runs pytest, smoke-tests the pipeline script, then builds the Docker
image and actually runs the CLI inside it, because a build that just compiles isn't
proof of much.

## Layout

```
src/test_harness/    parser.py, categorize.py, report.py, cli.py
tests/               unit tests, integration test, sample log fixture
scripts/             setup.sh, generate_sample_logs.sh, run_pipeline.sh
Dockerfile           installs the package, CLI as the entrypoint
.github/workflows/   ci.yml
```
