SELECT *
FROM iceberg.analytics.mart_daily_zone_revenue
ORDER BY gross_revenue DESC
LIMIT 10;

SELECT *
FROM iceberg.analytics.mart_top_routes
ORDER BY trip_count DESC
LIMIT 10;

SELECT pickup_hour, sum(trip_count) AS trips, sum(gross_revenue) AS revenue
FROM iceberg.analytics.mart_hourly_demand
WHERE pickup_borough = 'Manhattan'
GROUP BY pickup_hour
ORDER BY trips DESC;

SELECT dispatching_base_num, trip_count, gross_revenue, avg_revenue_per_trip
FROM iceberg.analytics.mart_base_monthly_kpi
ORDER BY gross_revenue DESC
LIMIT 10;
