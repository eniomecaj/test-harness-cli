# test-harness-cli

[![CI](https://github.com/eniomecaj/test-harness-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/eniomecaj/test-harness-cli/actions/workflows/ci.yml)

A small command-line tool that reads board-level test logs, works out the pass rate,
buckets the failures by type, and names the components that fail most often. It is
modeled on production test/QA workflows: a station runs a fixed battery of tests
against each board, appends a pass/fail record with a free-text failure reason, and
somebody has to turn a shift's worth of those lines into an answer to "what is
actually going wrong on the line?" Logs from a real test floor are messy — a station
resets mid-write, a field is missing, an operator's script emits an unexpected
result string — so the tool reports bad lines and keeps going rather than dying on
the first one.

## Log format

Pipe-delimited, one test result per line. The reason field is only expected on `FAIL`
lines. Blank lines and `#` comments are ignored.

```
timestamp | component_id | test_name | PASS/FAIL | reason (fail only)

2026-07-14T09:00:01 | BRD-0001 | power_on_self_test | PASS
2026-07-14T09:00:05 | BRD-0001 | i2c_bus_scan       | FAIL | I2C bus error on addr 0x48
```

Failure reasons are bucketed by keyword into `power`, `thermal`, `communication`,
`timeout`, `firmware`, `mechanical`, `calibration`, or `uncategorized`
(see [`categorize.py`](src/test_harness/categorize.py)).

## Run it locally

```bash
./scripts/setup.sh          # create .venv, install the package + dev deps
./scripts/run_pipeline.sh   # generate sample logs -> run the CLI -> write a report
```

`run_pipeline.sh` is the "one command to see it work" script. It prints the summary to
the console and writes `reports/summary.json`.

To drive the CLI directly:

```bash
source .venv/bin/activate                       # .venv/Scripts/activate on Windows

test-harness --input sample_logs/                                  # console report
test-harness --input sample_logs/ --format json --output out.json  # JSON export
test-harness --input sample_logs/ --format csv  --output out.csv   # CSV export
test-harness --input sample_logs/ --fail-under 95                  # exit 1 if pass rate < 95%
test-harness --help
```

`--fail-under` is the piece that makes this usable as a gate: it exits non-zero when
the pass rate drops below a threshold, so a CI job or a shift script can fail on it.

Exit codes: `0` OK, `1` pass rate below `--fail-under`, `2` no usable input.

## Run it in Docker

The image bakes in a small sample log, so it does something useful with no arguments:

```bash
docker build -t test-harness .
docker run --rm test-harness --input sample_logs/
```

To report on logs from your own machine, mount them in:

```bash
docker run --rm -v "$(pwd)/sample_logs:/data" test-harness --input /data
```

## Run the tests

```bash
source .venv/bin/activate
pytest -v          # unit tests + one end-to-end pipeline test
ruff check .       # lint
```

The unit tests cover parsing and failure categorization. The integration test
(`tests/test_pipeline_integration.py`) runs the CLI end to end over
`tests/data/sample_run.log` and asserts the exported report is correct. That sample
log deliberately contains four broken lines — a truncated record, a line that is not a
log line at all, an invalid result value, and an unparseable timestamp — so the tests
prove the tool reports bad input and still produces a correct report from the good
lines.

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push and pull
request to `main`: check out, set up Python, install, lint with ruff, run pytest,
smoke-test the pipeline script, then build the Docker image and run the CLI inside it
to confirm the image is actually usable and not just buildable.

## Layout

```
src/test_harness/    parser.py, categorize.py, report.py, cli.py
tests/               unit tests, integration test, sample log fixture
scripts/             setup.sh, generate_sample_logs.sh, run_pipeline.sh
Dockerfile           installs the package, CLI as the entrypoint
.github/workflows/   ci.yml
```
