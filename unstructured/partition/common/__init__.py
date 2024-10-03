class UnsupportedFileFormatError(Exception):
    """File-type is not supported for this operation.

    For example, when receiving a file for auto-partitioning where its file-formatt cannot be
    identified or there is no partitioner available for that file-format.
    """
