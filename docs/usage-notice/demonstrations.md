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

### Terminal capture limitation

Actual PTY allocation is denied in this worker: `openpty: Operation not permitted`. The fake-terminal tests verify one complete banner and one flush, but are not a real terminal transcript. A live PTY capture remains outstanding.
