import os
import tarfile

from unstructured.ingest.utils.compression import uncompress_tar_file


def test_uncompress_tar_file(tmpdir):
    tar_filename = os.path.join(tmpdir, "test.tar")
    filename = "example-docs/fake-text.txt"

    with tarfile.open(tar_filename, "w:gz") as tar:
        tar.add(filename, arcname=os.path.basename(filename))

    path = uncompress_tar_file(tar_filename, path=tmpdir.dirname)
    assert path == tmpdir.dirname
