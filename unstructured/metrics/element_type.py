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


def calculate_element_type_percent_match(
    output: Dict,
    source: Dict,
    category_depth_weight: float = 0.0,
) -> float:
    total_source_element_count = 0
    total_match_element_count = 0

    unmatched_depth_output = {}
    unmatched_depth_source = {}

    for k, v in output.items():
        if k in source:
            match_count = min(output[k], source[k])
            total_match_element_count += match_count
            total_source_element_count += match_count
            output[k] -= match_count
            source[k] -= match_count

            element_type = k[0]
            if element_type not in unmatched_depth_output:
                unmatched_depth_output[element_type] = output[k]
            else:
                unmatched_depth_output[element_type] += output[k]
            if element_type not in unmatched_depth_source:
                unmatched_depth_source[element_type] = source[k]
            else:
                unmatched_depth_source[element_type] += source[k]
    for k, v in unmatched_depth_source.items():
        if k in unmatched_depth_output:
            match_count = min(unmatched_depth_output[k], unmatched_depth_source[k])
            total_match_element_count += match_count * category_depth_weight
            total_source_element_count += unmatched_depth_source[k]

    return total_match_element_count / total_source_element_count


def _format_tuple_to_dict(
    t: Union[Dict[Tuple[str, Optional[int]], int], Dict]
) -> Dict[str, Dict[Optional[int], int]]:
    formatted_dict: Dict = {}
    for (type, depth), count in t.items():
        if type not in formatted_dict:
            formatted_dict[type] = {}
        if formatted_dict[type][depth] not in formatted_dict[type]:
            formatted_dict[type][depth] = count
        else:
            formatted_dict[type][depth] += count
    return formatted_dict
