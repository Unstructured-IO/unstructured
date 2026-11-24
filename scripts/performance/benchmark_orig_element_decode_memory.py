"""Measure reconstruction of one large original element without fixture-memory spikes."""

import argparse
import base64
import hashlib
import io
import json
import resource
import struct
import sys
import time
import zlib

from unstructured.staging.base import elements_from_base64_gzipped_json


def main() -> None:
    """Decode a native uncompressed BMP payload or a wide-Unicode text record."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["image", "unicode", "wide-image"], default="image")
    args = parser.parse_args()
    compressor = zlib.compressobj()
    compressed = io.BytesIO()

    def write(fragment: bytes) -> None:
        compressed.write(compressor.compress(fragment))

    write(b'[{"type":"Image","element_id":"large","text":"')
    if args.case == "unicode":
        # JSON uses ASCII escapes, while the returned text requires wide Unicode storage.
        unit = b"\\ud83d\\ude00"
        for _ in range(1024):
            write(unit * 8192)
    elif args.case == "wide-image":
        write("😀".encode())
    else:
        write(b"full-page image")
    write(b'","metadata":{"page_number":1,"languages":["eng"],"image_mime_type":')
    write(b'"image/bmp","image_base64":"')
    if args.case in {"image", "wide-image"}:
        # A valid 6000x6500 RGB black raster: header and pixels can be encoded separately
        # because the 54-byte header and each row are divisible by three.
        side, height = 6000, 6500
        size = side * height * 3
        header = struct.pack("<2sIHHI", b"BM", 54 + size, 0, 0, 54)
        header += struct.pack("<IiiHHIIiiII", 40, side, height, 1, 24, 0, size, 0, 0, 0, 0)
        write(base64.b64encode(header))
        row = b"A" * (side * 4)
        for _ in range(height):
            write(row)
    else:
        write(b"AAECAwQ=")
    write(b'"}}]')
    compressed.write(compressor.flush())
    encoded = base64.b64encode(compressed.getvalue()).decode()
    compressed.close()
    started = time.perf_counter()
    elements = elements_from_base64_gzipped_json(encoded)
    elapsed = time.perf_counter() - started
    element = elements[0]
    metadata = element.to_dict()
    payload = metadata["metadata"].pop("image_base64")
    text = metadata.pop("text")
    digest = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode())
    for value in [text, payload]:
        for offset in range(0, len(value), 65536):
            digest.update(value[offset : offset + 65536].encode())
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(
        json.dumps(
            {
                "case": args.case,
                "seconds": elapsed,
                "count": len(elements),
                "peak_rss_kib": peak // 1024 if sys.platform == "darwin" else peak,
                "output_sha256": digest.hexdigest(),
                "text_chars": len(text),
                "payload_chars": len(payload),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
