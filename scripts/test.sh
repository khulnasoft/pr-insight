#!/usr/bin/env bash

set -e
set -x

export PYTHONPATH=./docs
coverage run -m pytest tests ${@}
