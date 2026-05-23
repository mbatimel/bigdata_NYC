from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import sqlglot
import streamlit as st
import trino
import yaml


ROOT = Path(__file__).resolve().parent
DEFAULT_DETAIL_LIMIT = 20
MAX_DETAIL_LIMIT = 1000


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_semantic_layer() -> dict[str, Any]:
    path = Path(os.getenv("SEMANTIC_LAYER_PATH", ROOT / "semantic_layer.yaml"))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def trino_connection():
    return trino.dbapi.connect(
        host=os.getenv("TRINO_HOST", "localhost"),
        port=int(os.getenv("TRINO_PORT", "8080")),
        user=os.getenv("TRINO_USER", "analyst"),
        catalog=os.getenv("TRINO_CATALOG", "iceberg"),
        schema=os.getenv("TRINO_SCHEMA", "analytics"),
        http_scheme=os.getenv("TRINO_HTTP_SCHEME", "http"),
    )


@st.cache_data(ttl=300)
def schema_summary() -> str:
    sql = """
    SELECT table_schema, table_name, column_name, data_type
    FROM iceberg.information_schema.columns
    WHERE table_schema IN ('analytics', 'curated')
    ORDER BY table_schema, table_name, ordinal_position
    """
    try:
        rows = run_sql(sql, limit=None)
    except Exception:
        return ""
    grouped: dict[tuple[str, str], list[str]] = {}
    for row in rows.to_dict("records"):
        key = (row["table_schema"], row["table_name"])
        grouped.setdefault(key, []).append(f"{row['column_name']} {row['data_type']}")

    lines = []
    for (schema, table), columns in grouped.items():
        lines.append(f"{schema}.{table}: " + ", ".join(columns))
    return "\n".join(lines)


def run_sql(sql: str, limit: int | None = 1000) -> pd.DataFrame:
    conn = trino_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
    finally:
        conn.close()
    df = pd.DataFrame(rows, columns=columns)
    if limit is not None:
        return df.head(limit)
    return df


def call_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    response = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        },
        timeout=60,
    )
    if not response.ok:
        detail = ""
        try:
            detail = response.json().get("error", {}).get("message", "")
        except ValueError:
            detail = response.text.strip()
        detail = re.sub(r"\s+", " ", detail)[:400]
        message = f"OpenAI API returned HTTP {response.status_code}"
        if detail:
            message += f": {detail}"
        raise RuntimeError(message)
    return response.json()["choices"][0]["message"]["content"]


