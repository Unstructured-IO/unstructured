"""Run in a fresh process; streamed inputs make retained image payloads observable."""

import argparse
import hashlib
import json
import resource
import sys
import time

from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import ElementMetadata, Image, NarrativeText
from unstructured.staging.base import elements_to_base64_gzipped_json

parser = argparse.ArgumentParser()
parser.add_argument("--case", choices=["empty-images", "originals"], required=True)
parser.add_argument("--count", type=int, default=128)
parser.add_argument("--payload-mib", type=int, default=4)
args = parser.parse_args()


def inputs():
    for index in range(args.count):
        yield Image(
            text="",
            element_id=f"image-{index}",
            metadata=ElementMetadata(
                image_base64="x" * (args.payload_mib * 1024 * 1024),
                filename="streamed.pdf",
                page_number=1,
                languages=["eng"],
            ),
        )


print(json.dumps({"phase": "start", **vars(args)}), flush=True)
started = time.perf_counter()
if args.case == "empty-images":

    def document():
        yield from inputs()
        yield NarrativeText("final paragraph", element_id="paragraph")

    result = chunk_elements(document(), include_orig_elements=False)
    values = [chunk.to_dict() for chunk in result]
    for value in values:
        value.pop("element_id")
    output = json.dumps(values, sort_keys=True).encode()
else:
    output = elements_to_base64_gzipped_json(inputs()).encode()
print(
    json.dumps(
        {
            "phase": "complete",
            "elapsed_seconds": time.perf_counter() - started,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            // (1024 if sys.platform == "darwin" else 1),
            "output_bytes": len(output),
            "sha256": hashlib.sha256(output).hexdigest(),
        }
    ),
    flush=True,
)
