from typing import Optional

from unstructured.ingest.interfaces import BaseSessionHandle

# This is a global variable that can be set by the pool process to be used by the
# doc processor to assign the session handle to the doc. This is necessary because
# the session handle is not picklable and cannot be passed as an argument to the
# doc processor.
session_handle: Optional[BaseSessionHandle] = None
