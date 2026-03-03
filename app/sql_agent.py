"""
LangChain NL→SQL agent.
Uses a plain prompt with schema context to produce a single SELECT statement.
"""

import os
import re
import asyncio
from functools import lru_cache

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ── Schema ────────────────────────────────────────────────────────────────────
SCHEMA_DESCRIPTION = """
Table: public.sales_daily
Description: Daily sales data broken down by region and product category.

Columns:
  - date        DATE         The calendar date of the sales record          (PK)
  - region      TEXT         Sales region: 'North', 'South', 'East', 'West' (PK)
  - category    TEXT         Product category: 'Electronics','Grocery','Fashion' (PK)
  - revenue     NUMERIC(12,2) Total revenue in USD for that day/region/category
  - orders      INTEGER      Number of orders placed
  - created_at  TIMESTAMPTZ  Row insertion timestamp (usually not needed in queries)

Sample data dates: 2025-09-01 to 2025-09-02
"""

# ── Prompt ────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a PostgreSQL expert. Convert the user's natural language question 
into a single, valid PostgreSQL SELECT statement.

{schema}

Rules:
- Output ONLY the SQL query — no markdown fences, no explanations, no comments.
- Always use fully qualified table name: public.sales_daily
- Use ORDER BY for readability when listing multiple rows.
- Do not use LIMIT unless the user asks for top-N results.
- Do not use INSERT, UPDATE, DELETE, DROP, or any DDL/DML statement.
- If aggregating, use clear column aliases (e.g. SUM(revenue) AS total_revenue).
"""

HUMAN_PROMPT = "Question: {question}"


def _build_chain():
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        groq_api_key=os.environ["GROQ_API_KEY"],
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", HUMAN_PROMPT),
    ])
    return prompt | llm | StrOutputParser()


_chain = None


def _get_chain():
    global _chain
    if _chain is None:
        _chain = _build_chain()
    return _chain


def _clean_sql(raw: str) -> str:
    """Strip markdown code fences and extra whitespace from model output."""
    # Remove ```sql ... ``` or ``` ... ```
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
    raw = raw.replace("```", "").strip()
    # Safety: only allow SELECT statements
    first_token = raw.split()[0].upper() if raw.split() else ""
    if first_token not in ("SELECT", "WITH"):
        raise ValueError(
            f"Model returned a non-SELECT statement: {raw[:80]}. Only SELECT queries are allowed."
        )
    return raw


async def generate_sql(question: str) -> str:
    """
    Async wrapper: send question to LangChain chain, return clean SQL string.
    """
    chain = _get_chain()
    raw = await chain.ainvoke(
        {"schema": SCHEMA_DESCRIPTION, "question": question}
    )
    return _clean_sql(raw)