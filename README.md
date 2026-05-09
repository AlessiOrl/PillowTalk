# PillowTalk

PillowTalk is a daily social question bot for Telegram.

One question drops every day.
People answer privately.
Users only read anonymous answers from their own group.

## Stack

- Python 3.12+
- FastAPI
- SQLite + SQLAlchemy async ORM
- APScheduler
- python-telegram-bot
- pandas
- pydantic-settings + dotenv

## Features

- Daily question broadcast at a configurable hour
- CSV question import on startup
- Strict question categories: `open`, `closed`, `action`
- Private answers saved per daily prompt session
- One group per user
- Admin-created groups with invite codes
- Group-scoped anonymous answer feed
- Streak tracking
- Admin force-next question command
- Admin HTTP endpoints

## Project structure

```text
app/
  bot/
  models/
  routers/
  services/
data/
run.py
requirements.txt
.env.example
Dockerfile
docker-compose.yml
```

## Telegram setup

1. Open Telegram and message `@BotFather`.
2. Run `/newbot`.
3. Pick a display name and a username ending in `bot`.
4. Copy the bot token.
5. Find your own Telegram numeric ID using a bot like `@userinfobot`.
6. Put both values into `.env`.

## Environment variables

Copy `.env.example` to `.env` and adjust values.

- `TELEGRAM_BOT_TOKEN`: bot token from BotFather
- `ADMIN_TELEGRAM_ID`: your Telegram numeric ID for admin bot commands
- `ADMIN_API_TOKEN`: bearer token for the admin HTTP API
- `DATABASE_URL`: async SQLAlchemy URL, defaults to `data/pillowtalk.db`
- `QUESTIONS_CSV_PATH`: CSV seed file path
- `QUESTION_COOLDOWN_DAYS`: how long to avoid repeating questions
- `ANSWER_FEED_PAGE_SIZE`: number of group answers shown per page
- `DAILY_QUESTION_HOUR`: hour for the scheduled daily question
- `DAILY_QUESTION_MINUTE`: minute for the scheduled daily question
- `TIMEZONE`: scheduler timezone
- `LOG_LEVEL`: log verbosity

## Local run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

API health checks:

- `GET /`
- `GET /health`

Admin API examples:

```bash
curl -H "Authorization: Bearer change-me-now" http://localhost:8000/api/admin/stats
curl -X POST -H "Authorization: Bearer change-me-now" http://localhost:8000/api/admin/force-question
```

## Telegram bot commands

- `/start`
- `/streak`
- `/read`
- `/join <code>`
- `/mygroup`
- `/leavegroup`
- `/creategroup <name>` admin only
- `/addmember <telegram_id> <group_code>` admin only
- `/forcenext` admin only

## Docker compose

```bash
docker compose up --build
```

Before first run:

1. Create `.env` from `.env.example`
2. Set the real Telegram token and admin values
3. Keep `data/questions.csv` mounted or replace it with your own file
4. SQLite data is stored in `data/pillowtalk.db` by default

## Notes

- Questions are imported on every startup and updated by CSV `id`
- Answers are stored per prompt session, so the same question can return later
- Not answering is treated as a skip; there is no manual skip action
- `/read` hides the user’s own answer and only shows anonymous answers from the same group
- `open` questions accept free-text replies
- `closed` questions are answered by tapping a person from the user's current group
- `action` questions are reserved but not implemented yet
- If the Telegram token is missing, the API still starts but bot polling is skipped
