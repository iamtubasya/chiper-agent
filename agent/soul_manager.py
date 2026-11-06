"""
Chiper Agent - Soul / Persona Manager.

Manages switching and customizing agent identities (SOUL.md)
such as Chiper-Cyber (Bug Bounty & Offensive Security), Chiper-Dev (Full-Stack Engineer),
and user-defined custom souls.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from chiper_constants import get_chiper_home

logger = logging.getLogger(__name__)

# Built-in Chiper-Dev soul content
CHIPER_DEV_SOUL = """# SOUL.md — Chiper Dev: Senior Full-Stack Software Engineer & Architect

## 1. Identitas
Kamu adalah **Chiper-Dev**, seorang Senior Full-Stack Software Engineer, System Architect, dan DevOps Specialist kelas dunia.
Kamu berpikir seperti principal engineer: **pragmatis, teliti, efisien, dan selalu berorientasi pada software yang berfungsi nyata (working software).**

- **Peran:** Autonomous Coding Agent, Senior Architect, dan Full-Stack Problem Solver.
- **Mindset:** First principles, clean code, maintainability, modularity, high performance, dan user experience.
- **Tujuan akhir:** Menghasilkan solusi kode yang elegan, memecahkan bug sampai ke akar masalah, merancang arsitektur sistem yang scalable, dan mengoptimalkan performa.
- **Kepribadian:** Tenang, fokus, jujur, proaktif, dan to-the-point. Tidak membuat kode yang setengah jadi atau stub palsu.

## 2. Nilai Inti & Prinsip Kerja
1. **Working Code Over Fluff:** Solusi terbaik adalah kode nyata yang teruji, bukan sekadar teori panjang.
2. **First Understand, Then Implement:** Pahami konteks arsitektur dan akar masalah sebelum menulis kode. Hindari tambal-sulam sporadis.
3. **Clean, Idiomatic, and Maintainable:** Tulis kode yang rapi, terbaca jelas, terstruktur modular, dan mengikuti best practices bahasa/framework terkait.
4. **Test & Verify:** Buktikan bahwa kode bekerja dengan pengujian nyata, build checks, linter, dan eksekusi command.
5. **Simplicity First (KISS & YAGNI):** Jangan membuat sistem terlalu rumit (over-engineering). Solusi paling elegan adalah yang paling sederhana yang menyelesaikan masalah.
6. **Robust Error Handling:** Antisipasi edge cases, network failure, concurrency race conditions, dan invalid input secara gracefully.

## 3. Keahlian & Spesialisasi
- **Languages & Frameworks:** Python, TypeScript/JavaScript, Go, Rust, C/C++, React, Vue, Next.js, FastAPI, Node.js, Django.
- **Systems & Architecture:** Distributed systems, microservices, asynchronous I/O, event-driven design, REST, GraphQL, WebSocket, gRPC.
- **Database & Storage:** PostgreSQL, SQLite, MySQL, Redis, MongoDB, schema design, index optimization, migrations.
- **DevOps & Cloud:** Docker, Linux internals, systemd, bash/shell scripting, CI/CD pipelines, reverse proxy (Nginx, Caddy, Cloudflare).
- **Quality & Debugging:** Profiling, memory leak analysis, systematic root cause debugging, unit/integration testing (pytest, jest).

## 4. Gaya Komunikasi
- Bahasa default: **Bahasa Indonesia** santai namun profesional (istilah teknis tetap dalam English).
- Ringkas, terstruktur, langsung ke solusi.
- Tampilkan diff atau perintah yang relevan dengan jelas.
"""

# Default curated memory per soul
DEFAULT_SOUL_MEMORIES: Dict[str, str] = {
    "chiper-cyber": """User maintains Chiper agent repo /home/agentuser/chiper (github.com/iamtubasya/chiper-agent). Runtime home ~/.chiper (no .chiperflux). 140-domain chiper-cyber suite + core CLI tools (nmap, sqlmap, subfinder, httpx, nuclei, ffuf, gobuster, hydra, whatweb, wafw00f) di /usr/bin & /usr/local/bin.
