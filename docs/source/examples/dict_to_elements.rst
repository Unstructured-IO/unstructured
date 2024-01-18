Multi-files API Processing
==========================

Introduction
************

This guide demonstrates how to process multiple files using the Unstructured API and S3 Connector and implement context-aware chunking. The process involves installing dependencies, configuring settings, and utilizing Python scripts to manage and chunk data effectively.

Prerequisites
*************

Ensure you have Unstructured API key and access to an S3 bucket containing the target files.

Step-by-Step Process
********************

Step 1: Install Unstructured and S3 Dependency
----------------------------------------------

Install the `unstructured` package with S3 support.

.. code-block:: python

   pip install "unstructured[s3]"


Step 2: Import Libraries
------------------------

Import necessary libraries from the `unstructured` package for chunking and S3 processing.

.. code-block:: python

   from unstructured.ingest.interfaces import (
       FsspecConfig,
       PartitionConfig,
       ProcessorConfig,
       ReadConfig,
   )
   from unstructured.ingest.runner import S3Runner

   from unstructured.chunking.title import chunk_by_title
   from unstructured.staging.base import dict_to_elements


Step 3: Configuration
---------------------

Set up the API key and S3 URL for accessing the data.

.. code-block:: python

   UNSTRUCTURED_API_KEY = os.getenv('UNSTRUCTURED_API_KEY')
   S3_URL = "s3://rh-financial-reports/world-development-bank-2023/"


Step 4: Python Runner
---------------------

Configure and run the S3Runner for processing the data.

.. code-block:: python

   runner = S3Runner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="Connector-Output",
            num_processes=8,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            partition_endpoint="https://api.unstructured.io/general/v0/general",
            partition_by_api=True,
            api_key=UNSTRUCTURED_API_KEY,
            strategy="hi_res",
            hi_res_model_name="yolox",
            pdf_infer_table_structure=True,
        ),
        fsspec_config=FsspecConfig(
            remote_url=S3_URL,
        ),
    )

   runner.run(anonymous=True)


Step 5: Combine JSON Files from Multi-files Ingestion
-----------------------------------------------------

Combine JSON files into a single dataset for further processing.

.. code-block:: python

   combined_json_data = read_and_combine_json("Connector-Output/world-development-bank-2023")


Step 6: Convert into Unstructured Elements for Chunking
-------------------------------------------------------

Convert the combined JSON data into Unstructured Elements and apply chunking by title.

.. code-block:: python

   elements = dict_to_elements(combined_json_data)
   chunks = chunk_by_title(elements)


Conclusion
**********

Following these steps allows for efficient processing of multiple files using the Unstructured S3 Connector. The context-aware chunking helps in organizing and analyzing the data effectively.

