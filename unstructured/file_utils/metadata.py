from typing import Any, Dict, Optional

import docx


def get_docx_metadata(
    filename: str = "",
    file: Optional[bytes] = None,
) -> Dict[str, Any]:
    """Extracts document Metadata from a Microsoft .docx document. Returns the metadata
    as a dictionary."""
    if filename:
        doc = docx.Document(filename)
    elif file:
        doc = docx.Document(file)
    else:
        raise FileNotFoundError("No filename nor file were specified")

    metadata = dict()
    for attr in dir(doc.core_properties):
        if not attr.startswith("_"):
            metadata[attr] = getattr(doc.core_properties, attr)

    return metadata
