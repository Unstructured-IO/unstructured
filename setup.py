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
from setuptools import find_packages, setup

from unstructured.__version__ import __version__

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
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    author="Unstructured Technologies",
    author_email="devops@unstructuredai.io",
    license="Apache-2.0",
    packages=find_packages(),
    version=__version__,
    entry_points={
        'console_scripts': ['unstructured-ingest=unstructured.ingest.main:main'],
    },
    install_requires=[
        "argilla",
        "lxml",
        "nltk",
        "openpyxl",
        "pandas",
        "pillow",
        "python-docx",
        "python-pptx",
        "python-magic",
        "markdown",
        "requests",
        # NOTE(robinson) - The following dependencies are pinned
        # to address security scans
        "certifi>=2022.12.07",
    ],
    extras_require={
        "huggingface": [
            "langdetect",
            "sacremoses",
            "sentencepiece",
            "torch",
            "transformers",
        ],
        "local-inference": [
            # NOTE(robinson) - Upper bound is temporary due to a multithreading issue
            "unstructured-inference>=0.2.4,<0.2.8",
        ],
        "s3": ["boto3"],
        "github": [
            # NOTE - pygithub at 1.58.0 fails due to https://github.com/PyGithub/PyGithub/issues/2436
            # In the future, we can update this to pygithub>1.58.0
            "pygithub==1.57.0",
        ],
        "reddit": ["praw"],
        "wikipedia": ["wikipedia"],
    },
    package_dir={"unstructured": "unstructured"},
    package_data={"unstructured": ["nlp/*.txt"]},
)
