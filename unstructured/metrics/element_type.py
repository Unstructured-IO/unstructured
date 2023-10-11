import json
from typing import Dict, Optional, Tuple, Union


def get_element_type_frequency(
    elements: str,
) -> Union[Dict[Tuple[str, Optional[int]], int], Dict]:
    """
    Calculate the frequency of Element Types from a list of elements.
    """
    frequency: Dict = {}
    if len(elements) == 0:
        return frequency
    for element in json.loads(elements):
        type = element.get("type")
        category_depth = element["metadata"].get("category_depth")
        key = (type, category_depth)
        if key not in frequency:
            frequency[key] = 1
        else:
            frequency[key] += 1
    return frequency
