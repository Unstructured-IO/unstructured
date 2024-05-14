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
def setup_tmpdir():
    from unstructured.partition.utils.config import env_config

    _tmpdir = tempfile.tempdir
    _storage_tmpdir = env_config.STORAGE_TMPDIR
    _storage_tmpdir_bak = f"{env_config.STORAGE_TMPDIR}_bak"
    if Path(_storage_tmpdir).is_dir():
        shutil.move(_storage_tmpdir, _storage_tmpdir_bak)
        tempfile.tempdir = None
    yield
    if Path(_storage_tmpdir_bak).is_dir():
        if Path(_storage_tmpdir).is_dir():
            shutil.rmtree(_storage_tmpdir)
        shutil.move(_storage_tmpdir_bak, _storage_tmpdir)
        tempfile.tempdir = _tmpdir


def test_env_storage_disabled(monkeypatch, setup_tmpdir):
    monkeypatch.setenv("STORAGE_ENABLED", "false")
    from unstructured.partition.utils.config import env_config

    assert env_config.STORAGE_ENABLED == False
    assert str(Path.home() / ".cache/unstructured") == env_config.STORAGE_DIR
    assert Path(env_config.STORAGE_TMPDIR).is_dir() == False
    assert tempfile.gettempdir() != env_config.STORAGE_TMPDIR


def test_env_storage_enabled(monkeypatch, setup_tmpdir):
    monkeypatch.setenv("STORAGE_ENABLED", "true")
    from unstructured.partition.utils.config import env_config

    assert env_config.STORAGE_ENABLED == True
    assert str(Path.home() / ".cache/unstructured") == env_config.STORAGE_DIR
    assert Path(env_config.STORAGE_TMPDIR).is_dir() == True
    assert tempfile.gettempdir() == env_config.STORAGE_TMPDIR
