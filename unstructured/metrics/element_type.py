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
    category_depth_weight: float = 0.5,
) -> float:
    """
    Calculate the percent match between two frequency dictionary. Intended to use with
    `get_element_type_frequency` function. The function counts the absolute exact match
    (type and depth), and counts the weighted match (correct type but different depth),
    then normalized with source's total elements.
    """
    if len(output) == 0 or len(source) == 0:
        return 0.0

    output_copy = output.copy()
    source_copy = source.copy()
    total_source_element_count = 0
    total_match_element_count = 0

    unmatched_depth_output = {}
    unmatched_depth_source = {}

    # loop through the output list to find match with source
    for k, _ in output_copy.items():
        if k in source_copy:
            match_count = min(output_copy[k], source_copy[k])
            total_match_element_count += match_count
            total_source_element_count += match_count

            # update the dictionary by removing already matched values
            output_copy[k] -= match_count
            source_copy[k] -= match_count

        # add unmatched leftovers from output_copy to a new dictionary
        element_type = k[0]
        if element_type not in unmatched_depth_output:
            unmatched_depth_output[element_type] = output_copy[k]
        else:
            unmatched_depth_output[element_type] += output_copy[k]

    # add unmatched leftovers from source_copy to a new dictionary
    unmatched_depth_source = _convert_to_frequency_without_depth(source_copy)

    # loop through the source list to match any existing partial match left
    for k, _ in unmatched_depth_source.items():
        total_source_element_count += unmatched_depth_source[k]
        if k in unmatched_depth_output:
            match_count = min(unmatched_depth_output[k], unmatched_depth_source[k])
            total_match_element_count += match_count * category_depth_weight

    return min(max(total_match_element_count / total_source_element_count, 0.0), 1.0)


def _convert_to_frequency_without_depth(d: Dict) -> Dict:
    """
    Takes in element frequency with depth of format (type, depth): value
    and converts to dictionary without depth of format type: value
    """
    res = {}
    for k, v in d.items():
        element_type = k[0]
        if element_type not in res:
            res[element_type] = v
        else:
            res[element_type] += v
    return res
