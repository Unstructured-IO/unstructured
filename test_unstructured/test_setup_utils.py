import pytest

import setup_utils


def test_load_requirements():
    file = "./files/example.in"
    reqs = setup_utils.load_requirements(file=file)
    desired_deps = ["torch", "httpx", "requests", "sphinx<4.3.2", "pandas"]
    assert len(reqs) == len(desired_deps)
    assert sorted(reqs) == sorted(desired_deps)


def test_load_requirements_not_file():
    file = "./files/nothing.in"
    with pytest.raises(FileNotFoundError):
        setup_utils.load_requirements(file=file)


def test_load_base():
    setup_utils.get_base_reqs()


def test_load_doc_reqs():
    setup_utils.get_doc_reqs()


def test_load_all_doc_reqs():
    setup_utils.get_all_doc_reqs()


def test_load_extra_reqs():
    setup_utils.get_extras()
