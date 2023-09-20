from typing import BinaryIO, Optional, Union

import docx.document

def Document(docx: Optional[Union[str, BinaryIO]] = None) -> docx.document.Document: ...
