# Meridian

Monorepo for the Meridian document-processing libraries.

| Package | Directory | Description |
|-|-|-|
| `meridian_partition` | [`packages/meridian-partition`](packages/meridian-partition) | Partitions documents (PDF, HTML, Office, email, images, ...) into structured elements. |
| `meridian_ocr` | [`packages/meridian-ocr`](packages/meridian-ocr) | Layout detection, table structure recognition, and PDF rendering models used by the `hi_res` strategy of `meridian_partition`. Port of `unstructured-inference` 1.6.13. |

## Development

The repository is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/): all packages share
one lockfile (`uv.lock`) and one virtual environment at the repository root.

```bash
make install   # uv sync --locked --all-packages --all-extras --all-groups
make test      # run the test suites of all packages
make check     # lint and version checks for all packages
make tidy      # auto-format all packages
```

Each package has its own `Makefile` for package-scoped tasks. Run them from the package directory or with
`make -C`, for example `make -C packages/meridian-partition test-extra-pdf-image`.

Package tests resolve their fixtures relative to the package directory, so run `pytest` from inside the package
(the package `Makefile` targets already do).

The layout and table models used by `hi_res` partitioning are downloaded from private repositories in the
`Anacreonresearch` Hugging Face organization, so tests, CI and Docker builds need `HF_TOKEN` set to a token
with read access to it.

The Docker image is built from the repository root with `make docker-build`.
