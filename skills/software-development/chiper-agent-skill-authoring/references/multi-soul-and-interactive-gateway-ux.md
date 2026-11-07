# Multi-Soul Architecture and Interactive Gateway UX Patterns

## 1. Multi-Soul Persona Architecture

Chiper Agent supports dynamic multi-personality switching rather than a single static `SOUL.md`:

### Storage & Directory Structure
- All available souls reside in `$CHIPER_HOME/souls/<soul_id>.md` (e.g. `chiper-cyber.md`, `chiper-dev.md`, and custom user-defined souls).
- The active soul is always mirrored/copied to `$CHIPER_HOME/SOUL.md` so `agent/prompt_builder.py` loads it into the root system prompt identity slot without changing core prompt caching behavior.
- Core manager (`agent/soul_manager.py`) provides:
  - `list_souls()`: Discovers all `.md` files in `$CHIPER_HOME/souls`, parsing titles from top headers or predefined metadata.
  - `get_active_soul()`: Identifies the currently active persona.
  - `switch_soul(soul_id)`: Copies the selected soul into `$CHIPER_HOME/SOUL.md`.
  - `save_custom_soul(soul_id, content)`: Saves and immediately activates a new custom soul.

## 2. Interactive Session Kickoff via Inline Keyboard

When users invoke `/new` or `/reset` in messaging platforms (Telegram, Discord):
- Do not merely wipe context silently.
- Present an interactive persona selector (Telegram Inline Keyboard / buttons) offering:
  1. `[ 🛡️ Chiper-Cyber ]` (Offensive Security / Bug Bounty Mode)
  2. `[ 💻 Chiper-Dev ]` (Fullstack Software Engineering & Architecture)
  3. Additional registered custom souls
  4. `[ ➕ Add your SOUL.md ]` (Create a new custom soul)
- Command `/soul` acts as a direct shortcut to switch souls mid-session or inspect the active persona.

## 3. Conversational State for Inbound Content (The "No-Friction" UX Rule)

### The Anti-Pattern: CLI/Server Demands in Chat
When a user clicks "➕ Add your SOUL.md", never reply with manual technical instructions like:
`"1. Save a file to ~/.chiper/souls/... or 2. Type /soul add <name> <content>"`
Users on messaging apps (especially mobile Termius / Telegram) find multi-argument command syntax awkward and frustrating.

### The Correct Pattern: Direct Interactive Prompt State
1. **Set Pending State:** Latch a short-lived state in the platform adapter (e.g. `self._pending_soul_prompt[chat_id] = {"timestamp": time.time()}`).
2. **Prompt in Chat:** Send an intuitive prompt asking the user to send their soul definition directly in their next message:
   - Line 1: Soul Name (e.g. `Chiper-Trader` or `# Chiper Trader`)
   - Line 2+: Soul instructions, behavior, boundaries.
   - Include a `[ ❌ Batal ]` inline button to cancel cleanly.
3. **Intercept Text & Files:**
   - In `_handle_text_message`, if `chat_id` has an active pending prompt, intercept before sending to LLM.
   - Parse name and body, call `save_custom_soul(name, body)`, and confirm activation with action buttons (`[ 🔄 Menu Jiwa ]`, `[ ❌ Selesai ]`).
   - If the user sends a `.md` or `.txt` document file, extract the filename as the name and file text as the body automatically.
   - Provide an escape hatch: typing `batal`, `cancel`, or clicking the cancel button clears the pending state without side effects.

## 4. Container-Isolated Gateway Testing Workflow

When testing gateway changes, bot token switches, or agent modifications without dirtying the host git working tree:
1. **Read-Only Host Mount:** Mount the host repository read-only (`-v /path/to/host/chiper:/repo-src:ro`) into a test Docker container.
2. **Local Sync:** Rsync from `/repo-src` to `/home/ubuntu/chiper` inside the container, keeping `.git` isolated.
3. **Host Network Mode:** Run with `--network host` so the container seamlessly reaches local model endpoints (e.g. `http://localhost:20128/v1`).
4. **Isolate Bot Credentials:** Use dedicated test bot tokens (e.g. `@dilaagent_bot`) in the container's `.env`, leaving the production bot untouched.
5. **Clean Exit Locks:** Ensure `gateway.lock` and `gateway.pid` are cleared when spawning containerized instances.
