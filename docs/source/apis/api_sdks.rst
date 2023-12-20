Python and JavaScript SDK
=========================

This documentation covers the usage of the Python and JavaScript SDKs for interacting with the Unstructured API.

Python SDK
-----------

The Python SDK allows for easy interaction with the Unstructured API using Python.

Installation
~~~~~~~~~~~~

Install the Python SDK using pip:

.. code-block:: bash

    pip install unstructured-client

Usage
~~~~~

Here's a basic example of how to use the Python SDK:

.. code-block:: python

    from unstructured_client import UnstructuredClient
    from unstructured_client.models import shared
    from unstructured_client.models.errors import SDKError

    s = UnstructuredClient(api_key_auth="YOUR_API_KEY")

    filename = "sample-docs/layout-parser-paper.pdf"
    file = open(filename, "rb")

    req = shared.PartitionParameters(
        # Note that this currently only supports a single file
        files=shared.Files(
            content=file.read(),
            file_name=filename,
        ),
        # Other partition params
        strategy="fast",
    )

    try:
        res = s.general.partition(req)
        print(res.elements[0])
    except SDKError as e:
        print(e)

For more information, visit the `Python SDK GitHub repository <https://github.com/Unstructured-IO/unstructured-python-client>`_.

JavaScript SDK
--------------

The JavaScript SDK enables easy interaction with the Unstructured API using JavaScript.

Installation
~~~~~~~~~~~~

Install the JavaScript SDK using npm:

.. code-block:: bash

    npm install unstructured-client

Usage
~~~~~

Below is a basic example of how to use the JavaScript SDK:

.. code-block:: python

    import { UnstructuredClient } from "unstructured-client";
    import { PartitionResponse } from "unstructured-client/dist/sdk/models/operations";
    import * as fs from "fs";

    const key = "YOUR-API-KEY";

    const client = new UnstructuredClient({
        security: {
            apiKeyAuth: key,
        },
    });

    const filename = "sample-docs/layout-parser-paper.pdf";
    const data = fs.readFileSync(filename);

    client.general.partition({
        # Note that this currently only supports a single file
        files: {
            content: data,
            files: filename,
        },
        # Other partition params
        strategy: "fast",
    }).then((res: PartitionResponse) => {
        if (res.statusCode == 200) {
            console.log(res.elements);
        }
    }).catch((e) => {
        console.log(e.statusCode);
        console.log(e.body);
    });

For more information, visit the `JavaScript SDK GitHub repository <https://github.com/Unstructured-IO/unstructured-js-client>`_.
