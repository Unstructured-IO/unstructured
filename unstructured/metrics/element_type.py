from typing import Dict, List, Optional, Tuple, Union


def get_element_type_frequency(
    elements: List,
) -> Union[Dict[Tuple[str, Optional[int]], int], Dict]:
    """
    Calculate the frequency of Element Types from a list of elements.
    """
    frequency: Dict = {}
    if len(elements) == 0:
        return frequency
    for element in elements:
        category = element.category
        category_depth = element.metadata.category_depth
        key = (category, category_depth)
        if key not in frequency:
            frequency[key] = 1
        else:
            frequency[key] += 1
    return frequency
