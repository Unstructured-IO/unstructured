
AWS Marketplace Deployment Guide
================================

This guide provides step-by-step instructions for deploying Unstructured API from AWS Marketplace.

Pre-Requirements
----------------

1. **AWS Account**: Register at `AWS Registration Page <https://aws.amazon.com/>`_, if you don't have an AWS account.

2. **IAM Permissions**: Ensure permissions for ``CloudFormation``.

   - Refer to this `AWS blog post <https://blog.awsfundamentals.com/aws-iam-roles-with-aws-cloudformation#heading-creating-iam-roles-with-aws-cloudformation>`_ to create IAM Roles with CloudFormation.

3. **SSH KeyPair**: Create or use an existing KeyPair for secure access.

   - Follow the ``Create Key Pairs`` in the Amazon EC2 `User Guide <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html>`_.


Part 1: Setting-Up a Virtual Private Cloud (VPC)
------------------------------------------------

1. **Access VPC Dashboard**:

   - In the AWS Management Console, navigate to the VPC service.
   - Click on “Your VPCs” in the left navigation pane, then “Create VPC.”

2. **Create VPC**:

   - Select ``VPC only``
   - Enter a ``Name tag`` for your VPC.
   - Specify the IPv4 CIDR block (e.g., 10.0.0.0/16).

     - You may leave the IPv6 CIDR block and Tenancy settings as default.
   - Click “Create VPC” button

.. image:: imgs/AWS/VPC_Step2.png
  :align: center
  :alt: create vpc

3. **Create Subnets**:

   - After creating the VPC, click on “Subnets” in the left navigation pane.
   - Click “Create subnet” and select the VPC you just created from the dropdown menu.
   - For the first public subnet:

     - Enter a ``Name tag``.
     - Select an ``Availability Zone``.
     - Specify the IPv4 CIDR block (e.g., 10.0.1.0/24).
     - Click ``Add new subnet``.
   - Repeat the process for the second public subnet with a different Availability Zone and CIDR block (e.g., 10.0.2.0/24).

     - *Note: Each subnet must reside entirely within one Availability Zone and cannot span zones*.
     - Ref: AWS documentation on `Subnet basics <https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html#subnet-basics>`_.
   - For the private subnet:

     - Follow the same steps, but choose a different Availability Zone and CIDR block (e.g., 10.0.3.0/24).

   - Click ``Create subnet``.

.. image:: imgs/AWS/VPC_Step3.png
  :align: center
  :alt: create subnet

4. **Create Internet Gateway (for Public Subnets)**:

   - Go to “Internet Gateways” in the VPC dashboard.
   - Click “Create internet gateway,” enter a name, and create.
   - Attach the newly created internet gateway to your VPC.

.. image:: imgs/AWS/VPC_Step4.png
  :align: center
  :alt: create internet gateway

5. **Set Up Route Tables**:

   - Go to “Route tables” in the VPC dashboard.
   - Enter a ``Name``.
   - Select the ``VPC`` from Step 2 above.
   - Click ``Create route table``

.. image:: imgs/AWS/VPC_Step5.png
  :align: center
  :alt: create route table

6. **Connecting Route Tables and Internet Gateway**:

   - Go to the VPC set up in Step 2.
   - Connect the **public subnets** to the **route table** from Step 5.

     - Select the public subnet from Step 3.
     - Click ``Actions`` button on the top right-hand corner
     - Select ``Edit route table association``
     - Repeat the process for the two public subnets.

   - Connect the Route table to Internet Gateway

     - Click the ``route table`` from VPC Details page.
     - Click ``Edit route``
     - Click ``Add route``:

   - For the **private subnet**, use the main route table or create a new one without a route to the internet gateway.

.. image:: imgs/AWS/VPC_Step6.png
  :align: center
  :alt: connect public subnet to route table

7. **Inspect VPC Resource Map**:

   You can check the configurations from the Resource Maps on the VPC Details dashboard.

.. image:: imgs/AWS/VPC_Step7.png
  :align: center
  :alt: VPC Resource Maps

Part 2: Deploying Unstructured API from AWS Marketplace
-------------------------------------------------------

8. **Visit the Unstructured API page on AWS Marketplace**

   - Link: `Unstructured API Marketplace <http://aws.amazon.com/marketplace/pp/prodview-fuvslrofyuato>`_.
   - Click ``Continue to subscribe``
   - Review Terms and Conditions
   - Click ``Continue to Configuration``

.. image:: imgs/AWS/Marketplace_Step8.png
  :align: center
  :alt: Unstructured API on AWS Marketplace

9. **Configure the CloudFormation**

   - Select ``CloudFormation Template`` from the Fulfillment option dropdown menu.
   - Use the default ``Unstructured API`` template and software version.
   - Select the ``Region``

     - *Note: select the same region where you set up the VPC in Part 1.*
   - Click ``Continue to Launch`` button.
   - Select ``Launch CloudFormation`` from Choose Action dropdown menu.
   - Click ``Launch`` button.


.. image:: imgs/AWS/Marketplace_Step9.png
  :align: center
  :alt: CloudFormation Configuration


10. **Create Stack on CloudFormation**

    The Launch button will redirect to ``Create stack`` workflow in the CloudFormation.

    **Step 1: Create stack**

    - Select the ``Template is ready``
    - Use the default template source from ``Amazon S3 URL``
    - Click ``Next`` button.

    .. image:: imgs/AWS/Marketplace_Step10a.png
        :align: center
        :alt: Create Stack


    **Step 2: Specify stack details**

    - Provide ``stack name``
    - In the **Parameters** section, provide the ``KeyName``, ``Subnets``, and ``VPC`` from Part 1 above.
    - Specify, ``LoadBalancerScheme`` to *internet-facing* and ``SSHLocation`` to  *0.0.0.0/0*
    - Click ``Next`` button.

    .. image:: imgs/AWS/Marketplace_Step10b.png
        :align: center
        :alt: Specify stack details

    **Step 3: Configure stack options**

    - Specify the stack options or use default values.
    - Click ``Next`` button.

    .. image:: imgs/AWS/Marketplace_Step10c.png
        :align: center
        :alt: Specify stack options

    **Step 4: Review**

    - Review the Stack settings.
    - Click ``Submit`` button.

    .. image:: imgs/AWS/Marketplace_Step10d.png
        :align: center
        :alt: Review stack


11. **Get the Unstructured API Endpoint**

    - Check the status of the CloudFormation stack.
      - A successful deployment will show ``CREATE_COMPLETE`` status.
    - Click ``Resources`` tab and find ``ApplicationLoadBalancer``.
    - Copy the ``DNS Name`` from the Load Balancer dashboard.

.. image:: imgs/AWS/Marketplace_Step11.png
  :align: center
  :alt: Unstructured API Endpoint

Healthcheck
-----------

* Perform a health check using the curl command:

.. code-block:: bash

    curl https://<api_url>/healthcheck


Data Processing
---------------

* Data processing can be performed using curl commands below:

.. code-block:: bash

    curl -X 'POST' 'https://<api_url>' -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F 'files=@sample-docs/family-day.eml' | jq -C . | less -R


Getting Started with Unstructured
---------------------------------

* Explore examples in the Unstructured GitHub repository: `Unstructured GitHub <https://github.com/Unstructured-IO/unstructured>`_.

Support
-------

* For support inquiries, contact: `support@unstructured.io <mailto:support@unstructured.io>`_
