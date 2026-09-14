from .partition.utils.config import env_config
from .telemetry import init_telemetry

# init env_config
env_config

# Explicit startup boundary for the library-load telemetry ping (best-effort)
init_telemetry()
