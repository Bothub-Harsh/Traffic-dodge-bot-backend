import os
import hmac
import hashlib
import json
import time
from urllib.parse import parse_qsl

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ["BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]
GAME_URL = os.environ["GAME_URL"].rstrip("/")
PUBLIC_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
PORT = int(os.environ.get("PORT", "10000"))

app = FastAPI(title="Traffic Dodger Bot API")
telegram_app = Application.builder().token(BOT_TOKEN).build()


def db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                telegram_user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT NOT NULL DEFAULT '',
                best_score INTEGER NOT NULL DEFAULT 0,
                total_coins INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_scores (
                id BIGSERIAL PRIMARY KEY,
                telegram_user_id BIGINT NOT NULL REFERENCES players(telegram_user_id),
                chat_id BIGINT,
                score INTEGER NOT NULL,
                coins INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS game_scores_score_idx ON game_scores(score DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS game_scores_chat_idx ON game_scores(chat_id, score DESC)")


def verify_telegram_init_data(init_data: str) -> dict:
    """Verify Telegram Mini App initData using the bot token."""
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram initData")
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing initData hash")

    auth_date = values.get("auth_date")
    try:
        if not auth_date or abs(time.time() - int(auth_date)) > 86400:
            raise HTTPException(status_code=401, detail="Telegram initData expired")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid auth_date")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram initData signature")

    try:
        user = json.loads(values["user"])
    except (KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="No valid Telegram user in initData")
    return user


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        with db() as conn:
            conn.execute("""
                INSERT INTO players (telegram_user_id, username, first_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (telegram_user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    updated_at = NOW()
            """, (user.id, user.username, user.first_name or "Player"))

    keyboard = [[InlineKeyboardButton("🎮 Play Traffic Dodger", web_app=WebAppInfo(url=GAME_URL))]]
    await update.effective_message.reply_text(
        "Welcome to Arcade! 🕹️\n\nPlay Traffic Dodger, dodge traffic, collect coins, and compete for the high score.\n\n"
        "Commands:\n/play — open the game\n/leaderboard — top scores\n/myscore — your best score",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎮 Play now", web_app=WebAppInfo(url=GAME_URL))]]
    await update.effective_message.reply_text("Ready to play?", reply_markup=InlineKeyboardMarkup(keyboard))


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if update.effective_chat else None
    with db() as conn:
        if chat_id and update.effective_chat.type != "private":
            rows = conn.execute("""
                SELECT p.first_name, p.username, MAX(s.score) AS score
                FROM game_scores s JOIN players p USING (telegram_user_id)
                WHERE s.chat_id = %s
                GROUP BY p.telegram_user_id, p.first_name, p.username
                ORDER BY score DESC LIMIT 10
            """, (chat_id,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT p.first_name, p.username, p.best_score AS score
                FROM players p WHERE p.best_score > 0
                ORDER BY p.best_score DESC LIMIT 10
            """).fetchall()

    if not rows:
        await update.effective_message.reply_text(
            "🏆 The leaderboard is empty so far.\nOpen the game with /play and finish a run to submit your first score."
        )
        return
    lines = ["🏆 **Traffic Dodger Leaderboard**", ""]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows, 1):
        name = ("@" + row["username"]) if row["username"] else (row["first_name"] or "Player")
        lines.append(f"{medals[i-1] if i <= 3 else str(i)+'.'} {name} — **{row['score']}**")
    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")


async def myscore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    with db() as conn:
        row = conn.execute(
            "SELECT best_score, total_coins FROM players WHERE telegram_user_id = %s",
            (user.id,)
        ).fetchone()
    if not row:
        await update.effective_message.reply_text("No score saved yet. Send /play and finish a game!")
    else:
        await update.effective_message.reply_text(
            f"🏁 Your best score: {row['best_score']}\n🪙 Coins collected: {row['total_coins']}"
        )


telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("play", play_command))
telegram_app.add_handler(CommandHandler("leaderboard", leaderboard_command))
telegram_app.add_handler(CommandHandler("myscore", myscore_command))


@app.on_event("startup")
async def startup():
    init_db()
    await telegram_app.initialize()
    await telegram_app.start()
    # Polling works on a single Render Web Service; don't configure a webhook at the same time.
    await telegram_app.updater.start_polling(drop_pending_updates=False)


@app.on_event("shutdown")
async def shutdown():
    if telegram_app.updater and telegram_app.updater.running:
        await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()


@app.get("/")
async def root():
    return {"ok": True, "service": "Traffic Dodger Telegram bot/API"}


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/api/score")
async def submit_score(request: Request):
    body = await request.json()
    user = verify_telegram_init_data(request.headers.get("X-Telegram-Init-Data", ""))
    try:
        score = int(body.get("score", -1))
        coins = int(body.get("coins", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Score and coins must be integers")

    # Basic sanity limits only; this is not full anti-cheat validation.
    if score < 0 or score > 10_000_000 or coins < 0 or coins > 1_000_000:
        raise HTTPException(status_code=400, detail="Score or coins out of allowed range")

    user_id = int(user["id"])
    username = user.get("username")
    first_name = user.get("first_name") or "Player"
    chat_id = body.get("chat_id")
    try:
        chat_id = int(chat_id) if chat_id is not None else None
    except (TypeError, ValueError):
        chat_id = None

    with db() as conn:
        conn.execute("""
            INSERT INTO players (telegram_user_id, username, first_name, best_score, total_coins)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (telegram_user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                best_score = GREATEST(players.best_score, EXCLUDED.best_score),
                total_coins = players.total_coins + EXCLUDED.total_coins,
                updated_at = NOW()
        """, (user_id, username, first_name, score, coins))
        conn.execute("""
            INSERT INTO game_scores (telegram_user_id, chat_id, score, coins)
            VALUES (%s, %s, %s, %s)
        """, (user_id, chat_id, score, coins))
        row = conn.execute(
            "SELECT best_score FROM players WHERE telegram_user_id = %s", (user_id,)
        ).fetchone()

    return JSONResponse({"ok": True, "best_score": row["best_score"]})
