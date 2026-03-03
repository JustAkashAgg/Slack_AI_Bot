"""
Slack Block Kit formatters.
Produces rich, readable messages for query results and errors.
"""

import csv
import io
from typing import Any

MAX_PREVIEW_ROWS = 10   # rows shown in Slack preview
MAX_COL_WIDTH   = 20    # truncate long cell values in preview


def _truncate(value: Any, max_len: int = MAX_COL_WIDTH) -> str:
    s = str(value) if value is not None else "NULL"
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def _build_table_text(headers: list[str], rows: list[list]) -> str:
    """Build a fixed-width monospace table string for Slack code block."""
    if not headers or not rows:
        return "(no rows)"

    preview = rows[:MAX_PREVIEW_ROWS]

    col_widths = [len(h) for h in headers]
    for row in preview:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(_truncate(cell)))

    def fmt_row(values):
        return " │ ".join(
            _truncate(v).ljust(col_widths[i]) for i, v in enumerate(values)
        )

    sep = "─┼─".join("─" * w for w in col_widths)
    lines = [fmt_row(headers), sep]
    for row in preview:
        lines.append(fmt_row(row))

    if len(rows) > MAX_PREVIEW_ROWS:
        lines.append(f"… {len(rows) - MAX_PREVIEW_ROWS} more rows (export CSV to see all)")

    return "\n".join(lines)


def format_slack_response(
    question: str,
    sql: str,
    headers: list[str],
    rows: list[list],
    channel_id: str = "",
) -> list[dict]:
    """Build Slack Block Kit blocks for a successful query result."""
    total_rows = len(rows)
    table_text = _build_table_text(headers, rows)

    blocks = [
        # ── Header ────────────────────────────────────────────────────────
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📊 Query Results", "emoji": True},
        },
        # ── Question ──────────────────────────────────────────────────────
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Question*\n{question}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Rows Returned*\n{total_rows:,}",
                },
            ],
        },
        {"type": "divider"},
        # ── SQL used ──────────────────────────────────────────────────────
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Generated SQL*\n```{sql}```",
            },
        },
        {"type": "divider"},
        # ── Table ─────────────────────────────────────────────────────────
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Preview*\n```{table_text}```",
            },
        },
    ]

    # ── Export button (stretch goal) ───────────────────────────────────────
    if total_rows > 0:
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "⬇️  Export CSV", "emoji": True},
                        "style": "primary",
                        "action_id": "export_csv",
                        "value": channel_id,
                    }
                ],
            }
        )

    # ── Empty state ───────────────────────────────────────────────────────
    if total_rows == 0:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "ℹ️  *The query ran successfully but returned no rows.*",
                },
            }
        )

    return blocks


def format_error_response(question: str, error: str) -> list[dict]:
    """Build Slack Block Kit blocks for an error state."""
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "❌ Query Error", "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Question*\n{question}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Error Details*\n```{error}```",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "💡 Try rephrasing your question or check that column names are correct.",
                }
            ],
        },
    ]


def rows_to_csv(headers: list[str], rows: list[list]) -> str:
    """Serialise query results to a CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue()