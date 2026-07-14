#!/usr/bin/env bash
# Create a virtualenv and install the package plus dev tooling into it.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN=python
fi

echo "==> Creating virtualenv at ${VENV_DIR}"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"

# Windows git-bash puts the interpreter in Scripts/ instead of bin/.
if [[ -x "${VENV_DIR}/bin/python" ]]; then
  VENV_PYTHON="${VENV_DIR}/bin/python"
else
  VENV_PYTHON="${VENV_DIR}/Scripts/python.exe"
fi

echo "==> Installing test-harness-cli (editable) and dev dependencies"
"${VENV_PYTHON}" -m pip install --upgrade pip
"${VENV_PYTHON}" -m pip install -e "${REPO_ROOT}[dev]"

echo
echo "Done. Activate the venv with:"
echo "  source ${VENV_DIR}/bin/activate      # macOS / Linux"
echo "  source ${VENV_DIR}/Scripts/activate  # Windows (git-bash)"
echo
echo "Then try:  ./scripts/run_pipeline.sh"
