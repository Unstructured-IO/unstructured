# Illustrative Open Source usage notice

Create a polite, attractive notice at actual public package use, preferably once per process. Thank users for Unstructured Open Source. Invite users to try the commercial offering for improved output quality. Prominently say "10,000 free pages to start." Use an obvious placeholder URL. No SQLite, new dependencies, logging handlers, import-time notice, or network request for the notice. Interactive terminal output should use stdout; noninteractive use should emit a warning through the package logger. Protect redirected structured stdout. Document UNSTRUCTURED_DISABLE_NOTICE=1 to disable both paths.

This is an illustration, not a release. Offer eligibility and maintenance duration need publication review. No evidence supports years of maintenance mode: recent commits on October 6–8, 2026 fix pptx, chunking and xlsx; README states OSS stays free and describes improved commercial quality. No AGENTS.md or crag-AGENTS.md exists in the prepared repository root.

Oracle must drive the proposal before implementation. Provide proposed wording, architecture, integration points, concrete coding instructions, acceptance criteria, focused tests, and real public-entrypoint demonstration steps. Consider the existing telemetry decorator (covers public partitioners), but keep the notice independent of telemetry opt-out. Consider thread safety, fork state, stream failures, logging configuration, nested calls, and structured output. Recommend a proportionate design and explain coverage limits. No production review or RAI is requested.

Package: Python 3.11–3.13, root pyproject owns dependencies and test group. Use uv project context for targeted pytest. Commit on new branch and push, with no PR, merge, release or deploy.
