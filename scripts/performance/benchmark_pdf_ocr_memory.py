"""Exercise the real OCR-only PDF partitioner with deterministic blank pages."""

import argparse
import hashlib
import json
import resource
import sys
import tempfile
import time
from pathlib import Path

from pypdf import PdfWriter

from unstructured.partition.pdf import partition_pdf

parser = argparse.ArgumentParser()
parser.add_argument("--pages", type=int, default=20)
parser.add_argument("--page-points", type=int, default=1200)
args = parser.parse_args()
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "blank-pages.pdf"
    writer = PdfWriter()
    for _ in range(args.pages):
        writer.add_blank_page(width=args.page_points, height=args.page_points)
    with path.open("wb") as destination:
        writer.write(destination)
    print(json.dumps({"phase": "start", **vars(args)}), flush=True)
    started = time.perf_counter()
    with path.open("rb") as source:
        elements = partition_pdf(file=source, strategy="ocr_only", languages=["eng"])
    output = json.dumps([element.to_dict() for element in elements], sort_keys=True).encode()
    print(
        json.dumps(
            {
                "phase": "complete",
                "elapsed_seconds": time.perf_counter() - started,
                "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                // (1024 if sys.platform == "darwin" else 1),
                "output_count": len(elements),
                "sha256": hashlib.sha256(output).hexdigest(),
            }
        ),
        flush=True,
    )
