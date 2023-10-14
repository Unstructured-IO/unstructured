from typing import IO, Union

import pptx.presentation

def Presentation(pptx: Union[str, IO[bytes], None] = None) -> pptx.presentation.Presentation: ...
