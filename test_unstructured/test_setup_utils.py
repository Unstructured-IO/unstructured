from pathlib import Path

import pytest

import setup_utils

current_dir = Path(__file__).parent.absolute()


def test_load_requirements():
    file = current_dir / "files" / "example.in"
    reqs = setup_utils.load_requirements(file=file)
    desired_deps = ["torch", "httpx", "requests", "sphinx<4.3.2", "pandas"]
    assert len(reqs) == len(desired_deps)
    assert sorted(reqs) == sorted(desired_deps)


def test_load_requirements_not_file():
    file = current_dir / "files" / "nothing.in"
    with pytest.raises(FileNotFoundError):
        setup_utils.load_requirements(file=file)


def test_load_requirements_wrong_suffix():
    file = current_dir / "files" / "wrong_ext.txt"
    with pytest.raises(ValueError):
        setup_utils.load_requirements(file=file)


def test_load_base():
    setup_utils.get_base_reqs()


def test_load_doc_reqs():
    setup_utils.get_doc_reqs()


def test_load_all_doc_reqs():
    setup_utils.get_all_doc_reqs()


def test_load_extra_reqs():
    setup_utils.get_extras()
