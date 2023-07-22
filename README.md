<h3 align="center">
  <img
    src="https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/img/unstructured_logo.png"
    height="200"
  >
</h3>

<div align="center">

  <a href="https://github.com/Unstructured-IO/unstructured/blob/main/LICENSE.md">![https://pypi.python.org/pypi/unstructured/](https://img.shields.io/pypi/l/unstructured.svg)</a>
  <a href="https://pypi.python.org/pypi/unstructured/">![https://pypi.python.org/pypi/unstructured/](https://img.shields.io/pypi/pyversions/unstructured.svg)</a>
  <a href="https://GitHub.com/unstructured-io/unstructured/graphs/contributors">![https://GitHub.com/unstructured-io/unstructured.js/graphs/contributors](https://img.shields.io/github/contributors/unstructured-io/unstructured)</a>
  <a href="https://github.com/Unstructured-IO/unstructured/blob/main/CODE_OF_CONDUCT.md">![code_of_conduct.md](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg) </a>
  <a href="https://GitHub.com/unstructured-io/unstructured/releases">![https://GitHub.com/unstructured-io/unstructured.js/releases](https://img.shields.io/github/release/unstructured-io/unstructured)</a>
  <a href="https://pypi.python.org/pypi/unstructured/">![https://github.com/Naereen/badges/](https://badgen.net/badge/Open%20Source%20%3F/Yes%21/blue?icon=github)</a>
  [![Downloads](https://static.pepy.tech/badge/unstructured)](https://pepy.tech/project/unstructured)
  [![Downloads](https://static.pepy.tech/badge/unstructured/month)](https://pepy.tech/project/unstructured)

</div>

<div>
  <p align="center">
  <a
  href="https://join.slack.com/t/unstructuredw-kbe4326/shared_invite/zt-1x7cgo0pg-PTptXWylzPQF9xZolzCnwQ">
    <img src="https://img.shields.io/badge/JOIN US ON SLACK-4A154B?style=for-the-badge&logo=slack&logoColor=white" />
  </a>
  <a href="https://www.linkedin.com/company/unstructuredio/">
    <img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" />
  </a>
</div>

<h3 align="center">
  <p>API Announcement!</p>
</h3>

We are thrilled to announce our newly launched [Unstructured API](https://unstructured-io.github.io/unstructured/api.html). While access to the hosted Unstructured API will remain free, API Keys are required to make requests. To prevent disruption, get yours [here](https://unstructured.io/#get-api-key) now and start using it today! Check out the [readme](https://github.com/Unstructured-IO/unstructured-api#--) here to get started making API calls.</p>

#### :rocket: Beta Feature: Chipper Model

We are releasing the beta version of our Chipper model to deliver superior performance when processing high-resolution, complex documents. To start using the Chipper model in your API request, you can utilize the `hi_res` strategy. Please refer to the documentation [here](https://unstructured-io.github.io/unstructured/api.html#strategies).

As the Chipper model is in beta version, we welcome feedback and suggestions. For those interested in testing the Chipper model, we encourage you to connect with us on [Slack community](https://join.slack.com/t/unstructuredw-kbe4326/shared_invite/zt-1x7cgo0pg-PTptXWylzPQF9xZolzCnwQ).

<h3 align="center">
  <p>Open-Source Pre-Processing Tools for Unstructured Data</p>
</h3>

The `unstructured` library provides open-source components for pre-processing text documents
such as **PDFs**, **HTML** and **Word** Documents. These components are packaged as *bricks* 🧱, which provide
users the building blocks they need to build pipelines targeted at the documents they care
about. Bricks in the library fall into three categories:

- :jigsaw: ***Partitioning bricks*** that break raw documents down into standard, structured
  elements.
- :broom: ***Cleaning bricks*** that remove unwanted text from documents, such as boilerplate and
  sentence
  fragments.
- :performing_arts: ***Staging bricks*** that format data for downstream tasks, such as ML inference
  and data labeling.

Unstructured also provides the capabilities from `unstructured` as an API.
Checkout the [`unstructured-api` repo](https://github.com/Unstructured-IO/unstructured-api)
to get started making API calls.
You’ll also find instructions there about how to host your own version of the API.

## :bookmark: Documentation
This README gives an overview of how to install, use and develop the library.
For more comprehensive documentation, visit https://unstructured-io.github.io/unstructured/ .

## :eight_pointed_black_star: Quick Start

There are two ways to use the library: 1) run a container or 2) install it

### Using the library in a container

The following instructions are intended to help you get up and running using Docker to interact with `unstructured`.
See [here](https://docs.docker.com/get-docker/) if you don't already have docker installed on your machine.

NOTE: we build multi-platform images to support both x86_64 and Apple silicon hardware. `docker pull` should download the corresponding image for your architecture, but you can specify with `--platform` (e.g. `--platform linux/amd64`) if needed.

We build Docker images for all pushes to `main`. We tag each image with the corresponding short commit hash (e.g. `fbc7a69`) and the application version (e.g. `0.5.5-dev1`). We also tag the most recent image with `latest`. To leverage this, `docker pull` from our image repository.

```bash
docker pull quay.io/unstructured-io/unstructured:latest
```

Once pulled, you can create a container from this image and shell to it.

```bash
# create the container
docker run -dt --name unstructured quay.io/unstructured-io/unstructured:latest

# this will drop you into a bash shell where the Docker image is running
docker exec -it unstructured bash
```

You can also build your own Docker image.

If you only plan on parsing one type of data you can speed up building the image by commenting out some
of the packages/requirements necessary for other data types. See Dockerfile to know which lines are necessary
for your use case.

```bash
make docker-build

# this will drop you into a bash shell where the Docker image is running
make docker-start-bash
```

Once in the running container, you can try things out directly in Python interpreter's interactive mode.
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

- Install the Python SDK with `pip install "unstructured[local-inference]"`
		- If you do not need to process PDFs or images, you can run `pip install unstructured`
- Install the following system dependencies if they are not already available on your system.
  Depending on what document types you're parsing, you may not need all of these.
    - `libmagic-dev` (filetype detection)
    - `poppler-utils` (images and PDFs)
    - `tesseract-ocr` (images and PDFs)
    - `libreoffice` (MS Office docs)
    - `pandoc` (EPUBs, RTFs and Open Office docs)

- For suggestions on how to install on Windows and to learn about dependencies for other features, see the
  installation documentation [here](https://unstructured-io.github.io/unstructured/installing.html).

At this point, you should be able to run the following code:

```python
from unstructured.partition.auto import partition

elements = partition(filename="example-docs/eml/fake-email.eml")
print("\n\n".join([str(el) for el in elements]))
```

The following table shows the document types the `unstructured` library currently supports.
`partition` will recognize each of these document types and route the document to the
appropriate partitioning function. If you already know your document type, you can use
the partitioning function listed in the table directly.
See our [documentation page](https://unstructured-io.github.io/unstructured/) for more details
about the library.

| Document Type | Partition Function | Strategies | Table Support | Options |
| --- | --- | --- | --- | --- |
| CSV Files (`.csv`) | `partition_csv` | N/A | Yes | None |
| E-mails (`.eml`) | `partition_eml` | N/A | No | Encoding; Max Partition; Process Attachments |
| E-mails (`.msg`) | `partition_msg` | N/A | No | Encoding; Max Partition; Process Attachments |
| EPubs (`.epub`) | `partition_epub` | N/A | Yes | Include Page Breaks |
| Excel Documents (`.xlsx`/`.xls`) | `partition_xlsx` | N/A | Yes | None |
| HTML Pages (`.html`) | `partition_html` | N/A | No | Encoding; Include Page Breaks |
| Images (`.png`/`.jpg`) | `partition_image` | `"auto"`, `"hi_res"`, `"ocr_only"` | Yes | Encoding; Include Page Breaks; Infer Table Structure; OCR Languages, Strategy |
| Markdown (`.md`) | `partitin_md` | N/A | Yes | Include Page Breaks |
| Org Mode (`.org`) | `partition_org` | N/A | Yes | Include Page Breaks |
| Open Office Documents (`.odt`) | `partition_odt` | N/A | Yes | None |
| PDFs (`.pdf`) | `partition_pdf` | `"auto"`, `"fast"`, `"hi_res"`, `"ocr_only"` | Yes | Encoding; Include Page Breaks; Infer Table Structure; Max Partition; OCR Languages, Strategy |
| Plain Text (`.txt`) | `partition_text` | N/A | No | Encoding; Max Partition; Paragraph Grouper |
| Power Points (`.ppt`) | `partition_ppt` | N/A | Yes | Include Page Breaks |
| Power Points (`.pptx`) | `partition_pptx` | N/A | Yes | Include Page Breaks |
| ReStructured Text (`.rst`) | `partition_rst` | N/A | Yes | Include Page Breaks |
| Rich Text Files (`.rtf`) | `partition_rtf` | N/A | Yes | Include Page Breaks |
| TSV Files (`.tsv`) | `partition_tsv` | N/A | Yes | None |
| Word Documents (`.doc`) | `partition_doc` | N/A | Yes | Include Page Breaks |
| Word Documents (`.docx`) | `partition_docx` | N/A | Yes | Include Page Breaks |
| XML Documents (`.xml`) | `partition_xml` | N/A | No | Encoding; Max Partition; XML Keep Tags |



## :coffee: Installation Instructions for Local Development

The following instructions are intended to help you get up and running with `unstructured`
locally if you are planning to contribute to the project.

* Using `pyenv` to manage virtualenv's is recommended but not necessary
	* Mac install instructions. See [here](https://github.com/Unstructured-IO/community#mac--homebrew) for more detailed instructions.
		* `brew install pyenv-virtualenv`
	  * `pyenv install 3.8.17`
  * Linux instructions are available [here](https://github.com/Unstructured-IO/community#linux).

* Create a virtualenv to work in and activate it, e.g. for one named `unstructured`:

	`pyenv  virtualenv 3.8.17 unstructured` <br />
	`pyenv activate unstructured`

* Run `make install`

* Optional:
  * To install models and dependencies for processing images and PDFs locally, run `make install-local-inference`.
  * For processing image files, `tesseract` is required. See [here](https://tesseract-ocr.github.io/tessdoc/Installation.html) for installation instructions.
  * For processing PDF files, `tesseract` and `poppler` are required. The [pdf2image docs](https://pdf2image.readthedocs.io/en/latest/installation.html) have instructions on installing `poppler` across various platforms.

Additionally, if you're planning to contribute to `unstructured`, we provide you an optional `pre-commit` configuration
file to ensure your code matches the formatting and linting standards used in `unstructured`.
If you'd prefer not having code changes auto-tidied before every commit, you can use  `make check` to see
whether any linting or formatting changes should be applied, and `make tidy` to apply them.

If using the optional `pre-commit`, you'll just need to install the hooks with `pre-commit install` since the
`pre-commit` package is installed as part of `make install` mentioned above. Finally, if you decided to use `pre-commit`
you can also uninstall the hooks with `pre-commit uninstall`.

## :clap: Quick Tour

You can run this [Colab notebook](https://colab.research.google.com/drive/1U8VCjY2-x8c6y5TYMbSFtQGlQVFHCVIW) to run the examples below.

The following examples show how to get started with the `unstructured` library.
You can parse over a dozen document types with one line of code!
<br></br>
See our [documentation page](https://unstructured-io.github.io/unstructured) for a full description
of the features in the library.

### Document Parsing

The easiest way to parse a document in unstructured is to use the `partition` brick. If you
use `partition` brick, `unstructured` will detect the file type and route it to the appropriate
file-specific partitioning brick.
If you are using the `partition` brick, you may need to install additional parameters via `pip install unstructured[local-inference]`. Ensure you first install `libmagic` using the
instructions outlined [here](https://unstructured-io.github.io/unstructured/installing.html#filetype-detection)
`partition` will always apply the default arguments. If you need
advanced features, use a document-specific brick.
See the table above for a full list of document types supported in the library.

```python
from unstructured.partition.auto import partition

elements = partition("example-docs/layout-parser-paper.pdf")
```

Run `print("\n\n".join([str(el) for el in elements]))` to get a string representation of the
output, which looks like:

```

LayoutParser : A Uniﬁed Toolkit for Deep Learning Based Document Image Analysis

Zejiang Shen 1 ( (cid:0) ), Ruochen Zhang 2 , Melissa Dell 3 , Benjamin Charles Germain Lee 4 , Jacob Carlson 3 , and
Weining Li 5

Abstract. Recent advances in document image analysis (DIA) have been primarily driven by the application of neural
networks. Ideally, research outcomes could be easily deployed in production and extended for further investigation.
However, various factors like loosely organized codebases and sophisticated model conﬁgurations complicate the easy
reuse of im- portant innovations by a wide audience. Though there have been on-going eﬀorts to improve reusability and
simplify deep learning (DL) model development in disciplines like natural language processing and computer vision, none
of them are optimized for challenges in the domain of DIA. This represents a major gap in the existing toolkit, as DIA
is central to academic research across a wide range of disciplines in the social sciences and humanities. This paper
introduces LayoutParser , an open-source library for streamlining the usage of DL in DIA research and applica- tions.
The core LayoutParser library comes with a set of simple and intuitive interfaces for applying and customizing DL models
for layout de- tection, character recognition, and many other document processing tasks. To promote extensibility,
LayoutParser also incorporates a community platform for sharing both pre-trained models and full document digiti- zation
pipelines. We demonstrate that LayoutParser is helpful for both lightweight and large-scale digitization pipelines in
real-word use cases. The library is publicly available at https://layout-parser.github.io

Keywords: Document Image Analysis · Deep Learning · Layout Analysis · Character Recognition · Open Source library ·
Toolkit.

Introduction

Deep Learning(DL)-based approaches are the state-of-the-art for a wide range of document image analysis (DIA) tasks
including document image classiﬁcation [11,
```

See the [partitioning](https://unstructured-io.github.io/unstructured/bricks.html#partitioning)
section in our documentation for a full list of options and instructions on how to use
file-specific partitioning functions.

## :guardsman: Security Policy

See our [security policy](https://github.com/Unstructured-IO/unstructured/security/policy) for
information on how to report security vulnerabilities.

## :books: Learn more

| Section | Description |
|-|-|
| [Company Website](https://unstructured.io) | Unstructured.io product and company info |
| [Documentation](https://unstructured-io.github.io/unstructured) | Full API documentation |
| [Batch Processing](Ingest.md) | Ingesting batches of documents through Unstructured |
