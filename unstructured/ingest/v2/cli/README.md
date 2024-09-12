# Ingest CLI
This package helps map user input via a cli to the underlying ingest code to run a small ETL pipeline.

## Design Reference
[cli.py](./cli.py) is the main entrypoint to run the cli itself. The key points for this is the interaction between all
source and destination connectors.

To manually run the cli:
```shell
PYTHONPATH=. python unstructured/ingest/v2/main.py --help
```

The `main.py` file simply wraps the generated Click command created in `cli.py`.

### Source Commands
All source commands are added as sub commands to the parent ingest Click group. This allows each command to map to
different connectors with shared and unique parameters.

### Destination Commands
All destination commands are added as sub commands to each parent source command. This allows each invocation of the source
sub command to display all possible destination subcommands. The code un [utils.py](./utils.py) helps structure the
generated text from the Click library to be more intuitive on this approach (i.e. list sub commands as  `Destinations`).

### Configs
The configs in [configs/](./configs) and connector specific ones in [cmds/](./cmds) help surface all user parameters that
are needed to marshall the input dictionary from Click into all the respective configs needed to create a full pipeline run.
Because click returns a flat dictionary of user inputs, the `extract_config` method in `utils.py` helps deserialize this dictionary
into dataclasses that have nested fields (such as access configs).
