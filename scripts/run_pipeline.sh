#!/usr/bin/env bash
# One command to see the whole thing work:
#   generate sample logs -> run the CLI -> write a report -> say where it landed.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${REPO_ROOT}/sample_logs"
REPORT="${REPO_ROOT}/reports/summary.json"

# Prefer the venv interpreter if setup.sh has been run; fall back to whatever
# python is on PATH (which is what happens inside the Docker image).
if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PYTHON="${REPO_ROOT}/.venv/bin/python"
elif [[ -x "${REPO_ROOT}/.venv/Scripts/python.exe" ]]; then
  PYTHON="${REPO_ROOT}/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi

# Lets the script work even if the package was never pip-installed.
export PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH:-}"

echo "==> Step 1/3: generating sample logs"
"${REPO_ROOT}/scripts/generate_sample_logs.sh" "${LOG_DIR}" >/dev/null
echo "    logs in ${LOG_DIR}"

echo
echo "==> Step 2/3: running the CLI"
echo
"${PYTHON}" -m test_harness --input "${LOG_DIR}" --format json --output "${REPORT}"

echo
echo "==> Step 3/3: done"
echo "    Report written to: ${REPORT}"