§
Akun test chiperflux15@gmail.com VALID (2FA Google Auth + SMS ending 89, butuh OTP user). Email ini terhubung himalaya CLI (IMAP/SMTP) → bisa baca/kirim kode verifikasi. KYC tak perlu utk API-key/IDOR.
§
Sesi utama "AGENT-CHIPER-SECURITY" tersimpan permanen di state.db + ~/.chiper/sessions/AGENT-CHIPER-SECURITY.json (setup chiper-cyber, 140 skills, 10 core tools, SOUL.md self-healing).
§
Engagement aktif: odin.ai (Mozilla 0DIN) GenAI bounty — $500-15k, self-hosted, 0din@mozilla.com. Alur: submit abstract dulu → 3 hari kerja jawab in-scope+range. Scope: Prompt Extraction/Guardrail+Interpreter Jailbreak/Content Manipulation/Weights Disclosure + app bugs (prompt injection→Read/Write/Execute). Butuh akun+KYC utk payout. Intel ~/workspace/odin-ai/target-intel.md. garak 0.17.1+promptfoo di ~/workspace/odin-ai/venv (--no-deps, hindari torch). Blocker: belum ada API key LLM.
§
Browser: agent-browser + Chrome 157 terinstall di ~/.agent-browser.
§
User sering minta aksi grey/black (farm API key, scrape key bocor di X, bypass auth) — pola berulang.""",

    "chiper-dev": """User maintains independent ChiperRouter instance at `/home/agentuser/chiperrouter` (fork of 9router). State & SQLite DB located at `~/.chiperrouter`, CLI binary `chiperrouter`, running on port 20130 via `chiperrouter.service` (coexists with 9router on 20128). Exposed via Cloudflare tunnel as https://router.chiper.site. Web UI styled in Neon Cyan Cyber Obsidian.
§
User maintains Chiper agent repo at `/home/agentuser/chiper` (github.com/iamtubasya/chiper-agent) on branch main. Backup mirror repository at `iamtubasya/chiper-agent-backup`. Runtime home ~/.chiper.
§
Browser: agent-browser + Chrome 157 terinstall di ~/.agent-browser.
§
Test container `chiper-installer-test` active (Ubuntu 24.04, --network host, repo :ro, bot @dilaagent_bot). Mode test: jangan git push. Multi-soul switcher: /new & /soul trigger buttons (Chiper-Cyber, Chiper-Dev, Chiper-Web3). Sub-skills standardized under chiper-*.""",

    "chiper-web3": """Solana/SBF: Rust 1.99.1, Agave 4.3.2, cargo-build-sbf 4.4.0. Pin time 0.3.36. Metaplex: on-chain only, repo ~/workspace/metaplex.
§
Akun test chiperflux15@gmail.com VALID (2FA Google Auth + SMS ending 89, butuh OTP user). Email ini terhubung himalaya CLI (IMAP/SMTP) → bisa baca/kirim kode verifikasi. KYC tak perlu utk API-key/IDOR.
§
Chiper-Web3 suite & Hermes crypto engine (H1-H10) di `~/.chiper/skills/chiper-web3/`. RPC fallback: Ethereum (eth.llamarpc.com), Base (mainnet.base.org), Arbitrum, Polygon, Optimism, Solana. Spend Governor circuit breaker: max $500/tx, $2000/day, max slippage 5%, require simulation. CTF solvers di tools/ctf/."""
}


def get_souls_dir() -> Path:
    """Return the souls storage directory (~/.chiper/souls)."""
    souls_dir = get_chiper_home() / "souls"
    souls_dir.mkdir(parents=True, exist_ok=True)
    return souls_dir


def get_soul_memory_dir() -> Path:
    """Return the soul-isolated memories directory (~/.chiper/memories/souls)."""
    mem_dir = get_chiper_home() / "memories" / "souls"
    mem_dir.mkdir(parents=True, exist_ok=True)
    return mem_dir


def get_soul_memory_path(soul_id: str) -> Path:
    """Return path to a specific soul's memory file."""
    clean_id = soul_id.lower().strip()
    return get_soul_memory_dir() / f"{clean_id}.md"


def ensure_default_soul_memories() -> None:
    """Ensure default soul memory files exist in ~/.chiper/memories/souls/."""
    souls_mem_dir = get_soul_memory_dir()
    for s_id, default_content in DEFAULT_SOUL_MEMORIES.items():
        mem_path = souls_mem_dir / f"{s_id}.md"
        if not mem_path.exists():
            try:
                mem_path.write_text(default_content.strip(), encoding="utf-8")
            except Exception as e:
                logger.warning("Failed to initialize soul memory for %s: %s", s_id, e)


def sync_soul_memory_on_switch(from_soul_id: Optional[str], to_soul_id: str) -> None:
    """Sync active MEMORY.md to previous soul file and activate target soul memory."""
    ensure_default_soul_memories()
    chiper_home = get_chiper_home()
    memories_dir = chiper_home / "memories"
    memories_dir.mkdir(parents=True, exist_ok=True)
    active_mem = memories_dir / "MEMORY.md"

    # 1. Save current memory state to from_soul_id
    if from_soul_id and from_soul_id not in ("unknown", ""):
        from_path = get_soul_memory_path(from_soul_id)
        if active_mem.exists():
            try:
                content = active_mem.read_text(encoding="utf-8").strip()
                if content:
                    from_path.write_text(content, encoding="utf-8")
            except Exception as e:
                logger.warning("Failed to save memory for %s: %s", from_soul_id, e)

    # 2. Load target soul memory into active MEMORY.md
    to_path = get_soul_memory_path(to_soul_id)
    if not to_path.exists():
        init_content = DEFAULT_SOUL_MEMORIES.get(to_soul_id.lower(), "")
        to_path.write_text(init_content, encoding="utf-8")

    try:
        shutil.copy2(to_path, active_mem)
    except Exception as e:
        logger.error("Failed to copy target soul memory to MEMORY.md: %s", e)


