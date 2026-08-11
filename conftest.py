"""Global test configuration."""

import os

# Package import telemetry is default-on; keep ordinary test collection hermetic.
os.environ.setdefault("DO_NOT_TRACK", "1")
