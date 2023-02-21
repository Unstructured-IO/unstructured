#!/usr/bin/env python3
import multiprocessing as mp
import random
import string
import sys

import click

from unstructured.ingest.connector.s3_connector import S3Connector, SimpleS3Config
from unstructured.ingest.doc_processor.generalized import initialize, process_document


class MainProcess:
    def __init__(self, doc_connector, doc_processor_fn, num_processes, reprocess):
        # initialize the reader and writer
        self.doc_connector = doc_connector
        self.doc_processor_fn = doc_processor_fn
        self.num_processes = num_processes
        self.reprocess = reprocess

    def initialize(self):
        """Slower initialization things: check connections, load things into memory, etc."""
        initialize()

    def cleanup(self):
        self.doc_connector.cleanup()

    def _filter_docs_with_outputs(self, docs):
        num_docs_all = len(docs)
        docs = [doc for doc in docs if not doc.has_output()]
        num_docs_to_process = len(docs)
        if num_docs_to_process == 0:
            print(
                "All docs have structured outputs, nothing to do. Use --reprocess to process all."
            )
            return None
        elif num_docs_to_process != num_docs_all:
            print(
                f"Skipping processing for {num_docs_all - num_docs_to_process} docs out of "
                f"{num_docs_all} since their structured outputs already exist, use --reprocess to "
                "reprocess those in addition to the unprocessed ones."
            )
        return docs

    def run(self):
        self.initialize()

        # fetch the list of lazy downloading IngestDoc obj's
        docs = self.doc_connector.get_ingest_docs()

        # remove docs that have already been processed
        if not self.reprocess:
            docs = self._filter_docs_with_outputs(docs)
            if not docs:
                return

        # Debugging tip: use the below line and comment out the mp.Pool loop
        # block to remain in single process
        # self.doc_processor_fn(docs[0])

        with mp.Pool(processes=self.num_processes) as pool:
            results = pool.map(self.doc_processor_fn, docs)  # noqa: F841

        self.cleanup()


@click.command()
@click.option(
    "--s3-url",
    default=None,
    help="Prefix of s3 objects (files) to download. E.g. s3://bucket1/path/. This value may "
    "also be a single file.",
)
@click.option(
    "--s3-anonymous",
    is_flag=True,
    default=False,
    help="Connect to s3 without local AWS credentials.",
)
@click.option(
    "--re-download/--no-re-download",
    default=False,
    help="Re-download files from s3 even if they are already present in --download-dir.",
)
@click.option(
    "--download-dir",
    help="Where s3 files are downloaded to, defaults to tmp-ingest-<6 random chars>.",
)
@click.option(
    "--preserve-downloads",
    is_flag=True,
    default=False,
    help="Preserve downloaded s3 files. Otherwise each file is removed after being processed "
    "successfully.",
)
@click.option(
    "--structured-output-dir",
    default="structured-output",
    help="Where to place structured output .json files.",
)
@click.option(
    "--reprocess",
    is_flag=True,
    default=False,
    help="Reprocess a downloaded file from s3 even if the relevant structured output .json file "
    "in --structured-output-dir already exists.",
)
@click.option(
    "--num-processes",
    default=2,
    show_default=True,
    help="Number of parallel processes to process docs in.",
)
@click.option("-v", "--verbose", is_flag=True, default=False)
def main(
    s3_url,
    re_download,
    download_dir,
    preserve_downloads,
    structured_output_dir,
    reprocess,
    num_processes,
    s3_anonymous,
    verbose,
):
    if not preserve_downloads and download_dir:
        print("Warning: not preserving downloaded files but --download_dir is specified")
    if not download_dir:
        download_dir = "tmp-ingest-" + "".join(
            random.choice(string.ascii_letters) for i in range(6)
        )
    if s3_url:
        doc_connector = S3Connector(
            config=SimpleS3Config(
                download_dir=download_dir,
                s3_url=s3_url,
                output_dir=structured_output_dir,
                # set to False to use your AWS creds (not needed for this public s3 url)
                anonymous=s3_anonymous,
                re_download=re_download,
                preserve_downloads=preserve_downloads,
                verbose=verbose,
            ),
        )
    # Check for other connector-specific options here and define the doc_connector object
    # e.g. "elif azure_container:  ..."

    else:
        print("No connector-specific option was specified!")
        sys.exit(1)

    MainProcess(
        doc_connector=doc_connector,
        doc_processor_fn=process_document,
        num_processes=num_processes,
        reprocess=reprocess,
    ).run()


if __name__ == "__main__":
    main()
