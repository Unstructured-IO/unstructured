import importlib
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        ("true", True),
        ("1", True),
        ("t", True),
        ("false", False),
        ("0", False),
        ("no", False),
    ],
)
def test_include_debug_metadata_parses_bool_string(monkeypatch, env_value, expected):
    from unstructured.partition.utils import constants

    monkeypatch.setenv("UNSTRUCTURED_INCLUDE_DEBUG_METADATA", env_value)
    try:
        importlib.reload(constants)
        assert constants.UNSTRUCTURED_INCLUDE_DEBUG_METADATA is expected
    finally:
        monkeypatch.undo()
        importlib.reload(constants)


def test_include_debug_metadata_defaults_to_false_when_unset(monkeypatch):
    from unstructured.partition.utils import constants

    monkeypatch.delenv("UNSTRUCTURED_INCLUDE_DEBUG_METADATA", raising=False)
    try:
        importlib.reload(constants)
        assert constants.UNSTRUCTURED_INCLUDE_DEBUG_METADATA is False
    finally:
        monkeypatch.undo()
        importlib.reload(constants)


def test_default_config():
    from unstructured.partition.utils.config import env_config

    assert env_config.IMAGE_CROP_PAD == 0


def test_env_override(monkeypatch):
    monkeypatch.setenv("IMAGE_CROP_PAD", str(1))
    from unstructured.partition.utils.config import env_config

    assert env_config.IMAGE_CROP_PAD == 1


@pytest.fixture()
def _setup_tmpdir():
    from unstructured.partition.utils.config import env_config

    _tmpdir = tempfile.tempdir
    _storage_tmpdir = env_config.GLOBAL_WORKING_PROCESS_DIR
    _storage_tmpdir_bak = f"{env_config.GLOBAL_WORKING_PROCESS_DIR}_bak"
    if Path(_storage_tmpdir).is_dir():
        shutil.move(_storage_tmpdir, _storage_tmpdir_bak)
        tempfile.tempdir = None
    yield
    if Path(_storage_tmpdir_bak).is_dir():
        if Path(_storage_tmpdir).is_dir():
            shutil.rmtree(_storage_tmpdir)
        shutil.move(_storage_tmpdir_bak, _storage_tmpdir)
        tempfile.tempdir = _tmpdir


@pytest.mark.usefixtures("_setup_tmpdir")
def test_env_storage_disabled(monkeypatch):
    monkeypatch.setenv("GLOBAL_WORKING_DIR_ENABLED", "false")
    from unstructured.partition.utils.config import env_config

    assert not env_config.GLOBAL_WORKING_DIR_ENABLED
    assert str(Path.home() / ".cache/unstructured") == env_config.GLOBAL_WORKING_DIR
    assert not Path(env_config.GLOBAL_WORKING_PROCESS_DIR).is_dir()
    assert tempfile.gettempdir() != env_config.GLOBAL_WORKING_PROCESS_DIR


@pytest.mark.usefixtures("_setup_tmpdir")
def test_env_storage_enabled(monkeypatch):
    monkeypatch.setenv("GLOBAL_WORKING_DIR_ENABLED", "true")
    from unstructured.partition.utils.config import env_config

    assert env_config.GLOBAL_WORKING_DIR_ENABLED
    assert str(Path.home() / ".cache/unstructured") == env_config.GLOBAL_WORKING_DIR
    assert Path(env_config.GLOBAL_WORKING_PROCESS_DIR).is_dir()
    assert tempfile.gettempdir() == env_config.GLOBAL_WORKING_PROCESS_DIR
