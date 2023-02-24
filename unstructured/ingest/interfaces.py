"""Defines Abstract Base Classes (ABC's) core to batch processing documents
through Unstructured."""

from abc import ABC, abstractmethod

from unstructured.partition.auto import partition
from unstructured.staging.base import convert_to_dict


class BaseConnector(ABC):
    """Abstract Base Class for a connector to a remote source, e.g. S3 or Google Drive."""

    def __init__(self, config):
        """Expects a config object that implements BaseConnectorConfig."""
        pass

    @abstractmethod
    def cleanup(self, cur_dir=None):
        """Any additonal cleanup up need after processing is complete. E.g., removing
        temporary download dirs that are empty.

        By convention, documents that failed to process are typically not cleaned up."""
        pass

    @abstractmethod
    def initialize(self):
        """Initializes the connector. Should also validate the connector is properly
        configured: e.g., list a single a document from the source."""
        pass

    @abstractmethod
    def get_ingest_docs(self):
        """Returns all ingest docs (derived from BaseIngestDoc).
        This does not imply downloading all the raw documents themselves,
        rather each IngestDoc is capable of fetching its content (in another process)
        with IngestDoc.get_file()."""
        pass


class BaseConnectorConfig(ABC):
    """All connector configs must respect these attr's."""

    # where raw documents are stored for processing, and then removed if not preserve_downloads
    download_dir: str
    preserve_downloads: bool = False
    # where to write structured data outputs
    output_dir: str
    re_download: bool = False
    # if a structured output .json file already exists for a given doc, do not reprocess
    reprocess: bool = False
    verbose: bool = False


class BaseIngestDoc(ABC):
    """An "ingest document" is specific to a connector, and provides
    methods to fetch a single raw document, store it locally for processing, any cleanup
    needed after successful processing of the doc, and the ability to write the doc's
    structured outputs once processed.

    Crucially, it is not responsible for the actual processing of the raw document.
    """

    @property
    @abstractmethod
    def filename(self):
        """The local filename of the document after fetching from remote source."""

    @abstractmethod
    def cleanup_file(self):
        """Removes the local copy the file (or anything else) after successful processing."""
        pass

    # NOTE(crag): Future BaseIngestDoc classes could define get_file_object() methods
    # in addition to or instead of get_file()
    @abstractmethod
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        pass

    @abstractmethod
    def has_output(self):
        """Determine if structured output for this doc already exists."""
        pass

    @abstractmethod
    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        pass

    def process_file(self):
        print(f"Processing {self.filename}")

        elements = partition(filename=self.filename)
        isd_elems = convert_to_dict(elements)

        self.isd_elems_no_filename = []
        for elem in isd_elems:
            # type: ignore
            elem["metadata"].pop("filename")  # type: ignore[attr-defined]
            elem.pop("coordinates")  # type: ignore[attr-defined]
            self.isd_elems_no_filename.append(elem)

        return self.isd_elems_no_filename
