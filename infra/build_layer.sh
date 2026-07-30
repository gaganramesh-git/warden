#!/usr/bin/env bash
# Build the Lambda deps layer (cryptography). Run before `cdk deploy`.
# Produces infra/layers/python/... which the stack picks up automatically.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf layers/python && mkdir -p layers/python
# Target the Lambda runtime exactly (linux/x86_64, CPython 3.12) so every wheel —
# including non-abi3 ones like cffi — matches what the function will run on.
pip3 install \
  --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 \
  --only-binary=:all: --target layers/python \
  "cryptography>=42"
echo "layer built at infra/layers/python"
