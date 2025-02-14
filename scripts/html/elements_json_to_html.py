import argparse
import logging
import os
from pathlib import Path

from unstructured.partition.html.convert import elements_to_html
from unstructured.staging.base import elements_from_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Convert JSON elements to HTML.")
    parser.add_argument("filepath", type=str, help="Path to the JSON file containing elements.")
    parser.add_argument(
        "--outdir", type=str, help="Output directory for the HTML file.", default=""
    )
    parser.add_argument(
        "--exclude-img", action="store_true", help="Exclude binary image data from the HTML."
    )
    parser.add_argument("--no-group", action="store_true", help="Don't group elements by pages.")
    args = parser.parse_args()

    filepath = Path(args.filepath)
    outdir = Path(args.outdir)

    elements = elements_from_json(args.filepath)
    elements_html = elements_to_html(
        elements, exclude_binary_image_data=args.exclude_img, no_group_by_page=args.no_group
    )

    os.makedirs(outdir, exist_ok=True)
    outpath = outdir / filepath.with_suffix(".html").name
    with open(outpath, "w+") as f:
        f.write(elements_html)
    logger.info("HTML rendered and saved to: %s", outpath)


if __name__ == "__main__":
    main()
