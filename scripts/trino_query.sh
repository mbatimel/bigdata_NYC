#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 '<SQL>'" >&2
  exit 1
fi

docker compose exec -T trino trino \
  --server http://trino:8080 \
  --catalog iceberg \
  --schema analytics \
  --execute "$*"
