import os
from typing import Any, Dict, List, Optional, Sequence, Union

from unstructured.documents.elements import NoID, Text

VALID_ATTACHMENT_TYPES: List[str] = ["IMAGE", "VIDEO", "RAW_TEXT", "TEXT_URL", "HTML"]


def _validate_attachments(attachment_list: List[Dict[str, str]], element_index: int):
    """
    Validates attachment list specified for an element.
    Raises a ValueError with error message if the attachment list are not valid.
    """
    for attachment_index, attachment in enumerate(attachment_list):
        error_message_prefix = (
            f"Error at index {attachment_index} of attachments parameter "
            f"for element at index {element_index}."
        )
        try:
            attachment_type = attachment["type"]
            attachment_value = attachment["value"]
        except KeyError as e:
            raise ValueError(f" Missing required key: {e.args[0]}")

        if (
            not isinstance(attachment_type, str)
            or attachment_type.upper() not in VALID_ATTACHMENT_TYPES
        ):
            raise ValueError(
                f"{error_message_prefix}. Invalid value specified for attachment.type. "
                f"Must be one of: {', '.join(VALID_ATTACHMENT_TYPES)}",
            )
        if not isinstance(attachment_value, str):
            raise ValueError(
                f"{error_message_prefix}. Invalid value specified for attachment.value. "
                "Must be of type string.",
            )


def stage_for_label_box(
    elements: List[Text],
    output_directory: str,
    url_prefix: str,
    external_ids: Optional[List[str]] = None,
    attachments: Optional[List[List[Dict[str, str]]]] = None,
    create_directory: bool = False,
) -> List[Dict[str, Any]]:
    """
    Stages documents to be uploaded to LabelBox and generates LabelBox configuration.
    ref: https://docs.labelbox.com/reference/data-import-format-overview
    """
    ids: Sequence[Union[str, NoID]]
    if (external_ids is not None) and len(external_ids) != len(elements):
        raise ValueError(
            "The external_ids parameter must be a list and the length of external_ids parameter "
            "must be the same as the length of elements parameter.",
        )
    elif external_ids is None:
        ids = [element.id for element in elements]
    else:
        ids = external_ids

    if (attachments is not None) and len(attachments) != len(elements):
        raise ValueError(
            "The attachments parameter must be a list and the length of attachments parameter "
            "must be the same as the length of elements parameter.",
        )
    elif attachments is None:
        attachments = [[] for _ in elements]
    else:
        for index, attachment_list in enumerate(attachments):
            _validate_attachments(attachment_list, index)

    if create_directory:
        os.makedirs(output_directory, exist_ok=True)
    else:
        if not os.path.isdir(output_directory):
            raise FileNotFoundError(output_directory)

    config_data: List[Dict[str, str]] = []
    for element, element_id, attachment_list in zip(elements, ids, attachments):
        output_filename = f"{element_id}.txt"
        data_url = "/".join([url_prefix.rstrip("/"), output_filename])
        output_filepath = os.path.join(output_directory, output_filename)
        with open(output_filepath, "w+") as output_text_file:
            output_text_file.write(element.text)

        element_config: Dict[str, Any] = {
            "data": data_url,
            "attachments": [
                {"type": attachment["type"].upper(), "value": attachment["value"]}
                for attachment in attachment_list
            ],
        }
        if isinstance(element_id, str):
            element_config["externalId"] = element_id

        config_data.append(element_config)

    return config_data
