from unittest import mock

import unstructured.partition.pdf as pdf
import unstructured.partition.image as image


def test_partition_image():
    with mock.patch.object(pdf, "_partition_pdf_or_image_local", mock.MagicMock()):
        image.partition_image(filename="fake.png", url=None)
        _, kwargs = pdf._partition_pdf_or_image_local.call_args
        assert kwargs["is_image"]
