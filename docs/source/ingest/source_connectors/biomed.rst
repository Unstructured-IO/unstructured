Biomed
==========
Connect Biomed to your preprocessing pipeline, and batch process all your documents using ``unstructured-ingest`` to store structured outputs locally on your filesystem.

First you'll need to install the Biomed dependencies as shown here.

.. code:: shell

  pip install "unstructured[biomed]"

Run Locally
-----------

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
          biomed \
          --path "oa_pdf/07/07/sbaa031.073.PMC7234218.pdf" \
          --output-dir biomed-ingest-output-path \
          --num-processes 2 \
          --verbose \
          --preserve-downloads

   .. tab:: Python

      .. code:: python

        import os

        from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
        from unstructured.ingest.runner import BiomedRunner

        if __name__ == "__main__":
            runner = BiomedRunner(
                processor_config=ProcessorConfig(
                    verbose=True,
                    output_dir="bioemt-ingest-output",
                    num_processes=2,
                ),
                read_config=ReadConfig(),
                partition_config=PartitionConfig(),
            )
            runner.run(
                path="oa_pdf/07/07/sbaa031.073.PMC7234218.pdf",
            )

Run via the API
---------------

You can also use upstream connectors with the ``unstructured`` API. For this you'll need to use the ``--partition-by-api`` flag and pass in your API key with ``--api-key``.

.. tabs::

   .. tab:: Shell

      .. code:: shell

        unstructured-ingest \
          biomed \
          --path "oa_pdf/07/07/sbaa031.073.PMC7234218.pdf" \
          --output-dir biomed-ingest-output-path \
          --num-processes 2 \
          --verbose \
          --preserve-downloads \
          --partition-by-api \
          --api-key "<UNSTRUCTURED-API-KEY>"

   .. tab:: Python

      .. code:: python

        import os

        from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
        from unstructured.ingest.runner import BiomedRunner

        if __name__ == "__main__":
            runner = BiomedRunner(
                processor_config=ProcessorConfig(
                    verbose=True,
                    output_dir="bioemt-ingest-output",
                    num_processes=2,
                ),
                read_config=ReadConfig(),
                partition_config=PartitionConfig(
                    partition_by_api=True,
                    api_key=os.getenv("UNSTRUCTURED_API_KEY"),
                ),
            )
            runner.run(
                path="oa_pdf/07/07/sbaa031.073.PMC7234218.pdf",
            )

Additionally, you will need to pass the ``--partition-endpoint`` if you're running the API locally. You can find more information about the ``unstructured`` API `here <https://github.com/Unstructured-IO/unstructured-api>`_.

For a full list of the options the CLI accepts check ``unstructured-ingest biomed --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.
