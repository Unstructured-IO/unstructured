import shutil
import tempfile
from pathlib import Path

import pytest


def test_default_config():
    from unstructured.partition.utils.config import env_config

    assert env_config.IMAGE_CROP_PAD == 0


def test_env_override(monkeypatch):
    monkeypatch.setenv("IMAGE_CROP_PAD", 1)
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
