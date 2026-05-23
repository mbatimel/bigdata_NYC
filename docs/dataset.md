# Выбранный датасет

## Название

NYC TLC Trip Record Data - High Volume For-Hire Vehicle Trip Records.

## Источник

Официальный источник данных: NYC Taxi & Limousine Commission, раздел TLC Trip Record Data:

- https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

## Набор для проекта

Для локального lakehouse выбран помесячный FHVHV-набор за январь-март 2024:

- `fhvhv_tripdata_2024-01.parquet`
- `fhvhv_tripdata_2024-02.parquet`
- `fhvhv_tripdata_2024-03.parquet`

Эти три Parquet-файла дают raw-объём больше 1 ГБ и удовлетворяют требованию задания. При расширении проекта можно добавить следующие месяцы 2024 года без смены схемы загрузки.

## Что содержат данные

Данные описывают поездки high-volume for-hire vehicles в Нью-Йорке. В исходных файлах есть:

- время посадки и высадки;
- идентификаторы taxi zones посадки и высадки;
- dispatching base;
- расстояние и длительность поездки;
- passenger fare, taxes, tolls, surcharges, tips, airport fee и driver pay.

Для человекочитаемых названий borough и taxi zone ETL использует `taxi_zone_lookup.csv`, который команда `make download` кладёт в `data/raw/zones`.

## Размещение raw-файлов

Проект принимает один из двух вариантов локального размещения:

```text
digdata/
├── fhvhv_tripdata_2024-01.parquet
├── fhvhv_tripdata_2024-02.parquet
└── fhvhv_tripdata_2024-03.parquet
```

или уже подготовленную partition-like раскладку:

```text
data/raw/fhvhv/year=2024/month=01/fhvhv_tripdata_2024-01.parquet
data/raw/fhvhv/year=2024/month=02/fhvhv_tripdata_2024-02.parquet
data/raw/fhvhv/year=2024/month=03/fhvhv_tripdata_2024-03.parquet
```

Команда `make upload` отправляет raw-файлы в MinIO AS IS по пути `raw/nyc_taxi/fhvhv/year=.../month=...`, а Spark ETL читает их оттуда и строит Iceberg-таблицы и витрины.

## Аналитики

На этом наборе проект строит:

- выручку и количество поездок по дню и зоне посадки;
- KPI dispatching bases по месяцам;
- популярные маршруты между pickup и dropoff zones;
- почасовой спрос по borough;
- витрину аэропортовых поездок.
