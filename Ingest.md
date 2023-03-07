# Batch Processing Documents

## The unstructured-ingest CLI

The unstructured library includes a CLI to batch ingest documents from (soon to be
various) sources, storing structured outputs locally on the filesystem.

For example, the following command processes all the documents in S3 in the
`utic-dev-tech-fixtures` bucket with a prefix of `small-pdf-set/`. 

    unstructured-ingest \
       --s3-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
       --s3-anonymous \
       --structured-output-dir s3-small-batch-output \
       --num-processes 2

Naturally, --num-processes may be adjusted for better instance utilization with multiprocessing.

Installation note: make sure to install the following extras when installing unstructured, needed for the above command:

    pip install "unstructured[s3,local-inference]"

See the [Quick Start](https://github.com/Unstructured-IO/unstructured#eight_pointed_black_star-quick-start) which documents how to pip install `dectectron2` and other OS dependencies, necessary for the parsing of .PDF files.

# Developers' Guide

## Local testing

When testing from a local checkout rather than a pip-installed version of `unstructured`,
just execute `unstructured/ingest/main.py`, e.g.:

    PYTHONPATH=. ./unstructured/ingest/main.py \
       --s3-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
       --s3-anonymous \
       --structured-output-dir s3-small-batch-output \
       --num-processes 2

## Adding Data Connectors

To add a connector, refer to [unstructured/ingest/connector/github.py](unstructured/ingest/connector/github.py) as example that implements the three relelvant abstract base classes.

If the connector has an available `fsspec` implementation, then refer to [unstructured/ingest/connector/s3.py](unstructured/ingest/connector/s3.py).

Then, update [unstructured/ingest/main.py](unstructured/ingest/main.py) to instantiate
the connector specific to your class if its command line options are invoked.

Create at least one folder [examples/ingest](examples/ingest) with an easily reproducible
script that shows the new connector in action.

Finally, to ensure the connector remains stable, add a new script test_unstructured_ingest/test-ingest-\<the-new-data-source\>.sh similar to [test_unstructured_ingest/test-ingest-s3.sh](test_unstructured_ingest/test-ingest-s3.sh), and append a line invoking the new script in [test_unstructured_ingest/test-ingest.sh](test_unstructured_ingest/test-ingest.sh).

You'll notice that the unstructured outputs for the new documents are expected
to be checked into CI under test_unstructured_ingest/expected-structured-output/\<folder-name-relevant-to-your-dataset\>. So, you'll need to `git add` those json outputs so that `test-ingest.sh` passes in CI.

The `main.py` flags of --re-download/--no-re-download , --download-dir, --preserve-downloads, --structured-output-dir, and --reprocess are honored by the connector.

### The checklist:

In checklist form, the above steps are summarized as:

- [ ] Create a new module under [unstructured/ingest/connector/](unstructured/ingest/connector/) implementing the 3 abstract base classes, similar to [unstructured/ingest/connector/github.py](unstructured/ingest/connector/github.py).
  - [ ] The subclass of `BaseIngestDoc` overrides `process_file()` if extra processing logic is needed other than what is provided by [auto.partition()](unstructured/partition/auto.py).
- [ ] Update [unstructured/ingest/main.py](unstructured/ingest/main.py) with support for the new connector.
- [ ] Create a folder under [examples/ingest](examples/ingest) that includes at least one well documented script.
- [ ] Add a script test_unstructured_ingest/test-ingest-\<the-new-data-source\>.sh. It's json output files should have a total of no more than 100K.
- [ ] Git add the expected outputs under test_unstructured_ingest/expected-structured-output/\<folder-name-relevant-to-your-dataset\> so the above test passes in CI.
- [ ] Add a line to [test_unstructured_ingest/test-ingest.sh](test_unstructured_ingest/test-ingest.sh) invoking the new test script.
- [ ] If additional python dependencies are needed for the new connector:
  - [ ] Add them as an extra to [setup.py](unstructured/setup.py).
  - [ ] Update the Makefile, adding a target for `install-ingest-<name>` and adding another `pip-compile` line to the `pip-compile` make target. See [this commit](https://github.com/Unstructured-IO/unstructured/commit/ab542ca3c6274f96b431142262d47d727f309e37) for a reference.
  - [ ] The added dependencies should be imported at runtime when the new connector is invoked, rather than as top-level imports.
  - [ ] Add the decorator `unstructured.utils.requires_dependencies` on top of each class instance or function that uses those connector-specific dependencies e.g. for `GitHubConnector` should look like `@requires_dependencies(dependencies=["github"], extras="github")`
  - [ ] Run `make tidy` and `make check` to ensure linting checks pass.
- [ ] Honors the conventions of `BaseConnectorConfig` defined in [unstructured/ingest/interfaces.py](unstructured/ingest/interfaces.py) which is passed through [the CLI](unstructured/ingest/main.py):
  - [ ] If running with an `.output_dir` where structured outputs already exists for a given file, the file content is not re-downloaded from the data source nor is it reprocessed. This is made possible by implementing the call to `MyIngestDoc.has_output()` which is invoked in [MainProcess._filter_docs_with_outputs](ingest-prep-for-many/unstructured/ingest/main.py).
  - [ ] Unless `.reprocess` is `True`, then documents are always reprocessed.
  - [ ] If `.preserve_download` is `True`, documents downloaded to `.download_dir` are not removed after processing.
  - [ ] Else if `.preserve_download` is `False`, documents downloaded to `.download_dir` are removed after they are **successfully** processed during the invocation of `MyIngestDoc.cleanup_file()` in [process_document](unstructured/ingest/doc_processor/generalized.py)
  - [ ] Does not re-download documents to `.download_dir` if `.re_download` is False, enforced in `MyIngestDoc.get_file()`
  - [ ] Prints more details if `--verbose` in ingest CLI, similar to [unstructured/ingest/connector/github.py](unstructured/ingest/connector/github.py) logging messages.
