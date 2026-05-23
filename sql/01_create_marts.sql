CREATE SCHEMA IF NOT EXISTS iceberg.analytics
WITH (location = 's3://warehouse/analytics');

CREATE OR REPLACE TABLE iceberg.analytics.mart_revenue_by_borough AS
SELECT
    pickup_borough,
    sum(trip_count) AS trip_count,
    sum(gross_revenue) AS gross_revenue,
    sum(gross_revenue) / nullif(sum(trip_count), 0) AS avg_revenue_per_trip
FROM iceberg.analytics.mart_daily_zone_revenue
GROUP BY pickup_borough;

CREATE OR REPLACE TABLE iceberg.analytics.mart_route_rank AS
SELECT
    pickup_borough,
    pickup_zone,
    dropoff_borough,
    dropoff_zone,
    trip_count,
    gross_revenue,
    row_number() OVER (ORDER BY trip_count DESC) AS route_rank
FROM iceberg.analytics.mart_top_routes;
