Delta Table Source Connector
============================

Objectives
----------

1. Extract text and metadata from a PDF file using the Unstructured.io Python SDK.
2. Process and store this data in a Databricks Delta Table.
3. Retrieve data from the Delta Table using the Unstructured.io Delta Table Connector.

Prerequisites
-------------

- Unstructured Python SDK
- Databricks account and workspace
- AWS S3 for Delta Table storage


Extracting PDF Using Unstructured Python SDK
--------------------------------------------

1. Install Unstructured Python SDK

.. code-block:: bash

   pip install unstructuredio-sdk

2. Code Example

.. code-block:: python

   from unstructured_client import UnstructuredClient
   from unstructured_client.models import shared
   from unstructured_client.models.errors import SDKError

   s = UnstructuredClient(
       security=shared.Security(
           api_key_auth=UNSTRUCTURED_API_KEY, # replace with your own API key
       ),
   )

   req = shared.PartitionParameters(
       # Note that this currently only supports a single file
       files=shared.PartitionParametersFiles(
           content=file.read(),
           files=filename,
       ),
       # Other partition params
       strategy="hi_res",
       pdf_infer_table_structure=True,
       chunking_strategy="by_title",
   )

Processing and Storing into Databricks Delta Table
--------------------------------------------------

3. Initialize PySpark

.. code-block:: python

   from pyspark.sql import SparkSession

   spark = SparkSession.builder.appName('sparkdf').getOrCreate()

4. Convert JSON output into Dataframe

.. code-block:: python

   import pyspark

   dataframe = spark.createDataFrame(res.elements)

5. Store DataFrame as Delta Table

.. code-block:: python

   dataframe.write.mode("overwrite").format("delta").saveAsTable("delta_table")


Extracting Delta Table Using Unstructured Connector
---------------------------------------------------

6. Install Unstructured Connector Dependency

.. code-block:: bash

   pip install "unstructured[delta-table]"

7. Command Line Execution

.. code-block:: bash

   unstructured-ingest \
       delta-table \
       --table-uri <<REPLACE WITH S3 URI>> \
       --output-dir delta-table-example \
       --storage_options "AWS_REGION=us-east-2, \
                          AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID, \
                          AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
       --verbose


Conclusion
----------

This documentation covers the essential steps for converting unstructured PDF data into structured data and storing it in a Databricks Delta Table. It also outlines how to extract this data for further use.



