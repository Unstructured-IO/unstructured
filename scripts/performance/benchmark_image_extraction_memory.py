"""Measure peak memory of PIL image extraction and hash its output for cross-checkout comparison.

Run with PYTHONPATH pointing at the desired library checkout. The deterministic
100-megapixel BMP is written a row at a time, so fixture generation is bounded.
"""

import argparse
import hashlib
import json
import random
import resource
import struct
import sys
import tempfile
import time
from pathlib import Path

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import ElementMetadata, Image
from unstructured.partition.pdf_image.pdf_image_utils import save_elements


def _positive_int(value: str) -> int:
    """Accept only positive dimensions and extraction counts."""
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return result


def main() -> None:
    """Extract full-page figures from one high-resolution raster upload."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--side", type=_positive_int, default=10000)
    parser.add_argument("--count", type=_positive_int, default=2)
    args = parser.parse_args()
    side = args.side
    stride = (side * 3 + 3) // 4 * 4
    size = stride * side
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "scan.bmp"
        rng = random.Random(901)
        with path.open("wb") as output:
            output.write(struct.pack("<2sIHHI", b"BM", 54 + size, 0, 0, 54))
            output.write(struct.pack("<IiiHHIIiiII", 40, side, side, 1, 24, 0, size, 0, 0, 0, 0))
            for _ in range(side):
                output.write(rng.randbytes(side * 3))
                output.write(b"\0" * (stride - side * 3))
        elements = [
            Image(
                text=f"figure {index}",
                element_id=str(index),
                coordinates=((0, 0), (0, side), (side, side), (side, 0)),
                coordinate_system=PixelSpace(width=side, height=side),
                metadata=ElementMetadata(page_number=1),
            )
            for index in range(args.count)
        ]
        start = time.perf_counter()
        with path.open("rb") as source:
            save_elements(
                elements,
                1,
                "Image",
                200,
                file=source,
                is_image=True,
                extract_image_block_to_payload=True,
            )
            assert not source.closed
            assert source.tell() == path.stat().st_size
        seconds = time.perf_counter() - start
        # Hash each field without constructing another complete output JSON.
        digest = hashlib.sha256()
        for element in elements:
            metadata = element.to_dict()
            payload = metadata["metadata"].pop("image_base64")
            digest.update(json.dumps(metadata, sort_keys=True).encode())
            for offset in range(0, len(payload), 65536):
                digest.update(payload[offset : offset + 65536].encode())
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        print(
            json.dumps(
                {
                    "side": side,
                    "count": len(elements),
                    "seconds": seconds,
                    "peak_rss_kib": peak // 1024 if sys.platform == "darwin" else peak,
                    "output_sha256": digest.hexdigest(),
                    "payload_bytes_each": len(elements[0].metadata.image_base64 or ""),
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