def ensure_default_souls() -> None:
    """Ensure default soul files (cyber & dev) exist in ~/.chiper/souls."""
    souls_dir = get_souls_dir()
    chiper_home = get_chiper_home()

    # 1. Chiper-Cyber
    cyber_dest = souls_dir / "chiper-cyber.md"
    if not cyber_dest.exists():
        # Check source candidates
        cyber_src = chiper_home / "SOUL.md"
        if not cyber_src.exists():
            # Fallback to skills repo if available
            cyber_src = Path(__file__).resolve().parent.parent / "skills" / "chiper-cyber" / "SOUL.md"
        
        if cyber_src.exists():
            try:
                shutil.copy2(cyber_src, cyber_dest)
            except Exception as e:
                logger.warning("Failed to copy Chiper-Cyber SOUL.md: %s", e)
        else:
            # Minimal fallback
            cyber_dest.write_text("# SOUL.md — Chiper-Cyber\n\nKamu adalah Chiper-cyber, bug bounty hunter.", encoding="utf-8")

    # 2. Chiper-Dev
    dev_dest = souls_dir / "chiper-dev.md"
    if not dev_dest.exists():
        try:
            dev_dest.write_text(CHIPER_DEV_SOUL, encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to write Chiper-Dev SOUL.md: %s", e)

    # 3. Chiper-Web3
    web3_dest = souls_dir / "chiper-web3.md"
    if not web3_dest.exists():
        web3_src = chiper_home / "skills" / "chiper-web3" / "SOUL.md"
        if not web3_src.exists():
            web3_src = Path(__file__).resolve().parent.parent / "skills" / "chiper-web3" / "SOUL.md"
        if web3_src.exists():
            try:
                shutil.copy2(web3_src, web3_dest)
            except Exception as e:
                logger.warning("Failed to copy Chiper-Web3 SOUL.md: %s", e)


def list_souls() -> List[Dict[str, Any]]:
    """List all available souls in ~/.chiper/souls.
    
    Returns a list of dicts:
    [
        {"id": "chiper-cyber", "name": "Chiper-Cyber", "icon": "🛡️", "desc": "Bug Bounty & Pentest", "path": ...},
        {"id": "chiper-dev", "name": "Chiper-Dev", "icon": "💻", "desc": "Full-Stack Engineer & Architect", "path": ...},
        ...
    ]
    """
    ensure_default_souls()
    souls_dir = get_souls_dir()
    souls: List[Dict[str, Any]] = []

    # Map well-known IDs to metadata
    well_known = {
        "chiper-cyber": {
            "name": "Chiper-Cyber",
            "icon": "🛡️",
            "desc": "Bug Bounty Hunter & Offensive Security",
            "priority": 1,
        },
        "chiper-dev": {
            "name": "Chiper-Dev",
            "icon": "💻",
            "desc": "Senior Full-Stack Engineer & Architect",
            "priority": 2,
        },
        "chiper-web3": {
            "name": "Chiper-Web3",
            "icon": "⚡",
            "desc": "Web3, Crypto Ops, DeFi & CTF Whitehat",
            "priority": 3,
        },
    }

    for p in sorted(souls_dir.glob("*.md")):
        soul_id = p.stem.lower()
        if soul_id in well_known:
            meta = well_known[soul_id]
            souls.append({
                "id": soul_id,
                "name": meta["name"],
                "icon": meta["icon"],
                "desc": meta["desc"],
                "path": str(p),
                "priority": meta["priority"],
            })
        else:
            # Custom user-added soul: extract title from first line if available
            title = soul_id.replace("-", " ").replace("_", " ").title()
            desc = "Custom Soul / Persona"
            try:
                first_lines = p.read_text(encoding="utf-8").splitlines()[:5]
                for line in first_lines:
                    line = line.strip()
                    if line.startswith("#"):
                        raw_title = line.lstrip("#").strip()
                        # Clean common prefixes like 'SOUL.md —' or 'SOUL.md -'
                        if "—" in raw_title:
                            raw_title = raw_title.split("—")[1].strip()
                        elif " - " in raw_title:
                            raw_title = raw_title.split(" - ")[1].strip()
                        if ":" in raw_title:
                            raw_title = raw_title.split(":")[0].strip()
                        title = raw_title or title
                        break
            except Exception:
                pass

            souls.append({
                "id": soul_id,
                "name": title,
                "icon": "🧠",
                "desc": desc,
                "path": str(p),
                "priority": 10,
            })

    souls.sort(key=lambda s: s["priority"])
    return souls


def get_active_soul() -> Dict[str, Any]:
    """Detect which soul is currently active in ~/.chiper/SOUL.md."""
    chiper_home = get_chiper_home()
    active_path = chiper_home / "SOUL.md"
    if not active_path.exists():
        return {
            "id": "unknown",
            "name": "Default",
            "icon": "⚙️",
            "desc": "No active SOUL.md",
        }

    try:
        content = active_path.read_text(encoding="utf-8")
        if "Chiper-cyber" in content or "Professional Bug Bounty Hunter" in content or "Hacker Laws" in content:
            return {
                "id": "chiper-cyber",
                "name": "Chiper-Cyber",
                "icon": "🛡️",
                "desc": "Bug Bounty Hunter & Offensive Security",
            }
        elif "Chiper Dev" in content or "Senior Full-Stack" in content or "Chiper-Dev" in content:
            return {
                "id": "chiper-dev",
                "name": "Chiper-Dev",
                "icon": "💻",
                "desc": "Senior Full-Stack Engineer & Architect",
            }
        elif "Chiper-Web3" in content or "ChiperAgent Web3" in content or "SUPERAGENT" in content:
            return {
                "id": "chiper-web3",
                "name": "Chiper-Web3",
                "icon": "⚡",
                "desc": "Web3, Crypto Ops, DeFi & CTF Whitehat",
            }
        else:
            # Check custom souls
            first_line = content.splitlines()[0] if content.splitlines() else "Custom Soul"
            name = first_line.lstrip("#").strip() or "Custom Soul"
            return {
                "id": "custom",
                "name": name,
                "icon": "🧠",
                "desc": "User Custom SOUL.md",
            }
    except Exception as e:
        logger.debug("Failed to inspect active SOUL.md: %s", e)
        return {
            "id": "unknown",
            "name": "Active",
            "icon": "🎭",
            "desc": "Active SOUL.md",
        }


def switch_soul(soul_id: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Switch active SOUL.md to the specified soul_id and swap isolated memory.
    
    Returns (success, message, soul_dict).
    """
    ensure_default_souls()
    ensure_default_soul_memories()
    souls_dir = get_souls_dir()
    target_path = souls_dir / f"{soul_id.lower()}.md"

    if not target_path.exists():
        # Try finding by name substring
        for p in souls_dir.glob("*.md"):
            if soul_id.lower() in p.stem.lower():
                target_path = p
                soul_id = p.stem.lower()
                break

    if not target_path.exists():
        return False, f"Soul '{soul_id}' tidak ditemukan di ~/.chiper/souls/", {}

    prev_soul = get_active_soul()
    prev_id = prev_soul.get("id")

    dest_path = get_chiper_home() / "SOUL.md"
    try:
        shutil.copy2(target_path, dest_path)
        # Sync isolated memory on switch
        sync_soul_memory_on_switch(prev_id, soul_id)
        souls = list_souls()
        active = next((s for s in souls if s["id"] == soul_id), {
            "id": soul_id,
            "name": soul_id.title(),
            "icon": "🎭",
            "desc": "Active Soul",
        })
        return True, f"Berhasil mengaktifkan jiwa {active['icon']} *{active['name']}* dengan memori terisolasi", active
    except Exception as e:
        logger.error("Failed to switch soul to %s: %s", soul_id, e)
        return False, f"Gagal mengaktifkan jiwa: {e}", {}


def save_custom_soul(soul_id: str, content: str) -> Tuple[bool, str]:
    """Save a new custom soul to ~/.chiper/souls/<soul_id>.md."""
    if not soul_id or not content.strip():
        return False, "Nama jiwa dan isi SOUL.md tidak boleh kosong."

    clean_id = "".join(c if c.isalnum() or c in "-_" else "-" for c in soul_id.lower()).strip("-")
    if not clean_id:
        clean_id = "custom-soul"

    souls_dir = get_souls_dir()
    dest = souls_dir / f"{clean_id}.md"

    try:
        dest.write_text(content.strip(), encoding="utf-8")
        # Also activate it immediately
        switch_soul(clean_id)
        return True, f"Berhasil menyimpan dan mengaktifkan jiwa baru: *{clean_id}* (disimpan di {dest})"
    except Exception as e:
        logger.error("Failed to save custom soul %s: %s", clean_id, e)
        return False, f"Gagal menyimpan custom soul: {e}"
