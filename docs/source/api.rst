Unstructured API Services
#########################

The Unstructured API presents an extensive selection of API services, encompassing free access, Software-as-a-Service (SaaS), and Azure & AWS Marketplace applications. These API services offer a high-quality and scalable solution capable of ingesting and digesting files of various types and sizes.

Within this documentation, you will find a detailed guide for implementing the Unstructured API across these diverse service options to best meet your operational requirements. It includes details on supported file types, step-by-step guides on using various API services, Python and JavaScript SDKs, and API parameters & common error handling.

.. warning::
    Please review this manual carefully, as we've introduced significant updates to the API services, including a new usage cap for our free API tier, effective from January 10th, 2024.

    Also, documents submitted to the free API may be utilized for our proprietary model training and evaluation purposes. This is part of our continuous effort to improve the API's performance and capabilities.


Changes to the Free API Service
*******************************

Implementation of a 1000-Page Cap
---------------------------------
Starting from January 10th, 2024, our free API service includes a cap of 1,000 pages. This limitation is introduced to ensure the sustainability of our free offerings and to enhance service quality.

Premium API Services
--------------------

For users requiring privacy and scalable API services, we provide several alternatives:

- **Commercial SaaS API:** Our premium service available with advanced features and dedicated support. Get your premium SaaS API Key `here <https://unstructured.io/api-key-hosted>`__.
- **AWS and Azure Marketplace APIs:** A selection of specialized APIs available through various marketplaces, including `AWS Marketplace <https://aws.amazon.com/marketplace/pp/prodview-fuvslrofyuato>`__ and `Azure Marketplace <https://azuremarketplace.microsoft.com/en-us/marketplace/apps/unstructured1691024866136.customer_api_v1>`__.
- **Open Source Offering:** Access to our open-source tools for self-hosting and customization on `Unstructured GitHub repo <https://github.com/Unstructured-IO/unstructured>`__.

Supported File Types
********************

========== ========================================================================================================
Category    File Types
========== ========================================================================================================
Plaintext   ``.eml``, ``.html``, ``.json``, ``.md``, ``.msg``, ``.rst``, ``.rtf``, ``.txt``, ``.xml``
Images      ``.png``, ``.jpg``, ``.jpeg``, ``.tiff``, ``.bmp``, ``.heic``
Documents.  ``.csv``, ``.doc``, ``.docx``, ``.epub``, ``.odt``, ``.pdf``, ``.ppt``, ``.pptx``, ``.tsv``, ``.xlsx``
========== ========================================================================================================

**NOTE**: Currently, the pipeline is capable of recognizing the file type and choosing the relevant partition function to process the file.


Get Support
***********

Should you require any assistance or have any questions regarding the Unstructured API, please contact our support team at `support@unstructured.io <mailto:support@unstructured.io>`__.

Table of Content
****************

.. toctree::
   :maxdepth: 1

   apis/saas_api
   apis/azure_marketplace
   apis/aws_marketplace
   apis/api_sdks
   apis/usage_methods
   apis/api_parameters
   apis/validation_errors
