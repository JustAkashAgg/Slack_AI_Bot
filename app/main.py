"""
Slack AI Data Bot - Main Application
Handles /ask-data slash command, NL→SQL via LangChain, and Postgres execution.
"""

import os
import io
import csv
import logging
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from fastapi import FastAPI, Request, Response
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

from .sql_agent import generate_sql, SCHEMA_DESCRIPTION
from .database import execute_query, test_connection
from .formatters import format_slack_response, format_error_response, rows_to_csv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Slack App ─────────────────────────────────────────────────────────────────
slack_app = AsyncApp(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)

# In-memory cache: channel_id → last (sql, rows, headers)
query_cache: dict[str, tuple[str, list, list]] = {}


@slack_app.command("/ask-data")
async def handle_ask_data(ack, respond, command, say):
    """
    Entry point for /ask-data <natural language question>
    Flow: ack → generate SQL → execute → format → respond
    """
    await ack()  # Must acknowledge within 3s

    question = (command.get("text") or "").strip()
    channel_id = command.get("channel_id", "")
    user_id = command.get("user_id", "")

    if not question:
        await respond(
            text="Please provide a question. Example: `/ask-data show revenue by region for 2025-09-01`"
        )
        return

    # Immediate acknowledgement so user knows we're working
    await respond(text=f"⏳ Analyzing your question: *{question}*")

    try:
        # Step 1: Generate SQL using LangChain
        logger.info(f"Generating SQL for: {question}")
        sql = await generate_sql(question)
        logger.info(f"Generated SQL: {sql}")

        # Step 2: Execute SQL
        headers, rows = await execute_query(sql)

        # Step 3: Cache the result for potential CSV export
        query_cache[channel_id] = (sql, rows, headers)

        # Step 4: Format and send response
        blocks = format_slack_response(
            question=question,
            sql=sql,
            headers=headers,
            rows=rows,
            channel_id=channel_id,
        )

        await respond(blocks=blocks, text=f"Results for: {question}")

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        error_blocks = format_error_response(question=question, error=str(e))
        await respond(blocks=error_blocks, text=f"Error: {e}")


@slack_app.action("export_csv")
async def handle_export_csv(ack, body, client, respond):
    """Export the last query result as a CSV file upload."""
    await ack()

    channel_id = body.get("channel", {}).get("id", "")
    cached = query_cache.get(channel_id)

    if not cached:
        await respond(text="No recent query found to export.")
        return

    sql, rows, headers = cached

    try:
        csv_content = rows_to_csv(headers, rows)
        csv_bytes = csv_content.encode("utf-8")

        await client.files_upload_v2(
            channel=channel_id,
            content=csv_bytes,
            filename="query_results.csv",
            title="Query Export",
            initial_comment="📊 Here's your CSV export:",
        )
    except Exception as e:
        logger.error(f"CSV export failed: {e}")
        await respond(text=f"Export failed: `{e}`")


# ── FastAPI ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify DB connection."""
    ok = await test_connection()
    if ok:
        logger.info("✅ Database connection verified")
    else:
        logger.warning("⚠️  Could not verify database connection at startup")
    yield


app = FastAPI(
    title="Slack AI Data Bot",
    description="Natural language → SQL → Slack",
    lifespan=lifespan,
)

handler = AsyncSlackRequestHandler(slack_app)


@app.post("/slack/events")
async def slack_events(req: Request):
    return await handler.handle(req)


@app.get("/health")
async def health():
    db_ok = await test_connection()
    return {"status": "ok", "database": "connected" if db_ok else "unreachable"}