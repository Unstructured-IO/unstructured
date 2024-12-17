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
import logging
import os
import select
import sys
from collections import defaultdict
from typing import List, Sequence

from bs4 import BeautifulSoup

from unstructured.documents import elements
from unstructured.partition.html.transformations import unstructured_elements_to_ontology
from unstructured.staging.base import elements_from_json

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def extract_document_div(html_content: str) -> str:
    pos = html_content.find(">")
    if pos != -1:
        return html_content[: pos + 1]
    logger.error("No '>' found in the HTML content.")
    raise ValueError("No '>' found in the HTML content.")


def extract_page_div(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    page_divs = soup.find_all("div", class_="Page")
    if len(page_divs) != 1:
        logger.error(
            "Expected exactly one <div> element with class 'Page'. Found %d.", len(page_divs)
        )
        raise ValueError("Expected exactly one <div> element with class 'Page'.")
    return str(page_divs[0])


def fold_document_div(
    html_document_start: str, html_document_end: str, html_per_page: List[str]
) -> str:
    html_document = html_document_start
    for page_html in html_per_page:
        html_document += page_html
    html_document += html_document_end
    return html_document


def group_elements_by_page(
    unstructured_elements: Sequence[elements.Element],
) -> Sequence[Sequence[elements.Element]]:
    pages_dict = defaultdict(list)

    for element in unstructured_elements:
        page_number = element.metadata.page_number
        pages_dict[page_number].append(element)

    pages_list = list(pages_dict.values())
    return pages_list


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
    unstructured_elements_per_page = group_elements_by_page(unstructured_elements)
    # parsed_ontology = unstructured_elements_to_ontology(unstructured_elements)
    parsed_ontology_per_page = [
        unstructured_elements_to_ontology(elements) for elements in unstructured_elements_per_page
    ]
    html_per_page = [parsed_ontology.to_html() for parsed_ontology in parsed_ontology_per_page]

    html_document_start = extract_document_div(html_per_page[0])
    html_document_end = "</div>"
    html_per_page = [extract_page_div(page) for page in html_per_page]

    return fold_document_div(html_document_start, html_document_end, html_per_page)


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
