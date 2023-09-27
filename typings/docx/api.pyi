from typing import IO, Optional, Union

import docx.document

def Document(docx: Optional[Union[str, IO[bytes]]] = None) -> docx.document.Document: ...
