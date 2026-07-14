#!/usr/bin/env bash
# Generate a batch of fake board-test logs for local demo and testing.
#
# Usage: ./scripts/generate_sample_logs.sh [output_dir] [num_boards]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-${REPO_ROOT}/sample_logs}"
NUM_BOARDS="${2:-40}"

TESTS=(power_on_self_test rail_check i2c_bus_scan fw_verify thermal_soak rf_loopback)

REASONS=(
  "3v3 rail voltage out of range (measured 2.81V)"
  "Brownout detected during load step"
  "Overheat at 92C during soak"
  "I2C bus error on addr 0x48"
  "UART framing error on debug port"
  "No response from sensor after 3 retries"
  "Timed out waiting for handshake"
  "Firmware checksum mismatch"
  "Bootloader failed to hand off"
  "Connector J4 not seated"
  "Gain out of tolerance on channel 2"
  "Unexpected state; see station capture"
)

mkdir -p "${OUT_DIR}"
rm -f "${OUT_DIR}"/*.log

# Two stations, so the CLI has more than one file to chew through.
for station in ICT-01 ICT-02; do
  LOG_FILE="${OUT_DIR}/${station}.log"
  {
    echo "# station: ${station}  generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "# format: timestamp | component_id | test_name | PASS/FAIL | reason (fail only)"
  } >"${LOG_FILE}"

  for ((board = 1; board <= NUM_BOARDS; board++)); do
    component_id=$(printf "BRD-%05d" $((RANDOM % 900 + 100)))
    second=0

    for test_name in "${TESTS[@]}"; do
      second=$((second + RANDOM % 30 + 5))
      timestamp=$(printf "2026-07-14T%02d:%02d:%02d" \
        $((8 + (second / 3600) % 8)) $(((second / 60) % 60)) $((second % 60)))

      # ~18% of tests fail, which lands the pass rate in a realistic range.
      if ((RANDOM % 100 < 18)); then
        reason="${REASONS[$((RANDOM % ${#REASONS[@]}))]}"
        echo "${timestamp} | ${component_id} | ${test_name} | FAIL | ${reason}" >>"${LOG_FILE}"
      else
        echo "${timestamp} | ${component_id} | ${test_name} | PASS" >>"${LOG_FILE}"
      fi
    done
  done

  # Every real log has a few corrupt lines. Keep them so the demo shows the
  # tool reporting bad input instead of falling over on it.
  {
    echo "2026-07-14T11:59:00 | BRD-00999 | rail_check"
    echo "<<< station reset -- partial record >>>"
    echo "2026-07-14T11:59:30 | BRD-00999 | fw_verify | MAYBE | inconclusive"
  } >>"${LOG_FILE}"

  echo "==> Wrote $(grep -c . "${LOG_FILE}") lines to ${LOG_FILE}"
done

echo
echo "Sample logs are in ${OUT_DIR}"
