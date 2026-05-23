.PHONY: up down pull download upload etl etl-local marts smoke assistant eval logs clean

up:
	docker compose up -d --build

down:
	docker compose down

pull:
	docker compose pull

download:
	./scripts/download_raw.sh

upload:
	./scripts/upload_raw_to_minio.sh

etl:
	./scripts/run_etl.sh

etl-local:
	SPARK_MASTER='local[1]' ./scripts/run_etl.sh

marts:
	./scripts/trino_query.sh "$$(cat sql/01_create_marts.sql)"

smoke:
	./scripts/smoke_test.sh

assistant:
	docker compose up -d assistant

eval:
	docker compose exec -T assistant python /eval/llm_judge.py

logs:
	docker compose logs -f --tail=200

clean:
	docker compose down -v
