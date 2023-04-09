import csv
import io
from typing import Dict, Generator, Iterable, List, Optional, Union

from unstructured.documents.elements import Text

PRODIGY_TYPE = List[Dict[str, Union[str, Dict[str, str]]]]


def _validate_prodigy_metadata(
    elements: List[Text],
    metadata: Optional[List[Dict[str, str]]] = None,
) -> Iterable[Dict[str, str]]:
    """
    Returns validated metadata list for Prodigy bricks.
    Raises ValueError with error message if metadata is not valid.
    """
    validated_metadata: Iterable[Dict[str, str]]
    if metadata:
        if len(metadata) != len(elements):
            raise ValueError(
                "The length of the metadata parameter does not match with"
                " the length of the elements parameter.",
            )
        id_error_index: Optional[int] = next(
            (index for index, metadatum in enumerate(metadata) if "id" in metadatum),
            None,
        )
        if isinstance(id_error_index, int):
            raise ValueError(
                'The key "id" is not allowed with metadata parameter at index: {index}'.format(
                    index=id_error_index,
                ),
            )
        validated_metadata = metadata
    else:
        validated_metadata = [{} for _ in elements]
    return validated_metadata


def stage_for_prodigy(
    elements: List[Text],
    metadata: Optional[List[Dict[str, str]]] = None,
) -> PRODIGY_TYPE:
    """
    Converts the document to the JSON format required for use with Prodigy.
    ref: https://prodi.gy/docs/api-loaders#input
    """

    validated_metadata: Iterable[Dict[str, str]] = _validate_prodigy_metadata(elements, metadata)

    prodigy_data: PRODIGY_TYPE = []
    for element, metadatum in zip(elements, validated_metadata):
        if isinstance(element.id, str):
            metadatum["id"] = element.id
        data: Dict[str, Union[str, Dict[str, str]]] = {"text": element.text, "meta": metadatum}
        prodigy_data.append(data)

    return prodigy_data


def stage_csv_for_prodigy(
    elements: List[Text],
    metadata: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Converts the document to the CSV format required for use with Prodigy.
    ref: https://prodi.gy/docs/api-loaders#input
    """
    validated_metadata: Iterable[Dict[str, str]] = _validate_prodigy_metadata(elements, metadata)

    csv_fieldnames = ["text", "id"]
    csv_fieldnames += list(
        set().union(
            *((key.lower() for key in metadata_item) for metadata_item in validated_metadata),
        ),
    )

    def _get_rows() -> Generator[Dict[str, str], None, None]:
        for element, metadatum in zip(elements, validated_metadata):
            metadatum = {key.lower(): value for key, value in metadatum.items()}
            row_data = dict(text=element.text, **metadatum)
            if isinstance(element.id, str):
                row_data["id"] = element.id
            yield row_data

    with io.StringIO() as buffer:
        csv_writer = csv.DictWriter(buffer, fieldnames=csv_fieldnames)
        csv_writer.writeheader()
        csv_rows = _get_rows()
        csv_writer.writerows(csv_rows)
        return buffer.getvalue()
