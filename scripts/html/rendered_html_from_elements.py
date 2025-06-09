# pyright: reportPrivateUsage=false

"""
Script to render HTML from unstructured elements.
NOTE: This script is not intended to be used as a module.
NOTE: For now script is only intended to be used with elements generated with
      `partition_html(html_parser_version=v2)`
TODO: It was noted that unstructured_elements_to_ontology func always returns a single page
      This script is using helper functions to handle multiple pages.
"""

import argparse
import html
import logging
import os
import select
import sys

from unstructured.partition.html.transformations import unstructured_elements_to_ontology
from unstructured.staging.base import elements_from_json

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def rendered_html(*, filepath: str | None = None, text: str | None = None) -> str:
    """Renders HTML from a JSON file with unstructured elements.

    Args:
        filepath (str): path to JSON file with unstructured elements.

    Returns:
        str: HTML content.
    """
    if filepath is None and text is None:
        logger.error("Either filepath or text must be provided.")
        raise ValueError("Either filepath or text must be provided.")
    if filepath is not None and text is not None:
        logger.error("Both filepath and text cannot be provided.")
        raise ValueError("Both filepath and text cannot be provided.")
    if filepath is not None:
        logger.info("Rendering HTML from file: %s", filepath)
    else:
        logger.info("Rendering HTML from text.")

    unstructured_elements = elements_from_json(filename=filepath, text=text)
    ontology_root = unstructured_elements_to_ontology(unstructured_elements)
    html_document = ontology_root.to_html()
    unescaped_html = html.unescape(html_document)
    return unescaped_html


def _main():
    if os.getenv("PROCESS_FROM_STDIN") == "true":
        logger.info("Processing from STDIN (PROCESS_FROM_STDIN is set to 'true')")
        if select.select([sys.stdin], [], [], 0.1)[0]:
            content = sys.stdin.read()
            html = rendered_html(text=content)
            sys.stdout.write(html)
        else:
            logger.error("No input provided via STDIN. Exiting.")
            sys.exit(1)
    else:
        logger.info("Processing from command line arguments")
        parser = argparse.ArgumentParser(description="Render HTML from unstructured elements.")
        parser.add_argument(
            "filepath", help="Path to JSON file with unstructured elements.", type=str
        )
        parser.add_argument(
            "--outdir",
            help="Path to directory where the rendered html will be stored.",
            type=str,
            default=None,
            nargs="?",
        )
        args = parser.parse_args()

        html = rendered_html(filepath=args.filepath)
        if args.outdir is None:
            args.outdir = os.path.dirname(args.filepath)
        os.makedirs(args.outdir, exist_ok=True)
        outpath = os.path.join(
            args.outdir, os.path.basename(args.filepath).replace(".json", ".html")
        )
        with open(outpath, "w") as f:
            f.write(html)
        logger.info("HTML rendered and saved to: %s", outpath)


if __name__ == "__main__":
    _main()
