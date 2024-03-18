from unstructured.ingest.cli.common import options_redactions


def test_options_redactions():
    """There are no longer any redactions via this method. But may be added in the future."""
    given_options = {"uri": "http://uri.example.com/" "?authSource=admin&replicaSet=myRepl"}

    when_options = options_redactions(options=given_options)

    assert given_options["uri"] == when_options["uri"]
    assert when_options["uri"] == "http://uri.example.com/?authSource=admin&replicaSet=myRepl"
