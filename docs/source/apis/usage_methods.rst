Accessing Unstructured API
==========================

Method 1: Partition via API (``partition_via_api``)
---------------------------------------------------

- **Functionality**: Automates the partitioning of documents using the hosted or locally hosted Unstructured API.
- **Key Features**:
  - API Key Authentication.
  - Automatic or explicit MIME type handling.

- **Usage Examples**:

  - **Basic Use Case**::

      from unstructured.partition.api import partition_via_api

      filename = "example-docs/eml/fake-email.eml"
      elements = partition_via_api(filename=filename, api_key="MY_API_KEY", content_type="message/rfc822")

  - **Advanced Settings**::

      from unstructured.partition.api import partition_via_api

      filename = "example-docs/DA-1p.pdf"
      elements = partition_via_api(
        filename=filename, api_key="MY_API_KEY", strategy="auto", pdf_infer_table_structure="true"
      )

  - **Self-Hosting or Local API**::

      from unstructured.partition.api import partition_via_api

      filename = "example-docs/eml/fake-email.eml"
      elements = partition_via_api(
        filename=filename, api_url="http://localhost:5000/general/v0/general"
      )

- **More Details**: For comprehensive information, visit the `Partition via API Documentation <https://unstructured-io.github.io/unstructured/core/partition.html#partition-via-api>`_.

Method 2: Local Deployment Using ``unstructured-api`` Library
-------------------------------------------------------------

- **Environment Setup**:
  - Use ``pyenv`` and ``virtualenv`` for environment management.
  - Install dependencies as per OS requirements.

- **Running the Application**:
  - Run ``make install`` for dependencies installation.
  - Start with ``make run-jupyter`` for Jupyter Notebook or ``make run-web-app`` for FastAPI Web App.

- **Using the API Locally**:
  - Example API Call::

      curl -X 'POST' \
        'http://localhost:8000/general/v0/general' \
        -H 'accept: application/json' \
        -H 'Content-Type: multipart/form-data' \
        -F 'files=@sample-docs/family-day.eml' \
        | jq -C . | less -R

- **Additional Features**:

  - Parallel processing for PDFs with environment variables.
  - Server load management with UNSTRUCTURED_MEMORY_FREE_MINIMUM_MB.

- **Using Docker Image**: Docker commands for pulling and running the container.

- **More Details**: Check out the `unstructured-api GitHub Repository <https://github.com/Unstructured-IO/unstructured-api>`_ for further information.

Method 3: Accessing via Swagger UI
----------------------------------

- **Procedure**:

  1. Visit the Swagger UI Documentation: `Swagger UI <https://api.unstructured.io/general/docs#/default/pipeline_1_general_v0_general_post>`_.
  2. Click "Try it out" for interactive testing.
  3. Enter API key in "unstructured-api-key" field
  4. Enter parameters in "Request body".
  5. Click "execute" to send the request.
  6. Download or view the JSON output.
