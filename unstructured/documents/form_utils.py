from __future__ import annotations

import copy

from unstructured.documents.elements import FormKeyValuePair


def _kvform_rehydrate_internal_elements(kv_pairs: list[dict]) -> list[FormKeyValuePair]:
    from unstructured.staging.base import elements_from_dicts

    # safe to overwrite - deepcopy already happened
    for kv_pair in kv_pairs:
        if kv_pair["key"]["custom_element"] is not None:
            (kv_pair["key"]["custom_element"],) = elements_from_dicts(
                [kv_pair["key"]["custom_element"]]
            )
        if kv_pair["value"] is not None and kv_pair["value"]["custom_element"] is not None:
            (kv_pair["value"]["custom_element"],) = elements_from_dicts(
                [kv_pair["value"]["custom_element"]]
            )
    return kv_pairs


def _kvform_pairs_to_dict(kv_pairs: list[FormKeyValuePair]) -> list[dict]:
    kv_pairs: list[dict] = copy.deepcopy(kv_pairs)
    for kv_pair in kv_pairs:
        if kv_pair["key"]["custom_element"] is not None:
            kv_pair["key"]["custom_element"] = kv_pair["key"]["custom_element"].to_dict()
        if kv_pair["value"] is not None and kv_pair["value"]["custom_element"] is not None:
            kv_pair["value"]["custom_element"] = kv_pair["value"]["custom_element"].to_dict()

    return kv_pairs
