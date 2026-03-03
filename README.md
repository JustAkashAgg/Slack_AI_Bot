# 🤖 Slack AI Data Bot

A minimal Slack app that converts natural language questions into SQL using LangChain + Groq, executes them on PostgreSQL, and replies in Slack with formatted results.

```
/ask-data show revenue by region for 2025-09-01
```

---

## Architecture

```
Slack User
    │
    │  /ask-data <question>
    ▼
FastAPI + Slack Bolt                  ← receives slash command
    │
    │  question (text)
    ▼
LangChain → Groq (llama-3.1-8b)     ← NL → SQL (free, fast)
    │
    │  SELECT ...
    ▼
asyncpg → PostgreSQL                  ← execute query
    │
    │  headers + rows
    ▼
Block Kit Formatter                   ← build rich Slack message
    │
    ▼
Slack response_url                    ← post results back
```

---

## Project Structure

```
slack-ai-bot/
├── app/
│   ├── __init__.py
│   ├── main.py          ← FastAPI app + Slack Bolt handlers
│   ├── sql_agent.py     ← LangChain NL→SQL chain (Groq)
│   ├── database.py      ← asyncpg connection pool + query execution
│   └── formatters.py    ← Slack Block Kit response builder
├── docker/
│   └── Dockerfile
├── n8n/
│   └── workflow.json    ← N8N alternative (import into N8N UI)
├── sql/
│   ├── init.sql         ← table schema + indexes
│   └── seed.sql         ← sample data
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Prerequisites

- **Docker + Docker Compose** — for running PostgreSQL
- **Python 3.10+** — for running the bot locally
- **A Slack App** at [api.slack.com/apps](https://api.slack.com/apps) with:
  - Slash command `/ask-data`
  - Bot token scopes: `commands`, `chat:write`, `files:write`, `channels:join`
- **Groq API key** (free) — at [console.groq.com](https://console.groq.com)
- **ngrok** (free) — at [ngrok.com](https://ngrok.com) for local development

---

## Quick Start

### 1. Clone & configure

```bash
cp .env.example .env
# Fill in SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, GROQ_API_KEY
```

### 2. Start PostgreSQL with Docker

```bash
# Start only the database (bot runs directly on your Mac)
docker-compose up postgres -d
```

This automatically:
- Creates the `analytics` database
- Runs `sql/init.sql` to create the table
- Runs `sql/seed.sql` to insert 15 rows of sample data

### 3. Install Python dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 4. Run the bot

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:app.database:✅ Database pool created
INFO:app.main:✅ Database connection verified
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5. Expose with ngrok

```bash
# In a new terminal
ngrok http 8000
```

Copy the `https://` URL shown, e.g. `https://abc123.ngrok-free.app`

### 6. Configure your Slack App

