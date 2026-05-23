#!/usr/bin/env bash
set -euo pipefail

docker compose exec -T mc sh -lc '
  set -eu
  mc alias set local http://minio:9000 minioadmin minioadmin >/dev/null
  mc mb --ignore-existing local/raw >/dev/null
  mc mb --ignore-existing local/warehouse >/dev/null

  upload_root_parquet_files() {
    uploaded=0
    for source in /project/fhvhv_tripdata_*.parquet; do
      [ -f "$source" ] || continue
      file="$(basename "$source")"
      stem="${file#fhvhv_tripdata_}"
      year="${stem%%-*}"
      month="${stem#*-}"
      month="${month%.parquet}"
      case "${year}:${month}" in
        [0-9][0-9][0-9][0-9]:[0-9][0-9]) ;;
        *)
          echo "Skipping file with unsupported FHVHV name: ${file}" >&2
          continue
          ;;
      esac
      mc cp "$source" "local/raw/nyc_taxi/fhvhv/year=${year}/month=${month}/${file}"
      uploaded=1
    done
    [ "$uploaded" -eq 1 ]
  }

  staged_file="$(find /data/raw/fhvhv -type f -name "fhvhv_tripdata_*.parquet" -print -quit 2>/dev/null || true)"
  if [ -n "$staged_file" ]; then
    echo "Uploading partitioned parquet files from data/raw/fhvhv"
    mc mirror --overwrite /data/raw/fhvhv local/raw/nyc_taxi/fhvhv
  elif upload_root_parquet_files; then
    echo "Uploaded root parquet files from /project"
  else
    echo "No FHVHV parquet files found in data/raw/fhvhv or project root" >&2
    exit 1
  fi

  if [ ! -f /data/raw/zones/taxi_zone_lookup.csv ]; then
    echo "Missing data/raw/zones/taxi_zone_lookup.csv. Run make download to fetch the zone lookup." >&2
    exit 1
  fi
  mc cp /data/raw/zones/taxi_zone_lookup.csv local/raw/nyc_taxi/zones/taxi_zone_lookup.csv
  mc ls --recursive --summarize local/raw/nyc_taxi
'
