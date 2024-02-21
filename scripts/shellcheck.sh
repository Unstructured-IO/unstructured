#!/usr/bin/env bash

find . -name "*.sh" -exec shellcheck {} +
