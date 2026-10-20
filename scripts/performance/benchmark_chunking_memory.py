"""Run in a fresh process; streamed inputs make retained image payloads observable."""

import argparse
import base64
import hashlib
import json
import random
import resource
import sys
import tempfile
import time
from contextlib import contextmanager
from unittest.mock import patch

from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import ElementMetadata, Image, NarrativeText
from unstructured.staging.base import elements_to_base64_gzipped_json

parser = argparse.ArgumentParser()
parser.add_argument("--case", choices=["empty-images", "originals"], required=True)
parser.add_argument("--count", type=int, default=128)
parser.add_argument("--payload-mib", type=int, default=4)
parser.add_argument("--payload", choices=["incompressible", "repeated"], default="incompressible")
args = parser.parse_args()
rng = random.Random(4517)
rolled_over = False
real_spool = tempfile.SpooledTemporaryFile


@contextmanager
def tracked_spool(*args, **kwargs):
    global rolled_over
    with real_spool(*args, **kwargs) as spool:
        try:
            yield spool
        finally:
            rolled_over |= spool._rolled


def payload():
    size = args.payload_mib * 1024 * 1024
    if args.payload == "repeated":
        return "x" * size
    return base64.b64encode(rng.randbytes((size * 3 + 3) // 4)).decode()[:size]


def inputs():
    for index in range(args.count):
        yield Image(
            text="",
            element_id=f"image-{index}",
            metadata=ElementMetadata(
                image_base64=payload(),
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
    with patch.object(tempfile, "SpooledTemporaryFile", tracked_spool):
        output = elements_to_base64_gzipped_json(inputs()).encode()
    if args.payload == "incompressible" and args.count * args.payload_mib >= 2:
        assert rolled_over, "Compressed payload must exercise the >1 MiB disk rollover"
print(
    json.dumps(
        {
            "phase": "complete",
            "elapsed_seconds": time.perf_counter() - started,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            // (1024 if sys.platform == "darwin" else 1),
            "output_bytes": len(output),
            "rolled_over": rolled_over,
            "sha256": hashlib.sha256(output).hexdigest(),
        }
    ),
    flush=True,
)
