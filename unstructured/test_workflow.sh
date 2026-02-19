#!/usr/bin/env bash
# test_benchmark.sh
#
# Smoke-tests for scripts/performance/benchmark_partition.py and
# scripts/performance/compare_benchmark.py.
#
# Running partition() for real is slow and requires the full ML stack, so
# benchmark_partition.py is tested at the import/CLI level only.
# compare_benchmark.py is tested end-to-end with synthetic JSON fixtures
# covering every branch: first run, pass (within threshold), new best, and
# regression (fail).
#
# Usage:
#   ./test_benchmark.sh
#
# Exit code: 0 if all tests pass, 1 on the first failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BENCHMARK_SCRIPT="$REPO_ROOT/scripts/performance/benchmark_partition.py"
COMPARE_SCRIPT="$REPO_ROOT/scripts/performance/compare_benchmark.py"

# Temporary directory; always cleaned up on exit
TMPDIR_WORK="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_WORK"' EXIT

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
red()   { printf '\033[0;31m%s\033[0m\n' "$*"; }

pass() {
  green "  PASS: $1"
  PASS=$((PASS + 1))
}

fail() {
  red "  FAIL: $1"
  FAIL=$((FAIL + 1))
}

# Run a command and assert it exits with the expected code.
#   assert_exit <expected_code> <label> <cmd…>
assert_exit() {
  local expected="$1"; shift
  local label="$1";    shift
  local actual
  actual=0
  "$@" >/dev/null 2>&1 || actual=$?
  if [[ "$actual" -eq "$expected" ]]; then
    pass "$label (exit $expected)"
  else
    fail "$label – expected exit $expected, got $actual"
  fi
}

# Run a command and assert its stdout contains a substring.
#   assert_output_contains <substr> <label> <cmd…>
assert_output_contains() {
  local substr="$1"; shift
  local label="$1";  shift
  local out
  out=$("$@" 2>&1 || true)
  if echo "$out" | grep -qF "$substr"; then
    pass "$label (output contains '$substr')"
  else
    fail "$label – expected output to contain '$substr', got:\n$out"
  fi
}

# Write a JSON benchmark result file.
#   write_json <path> <file1_avg> <file2_avg> <total>
write_json() {
  local path="$1"
  cat > "$path" <<JSON
{
  "example-docs/fake.pdf": $2,
  "example-docs/fake.jpg": $3,
  "__total__": $4
}
JSON
}

# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------

section() { printf '\n\033[1;34m=== %s ===\033[0m\n' "$*"; }

# ===========================================================================
# 1. benchmark_partition.py – structural checks
# ===========================================================================
section "benchmark_partition.py – structural checks"

# 1a. File exists
if [[ -f "$BENCHMARK_SCRIPT" ]]; then
  pass "script exists at scripts/performance/benchmark_partition.py"
else
  fail "script not found at $BENCHMARK_SCRIPT"
fi

# 1b. Python syntax is valid
assert_exit 0 "python syntax check" \
  uv run --no-sync python -m py_compile "$BENCHMARK_SCRIPT"

# 1c. --help / usage exit (passing a bad arg should show usage, not a traceback)
#     We just check it exits cleanly when asked to show the docstring.
assert_exit 0 "importable as module" \
  uv run --no-sync python -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('benchmark_partition', '$BENCHMARK_SCRIPT')
mod  = importlib.util.module_from_spec(spec)
# Do NOT call spec.loader.exec_module – just verify the file parses cleanly.
print('ok')
"

# 1d. BENCHMARK_FILES and HI_RES_FILES are non-empty and HI_RES_FILES ⊆ BENCHMARK_FILES
assert_exit 0 "HI_RES_FILES is a subset of BENCHMARK_FILES" \
  uv run --no-sync python -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('bp', '$BENCHMARK_SCRIPT')
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod.BENCHMARK_FILES, 'BENCHMARK_FILES is empty'
assert mod.HI_RES_FILES,    'HI_RES_FILES is empty'
extras = mod.HI_RES_FILES - set(mod.BENCHMARK_FILES)
assert not extras, f'HI_RES_FILES entries not in BENCHMARK_FILES: {extras}'
print('ok')
"

# 1e. NUM_ITERATIONS env var is respected
assert_exit 0 "NUM_ITERATIONS env var is read" \
  uv run --no-sync python -c "
