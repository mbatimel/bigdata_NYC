import os
import re

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


CATALOG = os.getenv("ICEBERG_CATALOG", "lakehouse")
RAW_FHVHV_PATH = os.getenv(
    "RAW_FHVHV_PATH",
    "s3a://raw/nyc_taxi/fhvhv/year=2024/month=*/*.parquet",
)
RAW_ZONES_PATH = os.getenv(
    "RAW_ZONES_PATH",
    "s3a://raw/nyc_taxi/zones/taxi_zone_lookup.csv",
)


def table(namespace: str, name: str) -> str:
    return f"{CATALOG}.{namespace}.{name}"


def normalize_name(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return normalized.replace("pulocationid", "pu_location_id").replace(
        "dolocationid", "do_location_id"
    )


def normalize_columns(df):
    for col_name in df.columns:
        df = df.withColumnRenamed(col_name, normalize_name(col_name))
    return df


def ensure_column(df, name: str, data_type: str):
    if name in df.columns:
        return df
    return df.withColumn(name, F.lit(None).cast(data_type))


def numeric_zero(col_name: str):
    return F.coalesce(F.col(col_name).cast("double"), F.lit(0.0))


def write_iceberg(df, full_name: str, partition_cols=None):
    writer = (
        df.writeTo(full_name)
        .using("iceberg")
        .tableProperty("format-version", "2")
        .tableProperty("write.format.default", "parquet")
        .tableProperty("write.distribution-mode", "none")
        .tableProperty("write.target-file-size-bytes", "67108864")
        .tableProperty("write.parquet.row-group-size-bytes", "16777216")
    )
    if partition_cols:
        writer = writer.partitionedBy(*partition_cols)
    writer.createOrReplace()


spark = (
    SparkSession.builder.appName("nyc-taxi-iceberg-etl")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)

for namespace in ("raw", "curated", "analytics"):
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {CATALOG}.{namespace}")

raw = normalize_columns(spark.read.parquet(RAW_FHVHV_PATH))

for name, data_type in {
    "airport_fee": "double",
    "base_passenger_fare": "double",
    "bcf": "double",
    "congestion_surcharge": "double",
    "cbd_congestion_fee": "double",
    "driver_pay": "double",
    "sales_tax": "double",
    "tips": "double",
    "tolls": "double",
    "trip_miles": "double",
    "trip_time": "double",
}.items():
    raw = ensure_column(raw, name, data_type)

bronze = (
    raw.withColumn("pickup_datetime", F.col("pickup_datetime").cast("timestamp"))
    .withColumn("dropoff_datetime", F.col("dropoff_datetime").cast("timestamp"))
    .withColumn("pickup_date", F.to_date("pickup_datetime"))
    .withColumn("pickup_month", F.date_format("pickup_datetime", "yyyy-MM"))
    .withColumn("pickup_hour", F.hour("pickup_datetime"))
    .withColumn(
        "gross_revenue",
        numeric_zero("base_passenger_fare")
        + numeric_zero("tolls")
        + numeric_zero("bcf")
        + numeric_zero("sales_tax")
        + numeric_zero("congestion_surcharge")
        + numeric_zero("airport_fee")
        + numeric_zero("tips")
        + numeric_zero("cbd_congestion_fee"),
    )
    .withColumn("trip_minutes", numeric_zero("trip_time") / F.lit(60.0))
    .withColumn("is_airport_trip", numeric_zero("airport_fee") > F.lit(0.0))
)

write_iceberg(bronze, table("raw", "fhvhv_trips"), ["pickup_month"])

zones = normalize_columns(
    spark.read.option("header", True).option("inferSchema", True).csv(RAW_ZONES_PATH)
)
zones = (
    zones.withColumnRenamed("locationid", "location_id")
    .withColumn("location_id", F.col("location_id").cast("int"))
    .select("location_id", "borough", "zone", "service_zone")
)
write_iceberg(zones, table("raw", "taxi_zones"))

pu = zones.select(
    F.col("location_id").alias("pu_location_id"),
    F.col("borough").alias("pickup_borough"),
    F.col("zone").alias("pickup_zone"),
    F.col("service_zone").alias("pickup_service_zone"),
)
do = zones.select(
    F.col("location_id").alias("do_location_id"),
    F.col("borough").alias("dropoff_borough"),
    F.col("zone").alias("dropoff_zone"),
    F.col("service_zone").alias("dropoff_service_zone"),
)

silver = (
    bronze.filter(F.col("pickup_datetime").isNotNull())
    .filter(F.col("dropoff_datetime").isNotNull())
    .filter(F.col("pickup_date").isNotNull())
    .filter(F.col("trip_miles") >= 0)
    .filter(F.col("gross_revenue") >= 0)
    .join(pu, "pu_location_id", "left")
    .join(do, "do_location_id", "left")
)

write_iceberg(silver, table("curated", "fhvhv_trips_enriched"), ["pickup_month"])

daily_zone = (
    silver.groupBy("pickup_date", "pickup_borough", "pickup_zone")
    .agg(
        F.count("*").alias("trip_count"),
        F.sum("gross_revenue").alias("gross_revenue"),
        F.avg("gross_revenue").alias("avg_revenue_per_trip"),
        F.avg("trip_miles").alias("avg_trip_miles"),
        F.avg("trip_minutes").alias("avg_trip_minutes"),
        F.sum("tips").alias("tips_total"),
        F.sum("driver_pay").alias("driver_pay_total"),
    )
    .withColumn(
        "revenue_per_driver_pay",
        F.when(
            F.col("driver_pay_total") != 0,
            F.col("gross_revenue") / F.col("driver_pay_total"),
        ),
    )
)
write_iceberg(daily_zone, table("analytics", "mart_daily_zone_revenue"), ["pickup_date"])

base_monthly = silver.groupBy("pickup_month", "dispatching_base_num").agg(
    F.count("*").alias("trip_count"),
    F.countDistinct("pu_location_id").alias("pickup_zone_count"),
    F.sum("gross_revenue").alias("gross_revenue"),
    F.sum("driver_pay").alias("driver_pay_total"),
    F.avg("gross_revenue").alias("avg_revenue_per_trip"),
    F.avg("driver_pay").alias("avg_driver_pay_per_trip"),
    F.avg("trip_miles").alias("avg_trip_miles"),
    F.avg("trip_minutes").alias("avg_trip_minutes"),
)
write_iceberg(base_monthly, table("analytics", "mart_base_monthly_kpi"), ["pickup_month"])

top_routes = silver.groupBy(
    "pickup_borough", "pickup_zone", "dropoff_borough", "dropoff_zone"
).agg(
    F.count("*").alias("trip_count"),
    F.sum("gross_revenue").alias("gross_revenue"),
    F.avg("trip_miles").alias("avg_trip_miles"),
    F.avg("trip_minutes").alias("avg_trip_minutes"),
)
write_iceberg(top_routes, table("analytics", "mart_top_routes"))

hourly_demand = silver.groupBy("pickup_hour", "pickup_borough").agg(
    F.count("*").alias("trip_count"),
    F.sum("gross_revenue").alias("gross_revenue"),
    F.avg("gross_revenue").alias("avg_revenue_per_trip"),
)
write_iceberg(hourly_demand, table("analytics", "mart_hourly_demand"))

airport_trips = silver.filter(F.col("is_airport_trip")).groupBy(
    "pickup_date", "pickup_borough", "pickup_zone"
).agg(
    F.count("*").alias("airport_trip_count"),
    F.sum("gross_revenue").alias("gross_revenue"),
    F.avg("airport_fee").alias("avg_airport_fee"),
    F.avg("trip_miles").alias("avg_trip_miles"),
)
write_iceberg(airport_trips, table("analytics", "mart_airport_trips"), ["pickup_date"])

spark.stop()
