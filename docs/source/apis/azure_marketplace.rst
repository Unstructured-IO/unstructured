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


.. image:: imgs/Azure/Azure_Step2.png
  :align: center
  :alt: Azure Marketplace


3. Start Deployment Process
---------------------------
- Click the **Get it Now** button and fill out the form.
- Read the Terms and click **Continue**.
- Click **Create** button.


.. image:: imgs/Azure/Azure_Step3.png
  :align: center
  :alt: Deployment Process


4. Configure Deployment Options
-------------------------------

On the **Create a virtual machine** page, go to **Basics** tab and follow the steps below.

- Project details
    - Select **Subscription** and **Resource group** from dropdown menu.
    - Or, you can also ``Create New`` resource group.

.. image:: imgs/Azure/Azure_Step4a.png
  :align: center
  :alt: project details

- Instance details
    - Provide a name in the **Virtual machine name** field.
    - Select a **Region** from the dropdown menu.
    - **Image**: Select ``Unstructured Customer Hosted API Hourly - x64 Gen2`` (*default*)
    - **Size**: Select VM size from dropdown menu. Refer to this page for `Azure VM comparisons <https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/>`_

.. image:: imgs/Azure/Azure_Step4b.png
  :align: center
  :alt: instance details

- Administrator account
    - **Authentication type**: Select ``Password`` or ``SSH public key``.
    - Enter the ``credentials``.

.. image:: imgs/Azure/Azure_Step4c.png
  :align: center
  :alt: administrator account


5. Set Up Load Balancer
-----------------------

Before you click ``Review + create`` button, go to **Networking** tab and follow the steps below.

- Networking interface (required fields)
    - **Virtual network**: Click ``Create new`` link or select a ``Virtual network`` from dropdown menu, if you have created one. Refer to  `Quickstart: Use the Azure portal to create a virtual network <https://learn.microsoft.com/en-us/azure/virtual-network/quick-create-portal>`_.
    - **Subnet**: Click ``Manage subnet configuration`` link or select a subnet from dropdown menu, if you have created one. Refer to  `Add, change, or delete a virtual network subnet <https://learn.microsoft.com/en-us/azure/virtual-network/virtual-network-manage-subnet?tabs=azure-portal>`_
    - **Configure network security group**: Click ``Create new`` link or select a security group from dropdown menu, if you have created one. Refer to  `Create, change, or delete a network security group <https://learn.microsoft.com/en-us/azure/virtual-network/manage-network-security-group?tabs=network-security-group-portal>`_.

- Load balancing
    - **Load balancing option**: Select ``Azure load balancer``
    - **Select a load balancer**: If you have created a load balancer, select from dropdown menu, or click ``Create a load balancer`` and fill out the following fields in the pop-up window.
        - Enter **Load balancer name**
        - **Type**: Select ``Public`` or ``Internal``
        - **Protococl**: Select ``TCP`` or ``UDP``
        - **Port** and **Backend Port**: Set to ``port 80``

.. image:: imgs/Azure/Azure_Step5.png
  :align: center
  :alt: load balancer


6. Finalize and Deploy
----------------------
- Click **Review + Create**.
- Wait for validation.
- Click **Create**.

.. image:: imgs/Azure/Azure_Step6.png
  :align: center
  :alt: deployment


7. Post-Deployment Steps
------------------------
- Go to the **Virtual Machine** from Azure console.
- Retrieve the **Load balancer public IP address**
- The deployed endpoint is **http://<load-balancer-public-IP-address>/general/v0/general**

.. image:: imgs/Azure/Azure_Step7.png
  :align: center
  :alt: retrieve public ip


7. Verification and Testing
---------------------------
- Navigate to the public IP with the specified path for documentation and API testing.
- Perform API testing with `curl` commands.

.. code-block:: bash

  curl -q -X POST http://<you-IP-address>/general/v0/general
       -H 'accept: application/json'
       -H 'Content-Type: multipart/form-data'
       -F files=@<<FILENAME>>
       -o <<PATH/OUTPUT>>.json

.. image:: imgs/Azure/Azure_Step8.png
  :align: center
  :alt: testing