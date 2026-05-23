#!/usr/bin/env bash
set -euo pipefail

SPARK_MASTER="${SPARK_MASTER:-spark://spark-iceberg:7077}"

docker compose exec -T spark spark-submit \
  --master "${SPARK_MASTER}" \
  /home/iceberg/jobs/nyc_taxi_iceberg_etl.py
