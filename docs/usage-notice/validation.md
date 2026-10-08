# Focused validation

### Usage notice and existing telemetry tests

The root project owns the test dependencies. This run reused its prepared environment;
`PYTHONPATH=.` selected this checkout. No broad test suite was run.

```bash
DO_NOT_TRACK=1 PYTHONPATH=. uv run --no-sync --project . pytest -q \
  test_unstructured/test_usage_notice.py \
  test_unstructured/test_runtime_telemetry.py \
  test_unstructured/test_telemetry.py
........................................................................ [ 79%]
...................                                                      [100%]
91 passed in 4.71s
```

Coverage includes terminal rendering, nonterminal warning, absent/uninspectable streams,
stream and logger failures, at-most-one attempt, use-time disablement, independent
telemetry settings, argument/result/error preservation, concurrent and reentrant calls,
application-owned logging, filtered records, fork with an inherited locked claim,
spawn, import silence, empty first call, and real automatic/direct text entrypoints.
Fork and spawn tests ran; no platform lifecycle test was skipped.

### Focused lint and formatting

```bash
ruff check unstructured/_usage_notice.py unstructured/telemetry.py \
  test_unstructured/test_usage_notice.py docs/usage-notice/demo.py
All checks passed!
ruff format --check unstructured/_usage_notice.py unstructured/telemetry.py \
  test_unstructured/test_usage_notice.py docs/usage-notice/demo.py
4 files already formatted
```

### Diff whitespace check

```bash
git diff d621285e1b45b6ddbf2e16b62777231cdb268427 --check
```

Observed output: empty; exit status 0.

### Real output and remaining capture

[Demonstrations](demonstrations.md) preserve separate stdout/stderr from the real public
entrypoints. Redirected JSON parsed directly; enabled/disabled results matched byte for
byte. Only one notice appeared across nested automatic dispatch and direct use.
A real terminal capture remains outstanding because this worker denies PTY allocation.
The terminal route was verified with fake streams in tests. This limitation is a deviation
from the requested demonstration, not a claim of completed terminal evidence.
