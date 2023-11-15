AWS Marketplace Deployment Guide
================================

.. contents::
   :local:
   :depth: 2

Introduction
------------
This guide provides detailed steps for deploying the Unstructured API using AWS services.

1. Login to AWS Console
-----------------------

2. Access CloudFormation Console
--------------------------------

3. Create New Stack
-------------------
- Use the following S3 URL for the stack template: `https://utic-public-cf.s3.amazonaws.com/api-marketplace.yaml`

4. Fill in Required Fields
--------------------------
- **Stack Name**
- **KeyName** - SSH Key Pair
- **LoadBalancerScheme**
- **Subnets**
- **VPC**
- **SSHLocation**

5. Submit the Stack
-------------------

6. Deploying via AWS CLI
------------------------
- Use specific AWS CLI commands with parameters for key name, VPC, subnets, and load balancer scheme.

7. Healthcheck
-------------
- Perform health checks using the following `curl` command: `curl https://<api_url>/healthcheck`

8. Testing
----------
- Perform testing with `curl` commands.

9. Resources Created
--------------------
- **AutoScaling Group**
- **Public ALB load balancer**
- **EC2 Instance(s)**
- **Route53 DNS Record** (Optional)
- **SSL Certificate** (Optional)

10. Deployment Details
----------------------
- Details on regions, estimated deployment time, availability zone configuration, and root access.

11. Service Limits
------------------

12. Patches and Upgrades
-----------------------
- Instructions for patching and upgrading the deployment.

13. Fault Debugging and Recovery Actions
----------------------------------------
- Steps to debug faults and recover the application.

14. Support
-----------
- Contact information for support.

