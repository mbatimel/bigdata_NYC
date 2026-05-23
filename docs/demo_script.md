# Demo script

1. Show Docker services:

```bash
docker compose ps
```

2. Show raw data in MinIO:

```bash
docker compose exec -T mc mc ls --recursive --summarize local/raw/nyc_taxi
```

Expected: 4 objects, 1.3 GiB.

3. Show Iceberg tables from Trino:

```bash
./scripts/trino_query.sh "SHOW TABLES FROM iceberg.analytics"
```

4. Show a mart:

```bash
./scripts/trino_query.sh "SELECT * FROM iceberg.analytics.mart_top_routes ORDER BY trip_count DESC LIMIT 10"
```

Expected top route examples:

- Brooklyn / East New York -> Brooklyn / East New York
- Queens / JFK Airport -> Outside of NYC
- Brooklyn / Borough Park -> Brooklyn / Borough Park

5. Show row counts:

```bash
./scripts/trino_query.sh "SELECT 'raw.fhvhv_trips' AS table_name, count(*) AS rows FROM iceberg.raw.fhvhv_trips UNION ALL SELECT 'curated.fhvhv_trips_enriched', count(*) FROM iceberg.curated.fhvhv_trips_enriched UNION ALL SELECT 'mart_top_routes', count(*) FROM iceberg.analytics.mart_top_routes"
```

Expected: 60,303,866 raw trips, 60,301,548 curated trips, 62,093 top routes.

6. Open assistant at http://localhost:8501 and ask:

- Покажи топ-10 маршрутов по количеству поездок.
- Какая зона посадки дала максимальную выручку?
- В какие часы самый высокий спрос в Manhattan?
- Сравни базы по средней выручке на поездку.

7. Explain quality improvement:

- enrich `assistant/semantic_layer.yaml` with synonyms and business definitions;
- add verified examples to `eval/questions.yaml`;
- run `eval/llm_judge.py` after prompt changes;
- log generated SQL and failed questions;
- add deterministic guardrails for table selection and SQL validation.
