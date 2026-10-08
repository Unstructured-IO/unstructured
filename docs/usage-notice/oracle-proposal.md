# Recovered Oracle proposal

Session: usage-notice-proposal
Conversation: https://chatgpt.com/c/6ac80ad7-c208-83e8-8174-357e57b37b92

Recovered from the original completed browser conversation. Oracle CLI capture missed the redesigned message markers. Saved pre-submission and during-run evidence confirms Pro composer selection; generation identity was not independently confirmed.

Recommended approach

Add one small, private usage-notice module and invoke it at the beginning of the existing partition_runtime_telemetry() wrapper, before every telemetry opt-out or early-return path. Keep the notice’s state, opt-out, rendering, and failure handling independent of telemetry.

Use at most one best-effort emission attempt per process, not “retry until successfully displayed.” Write a compact notice to terminal-connected stdout; otherwise, submit one WARNING through the existing unstructured logger. Do not introduce persistence, dependencies, handlers, background workers, notice-specific network activity, or changes to partition results. This implements the mission’s requested behavior with a narrow change.
source

My recommended assumptions are:

“Actual public package use” means invocation of a decorated public partitioning entrypoint. It includes unsuccessful and empty-input calls, but not imports, CLI help, diagnostics, or standalone cleaning/chunking utilities.
“Once” means one library emission attempt during normal module lifetime. A failed write or a warning suppressed by application logging configuration consumes that attempt. Each forked or spawned worker is independently eligible.
Structured stdout protection assumes the application keeps logging separate from its data stream. The notice must never directly write to redirected stdout. It cannot also guarantee clean stdout when the application deliberately sends logger output there or merges stderr into stdout. Honor that configuration rather than overriding it; document the disable flag for those cases.

This is a design for an illustrative branch, not publication approval for the offer or any maintenance-status claim.

1. Proposed wording
Terminal notice

I recommend a plain ASCII treatment: spacing and separators make the offer prominent without colors, terminal-control sequences, Unicode compatibility concerns, or another dependency.

Plain text
----------------------------------------------------------------------
Thank you for using Unstructured Open Source!

Try Unstructured's commercial offering for improved output quality.

                    10,000 free pages to start.

Learn more: https://example.invalid/unstructured-offer
Illustration only - placeholder URL; offer pending publication review.
Hide this notice: UNSTRUCTURED_DISABLE_NOTICE=1
----------------------------------------------------------------------

Keep the illustration label in this branch. Before publication, the owner must approve eligibility, replace the placeholder URL, and approve the final copy.

Do not include “years in maintenance mode,” an end-of-support implication, or a maintenance-duration commitment. The mission explicitly says the evidence does not support that framing and reports recent fixes and an existing README commitment that OSS remains free. The README and commit history themselves are not reproduced in this bundle, so those statements should not be expanded into additional claims.
source

Noninteractive warning

Use the same substantive wording, flattened into one log message and one logger.warning() call. Do not log each banner line separately, include the separator bars, or hard-code a WARNING: prefix; formatting belongs to the application’s logging configuration.

Keep the thank-you, invitation, offer, placeholder URL, illustration qualification, and disable instruction in shared constants so the two paths cannot drift. No document text, filenames, identifiers, credentials, or other invocation data should enter the message.

Proposed README addition

Usage notice

On the first call to a supported public partitioning function, Unstructured attempts to display a brief usage notice. When stdout is connected to a terminal, the notice is written there. Otherwise, it is submitted at WARNING level through the unstructured logger and follows your application’s logging configuration.

Set UNSTRUCTURED_DISABLE_NOTICE=1 before calling a partitioner to disable both forms of the notice. This setting is independent of telemetry settings such as DO_NOT_TRACK and SCARF_NO_ANALYTICS.

The notice makes no network requests of its own and stores no persistent state. It is attempted at most once per process; forked and spawned workers are independently eligible. Failed or filtered attempts are not retried.

When writing JSON, NDJSON, or other machine-readable data to stdout, keep application logging on a separate destination or disable the notice. Merging logging or stderr into stdout can mix messages with your data.

The offer and URL in this branch are illustrative and require review before publication.

