from typing import Dict, List, Union


def get_element_type_frequency(
    elements: List,
) -> Union[Dict[str, Dict[str, int]], Dict]:
    frequency: Dict = {}
    if len(elements) == 0:
        return frequency
    for element in elements:
        category = element.category
        category_depth = element.metadata.category_depth
        if category not in frequency:
            frequency[category] = {}
        if str(category_depth) not in frequency[category]:
            frequency[category][str(category_depth)] = 1
        else:
            frequency[category][str(category_depth)] += 1
    return frequency