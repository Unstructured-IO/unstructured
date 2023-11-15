Azure Marketplace Deployment Guide
===================================

.. contents::
   :local:
   :depth: 2

Introduction
------------
This guide provides step-by-step instructions for deploying a service on Azure using the Azure Marketplace.

1. Login to Azure Portal
------------------------
- **URL**: `https://portal.azure.com`

2. Access Azure Marketplace
---------------------------
- Navigate to the Azure Marketplace using the following URL:
  `https://azuremarketplace.microsoft.com/en-us/marketplace/apps/unstructured1691024866136.customer_api_v1?tab=Overview`

3. Start Deployment Process
---------------------------
- Click the **Get it now** button and fill out the form.
- Click **Continue**.
- Click **Create**.
- Select `utic-dev` as the resource group.
- Fill in the **name field**.

4. Configure Deployment Options
-------------------------------
- Choose **Virtual machine scale set** from Availability options.
- Click **Create new**.
- Set fields as instructed and choose a custom name.
- Configure scaling options (either directly or through the scaling tab).
- Fill in fields as instructed.

5. Networking and Load Balancer Setup
-------------------------------------
- Click on the **networking tab**.
- Select `utic-dev` for the network.
- Select **Azure Load Balancer**.
- Create a load balancer with a name matching the deploy name.
- Check **Enable application health monitoring**.
- Set request path to `/healthcheck`.

6. Finalize and Deploy
----------------------
- Click **Review + Create**.
- Wait for validation.
- Click **Create**.

7. Post-Deployment Steps
------------------------
- Search for **resource groups** in Azure.
- Select `utic-dev` in the subscription.
- Monitor the deployment status and ensure success.
- Navigate to the deployed resource.
- Retrieve the public IP.
- Optionally, create a Route 53 A record for the IP.
- Remember to delete the resource group after usage.

8. Verification and Testing
---------------------------
- Navigate to the public IP with the specified path for documentation and API testing.
- Perform API testing with `curl` commands.

9. Notes and Observations
-------------------------
- Document any specific observations or issues encountered during the deployment and testing phase.
