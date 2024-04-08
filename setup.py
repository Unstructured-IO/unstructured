"""
setup.py

unstructured - pre-processing tools for unstructured data

Copyright 2022 Unstructured Technologies, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from typing import List, Optional, Union

from setuptools import find_packages, setup

from unstructured.__version__ import __version__


def load_requirements(file_list: Optional[Union[str, List[str]]] = None) -> List[str]:
    if file_list is None:
        file_list = ["requirements/base.in"]
    if isinstance(file_list, str):
        file_list = [file_list]
    requirements: List[str] = []
    for file in file_list:
        with open(file, encoding="utf-8") as f:
            requirements.extend(f.readlines())
    requirements = [
        req for req in requirements if not req.startswith("#") and not req.startswith("-")
    ]
    return requirements


csv_reqs = load_requirements("requirements/extra-csv.in")
doc_reqs = load_requirements("requirements/extra-docx.in")
docx_reqs = load_requirements("requirements/extra-docx.in")
epub_reqs = load_requirements("requirements/extra-epub.in")
image_reqs = load_requirements("requirements/extra-pdf-image.in")
markdown_reqs = load_requirements("requirements/extra-markdown.in")
msg_reqs = load_requirements("requirements/extra-msg.in")
odt_reqs = load_requirements("requirements/extra-odt.in")
org_reqs = load_requirements("requirements/extra-pandoc.in")
pdf_reqs = load_requirements("requirements/extra-pdf-image.in")
ppt_reqs = load_requirements("requirements/extra-pptx.in")
pptx_reqs = load_requirements("requirements/extra-pptx.in")
rtf_reqs = load_requirements("requirements/extra-pandoc.in")
rst_reqs = load_requirements("requirements/extra-pandoc.in")
tsv_reqs = load_requirements("requirements/extra-csv.in")
xlsx_reqs = load_requirements("requirements/extra-xlsx.in")

all_doc_reqs = list(
    set(
        csv_reqs
        + docx_reqs
        + epub_reqs
        + image_reqs
        + markdown_reqs
        + msg_reqs
        + odt_reqs
        + org_reqs
        + pdf_reqs
        + pptx_reqs
        + rtf_reqs
        + rst_reqs
        + tsv_reqs
        + xlsx_reqs,
    ),
)


setup(
    name="unstructured",
    description="A library that prepares raw documents for downstream ML tasks.",
    long_description=open("README.md", encoding="utf-8").read(),  # noqa: SIM115
    long_description_content_type="text/markdown",
    keywords="NLP PDF HTML CV XML parsing preprocessing",
    url="https://github.com/Unstructured-IO/unstructured",
    python_requires=">=3.9.0,<3.12",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    author="Unstructured Technologies",
    author_email="devops@unstructuredai.io",
    license="Apache-2.0",
    packages=find_packages(),
    version=__version__,
    entry_points={
        "console_scripts": ["unstructured-ingest=unstructured.ingest.main:main"],
    },
    install_requires=load_requirements(),
    extras_require={
        # Document specific extra requirements
        "all-docs": all_doc_reqs,
        "csv": csv_reqs,
        "doc": doc_reqs,
        "docx": docx_reqs,
        "epub": epub_reqs,
        "image": image_reqs,
        "md": markdown_reqs,
        "msg": msg_reqs,
        "odt": odt_reqs,
        "org": org_reqs,
        "pdf": pdf_reqs,
        "ppt": ppt_reqs,
        "pptx": pptx_reqs,
        "rtf": rtf_reqs,
        "rst": rst_reqs,
        "tsv": tsv_reqs,
        "xlsx": xlsx_reqs,
        # Extra requirements for data connectors
        "airtable": load_requirements("requirements/ingest/airtable.in"),
        "astra": load_requirements("requirements/ingest/astra.in"),
        "azure": load_requirements("requirements/ingest/azure.in"),
        "azure-cognitive-search": load_requirements(
            "requirements/ingest/azure-cognitive-search.in",
        ),
        "biomed": load_requirements("requirements/ingest/biomed.in"),
        "box": load_requirements("requirements/ingest/box.in"),
        "chroma": load_requirements("requirements/ingest/chroma.in"),
        "clarifai": load_requirements("requirements/ingest/clarifai.in"),
        "confluence": load_requirements("requirements/ingest/confluence.in"),
        "delta-table": load_requirements("requirements/ingest/delta-table.in"),
        "discord": load_requirements("requirements/ingest/discord.in"),
        "dropbox": load_requirements("requirements/ingest/dropbox.in"),
        "elasticsearch": load_requirements("requirements/ingest/elasticsearch.in"),
        "gcs": load_requirements("requirements/ingest/gcs.in"),
        "github": load_requirements("requirements/ingest/github.in"),
        "gitlab": load_requirements("requirements/ingest/gitlab.in"),
        "google-drive": load_requirements("requirements/ingest/google-drive.in"),
        "hubspot": load_requirements("requirements/ingest/hubspot.in"),
        "jira": load_requirements("requirements/ingest/jira.in"),
        "mongodb": load_requirements("requirements/ingest/mongodb.in"),
        "notion": load_requirements("requirements/ingest/notion.in"),
        "onedrive": load_requirements("requirements/ingest/onedrive.in"),
        "opensearch": load_requirements("requirements/ingest/opensearch.in"),
        "outlook": load_requirements("requirements/ingest/outlook.in"),
        "pinecone": load_requirements("requirements/ingest/pinecone.in"),
        "postgres": load_requirements("requirements/ingest/postgres.in"),
        "qdrant": load_requirements("requirements/ingest/qdrant.in"),
        "reddit": load_requirements("requirements/ingest/reddit.in"),
        "s3": load_requirements("requirements/ingest/s3.in"),
        "sharepoint": load_requirements("requirements/ingest/sharepoint.in"),
        "salesforce": load_requirements("requirements/ingest/salesforce.in"),
        "sftp": load_requirements("requirements/ingest/sftp.in"),
        "slack": load_requirements("requirements/ingest/slack.in"),
        "wikipedia": load_requirements("requirements/ingest/wikipedia.in"),
        "weaviate": load_requirements("requirements/ingest/weaviate.in"),
        # Legacy extra requirements
        "huggingface": load_requirements("requirements/huggingface.in"),
        "local-inference": all_doc_reqs,
        "paddleocr": load_requirements("requirements/extra-paddleocr.in"),
        "embed-huggingface": load_requirements("requirements/ingest/embed-huggingface.in"),
        "embed-octoai": load_requirements("requirements/ingest/embed-octoai.in"),
        "embed-vertexai": load_requirements("requirements/ingest/embed-vertexai.in"),
        "openai": load_requirements("requirements/ingest/embed-openai.in"),
        "bedrock": load_requirements("requirements/ingest/embed-aws-bedrock.in"),
        "databricks-volumes": load_requirements("requirements/ingest/databricks-volumes.in"),
    },
    package_dir={"unstructured": "unstructured"},
    package_data={"unstructured": ["nlp/*.txt"]},
)
