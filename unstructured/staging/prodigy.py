from typing import Iterable, List, Dict, Optional, Union

from unstructured.documents.elements import Text


PRODIGY_TYPE = List[Dict[str, Union[str, Dict[str, str]]]]


def stage_for_prodigy(
    elements: List[Text],
    metadata: Optional[List[Dict[str, str]]] = None,
) -> PRODIGY_TYPE:
    """
    Converts the document to the format required for use with Prodigy.
    ref: https://prodi.gy/docs/api-loaders***REMOVED***input
    """

    validated_metadata: Iterable[Dict[str, str]]
    if metadata:
        if len(metadata) != len(elements):
            raise ValueError(
                "The length of metadata parameter does not match with length of elements parameter."
            )
        id_error_index: Optional[int] = next(
            (index for index, metadatum in enumerate(metadata) if "id" in metadatum), None
        )
        if isinstance(id_error_index, int):
            raise ValueError(
                'The key "id" is not allowed with metadata parameter at index: {index}'.format(
                    index=id_error_index
                )
            )
        validated_metadata = metadata
    else:
        validated_metadata = [dict() for _ in elements]

    prodigy_data: PRODIGY_TYPE = list()
    for element, metadatum in zip(elements, validated_metadata):
        if isinstance(element.id, str):
            metadatum["id"] = element.id
        data: Dict[str, Union[str, Dict[str, str]]] = dict(text=element.text, meta=metadatum)
        prodigy_data.append(data)

    return prodigy_data
