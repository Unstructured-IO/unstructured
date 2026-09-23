"""Global test configuration."""

import os

# Package import telemetry is default-on; force ordinary test collection to opt out.
os.environ["DO_NOT_TRACK"] = "1"
