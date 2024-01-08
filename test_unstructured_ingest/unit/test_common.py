from unstructured.ingest.cli.common import options_redactions


def test_options_redactions():
    given_options = {
        "uri": "mongodb+srv://myDatabaseUser:D1fficultP%40ssw0rd@mongodb0.example.com/"
        "?authSource=admin&replicaSet=myRepl"
    }

    when_options = options_redactions(options=given_options)

    assert given_options["uri"] != when_options["uri"]
    assert (
        when_options["uri"] == "mongodb+srv://myDatabaseUser:***REDACTED***@mongodb0.example.com/"
        "?authSource=admin&replicaSet=myRepl"
    )
