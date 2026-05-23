#!/usr/bin/env bash
set -euo pipefail

YEAR="${YEAR:-2024}"
MONTHS="${MONTHS:-01 02 03}"
BASE_URL="${BASE_URL:-https://d37ci6vzurychx.cloudfront.net/trip-data}"
ZONE_URL="${ZONE_URL:-https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv}"

mkdir -p data/raw/fhvhv "data/raw/zones"

for month in ${MONTHS}; do
  target_dir="data/raw/fhvhv/year=${YEAR}/month=${month}"
  target_file="${target_dir}/fhvhv_tripdata_${YEAR}-${month}.parquet"
  root_file="fhvhv_tripdata_${YEAR}-${month}.parquet"
  mkdir -p "${target_dir}"
  if [[ -s "${target_file}" ]]; then
    echo "Using staged raw file ${target_file}"
  elif [[ -s "${root_file}" ]]; then
    echo "Using root raw file ${root_file}; make upload will read it directly"
  else
    echo "Downloading ${target_file}"
    curl --fail --location --continue-at - \
      "${BASE_URL}/fhvhv_tripdata_${YEAR}-${month}.parquet" \
      --output "${target_file}"
  fi
done

if [[ -s data/raw/zones/taxi_zone_lookup.csv ]]; then
  echo "Using staged taxi zone lookup data/raw/zones/taxi_zone_lookup.csv"
else
  echo "Downloading taxi zone lookup"
  curl --fail --location "${ZONE_URL}" --output data/raw/zones/taxi_zone_lookup.csv
fi

du -sh data/raw || true
