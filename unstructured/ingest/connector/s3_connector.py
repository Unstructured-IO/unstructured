import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
)
from unstructured.utils import requires_dependencies


@dataclass
class SimpleS3Config(BaseConnectorConfig):
    """Connector config where s3_url is an s3 prefix to process all documents from."""

    # S3 Specific Options
    s3_url: str

    # Standard Connector options
    download_dir: str
    # where to write structured data, with the directory structure matching s3 path
    output_dir: str
    re_download: bool = False
    preserve_downloads: bool = False
    verbose: bool = False

    # S3 Specific (optional)
    anonymous: bool = False

    s3_bucket: str = field(init=False)
    # could be single object or prefix
    s3_path: str = field(init=False)

    def __post_init__(self):
        if not self.s3_url.startswith("s3://"):
            raise ValueError("s3_url must begin with 's3://'")

        # just a bucket with no trailing prefix
        match = re.match(r"s3://([^/\s]+?)$", self.s3_url)
        if match:
            self.s3_bucket = match.group(1)
            self.s3_path = ""
            return

        # bucket with a path
        match = re.match(r"s3://([^/\s]+?)/([^\s]*)", self.s3_url)
        if not match:
            raise ValueError(
                f"s3_url {self.s3_url} does not look like a valid path. "
                "Expected s3://<bucket-name or s3://<bucket-name/path",
            )
        self.s3_bucket = match.group(1)
        self.s3_path = match.group(2) or ""


@dataclass
class S3IngestDoc(BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    config: SimpleS3Config
    s3_key: str

    # NOTE(crag): probably doesn't matter,  but intentionally not defining tmp_download_file
    # __post_init__ for multiprocessing simplicity (no Path objects in initially
    # instantiated object)
    def _tmp_download_file(self):
        return Path(self.config.download_dir) / self.s3_key

    def _output_filename(self):
        return Path(self.config.output_dir) / f"{self.s3_key}.json"

    def has_output(self):
        """Determine if structured output for this doc already exists."""
        return self._output_filename().is_file() and os.path.getsize(self._output_filename())

    def _create_full_tmp_dir_path(self):
        """includes "directories" in s3 object path"""
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @requires_dependencies(["boto3"], extras="s3")
    def get_file(self):
        """Actually fetches the file from s3 and stores it locally."""
        import boto3

        self._create_full_tmp_dir_path()
        if (
            not self.config.re_download
            and self._tmp_download_file().is_file()
            and os.path.getsize(self._tmp_download_file())
        ):
            if self.config.verbose:
                print(f"File exists: {self._tmp_download_file()}, skipping download")
            return

        if self.config.anonymous:
            from botocore import UNSIGNED
            from botocore.client import Config

            s3_cli = boto3.client("s3", config=Config(signature_version=UNSIGNED))
        else:
            s3_cli = boto3.client("s3")
        if self.config.verbose:
            print(f"fetching {self} - PID: {os.getpid()}")
        s3_cli.download_file(self.config.s3_bucket, self.s3_key, self._tmp_download_file())

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w") as output_f:
            json.dump(self.isd_elems_no_filename, output_f, ensure_ascii=False, indent=2)
        print(f"Wrote {output_filename}")

    @property
    def filename(self):
        """The filename of the file after downloading from s3"""
        return self._tmp_download_file()

    def cleanup_file(self):
        """Removes the local copy the file after successful processing."""
        if not self.config.preserve_downloads:
            if self.config.verbose:
                print(f"cleaning up {self}")
            os.unlink(self._tmp_download_file())


@requires_dependencies(["boto3"], extras="s3")
class S3Connector(BaseConnector):
    """Objects of this class support fetching document(s) from"""

    def __init__(self, config: SimpleS3Config):
        import boto3

        self.config = config
        self._list_objects_kwargs = {"Bucket": config.s3_bucket, "Prefix": config.s3_path}
        if config.anonymous:
            from botocore import UNSIGNED
            from botocore.client import Config

            self.s3_cli = boto3.client("s3", config=Config(signature_version=UNSIGNED))
        else:
            self.s3_cli = boto3.client("s3")
        self.cleanup_files = not config.preserve_downloads

    def cleanup(self, cur_dir=None):
        """cleanup linginering empty sub-dirs from s3 paths, but leave remaining files
        (and their paths) in tact as that indicates they were not processed"""
        if not self.cleanup_files:
            return

        if cur_dir is None:
            cur_dir = self.config.download_dir
        sub_dirs = os.listdir(cur_dir)
        os.chdir(cur_dir)
        for sub_dir in sub_dirs:
            # don't traverse symlinks, not that there every should be any
            if os.path.isdir(sub_dir) and not os.path.islink(sub_dir):
                self.cleanup(sub_dir)
        os.chdir("..")
        if len(os.listdir(cur_dir)) == 0:
            os.rmdir(cur_dir)

    def initialize(self):
        """Verify that can get metadata for an object, validates connections info."""
        response = self.s3_cli.list_objects_v2(**self._list_objects_kwargs, MaxKeys=1)
        if response["KeyCount"] < 1:
            raise ValueError(
                f"No objects found in {self.config.s3_url} -- response list object is {response}",
            )

    def _list_objects(self):
        response = self.s3_cli.list_objects_v2(**self._list_objects_kwargs)
        s3_keys = []
        while True:
            s3_keys.extend([s3_item["Key"] for s3_item in response["Contents"]])
            if not response.get("IsTruncated"):
                break
            next_token = response.get("NextContinuationToken")
            response = self.s3_cli.list_objects_v2(
                **self._list_objects_kwargs,
                ContinuationToken=next_token,
            )
        return s3_keys

    def get_ingest_docs(self):
        s3_keys = self._list_objects()
        return [
            S3IngestDoc(
                self.config,
                s3_key,
            )
            for s3_key in s3_keys
        ]
