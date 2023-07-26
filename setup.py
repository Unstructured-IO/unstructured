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


setup(
    name="unstructured",
    description="A library that prepares raw documents for downstream ML tasks.",
    long_description=open("README.md", encoding="utf-8").read(),  # noqa: SIM115
    long_description_content_type="text/markdown",
    keywords="NLP PDF HTML CV XML parsing preprocessing",
    url="https://github.com/Unstructured-IO/unstructured",
    python_requires=">=3.7.0",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
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
        "huggingface": load_requirements("requirements/huggingface.in"),
        "local-inference": load_requirements("requirements/local-inference.in"),
        "s3": load_requirements("requirements/ingest-s3.in"),
        "azure": load_requirements("requirements/ingest-azure.in"),
        "discord": load_requirements("requirements/ingest-discord.in"),
        "github": load_requirements("requirements/ingest-github.in"),
        "gitlab": load_requirements("requirements/ingest-gitlab.in"),
        "reddit": load_requirements("requirements/ingest-reddit.in"),
        "slack": load_requirements("requirements/ingest-slack.in"),
        "wikipedia": load_requirements("requirements/ingest-wikipedia.in"),
        "google-drive": load_requirements("requirements/ingest-google-drive.in"),
        "gcs": load_requirements("requirements/ingest-gcs.in"),
        "elasticsearch": load_requirements("requirements/ingest-elasticsearch.in"),
        "dropbox": load_requirements("requirements/ingest-dropbox.in"),
        "onedrive": load_requirements("requirements/ingest-onedrive.in"),
        "outlook": load_requirements("requirements/ingest-outlook.in"),
        "confluence": load_requirements("requirements/ingest-confluence.in"),
    },
    package_dir={"unstructured": "unstructured"},
    package_data={"unstructured": ["nlp/*.txt"]},
)
