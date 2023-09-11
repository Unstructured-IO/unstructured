from typing import BinaryIO, Optional, Union

import pptx.presentation

def Presentation(pptx: Optional[Union[str, BinaryIO]] = None) -> pptx.presentation.Presentation: ...
