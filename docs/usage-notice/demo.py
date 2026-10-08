"""Run with DO_NOT_TRACK=1; call two real public entrypoints in one process."""

import io
import json

from unstructured.partition.auto import partition
from unstructured.partition.text import partition_text

sample = b"This is a local usage notice demonstration sentence."
options = {"paragraph_grouper": False, "languages": ["eng"]}
automatic = partition(
    file=io.BytesIO(sample),
    content_type="text/plain",
    metadata_filename="notice-demo.txt",
    **options,
)
direct = partition_text(text=sample.decode(), **options)


def project(elements):
    return [{"type": element.category, "text": element.text} for element in elements]


assert project(automatic) == project(direct)
print(json.dumps(project(automatic)))
