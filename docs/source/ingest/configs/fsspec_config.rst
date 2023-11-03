Fsspec Configuration
=========================

A common fsspec configuration is a shared set of parameters and settings utilized by connectors responsible
for managing cloud-based file-system content. These configurations enable connectors to interact with cloud
storage systems consistently, specifying details such as authentication credentials, access permissions, storage
locations, and optimization options. By standardizing these fsspec configurations, connectors can seamlessly
interface with various cloud-based file systems, promoting interoperability and efficient management of remote
data storage across different cloud providers.

File Storage Configuration
----------------------------

Fsspec configuration is an extension of the `File Storage Config`:
* ``remote_url``: Path to the content on the remote system, prefixed with the protocol (i.e. ``s3://...``)
* ``uncompress (default False)``: Whether to uncompress tar and zip files when downloaded. Will ignore these otherwise.
* ``recursive (default False)``: If a directory path is provided, if further folders should be traversed recursively.

Configs
----------------------------

The following are configurations set on the fsspec config itself:
* ``access_kwargs``: An optional dictionary of access key-word arguments that might be needed to provide access to the cloud provider associated with the data.

The following are generated for the user after the config is initialized:
* ``protocol``: The protocol is pulled out from the raw remote path passed in (i.e. ``s3`` from ``s3://...``)
* ``path_without_protocol``: The file path on the remote source without the protocol.
* ``dir_path`` and ``file_path``: The raw remote path is parsed into the directory and file if it exists.
