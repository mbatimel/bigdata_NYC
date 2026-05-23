#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
import yaml

for candidate in (Path("/app"), Path(__file__).resolve().parents[1] / "assistant"):
    if candidate.exists():
        sys.path.append(str(candidate))

from agent import generate_sql, run_sql, summarize  # noqa: E402


def judge(question: str, sql: str, answer: str, expected_tables: list[str]) -> str:
    api_key = os.getenv("JUDGE_OPENAI_API_KEY")
    if not api_key:
        table_hits = [table for table in expected_tables if table.lower() in sql.lower()]
        return "PASS" if table_hits else "REVIEW"

    prompt = f"""
You are judging a text-to-SQL BI assistant.
Return PASS or FAIL with one short reason.

Question: {question}
Expected tables: {expected_tables}
SQL: {sql}
Answer: {answer}
"""
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": os.getenv("JUDGE_OPENAI_MODEL", "gpt-4.1-mini"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def main() -> None:
    questions_path = Path(__file__).with_name("questions.yaml")
    questions = yaml.safe_load(questions_path.read_text(encoding="utf-8"))["questions"]
    for item in questions:
        sql = generate_sql(item["question"])
        df = run_sql(sql)
        answer = summarize(item["question"], sql, df)
        verdict = judge(item["question"], sql, answer, item["expected_tables"])
        print(f"{item['id']}: {verdict}")
        print(sql)
        print(answer)
        print()


if __name__ == "__main__":
    main()
