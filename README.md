# Traffic Dodger — Telegram Mini App starter

This folder contains your existing Traffic Dodger game adapted to run as a Telegram Mini App.
The original traffic, collision, lane movement, braking, boost, coins, levels, and score mechanics are preserved.

## What's changed

- Added Telegram's official Web App SDK.
- Calls `Telegram.WebApp.ready()` and `expand()` when opened inside Telegram.
- Matches Telegram's header/background colors to the game.
- Uses mobile safe-area padding and dynamic viewport height.
- Adds optional haptic feedback for crashes, level-ups, coins, and power-ups.
- Saves the best score in this browser/device using `localStorage`.
- Still works in an ordinary browser.

## Important limitation

This first version does **not** yet save scores to a server or create a shared leaderboard. `localStorage` is local to the browser/device and is not secure proof of a score. Do not use client-submitted scores for prizes or competitive rankings until a backend validates them.

## Deploy on Render as a Static Site

1. Create a GitHub repository, for example `traffic-dodger-miniapp`.
2. Upload `index.html` from this folder to the repository root.
3. In Render, choose **New + → Static Site** and connect that GitHub repository.
4. Use these settings:
   - **Build Command:** leave blank
   - **Publish Directory:** `.`
5. Deploy. Copy the public HTTPS URL Render gives you, for example `https://your-game-name.onrender.com`.

You do not need an EC2 instance, Node.js build, or a backend for this first static-game version.

## Create the Telegram bot

1. Open Telegram and chat with **@BotFather**.
2. Send `/newbot`, follow the prompts, and save the bot token privately.
3. In BotFather, open `/mybots`, choose your bot, and find **Bot Settings → Configure Mini App** (the exact menu wording may vary).
4. Set up the Mini App and use your Render HTTPS URL as its URL.
5. If BotFather offers a Main Mini App setting, configure it so users can open the app from the bot profile.
6. Add the bot to your group if you want group commands later. This static first version only hosts the game; `/play` and leaderboard commands require bot code in the next stage.

Telegram Mini Apps require HTTPS for the hosted web app.

## Test it

1. Open the Render URL in a normal browser and confirm the game starts.
2. Open the Mini App from your bot in the Telegram mobile app.
3. Test left/right controls, brake, boost, coins, collision, and Play Again.
4. Crash after achieving a high score, then refresh the game. The Best value should remain on the same browser/device.
5. Try on another device: its local Best value will be separate until we add a backend.

## Next stage

Build a Telegram bot service and API, verify Telegram `initData` on the server, and store scores in PostgreSQL. Only then add group-specific `/leaderboard` and `/myscore` commands.
