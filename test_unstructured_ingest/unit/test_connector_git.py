from pathlib import Path

import pytest

from unstructured.ingest.connector.git import GitAccessConfig, GitSourceConnector, SimpleGitConfig


@pytest.mark.parametrize(
    ("given_file_path", "then_is_supported"),
    [
        (Path("src/submodule/document.md"), True),
        (Path("src/submodule/document.txt"), True),
        (Path("src/submodule/document.pdf"), True),
        (Path("src/submodule/document.doc"), True),
        (Path("src/submodule/document.docx"), True),
        (Path("src/submodule/document.eml"), True),
        (Path("src/submodule/document.html"), True),
        (Path("src/submodule/document.png"), True),
        (Path("src/submodule/document.jpg"), True),
        (Path("src/submodule/document.ppt"), True),
        (Path("src/submodule/document.pptx"), True),
        (Path("src/submodule/document.xml"), True),
        (Path("src/submodule/code.py"), False),
        (Path("src/submodule/Dockerfile"), False),
        (Path("src/submodule/Makefile"), False),
        (Path("src/submodule/LICENSE"), False),
    ],
)
def test_connector_supports_file(given_file_path, then_is_supported):
    when_is_supported = GitSourceConnector.is_file_type_supported(str(given_file_path))

    assert when_is_supported == then_is_supported


class FakeGitSourceConnectorImpl(GitSourceConnector):
    def get_ingest_docs(self):
        pass


@pytest.mark.parametrize(
    ("given_file_path", "given_file_glob", "then_matches_glob"),
    [
        (Path("LICENSE"), None, True),
        (Path("Makefile"), ["Makefile"], True),
        (Path("src/my/super/module/main.py"), ["**/*.py"], True),
        (Path("src/my/super/module/main.pyc"), ["**/*.py"], False),
    ],
)
def test_connector_does_path_match_glob(given_file_path, given_file_glob, then_matches_glob):
    connector_config = SimpleGitConfig(
        url="some_fake_url",
        access_config=GitAccessConfig(access_token="some_fake_token"),
        file_glob=given_file_glob,
    )
    connector = FakeGitSourceConnectorImpl(
        processor_config=None, read_config=None, connector_config=connector_config
    )

    when_matches_glob = connector.does_path_match_glob(str(given_file_path))

    assert when_matches_glob == then_matches_glob