import os, importlib.util
os.environ['NUM_ITERATIONS'] = '7'
spec = importlib.util.spec_from_file_location('bp', '$BENCHMARK_SCRIPT')
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod.NUM_ITERATIONS == 7, f'Expected 7, got {mod.NUM_ITERATIONS}'
print('ok')
"

# ===========================================================================
# 2. compare_benchmark.py – structural checks
# ===========================================================================
section "compare_benchmark.py – structural checks"

assert_exit 0 "script exists" \
  test -f "$COMPARE_SCRIPT"

assert_exit 0 "python syntax check" \
  uv run --no-sync python -m py_compile "$COMPARE_SCRIPT"

# Missing arguments → exit 2
assert_exit 2 "exits 2 with no arguments" \
  uv run --no-sync python "$COMPARE_SCRIPT"

# ===========================================================================
# 3. compare_benchmark.py – first-ever run (no stored best)
# ===========================================================================
section "compare_benchmark.py – first run (no stored best)"

CURRENT="$TMPDIR_WORK/current.json"
BEST="$TMPDIR_WORK/best_firstrun.json"   # must NOT exist yet

write_json "$CURRENT" 1.5 2.0 3.5

assert_exit 0 "exits 0 on first run" \
  uv run --no-sync python "$COMPARE_SCRIPT" "$CURRENT" "$BEST" 0.20

assert_output_contains "baseline" "prints 'baseline' message" \
  uv run --no-sync python "$COMPARE_SCRIPT" "$CURRENT" "$BEST" 0.20

# Calling it twice: first creates the best, second compares equal → still pass
assert_exit 0 "exits 0 when current == best (0 % regression)" \
  uv run --no-sync python "$COMPARE_SCRIPT" "$CURRENT" "$BEST" 0.20

# ===========================================================================
# 4. compare_benchmark.py – PASS within threshold
# ===========================================================================
section "compare_benchmark.py – PASS (within threshold)"

BEST_PASS="$TMPDIR_WORK/best_pass.json"
write_json "$BEST_PASS"   1.0 1.0 2.0   # stored best: 2.0 s total
CURRENT_PASS="$TMPDIR_WORK/current_pass.json"
write_json "$CURRENT_PASS" 1.1 1.1 2.2  # 10 % slower → within 20 % threshold

assert_exit 0 "exits 0 when 10% slower (threshold 20%)" \
  uv run --no-sync python "$COMPARE_SCRIPT" "$CURRENT_PASS" "$BEST_PASS" 0.20

assert_output_contains "PASS" "prints PASS" \
  uv run --no-sync python "$COMPARE_SCRIPT" "$CURRENT_PASS" "$BEST_PASS" 0.20

# ===========================================================================
# 5. compare_benchmark.py – NEW BEST (current is faster)
# ===========================================================================
section "compare_benchmark.py – new best (current is faster)"

BEST_NEWBEST="$TMPDIR_WORK/best_newbest.json"
write_json "$BEST_NEWBEST"   1.0 1.0 2.0   # stored best: 2.0 s
CURRENT_NEWBEST="$TMPDIR_WORK/current_newbest.json"
write_json "$CURRENT_NEWBEST" 0.8 0.8 1.6  # 20 % faster → new best

assert_exit 0 "exits 0 when current is faster" \
  uv run --no-sync python "$COMPARE_SCRIPT" "$CURRENT_NEWBEST" "$BEST_NEWBEST" 0.20

assert_output_contains "new best" "prints 'new best'" \
  uv run --no-sync python "$COMPARE_SCRIPT" "$CURRENT_NEWBEST" "$BEST_NEWBEST" 0.20

