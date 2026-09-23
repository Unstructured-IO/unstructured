import os
import tempfile
from pathlib import Path

import pytest


def test_default_config():
    from meridian_partition.partition.utils.config import env_config

    assert env_config.IMAGE_CROP_PAD == 0


def test_get_tempdir_without_getpgid(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Windows has no os.getpgid; the process temp dir must still resolve."""
    import meridian_partition.partition.utils.config as config_mod

    monkeypatch.delattr(config_mod.os, "getpgid", raising=False)
    config_mod.get_tempdir.cache_clear()
    try:
        tempdir = Path(config_mod.get_tempdir(str(tmp_path)))
        assert tempdir == tmp_path / "tmp" / str(os.getpid())
    finally:
        config_mod.get_tempdir.cache_clear()


def test_env_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IMAGE_CROP_PAD", str(1))
    from meridian_partition.partition.utils.config import env_config

    assert env_config.IMAGE_CROP_PAD == 1


def test_global_working_dir_defaults_to_the_user_cache(monkeypatch: pytest.MonkeyPatch):
    """The default location, asserted with the feature disabled so nothing is created."""
    monkeypatch.delenv("GLOBAL_WORKING_DIR", raising=False)
    monkeypatch.setenv("GLOBAL_WORKING_DIR_ENABLED", "false")
    from meridian_partition.partition.utils.config import env_config

    assert str(Path.home() / ".cache/meridian_partition") == env_config.GLOBAL_WORKING_DIR


def test_env_storage_disabled(monkeypatch: pytest.MonkeyPatch, isolated_global_working_dir: Path):
    monkeypatch.setenv("GLOBAL_WORKING_DIR_ENABLED", "false")
    from meridian_partition.partition.utils.config import env_config

    assert not env_config.GLOBAL_WORKING_DIR_ENABLED
    assert str(isolated_global_working_dir) == env_config.GLOBAL_WORKING_DIR
    assert not Path(env_config.GLOBAL_WORKING_PROCESS_DIR).is_dir()
    assert tempfile.gettempdir() != env_config.GLOBAL_WORKING_PROCESS_DIR


def test_env_storage_enabled(monkeypatch: pytest.MonkeyPatch, isolated_global_working_dir: Path):
    monkeypatch.setenv("GLOBAL_WORKING_DIR_ENABLED", "true")
    from meridian_partition.partition.utils.config import env_config

    assert env_config.GLOBAL_WORKING_DIR_ENABLED
    assert str(isolated_global_working_dir) == env_config.GLOBAL_WORKING_DIR

    process_dir = Path(env_config.GLOBAL_WORKING_PROCESS_DIR)
    assert process_dir.is_dir()
    assert tempfile.gettempdir() == str(process_dir)
    # -- the dir this test creates must be its own, not the pgid-keyed one every worker shares --
    assert isolated_global_working_dir in process_dir.parents
