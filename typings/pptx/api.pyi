from typing import BinaryIO, Union

import pptx.presentation

def Presentation(pptx: Union[str, BinaryIO]) -> pptx.presentation.Presentation: ...
