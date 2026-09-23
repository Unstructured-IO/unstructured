## :eight_pointed_black_star: Quick Start

There are several ways to use the `unstructured` library:
* [Run the library in a container](#run-the-library-in-a-container) or
* Install the library
    1. [Install from PyPI](#installing-the-library)
    2. [Install for local development](#installation-instructions-for-local-development)
* For installation with `conda` on Windows system, please refer to the [documentation](https://unstructured-io.github.io/unstructured/installing.html#installation-with-conda-on-windows)

### Run the library in a container

The following instructions are intended to help you get up and running using Docker to interact with `unstructured`.
See [here](https://docs.docker.com/get-docker/) if you don't already have docker installed on your machine.

NOTE: we build multi-platform images to support both x86_64 and Apple silicon hardware. `docker pull` should download the corresponding image for your architecture, but you can specify with `--platform` (e.g. `--platform linux/amd64`) if needed.

We build Docker images for all pushes to `main`. We tag each image with the corresponding short commit hash (e.g. `fbc7a69`) and the application version (e.g. `0.5.5-dev1`). We also tag the most recent image with `latest`. To leverage this, `docker pull` from our image repository.

```bash
docker pull downloads.unstructured.io/unstructured-io/unstructured:latest
```

Once pulled, you can create a container from this image and shell to it.

```bash
# create the container
docker run -dt --name unstructured downloads.unstructured.io/unstructured-io/unstructured:latest

# this will drop you into a bash shell where the Docker image is running
docker exec -it unstructured bash
```

You can also build your own Docker image. Note that the base image is `wolfi-base`, which is
updated regularly. If you are building the image locally, it is possible `docker-build` could
fail due to upstream changes in `wolfi-base`.

If you only plan on parsing one type of data you can speed up building the image by commenting out some
of the packages/requirements necessary for other data types. See Dockerfile to know which lines are necessary
for your use case.

```bash
make docker-build

# this will drop you into a bash shell where the Docker image is running
make docker-start-bash
```

Once in the running container, you can try things directly in Python interpreter's interactive mode.
```bash
# this will drop you into a python console so you can run the below partition functions
python3

>>> from unstructured.partition.pdf import partition_pdf
>>> elements = partition_pdf(filename="example-docs/layout-parser-paper-fast.pdf")

>>> from unstructured.partition.text import partition_text
>>> elements = partition_text(filename="example-docs/fake-text.txt")
```

### Installing the library
Use the following instructions to get up and running with `unstructured` and test your
installation.

- Install the Python SDK to support all document types with `pip install "unstructured[all-docs]"`
  - For plain text files, HTML, XML, JSON and Emails that do not require any extra dependencies, you can run `pip install unstructured`
  - To process other doc types, you can install the extras required for those documents, such as `pip install "unstructured[docx,pptx]"`
- Install the following system dependencies if they are not already available on your system.
  Depending on what document types you're parsing, you may not need all of these.
    - `libmagic-dev` (filetype detection)
    - `poppler-utils` (images and PDFs)
    - `tesseract-ocr` (images and PDFs, install `tesseract-lang` for additional language support)
    - `libreoffice` (MS Office docs)
    - `pandoc` is bundled automatically via the `pypandoc-binary` Python package (no system install needed)

- For suggestions on how to install on the Windows and to learn about dependencies for other features, see the
  installation documentation [here](https://unstructured-io.github.io/unstructured/installing.html).

At this point, you should be able to run the following code:

```python
from unstructured.partition.auto import partition

elements = partition(filename="example-docs/eml/fake-email.eml")
print("\n\n".join([str(el) for el in elements]))
```

### Installation Instructions for Local Development

The following instructions are intended to help you get up and running with `unstructured`
locally if you are planning to contribute to the project.

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. Install it first:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install all dependencies (base, extras, dev, test, and lint groups):

```bash
make install
```

This runs `uv sync --locked --all-extras --all-groups`, which creates a virtual environment
and installs everything in one step. No need to manually create or activate a virtualenv.

To install only specific document-type extras:

```bash
uv sync --extra pdf
uv sync --extra csv --extra docx
```

To update the lock file after changing dependencies in `pyproject.toml`:

```bash
make lock
```

* Optional:
  * To install extras for processing images and PDFs locally, run `uv sync --extra pdf --extra image`.
  * For processing image files, `tesseract` is required. See [here](https://tesseract-ocr.github.io/tessdoc/Installation.html) for installation instructions.
  * For processing PDF files, `tesseract` and `poppler` are required. The [pdf2image docs](https://pdf2image.readthedocs.io/en/latest/installation.html) have instructions on installing `poppler` across various platforms.

Additionally, if you're planning to contribute to `unstructured`, we provide you an optional `pre-commit` configuration
file to ensure your code matches the formatting and linting standards used in `unstructured`.
If you'd prefer not to have code changes auto-tidied before every commit, you can use  `make check` to see
whether any linting or formatting changes should be applied, and `make tidy` to apply them.

If using the optional `pre-commit`, you'll just need to install the hooks with `pre-commit install` since the
`pre-commit` package is installed as part of `make install` mentioned above. Finally, if you decided to use `pre-commit`
you can also uninstall the hooks with `pre-commit uninstall`.

In addition to develop in your local OS we also provide a helper to use docker providing a development environment:

```bash
make docker-start-dev
```

This starts a docker container with your local repo mounted to `/mnt/local_unstructured`. This docker image allows you to develop without worrying about your OS's compatibility with the repo and its dependencies.
