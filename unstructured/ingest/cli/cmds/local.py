import click

from unstructured.ingest.cli.common import (
    log_options,
    map_to_standard_config,
    process_documents,
    run_init_checks,
)


@click.command()
@click.option(
    "--file-glob",
    default=None,
    help="A comma-separated list of file globs to limit which types of local files are accepted,"
    " e.g. '*.html,*.txt'",
)
@click.option(
    "--input-path",
    required=True,
    help="Path to the location in the local file system that will be processed.",
)
def local(**options):
    local_fn(**options)


def local_fn(**options):
    run_init_checks(options=options)
    log_options(options=options)

    from unstructured.ingest.connector.local import (
        LocalConnector,
        SimpleLocalConfig,
    )

    doc_connector = LocalConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleLocalConfig(
            input_path=options["input_path"],
            recursive=options["recursive"],
            file_glob=options["file_glob"],
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
