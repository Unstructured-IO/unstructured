Docker Installation
=======================================

The instructions below guide you on how to use the `unstructured` library inside a Docker container.

Prerequisites
-------------

If you haven't installed Docker on your machine, you can find the installation guide `here <link_to_docker_installation>`_. 

.. note::
   We build multi-platform images to support both x86_64 and Apple silicon hardware. Using `docker pull` should download the appropriate image for your architecture. However, if needed, you can specify the platform with the `--platform` flag, e.g., `--platform linux/amd64`.

Pulling the Docker Image
-------------------------

We create Docker images for every push to the main branch. These images are tagged with the respective short commit hash (like `fbc7a69`) and the application version (e.g., `0.5.5-dev1`). The most recent image also receives the `latest` tag. To use these images, pull them from our repository:

.. code-block:: bash

   docker pull downloads.unstructured.io/unstructured-io/unstructured:latest

Using the Docker Image
----------------------

After pulling the image, you can create and start a container from it:

.. code-block:: bash

   # create the container
   docker run -dt --name unstructured downloads.unstructured.io/unstructured-io/unstructured:latest

   # start a bash shell inside the running Docker container
   docker exec -it unstructured bash

Building Your Own Docker Image
------------------------------

You can also build your own Docker image. If you only plan to parse a single type of data, you can accelerate the build process by excluding certain packages or requirements needed for other data types. Refer to the `Dockerfile` to determine which lines are necessary for your requirements.

.. code-block:: bash

   make docker-build

   # start a bash shell inside the running Docker container
   make docker-start-bash

Interacting with Python Inside the Container
--------------------------------------------

Once inside the running Docker container, you can directly test the library using Python's interactive mode:

.. code-block:: python

   python3

   >>> from unstructured.partition.pdf import partition_pdf
   >>> elements = partition_pdf(filename="example-docs/layout-parser-paper-fast.pdf")

   >>> from unstructured.partition.text import partition_text
   >>> elements = partition_text(filename="example-docs/fake-text.txt")
