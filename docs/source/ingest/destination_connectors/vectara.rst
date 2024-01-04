Vectara
===========

Process all your records using ``unstructured-ingest`` to store structured outputs locally on your filesystem and upload those to a Vectara corpus.
If you don't yet have a Vectara account, [sign up](https://vectara.com/integrations/unstructured/) for your account.

Run Locally
-----------
The upstream connector can be any of the ones supported, but for convenience here, showing a sample command using the
upstream local connector.

.. tabs::

   .. tab:: Shell

      .. literalinclude:: ./code/bash/vectara.sh
         :language: bash

   .. tab:: Python

      .. literalinclude:: ./code/python/vectara.py
         :language: python


For a full list of the options the CLI accepts check ``unstructured-ingest <upstream connector> vectara --help``.

NOTE: Keep in mind that you will need to have all the appropriate extras and dependencies for the file types of the documents contained in your data storage platform if you're running this locally. You can find more information about this in the `installation guide <https://unstructured-io.github.io/unstructured/installing.html>`_.