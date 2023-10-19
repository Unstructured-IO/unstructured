def test_default_config():
    from unstructured.partition.utils.config import env_config

    assert env_config.IMAGE_CROP_PAD == 12


def test_env_override(monkeypatch):
    monkeypatch.setenv("IMAGE_CROP_PAD", 1)
    from unstructured.partition.utils.config import env_config

    assert env_config.IMAGE_CROP_PAD == 1