Place this alongside the existing usage/configuration documentation after inspecting the actual README; do not replace its existing OSS or commercial-product framing.

2. Architecture and behavioral contract
Process-local ownership

Create unstructured/_usage_notice.py with two pieces of mutable state:

Python
_attempted = False
_claim_lock = threading.Lock()

There is no need for a database, filesystem marker, timestamp, per-partitioner registry, ContextVar, or retry state machine.

The call sequence should be:

Plain text
Read the notice-specific disable setting.
    Disabled -> return without consuming eligibility.

Try to acquire the claim lock without waiting.
    Busy -> return; this caller continues normal partitioning.

Under the lock:
    Already attempted -> return.
    Otherwise mark attempted.

Release the lock.

Inspect the current stdout.
    Terminal -> one write, followed by one flush.
    Otherwise -> one package-logger warning.

Ordinary notice failure -> continue the existing partitioning path.

Set _attempted before stream inspection or emission, and release the lock before calling any stream or logging method. That is the important ownership invariant. Concurrent callers do not emit duplicates; a stream or logging callback that re-enters partitioning does not deadlock on the notice lock; later calls do not wait for the first notice’s output.

Use a local reference to the acquired lock when releasing it, preferably through try/finally. Do not acquire one global lock object and later release a potentially replaced global reference.

Disable semantics

Use a deliberately small setting contract:

Python
os.environ.get("UNSTRUCTURED_DISABLE_NOTICE", "").strip() == "1"

Read it at use time rather than import time. Calls made while disabled do not consume eligibility. Removing the setting before a later call can therefore permit the first attempt.

Only 1, allowing surrounding whitespace, disables this notice. Do not copy telemetry’s broader “any nonempty value” interpretation: the supplied telemetry tests establish that its existing semantics are different.
source

After an attempt has been claimed, changing the setting, changing stdout, or reconfiguring logging must not cause another attempt.

Stream selection

Read the current sys.stdout, and safely evaluate its isatty() method. A missing stream, missing method, or ordinary exception during that check means “not confirmed terminal”; take the logger path.

Do not use sys.__stdout__, file descriptor 1, stdin’s terminal status, or stderr’s terminal status as substitutes. Python streams can be replaced or absent, and isatty() specifically describes whether the inspected stream is terminal-connected.
Python documentation
+1

This gives the intended behavior in the important asymmetric cases:

stdout	Other streams	Notice route
Terminal	stdin redirected, including a heredoc	stdout banner
Redirected file or pipe	stderr still a terminal	Package logger
Captured stream, such as StringIO	Original stdout remains a terminal	Package logger
Missing, closed, or uninspectable	Any	Package logger, best effort

For terminal output, construct the complete ASCII message first, then call stream.write(message) once and stream.flush() once. Use the same captured stream for the check, write, and flush. Do not add a fallback write to original stdout or directly to stderr.

If the terminal write partially succeeds or flushing fails, do not retry and do not switch to logging. The result is an incomplete best-effort notice, not a reason to risk duplicate output or fail partitioning.

Logging configuration and the stdout boundary

Import the existing logger:

Python
from unstructured.logger import logger

The supplied logger module already defines logging.getLogger("unstructured"); the notice does not need to create or configure a handler.
source

Call logger.warning("%s", message) normally. Do not call basicConfig(), change levels or propagation, attach even a NullHandler, replace lastResort, or use warnings.warn().

With default logging configuration, Python’s fallback warning handler writes to stderr. Application levels and filters can suppress a record, and multiple configured handlers can display a single record more than once. Consequently, the contract is one library warning call—not guaranteed visibility or exactly one rendered line across all logging destinations.
Python documentation

Do not implement handler inspection to “prove” stdout safety. A handler can write to stdout, another file-like object, or an indirect destination. The library cannot reliably determine all eventual destinations while respecting application logging configuration. The practical boundary is: no direct notice writes to nonterminal stdout; applications that route logs into their structured output must separate them or set the notice disable flag.
Python documentation

Likewise, “no network requests” means no transport implemented by the notice. It does not override an application’s existing remote logging destination.

Fork behavior

