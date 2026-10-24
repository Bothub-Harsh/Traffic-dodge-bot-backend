# Arcade Telegram bot + score API (starter)

This adds `/start`, `/play`, `/leaderboard`, `/myscore`, PostgreSQL storage, and a score API.
Your existing Mini App remains hosted separately as a Render Static Site.

## Render services

### 1. PostgreSQL
Create a Render PostgreSQL database. Copy its **Internal Database URL** for a service in the same Render region. Use the External URL only if you have a specific reason to connect from outside Render.

### 2. Web Service
Push these files to a GitHub repository. Create a Render **Web Service** connected to that repository:
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`

Set these environment variables in Render:
- `BOT_TOKEN` = token from @BotFather (keep secret)
- `DATABASE_URL` = Render PostgreSQL Internal Database URL
- `GAME_URL` = your deployed Static Site URL (must be HTTPS)

This starter runs Telegram long polling and the score API in one Web Service. Run only one instance/replica, because multiple polling instances with the same token will conflict.

## Important game integration still needed

The API endpoint `/api/score` verifies Telegram Mini App `initData` and saves a score. Your HTML game must POST the final score and coins to this endpoint with the header `X-Telegram-Init-Data: window.Telegram.WebApp.initData`. Since the game is on a different Render hostname from the API, configure CORS for your exact Static Site URL before calling it from browser JavaScript. The current uploaded HTML does not yet send score submissions, so the leaderboard will stay empty until that client integration is added.

`chat_id` is optional. If omitted, `/leaderboard` in a group currently has no group-specific scores to display; a later version can associate runs with a group using a start parameter or explicit group session.

## Test

- Open `https://<your-web-service>.onrender.com/health` and expect `{"ok":true}`.
- Open the bot in Telegram and send `/start`, `/play`, `/leaderboard`, `/myscore`.
- `/leaderboard` initially says it is empty until scores are submitted.

## Security notes

- Never commit your BotFather token or database URL to GitHub.
- Mini App initData is signature-checked server-side.
- Score range checks are only basic sanity checks, not robust anti-cheat. For competitive rewards, add server-authoritative game sessions and stronger score validation.
