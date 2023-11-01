Read Configuration
=========================

A shared read configuration serves as a universal set of parameters that are consistent across
all source connectors, providing a standardized way to access and retrieve documents from various sources.
This configuration typically includes settings such as the download directory, which specifies the location
where retrieved documents are stored. By maintaining common parameters like the download directory, users can
streamline their data extraction processes, making it easier to manage and organize the downloaded documents
irrespective of the source connector in use. This promotes consistency, ease of maintenance, and a more straightforward
integration process when working with multiple source connectors within a system.

Configs
---------------------

* ``download_dir``: What location to download the files to. When run via the CLI, a default
  location will be used if one is not provided.
* ``re_download (default False)``: By default, the process will skip downloads if the files already exist in the download directory.
  By setting this to ``True``, it will force the files to be re downloaded regardless of them existing already.
* ``preserve_downloads (default False)``: By default, the process will delete the downloaded content at the end if everything finished without error.
  By setting this to ``True``, those files will be preserved.
* ``download_only (default False)``: If set to ``True``, the process wil exit right after all the files are downloaded and omit any future
  steps such as partitioning and uploading to a destination.
* ``max_docs``: An optional integer which will cap how many documents are pulled in in a single process.
