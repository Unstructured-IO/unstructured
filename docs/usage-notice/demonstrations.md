# Observed public-entrypoint demonstrations

Captured on 2026-10-08. The demo invokes automatic text dispatch, then direct text partitioning. Each command is a fresh process. Commands used the existing root-project environment (`UV_PROJECT_ENVIRONMENT=/r/unstructured/.venv`, `VIRTUAL_ENV` unset), with `PYTHONPATH=.` to load this checkout. In a newly synchronized environment, use `uv run --project .` instead. Stdout and stderr were captured separately.

### Server / redirected stdout; notice enabled

```bash
PYTHONPATH=. DO_NOT_TRACK=1 env -u UNSTRUCTURED_DISABLE_NOTICE uv run --no-sync --project . python docs/usage-notice/demo.py
```

Observed stdout:
```text
[{"type": "NarrativeText", "text": "This is a local usage notice demonstration sentence."}]
```

Observed stderr:
```text
Thank you for using Unstructured Open Source! Try Unstructured's commercial offering for improved output quality. 10,000 free pages to start. Learn more: https://example.invalid/unstructured-offer Illustration only - placeholder URL; offer pending publication review. Hide this notice: UNSTRUCTURED_DISABLE_NOTICE=1
```

### Server / redirected stdout; notice disabled

```bash
PYTHONPATH=. DO_NOT_TRACK=1 UNSTRUCTURED_DISABLE_NOTICE=1 uv run --no-sync --project . python docs/usage-notice/demo.py
```

Observed stdout:
```text
[{"type": "NarrativeText", "text": "This is a local usage notice demonstration sentence."}]
```

Observed stderr:
```text
(empty)
```

### Import silence

```bash
PYTHONPATH=. DO_NOT_TRACK=1 uv run --no-sync --project . python -c 'import unstructured; import unstructured.partition.text; print("imports-ok")'
```

Observed stdout:
```text
imports-ok
```

Observed stderr:
```text
(empty)
```

### Repeated-use evidence

The enabled process calls automatic partitioning (which dispatches to text partitioning), then calls text partitioning directly. The observed stderr contains the offer once. Both calls returned the same projected elements. Enabled and disabled stdout were byte-identical and parsed as JSON.

### Real terminal capture

Captured in the originating Codex chat on 2026-10-08 with an actual pseudo-terminal (`tty=true`). The worker's PTY restriction was resolved by running the same public-entrypoint demo from the parent chat. Both commands exited 0. Environment: `VIRTUAL_ENV` unset, `UV_PROJECT_ENVIRONMENT=/r/unstructured/.venv`, `PYTHONPATH=.`, and `DO_NOT_TRACK=1`.

Enabled command:

```bash
env -u VIRTUAL_ENV -u UNSTRUCTURED_DISABLE_NOTICE UV_PROJECT_ENVIRONMENT=/r/unstructured/.venv PYTHONPATH=. DO_NOT_TRACK=1 uv run --no-sync --project . python docs/usage-notice/demo.py
```

Observed terminal output:

```text
----------------------------------------------------------------------
Thank you for using Unstructured Open Source!

Try Unstructured's commercial offering for improved output quality.

                     10,000 free pages to start.

Learn more: https://example.invalid/unstructured-offer
Illustration only - placeholder URL; offer pending publication review.
Hide this notice: UNSTRUCTURED_DISABLE_NOTICE=1
----------------------------------------------------------------------
[{"type": "NarrativeText", "text": "This is a local usage notice demonstration sentence."}]
```

The environment manager emitted an interpreter-cache warning before this enabled run; it was separate from the package output above. Automatic dispatch and a subsequent direct text call produced one banner.

Disabled command:

```bash
env -u VIRTUAL_ENV UV_PROJECT_ENVIRONMENT=/r/unstructured/.venv PYTHONPATH=. DO_NOT_TRACK=1 UNSTRUCTURED_DISABLE_NOTICE=1 uv run --no-sync --project . python docs/usage-notice/demo.py
```

Observed terminal output:

```text
[{"type": "NarrativeText", "text": "This is a local usage notice demonstration sentence."}]
```
