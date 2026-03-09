import logging

from unstructured.utils import scarf_analytics

logger = logging.getLogger("unstructured")
trace_logger = logging.getLogger("unstructured.trace")

# Create a custom logging level
DETAIL = 15
logging.addLevelName(DETAIL, "DETAIL")


# Create a custom log method for the "DETAIL" level
def detail(self, message, *args, **kws):
    if self.isEnabledFor(DETAIL):
        self._log(DETAIL, message, args, **kws)


# Telemetry is off by default. To opt in, set UNSTRUCTURED_TELEMETRY_ENABLED=true.
# To opt out when enabled elsewhere, set SCARF_NO_ANALYTICS=true or DO_NOT_TRACK=true.
# See the README.
scarf_analytics()

# Add the custom log method to the logging.Logger class
logging.Logger.detail = detail  # type: ignore
