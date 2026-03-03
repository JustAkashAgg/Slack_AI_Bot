"""
Async PostgreSQL interface using asyncpg.
Provides execute_query() which returns (headers, rows).
"""

import os
import asyncio
import logging
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None

MAX_ROWS_RETURNED = int(os.getenv("MAX_ROWS_RETURNED", "500"))


async def _get_pool() -> asyncpg.Pool:
    """Lazy-create a connection pool."""
    global _pool
    if _pool is None or _pool._closed:
        dsn = os.environ.get("DATABASE_URL") or (
            f"postgresql://{os.environ['POSTGRES_USER']}:"
            f"{os.environ['POSTGRES_PASSWORD']}@"
            f"{os.environ.get('POSTGRES_HOST', 'localhost')}:"
            f"{os.environ.get('POSTGRES_PORT', '5432')}/"
            f"{os.environ['POSTGRES_DB']}"
        )
        _pool = await asyncpg.create_pool(
            dsn,
            min_size=1,
            max_size=5,
            command_timeout=30,
            server_settings={"application_name": "slack-ai-bot"},
        )
        logger.info("✅ Database pool created")
    return _pool


async def execute_query(sql: str) -> tuple[list[str], list[list]]:
    """
    Execute a SELECT query and return (headers, rows).
    Rows are capped at MAX_ROWS_RETURNED to prevent giant Slack messages.

    Returns:
        headers: list of column names
        rows:    list of rows, each row is a list of values
    """
    pool = await _get_pool()

    async with pool.acquire() as conn:
        # Run in a read-only transaction for safety
        async with conn.transaction(readonly=True):
            records = await conn.fetch(sql)

    if not records:
        return [], []

    headers = list(records[0].keys())
    rows = [list(r.values()) for r in records[:MAX_ROWS_RETURNED]]

    return headers, rows


async def test_connection() -> bool:
    """Returns True if the database is reachable."""
    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return False