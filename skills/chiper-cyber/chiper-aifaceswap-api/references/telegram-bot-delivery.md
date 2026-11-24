# Wrapping a batch pipeline as a Telegram bot

Turn the face-swap (or any long batch) pipeline into a chat bot: user sends inputs in chat, bot
runs the blocking job in a thread, streams progress, and sends the finished `.zip` as a document.

Session context: built `bot.py` beside the FastAPI engine, reused `engine.GenPool` / `UploadPool`.
Bot is `python-telegram-bot` **v22.8** (already in the `chiper` venv). Result: user sends video →
photo → gets zip in chat, no CF-tunnel timeout.

## Why this beats the web UI for this class
- **No edge timeout**: a 10MB video to the web UI *through a CF tunnel* can 524; sending it to a
  Telegram bot has no such origin-timeout problem (Telegram bot API caps at 20MB download for
  `getFile` unless you run a local Bot API server — that's the real limit here).
- **Push, not pull**: progress edits + the final document arrive on their own.
- **Phone-friendly**: works with no DNS/browser setup.

## Token: use a SEPARATE bot (do not share the gateway's)
The Chiper gateway long-polls its own `TELEGRAM_BOT_TOKEN`. A second process polling the **same**
bot gets `Conflict: terminated by other getUpdates request` (409). So:
1. @BotFather → `/newbot` → get a fresh token.
2. Write it to a dedicated env file, `chmod 600`:
   ```
   TELEGRAM_FACESWAP_TOKEN=<token>
   FACESWAP_ALLOWED_USERS=            # optional comma-list of user ids (empty = open)
   ```
3. Sanity check: `GET https://api.telegram.org/bot<tok>/getWebhookInfo` → empty `url` + `pending:0`.
4. Load via systemd `EnvironmentFile=` (keeps the secret out of the unit and the repo).

## The one hard part: sync job → async progress bridge
`run_job` is *blocking* (spawned in a `threading.Thread`); `python-telegram-bot` is *async*. Capture
the running event loop at handler time, then from the worker thread schedule coroutines onto it.

**CRITICAL (this bit us in production):** `asyncio.run_coroutine_threadsafe()` returns a
`concurrent.futures.Future`, **not** the coroutine's result. `push(...)` must `.result()` the future
to get the `Message` object — otherwise `m = push(...)` is `None`, every later `patch(m, ...)` silently
no-ops (you pass `message_id=None` → 400 Bad Request), and the user sees a frozen status forever.
Resolve the future, kernel-timeout it, and swallow errors so a bot hiccup never kills the job:

```python
import asyncio, threading, time, traceback
from telegram.constants import ParseMode

def run_job(uid, video_path, face_path, chat_id, bot):
    st = JOBS[uid]
    loop = st["loop"]                       # captured in the async handler = asyncio.get_event_loop()

    def _sync(coro, timeout=30):            # run a coroutine on the bot loop, return its RESULT
        fut = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return fut.result(timeout=timeout)
        except Exception as e:
            log.warning("bot call failed: %s", e)
            return None

    def push(text):
        return _sync(bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML))

    def patch(msg_id, text):
        if not msg_id:                      # never edit with None
            return
        if st.get("_last_text") == text:    # Telegram 400s on identical-text edit — skip no-ops
            return
        st["_last_text"] = text
        _sync(bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text,
                                    parse_mode=ParseMode.HTML))

    try:
        m0 = push("🎭 Mulai…")
        m = m0.message_id if m0 else None   # <-- grab the id, do NOT store the whole Message
        # ... engine.Uploader / split_video / UploadPool / GenPool ...
        def on_done(idx, ok, payload):
            patch(m, progress_bar(done, total))   # updates the same status message
        get_pool().run(tasks, on_done=on_done)
        cap = "✅ Selesai! …"
        patch(m, cap)
        # send the file from the thread, with a retry so a transient failure isn't silent:
        for att in range(2):
            res = _sync(bot.send_document(chat_id=chat_id, document=open(zip_path, "rb"),
                                          filename=os.path.basename(zip_path),
                                          caption=cap, parse_mode=ParseMode.HTML), timeout=180)
            if res:
                break
            time.sleep(3)
        else:
            push(f"⚠️ Zip jadi tapi gagal kirim otomatis.\n📁 <code>{zip_path}</code>")
        st["stage"] = "done"
    except Exception as e:
        log.error("job error: %s\n%s", e, traceback.format_exc())
        push(f"❌ <code>{html_escape(str(e)[:400])}</code>")
```
Do NOT wrap the final `send_document` in a bare `with open(...)` fire-and-forget — if it errors you
lose the file silently and the user waits forever (exactly what happened: job finished at 07:16,
user still waiting at 07:25). Always resolve + retry + fall back to posting the file path.

**Register an error handler too** (`app.add_error_handler(on_error)`) so any uncaught handler
exception replies in-chat instead of only logging — otherwise the bot looks "dead" when a handler
throws (e.g. a stale import like `NameError: InlineKeyboardMarkup`).

Handler side (async) sets `JOBS[uid]["loop"] = asyncio.get_event_loop()` and starts the thread:

```python
async def on_photo(update, ctx):
    JOBS[uid] = {"id": jid, "results": [], "failed": [], "created": time.time(),
                 "loop": asyncio.get_event_loop()}
    await update.message.reply_text("🚀 Mulai!")
    threading.Thread(target=run_job,
                     args=(uid, video_path, face_path, msg.chat_id, ctx.bot),
                     daemon=True).start()
```

`edit_message_text` throttles at ~1 edit/s — patch once per completed clip, not per second.

## Two-step input flow (video then photo)
- `on_video`: `await ctx.bot.get_file(vid.file_id).download_to_drive(path)` → stash in
  `PENDING[uid]`, prompt for the face photo.
- `on_photo`: pop `PENDING[uid]`, download face, kick off the job.
- Allow either order (if a photo arrives first, tell the user to send a video first and keep PENDING).
- Reject oversize early: `if (vid.file_size or 0) > MAX_VIDEO_MB*1024*1024: reply "too big"`.

## Guided wizard UX (user explicitly asked for this — "harus ada opsi biar mudah … biar ada instruksi")
A bare "send video then send photo" instruction leaves users guessing. Make it a **button-driven
wizard** with a step counter and a confirm gate. User feedback that drove this: an unguided flow is
confusing; a tap-to-start button + numbered steps is the desired feel.
- `/start` (and `/swipe`) → `InlineKeyboardMarkup` with a big primary button
  `🎭 SWIPE FACE — mulai sekarang` (callback_data `swipe`), plus `📖 Cara Pakai` / `ℹ️ Status`.
- Tapping `swipe` edits that message into **"LANGKAH 1 dari 2 — kirim VIDEO"** (with a `❌ Batal`
  button), instead of sending a new message. Edit-in-place keeps the chat clean.
- On video received → reply **"✅ Video diterima (N MB) · LANGKAH 2 dari 2 — kirim FOTO WAJAH"**.
- On photo received → do **not** auto-start. Show **"Semua siap"** with
  `▶️ PROSES SEKARANG` (callback `process`), `🔁 Ganti Video`, `❌ Batal`. Start only on `process`.
- One `CallbackQueryHandler(on_callback)` dispatches all callback_data (`swipe`/`how`/`status`/
  `menu`/`process`/`cancel`). Keep `WIZ[uid] = {"step": ...}` for state, `PENDING[uid]` for files.
- Every command and callback must `await q.answer()` first, else the button shows a spinner.

## Pitfalls
- **`APP_DIR` off-by-one**: `bot.py` sits at the app root, so it must be
  `os.path.dirname(os.path.abspath(__file__))` — a second `dirname()` (as if it lived in `app/`)
  silently writes results one level too high (e.g. `~/results_bot/` instead of `~/faceswap-ui/results_bot/`).
  Symptom: job completes but "results dir is empty". Set `WORK`/`RESULTS` from the *single*-dirname root.
- **Import path**: if the engine lives in `app/`, add *both* `scripts_dir` and `scripts_dir/app`
  to `sys.path` in `bot.py`, or the `import engine` fails (`ModuleNotFoundError`).
- **Don't run two pollers** on one bot token (409) — gateway or bot, not both.
- `run_polling(drop_pending_updates=True)` on startup avoids replaying old messages after a redeploy.
- Escape user/exception text before putting it in an HTML-parse message (`&`,`<`,`>`), else the send
  itself 400s.
- **`editMessageText` 400 "message is not modified"**: Telegram rejects editing a message to text
  identical to its current content. Cache the last text per message and skip no-op edits (see bridge).
- **Validate callback/import symbols on redeploy**: after refactoring handlers, a dropped import
  (e.g. `InlineKeyboardButton`) only surfaces at *first button tap*, not at startup. Import the module
  once and `assert hasattr(bot, 'InlineKeyboardButton')` etc., or rely on the error handler's in-chat reply.
- Bot API file download limit is **20MB** by default; bigger needs a self-hosted local Bot API server.

## systemd unit
```
[Unit]
Description=... Telegram Bot
After=network.target tor.service
Wants=tor.service
[Service]
Type=simple
User=<user>
WorkingDirectory=<app dir>
Environment=CHIPER_UPLOAD_PROXY=socks5h://127.0.0.1:9050
Environment=FACESWAP_WORKERS=4
EnvironmentFile=<home>/.chiper/faceswap_bot.env
ExecStart=<venv>/python3 <app dir>/bot.py
Restart=always
[Install]
WantedBy=multi-user.target
```
`systemctl enable --now <name>`; verify `journalctl -u <name>` shows
`getMe 200 → deleteWebhook 200 → Application started`.
