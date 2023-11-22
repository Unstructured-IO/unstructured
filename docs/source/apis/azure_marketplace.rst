Azure Marketplace Deployment Guide
===================================

Introduction
------------
This guide provides step-by-step instructions for deploying a service on Azure using the Azure Marketplace.

1. Login to Azure Portal
------------------------
- **URL**: `https://portal.azure.com <https://portal.azure.com/>`__.

2. Access Azure Marketplace
---------------------------
- Navigate to the Azure Marketplace using `this URL <https://azuremarketplace.microsoft.com/en-us/marketplace/apps/unstructured1691024866136.customer_api_v1?tab=Overview/>`__.


.. image:: imgs/Azure_Step2.png
  :align: center
  :alt: Azure Marketplace


3. Start Deployment Process
---------------------------
- Click the **Get it Now** button and fill out the form.
- Read the Terms and click **Continue**.
- Click **Create** button.


.. image:: imgs/Azure_Step3.png
  :align: center
  :alt: Deployment Process


4. Configure Deployment Options
-------------------------------

On the **Create a virtual machine** page, go to **Basics** tab and follow the steps below.

- Project details
    - Select **Subscription** and **Resource group** from dropdown menu.
    - Or, you can also ``Create New`` resource group.

.. image:: imgs/Azure_Step4a.png
  :align: center
  :alt: project details

- Instance details
    - Provide a name in the **Virtual machine name** field.
    - Select a **Region** from the dropdown menu.
    - **Image**: Select ``Unstructured Customer Hosted API Hourly - x64 Gen2`` (*default*)
    - **Size**: Select VM size from dropdown menu.

.. image:: imgs/Azure_Step4b.png
  :align: center
  :alt: instance details

- Administrator account
    - **Authentication type**: Select ``Password`` or ``SSH public key``.
    - Enter the ``credentials``.

.. image:: imgs/Azure_Step4c.png
  :align: center
  :alt: administrator account


5. Set Up Load Balancer
-----------------------

On the **Create a virtual machine** page, go to **Networking** tab and follow the steps below.

- Networking interface (required fields)
    - **Virtual network**: Select from dropdown menu or create new
    - **Subnet**: Select from dropdown menu
    - **Configure network security group**: Select from dropdown menu or create new

- Load balancing
    - **Load balancing option**: Select ``Azure load balancer``
    - **Select a load balance**: Select from dropdown menu or create new
        - **Type**: Select ``Public`` or ``Internal``
        - **Protococl**: Select ``TCP`` or ``UDP``
        - **Port** and **Backend Port**: Set to ``port 80``

.. image:: imgs/Azure_Step5.png
  :align: center
  :alt: load balancer


6. Finalize and Deploy
----------------------
- Click **Review + Create**.
- Wait for validation.
- Click **Create**.

.. image:: imgs/Azure_Step6.png
  :align: center
  :alt: deployment


7. Post-Deployment Steps
------------------------
- Go to the **Virtual Machine** from Azure console.
- Retrieve the **Load balancer public IP address**
- The deployed endpoint is **http://<load-balancer-public-IP-address>/general/v0/general**

.. image:: imgs/Azure_Step7.png
  :align: center
  :alt: retrieve public ip


7. Verification and Testing
---------------------------
- Navigate to the public IP with the specified path for documentation and API testing.
- Perform API testing with `curl` commands.

.. code-block:: bash

  curl -q -X POST http://<you-IP-address>/general/v0/general -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F files=@english-and-korean.png -o /tmp/english-and-korean.png.json

.. image:: imgs/Azure_Step8.png
  :align: center
  :alt: testing