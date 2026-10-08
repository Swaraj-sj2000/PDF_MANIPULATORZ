#!/usr/bin/env bash
set -euo pipefail

image_id="$(docker build --target build -q .)"
container_id="$(docker create "$image_id")"
mkdir -p dist
docker cp "$container_id:/artifact/." dist/
docker rm "$container_id" >/dev/null
ls -lh dist/*.deb
