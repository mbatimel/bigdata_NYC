# Lakehouse Project

Проект содержит локальный контур Data Lakehouse для учебного проекта по теме Data Lakehouse и BI-ассистент.

## Выполненная часть

В рамках данной части выполнены пункты:

1. Найдены данные для обработки объёмом более 1 ГБ.
2. Развёрнут локальный стек Data Lakehouse:
   - MinIO;
   - PostgreSQL;
   - Hive Metastore;
   - Apache Iceberg;
   - Trino.

## Используемый стек

- MinIO — S3-совместимое объектное хранилище.
- PostgreSQL — база данных для хранения внутренних метаданных Hive Metastore.
- Hive Metastore — каталог метаданных таблиц.
- Apache Iceberg — табличный формат для Data Lakehouse.
- Trino — SQL-движок для работы с Iceberg-таблицами.

## Структура проекта

```text
lakehouse-project/
├── docker-compose.yml
├── README.md
├── dataset.md
├── hive/
│   ├── hive-site.xml
│   └── postgresql-42.7.3.jar
├── trino/
│   └── catalog/
│       └── iceberg.properties
└── screenshots/