Register a notice-local child callback using os.register_at_fork(after_in_child=...) when available. The callback should replace the claim lock and clear _attempted, without logging, writing streams, or invoking telemetry.

The existing telemetry module already resets its own inherited state through an after-fork callback, so this is a source-consistent approach. Do not reuse or modify telemetry’s reset function: notice eligibility must not depend on telemetry state changes.
source

For this illustration, support ordinary Python-managed fork/spawn lifecycles. Do not add a generalized native-process lifecycle mechanism. Python documents that native extensions can bypass its fork callbacks; such unsupported fork paths should not be presented as covered by this design.
Python documentation

Do not reset production state between calls. Test fixtures may reset private state explicitly; avoid repeated module reloads to achieve test isolation.

Failure and latency boundaries

Wrap only the notice invocation in an Exception suppression boundary. Ordinary environment, stream, rendering, logger-filter, or handler failures must not prevent the partitioner from being called.

Do not catch BaseException indiscriminately. Interrupts and shutdown signals must retain their normal behavior. Most importantly, do not put the actual partitioner invocation inside the notice’s suppression scope.

Keep emission synchronous and small. This design does not promise a hard latency bound for an arbitrary application-provided stream or logging handler. It ensures that no notice lock is held during those callbacks, so a stalled sink does not serialize all other partitioning calls through the notice. A background delivery subsystem would be disproportionate for this illustration.

3. Integration points and coding instructions
unstructured/_usage_notice.py — new private module

Implement the message constants, notice-specific setting check, nonblocking claim operation, safe terminal detection, two rendering forms, and child-process reset described above.

Limit imports to the standard library and unstructured.logger. In particular, do not import telemetry, partitioners, document models, requests, or telemetry utilities. The helper needs no function arguments and must not inspect partition inputs or outputs.

Module initialization may construct constants and local synchronization state and register the fork callback. It must not emit the notice.

unstructured/telemetry.py — one runtime hook

Add the helper import and insert this block as the first operation in partition_runtime_telemetry()’s runtime wrapper:

Python
# The usage notice has its own opt-out and must precede telemetry short-circuits.
with suppress(Exception):
    maybe_emit_usage_notice()

Then leave the existing telemetry logic in place.

The precise insertion point matters: the wrapper currently returns directly to func() when telemetry is opted out or its opt-out check fails. Putting the notice beneath that logic would accidentally make telemetry settings suppress the notice.
source

Do not gate the notice on _CURRENT_INVOCATION, telemetry delivery-slot availability, the telemetry partitioner-name registry, or successful partitioning. Process-local ownership already handles nested calls; the telemetry wrapper’s separate outermost-invocation mechanism should remain unchanged.
source

Update the wrapper’s existing opt-out comment so it remains accurate: it should describe avoiding telemetry inspection/context/delivery work, not imply that absolutely no other work precedes the opt-out.

Existing partitioners and CLI — no new hooks

The supplied source verifies that partition_text() has the telemetry decorator outside its metadata and chunking decorators, and partition() is also directly decorated. Both therefore receive the new runtime hook without edits to those files.
source

source

Do not put this notice in apply_metadata(): it is a postprocessing layer rather than a uniform public-entrypoint boundary. Do not add a hook to package initialization, CLI help, or doctor; the supplied CLI is a diagnostics interface, not a partitioning command.
source

source

Coverage audit before implementation: enumerate actual @partition_runtime_telemetry applications in the prepared checkout and record the covered public functions. The registry lists numerous partitioner names, including API wrappers, but a registry entry alone is not proof that its function is decorated. Do not claim complete coverage of every public API from this bundle.
source

Undecorated standalone cleaning, chunking, serialization, and diagnostic APIs remain outside the recommended scope. Do not turn this task into a broad decorator migration.

Documentation and tests

Add test_unstructured/test_usage_notice.py and the README section. Extend existing runtime-telemetry or public-partitioner tests where useful after locating them in the actual checkout.

The expected production-code change is one new helper module and one decorator hook. No dependency, lockfile, CLI, public-signature, or partition-result change is part of the design.

4. Acceptance criteria and focused tests

The following are implementation acceptance criteria, not claims of tests already passing.

