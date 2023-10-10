from typing import Dict, List, Optional, Tuple, Union

from unstructured.documents.elements import TYPE_TO_TEXT_ELEMENT_MAP


def get_element_type_frequency(
    elements: List,
) -> Union[Dict[str, Tuple[Optional[str], int]], Dict]:
    frequency: Dict = {key: {} for key in TYPE_TO_TEXT_ELEMENT_MAP}
    if len(elements) == 0:
        return frequency
    for element in elements:
        category = element.category
        category_depth = element.metadata.category_depth

        if str(category_depth) not in frequency[category]:
            frequency[category][str(category_depth)] = 1
        else:
            frequency[category][str(category_depth)] += 1
    for key in frequency:
        frequency[key] = list(frequency[key].items())
    return frequency
