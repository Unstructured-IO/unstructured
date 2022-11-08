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
import os

from setuptools import setup, find_packages

from unstructured.__version__ import __version__

cwd = os.path.dirname(os.path.abspath(__file__))

# Read in README.md for our long_description
with open(os.path.join(cwd, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="unstructured",
    description="A library that prepares raw documents for downstream ML tasks.",
    long_description=long_description,
    author="Unstructured Technologies",
    author_email="devops@unstructuredai.io",
    license="Apache-2.0",
    packages=find_packages(),
    version=__version__,
    entry_points={},
    install_requires=[
        "lxml",
        "nltk",
    ],
    extras_require={
        "pdf": ["layoutparser[layoutmodels,tesseract]"],
        "huggingface": ["transformers"],
    },
)