def call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0}},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def call_llm(prompt: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "openai":
        return call_openai(prompt)
    if provider == "gemini":
        return call_gemini(prompt)
    raise RuntimeError("LLM_PROVIDER is mock")


def requested_limit(question: str, default: int) -> int:
    numeric_tokens = [int(token) for token in re.findall(r"(?<!\d)\d{1,4}(?!\d)", question)]
    explicit_counts = [
        value
        for value in numeric_tokens
        if 0 < value <= MAX_DETAIL_LIMIT and not 1900 <= value <= 2100
    ]
    if explicit_counts:
        return explicit_counts[-1]
    return default


def deterministic_sql(question: str) -> str:
    q = question.lower()
    if any(token in q for token in ["маршрут", "route", "routes"]):
        limit = requested_limit(question, 10)
        return f"""
        SELECT pickup_borough, pickup_zone, dropoff_borough, dropoff_zone,
               trip_count, gross_revenue, avg_trip_miles, avg_trip_minutes
        FROM iceberg.analytics.mart_top_routes
        ORDER BY trip_count DESC
        LIMIT {limit}
        """
    if any(token in q for token in ["час", "hour", "спрос", "demand"]):
        borough_filter = "WHERE pickup_borough = 'Manhattan'" if "manhattan" in q else ""
        return f"""
        SELECT pickup_hour, pickup_borough, trip_count, gross_revenue, avg_revenue_per_trip
        FROM iceberg.analytics.mart_hourly_demand
        {borough_filter}
        ORDER BY trip_count DESC
        LIMIT 24
        """
    if any(token in q for token in ["аэропорт", "airport"]):
        limit = requested_limit(question, DEFAULT_DETAIL_LIMIT)
        return f"""
        SELECT pickup_date, pickup_borough, pickup_zone,
               airport_trip_count, gross_revenue, avg_airport_fee, avg_trip_miles
        FROM iceberg.analytics.mart_airport_trips
        ORDER BY airport_trip_count DESC
        LIMIT {limit}
        """
    if any(token in q for token in ["база", "base", "dispatching", "kpi"]):
        limit = requested_limit(question, DEFAULT_DETAIL_LIMIT)
        return f"""
        SELECT pickup_month, dispatching_base_num, trip_count, gross_revenue,
               avg_revenue_per_trip, avg_driver_pay_per_trip, avg_trip_miles
        FROM iceberg.analytics.mart_base_monthly_kpi
        ORDER BY gross_revenue DESC
        LIMIT {limit}
        """
    limit = requested_limit(question, DEFAULT_DETAIL_LIMIT)
    return f"""
    SELECT pickup_date, pickup_borough, pickup_zone, trip_count,
           gross_revenue, avg_revenue_per_trip, avg_trip_miles
    FROM iceberg.analytics.mart_daily_zone_revenue
    ORDER BY gross_revenue DESC
    LIMIT {limit}
    """


def clean_sql(text: str) -> str:
    text = text.strip()
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    text = re.sub(r";+\s*$", "", text)
    return text


def validate_sql(sql: str) -> str:
    lowered = sql.lower()
    blocked = ["insert", "update", "delete", "drop", "alter", "create", "truncate", "merge", "call"]
    if any(re.search(rf"\b{word}\b", lowered) for word in blocked):
        raise ValueError("Only read-only SELECT queries are allowed")
    expressions = sqlglot.parse(sql, read="trino")
    if len(expressions) != 1:
        raise ValueError("Only one SQL statement is allowed")
    root = expressions[0]
    if root.key not in {"select", "with"}:
        raise ValueError("Only SELECT or WITH queries are allowed")
    return sql


def generate_sql(question: str, diagnostics: list[str] | None = None) -> str:
    semantic = yaml.safe_dump(load_semantic_layer(), allow_unicode=True, sort_keys=False)
    prompt = load_text(ROOT / "prompts" / "sql_generation.md").format(
        semantic_layer=semantic,
        schema_summary=schema_summary(),
        question=question,
    )
    try:
        sql = clean_sql(call_llm(prompt))
    except Exception as exc:
        if diagnostics is not None:
            diagnostics.append(f"SQL generation fallback: {exc}")
        sql = clean_sql(deterministic_sql(question))
    return validate_sql(sql)


def summarize(
    question: str,
    sql: str,
    df: pd.DataFrame,
    diagnostics: list[str] | None = None,
) -> str:
    rows = df.head(20).to_dict("records")
    prompt = load_text(ROOT / "prompts" / "answer.md").format(
        question=question,
        sql=sql,
        rows=rows,
    )
    try:
        return call_llm(prompt).strip()
    except Exception as exc:
        if diagnostics is not None:
            diagnostics.append(f"Answer fallback: {exc}")
        if df.empty:
            return "По запросу не найдено строк."
        if {"pickup_zone", "dropoff_zone", "trip_count"}.issubset(df.columns):
            route = df.iloc[0]
            route_parts = []
            if "pickup_borough" in df.columns:
                route_parts.append(f"{route['pickup_borough']} / {route['pickup_zone']}")
            else:
                route_parts.append(str(route["pickup_zone"]))
            if "dropoff_borough" in df.columns:
                route_parts.append(f"{route['dropoff_borough']} / {route['dropoff_zone']}")
            else:
                route_parts.append(str(route["dropoff_zone"]))
            return (
                f"Показано {len(df)} маршрутов. Лидер: "
                f"{route_parts[0]} -> {route_parts[1]}, поездок: {int(route['trip_count']):,}."
            )
        numeric_cols = list(df.select_dtypes(include="number").columns)
        if numeric_cols:
            col = numeric_cols[0]
            return f"Запрос вернул {len(df)} строк. Максимальное значение {col}: {df[col].max():,.2f}."
        return f"Запрос вернул {len(df)} строк."
