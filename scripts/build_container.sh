#!/usr/bin/env bash
set -euo pipefail

docker build --target runtime -t manual-notes-compiler:local .
