import logging

logger = logging.getLogger("unstructured")
trace_logger = logging.getLogger("unstructured.trace")

from unstructured.utils import scarf_analytics

# Create a custom logging level
DETAIL = 15
logging.addLevelName(DETAIL, "DETAIL")


# Create a custom log method for the "DETAIL" level
def detail(self, message, *args, **kws):
    if self.isEnabledFor(DETAIL):
        self._log(DETAIL, message, args, **kws)

scarf_analytics()

# Add the custom log method to the logging.Logger class
logging.Logger.detail = detail  # type: ignore
