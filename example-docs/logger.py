import logging
from typing import Any

logger = logging.getLogger("unstructured")
trace_logger = logging.getLogger("unstructured.trace")

# Create a custom logging level
DETAIL = 15
logging.addLevelName(DETAIL, "DETAIL")


# Create a custom log method for the "DETAIL" level
def detail(self: logging.Logger, message: str, *args: Any, **kwargs: Any):
    if self.isEnabledFor(DETAIL):
        self._log(DETAIL, message, args, **kwargs)


# Add the custom log method to the logging.Logger class
logging.Logger.detail = detail  # type: ignore
