
AWS Marketplace Deployment Guide
================================

Requirements
------------
1. **AWS Account**: Register at `AWS Registration Page <https://aws.amazon.com/>`_, if you don't have an AWS account.

2. **IAM Permissions**: Ensure permissions for ``CloudFormation``.

   - Refer to this `AWS blog post <https://blog.awsfundamentals.com/aws-iam-roles-with-aws-cloudformation#heading-creating-iam-roles-with-aws-cloudformation>`_ to create IAM Roles with CloudFormation.

3. **SSH KeyPair**: Create or use an existing KeyPair for secure access.
   - Follow the ``Create Key Pairs`` in the Amazon EC2 `User Guide <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html>`_.


Deploying via AWS Console
-------------------------

1. **Login to AWS Console**:

   - Navigate to the ``CloudFormation`` console.

2. **Create New Stack**:

   - Use the S3 URL: `https://utic-public-cf.s3.amazonaws.com/api-marketplace.yaml <https://utic-public-cf.s3.amazonaws.com/api-marketplace.yaml>`_ to create a new stack.
   - Fill in the required fields:

     - **Stack Name**: Name your stack.
     - **KeyName**: SSH Key Pair. Create or use an existing keypair (`Create Key Pairs <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html>`_).
     - **LoadBalancerScheme**: Choose between internal or public-facing. Ensure subnets match the scheme.
     - **Subnets**: Specify subnets for the load balancer and autoscaling group.
     - **VPC**: Provide the ID of your VPC.
     - **SSHLocation**: Define the source IP range for SSH traffic to instances.
   - Proceed through the dialogs and submit to deploy.

Deploying via AWS CLI
---------------------

* Use the following command to deploy via AWS CLI:

.. code-block:: bash

    aws cloudformation create-stack --region <Region> --stack-name <StackName> --template-body file://api-marketplace.yaml --parameters ParameterKey=KeyName,ParameterValue=<KeyName> ParameterKey=VPC,ParameterValue='<VPC>' ParameterKey=Subnets,ParameterValue='<Subnet1>,<Subnet2>' ParameterKey=LoadBalancerScheme,ParameterValue=<LoadBalancerScheme>

Healthcheck
-----------

* Perform a health check using the curl command:

.. code-block:: bash

    curl https://<api_url>/healthcheck

Testing
-------

* Testing can be performed using curl commands with sample documents:

.. code-block:: bash

    curl -X 'POST' 'https://<api_url>' -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F 'files=@sample-docs/family-day.eml' | jq -C . | less -R

* Testing documents are available at the `Unstructured GitHub repository <https://github.com/Unstructured-IO/unstructured-api/tree/main/sample-docs>`_.

Resources Created
-----------------

* The deployment process will create the following resources:

  - AutoScaling Group
  - Public ALB load balancer
  - EC2 Instance(s)
  - Route53 DNS Record (Optional)
  - SSL Certificate (Optional)

Deployment Details
------------------

* **Regions**: Available in all supported regions.
* **Estimated Deployment Time**: Approximately 20 minutes.
* **Availability Zone Configuration**: Multi-AZ (Configurable).
* **Root Access**: No root access required. AMI runs as the rocky user.

Service Limits
--------------

* Default limits are generally sufficient. If necessary, consider increasing limits for instance types and load balancers.

Patches and Upgrades
--------------------

* Regular updates and new AMI deployments are provided. To upgrade:
  
  .. code-block:: bash

      sudo dnf upgrade -y

* For manual patching without updating the Unstructured service, SSH into the instance.

Fault Debugging
---------------

* SSH into the instance for debugging:

  .. code-block:: bash

      docker ps
      docker logs <container_id>

Recovery Actions
----------------

* In case of non-responsiveness, restart the Docker container:

  .. code-block:: bash

      sudo docker ps
      sudo docker rm -f <container_id>
      sudo docker run -d --restart unless-stopped -p 80:8000 quay.io/unstructured-io/unstructured-api:<version_tag>

* Replace `<version_tag>` with the current image version.

Getting Started
---------------

* Explore examples in the Unstructured GitHub repository: `Unstructured GitHub <https://github.com/Unstructured-IO/unstructured>`_.

Support
-------

* For support inquiries, contact: `support@unstructured.io <mailto:support@unstructured.io>`_
