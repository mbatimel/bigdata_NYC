#!/usr/bin/env bash
set -euo pipefail

./scripts/trino_query.sh "SHOW SCHEMAS FROM iceberg"

analytics_tables="$(./scripts/trino_query.sh "SHOW TABLES FROM iceberg.analytics")"
printf '%s\n' "${analytics_tables}"

expected_analytics_tables=(
  mart_daily_zone_revenue
  mart_base_monthly_kpi
  mart_top_routes
  mart_hourly_demand
  mart_airport_trips
)
missing_analytics_tables=()

for table_name in "${expected_analytics_tables[@]}"; do
  if [[ "${analytics_tables}" != *"\"${table_name}\""* ]]; then
    missing_analytics_tables+=("${table_name}")
  fi
done

if ((${#missing_analytics_tables[@]})); then
  printf 'Missing expected analytics marts: %s\n' "${missing_analytics_tables[*]}" >&2
  printf 'Run make etl to completion before make smoke. For a memory-constrained Docker setup, use make etl-local.\n' >&2
  exit 1
fi

./scripts/trino_query.sh "SELECT 'daily_zone' AS table_name, count(*) AS rows FROM iceberg.analytics.mart_daily_zone_revenue"
./scripts/trino_query.sh "SELECT 'top_routes' AS table_name, count(*) AS rows FROM iceberg.analytics.mart_top_routes"
