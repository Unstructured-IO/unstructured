Unstructured API
#################

Try our hosted API! You can get your API key `here <https://unstructured.io/api-key>`__ now and start using it today.

You will find a more comprehensive overview of the API capabilities. For detailed information on request and response schemas, refer to the `API documentation <https://api.unstructured.io/general/docs#/>`__.

NOTE: You can also host the API locally. For more information check the `Using the API Locally <https://github.com/Unstructured-IO/unstructured-api>`__ section.


Supported File Types
*********************

========== ========================================================================================================
Category    Output
========== ========================================================================================================
Plaintext   ``.eml``, ``.html``, ``.json``, ``.md``, ``.msg``, ``.rst``, ``.rtf``, ``.txt``, ``.xml``
Images      ``.jpeg``, ``.png``
Documents.  ``.csv``, ``.doc``, ``.docx``, ``.epub``, ``.odt``, ``.pdf``, ``.ppt``, ``.pptx``, ``.tsv``, ``.xlsx``
========== ========================================================================================================

NOTE: Currently, the pipeline is capable of recognizing the file type and choosing the relevant partition function to process the file.


.. toctree::
   :maxdepth: 1

   apis/paid_api
   apis/api_sdks
   apis/usage_methods
   apis/azure_marketplace
   apis/aws_marketplace
   apis/api_parameters
   apis/validation_errors
