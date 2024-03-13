Salesforce
==========

This page contains the information to ingest your data from Salesforce.

Prerequisites
--------------

- Salesforce Account
- Salesforce categories (objects) you wish to access
- Consumer Key and Private Key (PEM) from Salesforce connected app

For more information, please refer to `Salesforce API documentation <https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/>`__.


Step-by-Step Guide
-------------------

.. image:: imgs/Source-Salesforce.png
  :alt: Source Connector Salesforce

1. **Access the Create Source Page**. Navigate to the "Sources" section on the left sidebar and click the "New Source" button.

2. **Select Source Type**. Select **Salesforce** from the ``Type`` dropdown menu.

3. **Configure Source Details to connect to Salesforce**

  - ``Name`` (*required*): Enter a unique name for the Salesforce source connector.
  - ``Username`` (*required*): Enter the Salesforce username that has access to the required Salesforce categories.
  - ``Salesforce categories`` (*required*): Specify the Salesforce objects you wish to access, such as Account, Case, etc.
  - ``Consumer Key`` (*required*): Provide the Consumer Key from the Salesforce connected app.
  - ``Private Key (PEM)`` (*required*): Input the Private Key associated with the Consumer Key for the Salesforce connected app.

    - *Note: PEM begins with ``-----BEGIN RSA PRIVATE KEY-----`` and ends with ``-----END RSA PRIVATE KEY-----``.*

4. **Submit**. After filling in the necessary information, click 'Submit' to create the Source Connector. The newly completed Salesforce connector will be listed on the Sources dashboard.