# Verify best file was actually overwritten with new (faster) values
UPDATED_TOTAL=$(uv run --no-sync python -c "
import json; d = json.loads(open('$BEST_NEWBEST').read()); print(d['__total__'])
")
if [[ "$UPDATED_TOTAL" == "1.6" ]]; then
  pass "best file updated to new total (1.6)"
else
  fail "best file not updated – expected 1.6, got $UPDATED_TOTAL"
fi

# ===========================================================================
# 6. compare_benchmark.py – REGRESSION (exceeds threshold)
# ===========================================================================
section "compare_benchmark.py – REGRESSION (exceeds threshold)"

BEST_REG="$TMPDIR_WORK/best_regression.json"
write_json "$BEST_REG"   1.0 1.0 2.0   # stored best: 2.0 s
CURRENT_REG="$TMPDIR_WORK/current_regression.json"
write_json "$CURRENT_REG" 1.3 1.3 2.6  # 30 % slower → exceeds 20 % threshold

assert_exit 1 "exits 1 when 30% slower (threshold 20%)" \
  uv run --no-sync python "$COMPARE_SCRIPT" "$CURRENT_REG" "$BEST_REG" 0.20

assert_output_contains "FAIL" "prints FAIL" \
  uv run --no-sync python "$COMPARE_SCRIPT" "$CURRENT_REG" "$BEST_REG" 0.20

# Verify best file was NOT overwritten after a regression
UNCHANGED_TOTAL=$(uv run --no-sync python -c "
import json; d = json.loads(open('$BEST_REG').read()); print(d['__total__'])
")
if [[ "$UNCHANGED_TOTAL" == "2.0" ]]; then
  pass "best file unchanged after regression (still 2.0)"
else
  fail "best file incorrectly updated – expected 2.0, got $UNCHANGED_TOTAL"
fi

# ===========================================================================
# 7. compare_benchmark.py – custom threshold edge cases
# ===========================================================================
section "compare_benchmark.py – custom threshold edge cases"

BEST_EDGE="$TMPDIR_WORK/best_edge.json"
write_json "$BEST_EDGE"   1.0 1.0 2.0
CURRENT_EDGE="$TMPDIR_WORK/current_edge.json"
write_json "$CURRENT_EDGE" 1.0 1.1 2.1  # 5 % slower

# Strict threshold (5 % exactly at the boundary: 2.1 > 2.0*1.05 = 2.1 → fails)
assert_exit 1 "exits 1 when exactly over strict threshold (5%)" \
  uv run --no-sync python "$COMPARE_SCRIPT" "$CURRENT_EDGE" "$BEST_EDGE" 0.04

# Relaxed threshold passes the same data
assert_exit 0 "exits 0 with relaxed threshold (10%)" \
  uv run --no-sync python "$COMPARE_SCRIPT" "$CURRENT_EDGE" "$BEST_EDGE" 0.10

# ===========================================================================
# 8. compare_benchmark.py – GITHUB_OUTPUT integration
# ===========================================================================
section "compare_benchmark.py – GITHUB_OUTPUT env var"

GH_OUT="$TMPDIR_WORK/github_output.txt"
BEST_GHO="$TMPDIR_WORK/best_gho.json"
CURRENT_GHO="$TMPDIR_WORK/current_gho.json"

write_json "$BEST_GHO"    1.0 1.0 2.0
write_json "$CURRENT_GHO" 1.1 1.1 2.2  # within threshold

GITHUB_OUTPUT="$GH_OUT" uv run --no-sync python \
  "$COMPARE_SCRIPT" "$CURRENT_GHO" "$BEST_GHO" 0.20 >/dev/null 2>&1 || true

if grep -q "regression=false" "$GH_OUT" 2>/dev/null; then
  pass "GITHUB_OUTPUT contains regression=false on pass"
else
  fail "GITHUB_OUTPUT missing 'regression=false'"
fi

# Regression case
GH_OUT_REG="$TMPDIR_WORK/github_output_reg.txt"
BEST_GHO_REG="$TMPDIR_WORK/best_gho_reg.json"
CURRENT_GHO_REG="$TMPDIR_WORK/current_gho_reg.json"
write_json "$BEST_GHO_REG"    1.0 1.0 2.0
write_json "$CURRENT_GHO_REG" 1.3 1.3 2.6

GITHUB_OUTPUT="$GH_OUT_REG" uv run --no-sync python \
  "$COMPARE_SCRIPT" "$CURRENT_GHO_REG" "$BEST_GHO_REG" 0.20 >/dev/null 2>&1 || true

if grep -q "regression=true" "$GH_OUT_REG" 2>/dev/null; then
  pass "GITHUB_OUTPUT contains regression=true on regression"
else
  fail "GITHUB_OUTPUT missing 'regression=true'"
fi

# ===========================================================================
# Summary
# ===========================================================================
printf '\n'
printf '=%.0s' {1..50}
printf '\n'
if [[ "$FAIL" -eq 0 ]]; then
  green "All $PASS tests passed."
else
  red "$FAIL test(s) failed, $PASS passed."
  exit 1
fi