Go to [api.slack.com/apps](https://api.slack.com/apps) → your app:

| Setting | Value |
|---|---|
| Slash Command `/ask-data` Request URL | `https://abc123.ngrok-free.app/slack/events` |
| Interactivity Request URL | `https://abc123.ngrok-free.app/slack/events` |

### 7. Invite bot to your Slack channel

In the Slack channel where you want to use the bot:
```
/invite @YourBotName
```

### 8. Test it

```
/ask-data show revenue by region for 2025-09-01
```

---

## Usage

In any Slack channel where the bot is a member:

```
/ask-data show revenue by region for 2025-09-01
/ask-data what are the top 3 categories by total orders?
/ask-data compare revenue between North and South regions
/ask-data total revenue per day
/ask-data which region had the highest orders on 2025-09-02?
```

The bot replies with:
- The question asked
- The SQL that was generated
- A formatted table preview (up to 10 rows)
- An **⬇️ Export CSV** button for the full dataset

---

## N8N Alternative (No-Code)

If you prefer a visual workflow instead of Python:

### Local N8N
```bash
docker-compose --profile n8n up -d
```
Go to [http://localhost:5678](http://localhost:5678) (admin / admin123)

### Setup Steps
1. **Add Groq credential** → Credentials → Add → Header Auth
   ```
   Name:  Authorization
   Value: Bearer gsk_...your-groq-key
   ```
   Save as `Groq API Key`

2. **Add Postgres credential** → Credentials → Add → Postgres
   ```
   Host:     postgres        ← use "postgres" not "localhost" inside Docker
   Port:     5432
   Database: analytics
   User:     analytics
   Password: analytics_pass
   SSL:      Disable
   ```
   Save as `analytics DB`

3. **Import workflow** → Workflows → Add → Import from File → select `n8n/workflow.json`

4. **Attach credentials** to the Groq and Postgres nodes

5. **Expose with ngrok** (port 5678 for N8N)
   ```bash
   ngrok http 5678
   ```

6. **Update Slack app URLs** to:
   ```
   https://abc123.ngrok-free.app/webhook/slack-ask-data
   ```

7. **Activate the workflow** (toggle top right → green)

---

## Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok","database":"connected"}
```

---

## Example Slack Response

```
📊 Query Results
──────────────────────────────────────
Question: show revenue by region for 2025-09-01
Rows Returned: 3
──────────────────────────────────────
Generated SQL
SELECT region, SUM(revenue) AS total_revenue
FROM public.sales_daily
WHERE date = '2025-09-01'
GROUP BY region
ORDER BY total_revenue DESC

Preview
region │ total_revenue
───────┼──────────────
North  │ 125000.50
South  │ 54000.00
West   │ 40500.00

[⬇️ Export CSV]
```

---

## Configuration

| Env Var | Default | Description |
|---|---|---|
| `SLACK_BOT_TOKEN` | — | Slack bot OAuth token (starts with `xoxb-`) |
| `SLACK_SIGNING_SECRET` | — | Slack app signing secret |
| `GROQ_API_KEY` | — | Groq API key (free at console.groq.com) |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model for SQL generation |
| `POSTGRES_USER` | `analytics` | DB username |
| `POSTGRES_PASSWORD` | `analytics_pass` | DB password |
| `POSTGRES_DB` | `analytics` | Database name |
| `POSTGRES_HOST` | `localhost` | Use `localhost` on Mac, `postgres` inside Docker |
| `POSTGRES_PORT` | `5432` | Database port |
| `MAX_ROWS_RETURNED` | `500` | Cap on rows fetched per query |

---

## Getting API Keys

### Groq API Key (Free)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up with Google/GitHub — no credit card needed
3. **API Keys** → **Create API Key**
4. Copy the key starting with `gsk_...`
5. Free limits: **6,000 requests/day**, **30 requests/minute**

### Slack Tokens
1. Go to [api.slack.com/apps](https://api.slack.com/apps) → your app
2. `SLACK_BOT_TOKEN` → **OAuth & Permissions** → Bot User OAuth Token
3. `SLACK_SIGNING_SECRET` → **Basic Information** → Signing Secret

---

## Postgres Host Rules

| Running From | POSTGRES_HOST |
|---|---|
| Mac terminal / local Python | `localhost` |
| Inside Docker (N8N, bot container) | `postgres` |

---

## Stretch Goals Implemented

- [x] **Export CSV** button — uploads a CSV file directly to the Slack channel
- [x] **Error handling** — displays errors in a formatted Slack code block
- [x] **Safety check** — rejects all non-SELECT SQL statements
- [x] **N8N workflow** — complete no-code alternative implementation using Groq
- [x] **Query caching** — last result cached per channel for instant CSV export
- [x] **Read-only transactions** — all queries run in read-only mode for safety
- [x] **Row cap** — results capped at 500 rows to prevent oversized messages

---

## Common Issues

| Error | Cause | Fix |
|---|---|---|
| `KeyError: GROQ_API_KEY` | `.env` not loaded | Add `load_dotenv()` at top of `sql_agent.py` |
| `database: unreachable` | Docker not running | Run `docker-compose up postgres -d` |
| `dispatch_failed` | Wrong ngrok URL in Slack | Update Slack slash command URL |
| `Connection refused` | Wrong host in Docker | Use `postgres` not `localhost` inside Docker |
| `not_in_channel` | Bot not in channel | Run `/invite @YourBotName` in the channel |
| `429 quota exceeded` | Groq rate limit hit | Wait 1 minute and retry |