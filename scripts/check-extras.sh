#!/usr/bin/env bash

extras=$(python -c 'from importlib.metadata import metadata; print("\n".join(metadata("unstructured").json["provides_extra"]))')
pip install .
for e in $extras; do
  pip install ".[$e]"
done
