# pyright: reportPrivateUsage=false

from typing import Union

from lxml import etree

def parse_xml(xml: Union[str, bytes]) -> etree._Element: ...
