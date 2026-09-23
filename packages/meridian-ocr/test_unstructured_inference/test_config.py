def test_default_config():
    from unstructured_inference.config import inference_config

    assert inference_config.TT_TABLE_CONF == 0.5


def test_env_override(monkeypatch):
    monkeypatch.setenv("TT_TABLE_CONF", 1)
    from unstructured_inference.config import inference_config

    assert inference_config.TT_TABLE_CONF == 1