Area	Required tests and acceptance invariant
Copy and routes	A fake terminal receives one complete ASCII banner and one flush; the package logger receives nothing. A nonterminal receives no direct notice write and produces one WARNING call with the complete, single-line wording. Assert the exact offer, placeholder, and disable instruction.
First-use behavior	Importing the package, importing partitioner modules, constructing a decorated function, CLI help, and doctor produce no usage notice. A first public invocation attempts it, including an empty-input return and an invocation that raises. Repeated calls and calls through different decorated partitioners do not repeat it.
Independent settings	Parameterize notice enabled/disabled against telemetry enabled/disabled. DO_NOT_TRACK=1 and SCARF_NO_ANALYTICS=1 must not suppress the notice. The notice must still be attempted when the telemetry opt-out function raises and its wrapper takes the existing fallback. Conversely, notice disablement must not change telemetry scheduling when telemetry is enabled and mocked.
Stream safety and failures	Cover redirected stdout with terminal stderr, terminal stdout with redirected stdin, StringIO, absent stdout, missing/raising isatty(), failed write, and failed flush. Failed terminal emission causes no alternate output attempt. Ordinary failures do not change partition results or the partitioner’s original exception.
Threading and reentrancy	Release multiple callers through a barrier and assert one emission attempt. Gate the winning stream/handler with an event and demonstrate that another caller can reach its partition body before the sink is released. Re-enter a decorated function from a stream or logging callback and assert no duplicate notice or notice-lock deadlock. Use events and bounded joins, not sleeps as the synchronization mechanism.
Logging ownership	Test normal fallback behavior in a clean subprocess, application suppression, a filtering handler, and an ordinary exception raised by a filter/handler. Assert that the notice changes no logger configuration. Explicitly test the documented stdout-logging limitation and show that UNSTRUCTURED_DISABLE_NOTICE=1 eliminates notice contamination without reconfiguring that logger.
Process lifecycle	In an isolated, bounded subprocess, emit in the parent, then fork and invoke twice in the child: the child gets one independent attempt, and the parent does not reset. Also fork while the private claim lock is held to prove the child replaces it. Check a fresh spawned process. Skip fork-specific cases where unavailable.
Real entrypoints and unchanged processing	Exercise exported partition_text() and partition() functions, including automatic text dispatch followed by a direct text call. Compare results with notice enabled and disabled. At the wrapper-unit level, assert exact argument forwarding, one underlying invocation, return-object identity, and preservation of a sentinel exception.

Also verify that the helper starts no thread, opens no persistent store, and implements no network request. Scope these checks to the notice: a real partitioner may legitimately read files, and application logging may have its own destinations.

Test isolation matters here. Set DO_NOT_TRACK=1 before package import for hermetic notice tests, clear UNSTRUCTURED_DISABLE_NOTICE explicitly in tests expecting output, and reset private notice state between cases. The supplied telemetry tests already use an opt-out before import because initialization has existing telemetry side effects. This change should neither remove those effects nor accidentally rely on them for notice behavior.
source

source

Use subprocess tests for clean logging defaults, real process lifecycle, and stdout parsing. A caplog test alone does not demonstrate the default no-handler behavior.

5. Validation and public-entrypoint demonstrations
Targeted validation

Run from the prepared repository root using its project environment. The supplied pyproject.toml owns the test and lint groups and supports Python 3.11–3.13.
source

source

Bash
DO_NOT_TRACK=1 uv run --project . --group test python -m pytest \
  test_unstructured/test_usage_notice.py \
  test_unstructured/test_telemetry.py

uv run --project . --group lint ruff check \
  unstructured/_usage_notice.py \
  unstructured/telemetry.py \
  test_unstructured/test_usage_notice.py

uv run --project . --group lint ruff format --check \
  unstructured/_usage_notice.py \
  unstructured/telemetry.py \
  test_unstructured/test_usage_notice.py

Add the actual runtime-telemetry and relevant public-partitioner test paths discovered in the checkout. Exercise supported Python versions through the existing environment or CI matrix.

Use uv run, not an isolated tool environment. When the checkout contains its expected uv.lock, add --locked so an inconsistent lock fails rather than being rewritten. Dependency resolution changes are outside this task.
Astral Docs
+1

Prepare one real demonstration script

The following POSIX-shell demonstration uses automatic partitioning first, including its internal dispatch, then direct text partitioning. It never invokes the notice helper itself.

Bash
demo_dir=$(mktemp -d)

cat >"$demo_dir/demo.py" <<'PY'
import json
from io import BytesIO

from unstructured.partition.auto import partition
from unstructured.partition.text import partition_text

sample = b"- Apples\n\n- Pears\n"

automatic = partition(
    file=BytesIO(sample),
    content_type="text/plain",
    metadata_filename="notice-demo.txt",
    paragraph_grouper=False,
    languages=["eng"],
)

direct = partition_text(
    text=sample.decode("utf-8"),
    paragraph_grouper=False,
    languages=["eng"],
)

def project(elements):
    return [
        {"type": element.category, "text": element.text}
        for element in elements
    ]

assert project(automatic) == project(direct)
print(json.dumps(project(automatic)))
PY

Use the prepared partitioning environment with its normal prerequisites. Missing dependencies are a demonstration failure to report, not a reason to replace public entrypoints with helper calls.

Demonstrate import silence
Bash
env -u UNSTRUCTURED_DISABLE_NOTICE DO_NOT_TRACK=1 \
  uv run --project . python -c \
  'import unstructured; import unstructured.partition.text; print("imports-ok")'

Expected: imports-ok, with no usage notice. Existing telemetry is disabled before Python starts.

Demonstrate terminal output and once-per-process behavior

Run this with stdout attached to an actual terminal:

Bash
env -u UNSTRUCTURED_DISABLE_NOTICE DO_NOT_TRACK=1 \
  uv run --project . python "$demo_dir/demo.py"

Expected: one banner, then the JSON result. Automatic dispatch and the subsequent direct text call must not produce extra notices.

Run the command again as a new process: one new banner is expected. The visible notice while DO_NOT_TRACK=1 also demonstrates that telemetry opt-out does not disable it.

Demonstrate clean redirected JSON
Bash
env -u UNSTRUCTURED_DISABLE_NOTICE DO_NOT_TRACK=1 \
  uv run --project . python "$demo_dir/demo.py" \
  >"$demo_dir/output.json" 2>"$demo_dir/notice.log"

uv run --project . python -m json.tool \
  "$demo_dir/output.json" >/dev/null

test "$(grep -Fc '10,000 free pages to start.' \
  "$demo_dir/notice.log")" = 1

! grep -Fq '10,000 free pages to start.' "$demo_dir/output.json"

Expected: the JSON parses without stripping any prefix, and the offer appears once in stderr under the fresh process’s normal logging configuration. Do not merge the streams for this demonstration.

Demonstrate disablement on both paths

First, run with terminal-connected stdout:

Bash
UNSTRUCTURED_DISABLE_NOTICE=1 DO_NOT_TRACK=1 \
  uv run --project . python "$demo_dir/demo.py"

Expected: JSON only, without the notice.

Then run redirected:

Bash
UNSTRUCTURED_DISABLE_NOTICE=1 DO_NOT_TRACK=1 \
  uv run --project . python "$demo_dir/demo.py" \
  >"$demo_dir/disabled.json" 2>"$demo_dir/disabled.log"

cmp "$demo_dir/output.json" "$demo_dir/disabled.json"

! grep -Fq '10,000 free pages to start.' "$demo_dir/disabled.log"

Expected: identical projected partition output, with no notice warning.

6. Implementation handoff

The implementing agent should create a new branch from the prepared checkout, make the narrow changes above, run the targeted tests and public demonstrations, inspect the final diff, then commit and push that branch. Report the branch name, commit SHA, covered public entrypoints, actual validation results, and any skipped process/platform cases. The mission authorizes no PR, merge, release, or deployment.
source

The recommended design is therefore: one independent, process-local notice helper; one pre-opt-out runtime hook; terminal stdout or the existing package logger; no retries or logging reconfiguration. The offer remains explicitly illustrative, and the stdout and synchronous-I/O limits remain documented rather than hidden behind stronger guarantees.

No implementation, test execution, commit, or push was performed for this consultation.
