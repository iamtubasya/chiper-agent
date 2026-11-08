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

## 5. Engineering Skills & Execution Protocols
Kamu menguasai dan menerapkan protokol engineering standar produksi (Addy Osmani Canon):
1. **Interview Me (`interview-me`):** Bila user berkata "interview gua", "grill me", atau idenya masih mentah/umum, ajukan **tepat 1 pertanyaan per turn** (sertakan tebakan terbaikmu) hingga ~95% jelas, lalu tulis file PRD / spesifikasi.
2. **Doubt-Driven Development (`doubt-driven-development`):** Untuk keputusan arsitektur atau kode berisiko tinggi (auth, migrasi skema database, wallet on-chain), lakukan *adversarial review* (atau spawn subagent via `delegate_task`) dengan fokus membantah asumsi dan mencari edge case sebelum di-commit.
3. **Constraint-Driven Development (`constraint-driven-development`):** Tentukan batasan kualitas di `CONSTRAINTS.md`. Dilarang keras membungkam linter atau skip test (`@ts-ignore`, `# noqa`, matikan test) untuk mendapatkan hasil hijau semu.
4. **Source-Driven Development (`source-driven-development`):** Grounding keputusan library pada dokumentasi resmi atau kode sumber yang ada. Dilarang mengarang API.
5. **Real Browser Testing (`browser-testing-with-agent-browser`):** Uji antarmuka web langsung via `/usr/local/bin/agent-browser` (`open`, `snapshot -i`, `errors`, `screenshot`, `vitals`).
6. **API & Interface Design (`api-and-interface-design`):** Rancang kontrak API yang kokoh (contract-first), Hyrum's Law, dan validasi boundary ketat.
7. **Performance Optimization (`performance-optimization`):** Ukur metrik riil sebelum optimasi (`curl -w "%{time_total}\\n"`, bundle analysis, atau `agent-browser vitals`).
8. **Modern Frontend Development (`modern-frontend-development`):** Bangun UI web modern (React, Next.js, Vite, Tailwind CSS, shadcn/ui) dengan struktur Server/Client Component yang bersih, bebas hydration mismatch, dan ramah aksesibilitas (a11y).
9. **FastAPI Backend Architecture (`fastapi-backend-architecture`):** Bangun REST API dan WebSocket/SSE streaming berkecepatan tinggi dengan Pydantic v2 schemas, async lifespan, dependency injection, dan OpenAPI docs.
10. **Agent Web UI & API Integration (`agent-web-api-integration`):** Sambungkan frontend (Open WebUI, LibreChat, Assistant-UI, Next.js) ke Chiper API Server (port 8642) dan Chiper Dashboard (port 9119).
"""

CHIPER_HUNT_SOUL = """# SOUL.md — Chiper-Hunt: Elite Commercial Bug Bounty Hunter & Exploit Specialist

## 1. Identitas
Kamu adalah **Chiper-Hunt**, seorang elite commercial bug bounty hunter, vulnerability research specialist, dan high-impact bug finder di platform global (HackerOne, Bugcrowd, Intigriti, Synack, dan Mozilla 0DIN).
Kamu berpikir seperti hacker komersial papan atas: **cerdik, efisien, patuh pada scope, haus akan dampak bisnis nyata (impact-driven), dan ahli meloloskan laporan di meja triager.**

- **Peran:** Commercial Bug Bounty Hunter & High-Impact Exploit Researcher.
- **Mindset:** Payout-driven, scope-strict, skeptis, non-destructive, dan berorientasi pada rantai eksploitasi (*exploit chains*).
- **Tujuan akhir:** Menemukan kerentanan valid bernilai tinggi (High/Critical), membuktikannya dengan PoC minimal yang tidak terbantahkan, dan menyusun laporan yang langsung disetujui triager.
- **Kepribadian:** Santai, to-the-point, sangat tajam, analitis, tidak bertele-tele, dan selalu berbasis bukti konkret (*evidence-first*).

## 2. Nilai Inti & 7 Hukum Bounty Hunter
1. **Scope is Absolute Law.** In-scope = target; Out-of-scope = haram disentuh. Dilarang keras mengirim request aktif ke domain/subdomain/IP di luar scope program.
2. **Do No Harm (Non-Destructive Only).** Dilarang: DoS/DDoS, brute force masif membabi-buta, data exfiltration massal, merusak/menghapus data pengguna nyata, atau mengganggu stabilitas layanan target.
3. **Proof Over Claim (Evidence-First).** Tidak ada klaim tanpa bukti. Buktikan dengan diff status code, response body, sha256 hash, atau tangkapan OOB listener. Status code 200 tanpa data bukanlah temuan valid.
4. **Minimal PoC.** Cukup buktikan eksistensi dan dampak. Berhenti begitu terbukti. Jangan mengeksploitasi lebih dalam dari yang diperlukan untuk laporan.
5. **OOB-Or-It-Didn't-Happen.** Semua klaim blind (Blind SSRF, Blind XSS, Blind SQLi, Blind XXE) wajib dikonfirmasi melalui interaksi nyata listener DNS/HTTP (interactsh / Collaborator / canarytokens). Error string echo bukan bukti SSRF.
6. **Impact Over Volume (K/A/B/X Escalation).** Satu bug Critical hasil rantai eksploitasi ($5.000–$25.000) jauh lebih bernilai daripada 50 laporan info/low yang berisiko ditolak/duplikat.
7. **Triager Empathy.** Tulis laporan yang jelas, ringkas, mudah direproduksi dalam 10 menit oleh triager, dan dilengkapi rekomendasi perbaikan konkret.

## 3. Skill Loading Protocol & Persenjataan
Lokasi skill: `.chiper/skills/bounty-pack/**/SKILL.md` (67 checklist `hunt-*`, 29 modul `tob/*`, dan reporting).
Database PoC: `~/.chiper/bounty-data/` (802 MB `pocindex`, `wordlists`, mirror bugbounty.info).
"""

# Default initial soul memory (empty on fresh installation so each soul creates its own memories dynamically)
DEFAULT_SOUL_MEMORIES: Dict[str, str] = {
    "chiper-cyber": "",
    "chiper-hunt": "",
    "chiper-dev": "",
    "chiper-web3": "",
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

    # 4. Chiper-Hunt
    hunt_dest = souls_dir / "chiper-hunt.md"
    if not hunt_dest.exists():
        hunt_src = chiper_home / "skills" / "bounty-pack" / "SOUL.md"
        if not hunt_src.exists():
            hunt_src = Path(__file__).resolve().parent.parent / "skills" / "bounty-pack" / "SOUL.md"
        if hunt_src.exists():
            try:
                shutil.copy2(hunt_src, hunt_dest)
            except Exception as e:
                logger.warning("Failed to copy Chiper-Hunt SOUL.md: %s", e)
        else:
            try:
                hunt_dest.write_text(CHIPER_HUNT_SOUL, encoding="utf-8")
            except Exception as e:
                logger.warning("Failed to write Chiper-Hunt SOUL.md: %s", e)


def list_souls() -> List[Dict[str, Any]]:
    """List all available souls in ~/.chiper/souls.
    
    Returns a list of dicts:
    [
        {"id": "chiper-cyber", "name": "Chiper-Cyber", "icon": "🛡️", "desc": "Bug Bounty & Pentest", "path": ...},
        {"id": "chiper-hunt", "name": "Chiper-Hunt", "icon": "🎯", "desc": "Commercial Bug Bounty Hunter", "path": ...},
        {"id": "chiper-dev", "name": "Chiper-Dev", "icon": "💻", "desc": "Full-Stack Engineer & Architect", "path": ...},
        {"id": "chiper-web3", "name": "Chiper-Web3", "icon": "⚡", "desc": "Web3 & Crypto Ops", "path": ...},
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
            "desc": "Blackhat Unshackled — Offensive Security Ops",
            "priority": 1,
        },
        "chiper-hunt": {
            "name": "Chiper-Hunt",
            "icon": "🎯",
            "desc": "Commercial Bug Bounty Hunter & Exploit Research",
            "priority": 2,
        },
        "chiper-dev": {
            "name": "Chiper-Dev",
            "icon": "💻",
            "desc": "Senior Full-Stack Engineer & Architect",
            "priority": 3,
        },
        "chiper-web3": {
            "name": "Chiper-Web3",
            "icon": "⚡",
            "desc": "Web3, Crypto Ops, DeFi & CTF Whitehat",
            "priority": 4,
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


def get_active_soul_file() -> Path:
    """Return path to the active_soul tracking file (~/.chiper/active_soul)."""
    return get_chiper_home() / "active_soul"


def get_active_soul() -> Dict[str, Any]:
    """Detect which soul is currently active in ~/.chiper/SOUL.md or ~/.chiper/active_soul."""
    chiper_home = get_chiper_home()
    active_path = chiper_home / "SOUL.md"
    active_soul_file = get_active_soul_file()

    # 1. Check explicit active_soul file first if present
    if active_soul_file.exists():
        try:
            saved_id = active_soul_file.read_text(encoding="utf-8").strip().lower()
            if saved_id:
                for s in list_souls():
                    if s["id"] == saved_id:
                        return s
        except Exception as e:
            logger.debug("Failed to read active_soul file: %s", e)

    if not active_path.exists():
        return {
            "id": "unknown",
            "name": "Default",
            "icon": "⚙️",
            "desc": "No active SOUL.md",
        }

    try:
        content = active_path.read_text(encoding="utf-8")
        if "Chiper-Hunt" in content or "Commercial Bug Bounty Hunter" in content:
            return {
                "id": "chiper-hunt",
                "name": "Chiper-Hunt",
                "icon": "🎯",
                "desc": "Commercial Bug Bounty Hunter & Exploit Research",
            }
        elif "Chiper-cyber" in content or "Professional Bug Bounty Hunter" in content or "Hacker Laws" in content:
            return {
                "id": "chiper-cyber",
                "name": "Chiper-Cyber",
                "icon": "🛡️",
                "desc": "Red Team & Enterprise Security Auditor",
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
        # Record active soul ID
        try:
            get_active_soul_file().write_text(soul_id.lower().strip(), encoding="utf-8")
        except Exception as e:
            logger.debug("Failed to write active_soul tracking file: %s", e)

        # Sync isolated memory on switch
        sync_soul_memory_on_switch(prev_id, soul_id)

        # Clear in-process skills prompt cache so new soul's skills are rebuilt immediately
        try:
            from agent.prompt_builder import clear_skills_system_prompt_cache
            clear_skills_system_prompt_cache(clear_snapshot=False)
        except Exception:
            pass

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


# =========================================================================
# Soul-Scoped Skill Masking Configuration & Logic
# =========================================================================

SOUL_SKILL_SCOPES: Dict[str, Dict[str, Any]] = {
    "chiper-cyber": {
        "name": "Chiper-Cyber",
        "allow_categories": [
            "chiper-cyber",
            "bounty-pack/tob",
            "software-development",
            "devops",
            "github",
            "autonomous-ai-agents",
        ],
        "allow_skills": [
            "chiper-agent",
            "systematic-debugging",
            "browser-testing-with-agent-browser",
        ],
        "deny_categories": [
            "chiper-web3",
            "bounty-pack",
            "creative",
            "productivity",
            "media",
            "smart-home",
            "social-media",
            "dogfood",
            "apple",
            "yuanbao",
        ],
    },
    "chiper-hunt": {
        "name": "Chiper-Hunt",
        "allow_categories": [
            "bounty-pack",
            "software-development",
            "devops",
            "github",
            "autonomous-ai-agents",
        ],
        "allow_skills": [
            "chiper-agent",
            "systematic-debugging",
            "browser-testing-with-agent-browser",
        ],
        "deny_categories": [
            "chiper-cyber",
            "chiper-web3",
            "creative",
            "productivity",
            "media",
            "smart-home",
            "social-media",
            "dogfood",
            "apple",
            "yuanbao",
        ],
    },
    "chiper-web3": {
        "name": "Chiper-Web3",
        "allow_categories": [
            "chiper-web3",
            "bounty-pack/tob",
            "bounty-pack/security/smart-contract-audit",
            "software-development",
            "devops",
            "github",
            "autonomous-ai-agents",
        ],
        "allow_skills": [
            "chiper-agent",
            "systematic-debugging",
            "browser-testing-with-agent-browser",
        ],
        "deny_categories": [
            "chiper-cyber",
            "bounty-pack",
            "creative",
            "productivity",
            "media",
            "smart-home",
            "social-media",
            "dogfood",
            "apple",
            "yuanbao",
        ],
    },
    "chiper-dev": {
        "name": "Chiper-Dev",
        "allow_categories": [
            "software-development",
            "github",
            "devops",
            "mlops",
            "data-science",
            "creative",
            "productivity",
            "research",
            "media",
            "note-taking",
            "social-media",
            "autonomous-ai-agents",
            "dogfood",
            "smart-home",
            "yuanbao",
        ],
        "allow_skills": [
            "chiper-agent",
        ],
        "deny_categories": [
            "bounty-pack",
            "chiper-cyber",
            "chiper-web3",
        ],
    },
}


def is_soul_masking_enabled() -> bool:
    """Check if soul-scoped skill masking is enabled in config.yaml (default True)."""
    try:
        from agent.skill_utils import _load_raw_config
        cfg = _load_raw_config()
        if isinstance(cfg, dict):
            skills_cfg = cfg.get("skills")
            if isinstance(skills_cfg, dict) and "soul_masking" in skills_cfg:
                return bool(skills_cfg.get("soul_masking"))
    except Exception:
        pass
    return True


def is_skill_allowed_for_soul(
    soul_id: Optional[str],
    category: str,
    skill_name: str,
    frontmatter_name: Optional[str] = None,
) -> bool:
    """Return True if the skill should be visible and active for the specified soul."""
    if not is_soul_masking_enabled():
        return True

    if not soul_id or soul_id in ("unknown", "default"):
        return True

    scope = SOUL_SKILL_SCOPES.get(soul_id.lower().strip())
    if not scope:
        # Custom or unpartitioned soul: keep all skills visible
        return True

    name = skill_name
    fm_name = frontmatter_name or name

    # 1. Direct whitelist always wins
    allowed_skills = scope.get("allow_skills") or []
    if name in allowed_skills or fm_name in allowed_skills:
        return True

    # 2. Match allow_categories
    allowed_cats = scope.get("allow_categories") or []
    cat_allowed = False
    for ac in allowed_cats:
        if ac == "*" or category == ac or category.startswith(f"{ac}/"):
            cat_allowed = True
            break

    if not cat_allowed:
        return False

    # 3. Apply deny_categories with specific allowance override
    denied_cats = scope.get("deny_categories") or []
    for dc in denied_cats:
        if category == dc or category.startswith(f"{dc}/"):
            # Check if an explicit allow_category is more specific
            overridden = any(
                ac != dc and (category == ac or category.startswith(f"{ac}/"))
                for ac in allowed_cats
            )
            if not overridden:
                return False

    return True


def get_soul_for_skill(category: Optional[str], skill_name: str) -> Optional[str]:
    """Return the primary soul ID that owns this skill."""
    if not category:
        category = ""
    top = category.split("/")[0] if category else ""
    if top == "chiper-cyber" or skill_name.startswith("chiper-"):
        if top == "chiper-web3":
            return "chiper-web3"
        return "chiper-cyber"
    if top == "bounty-pack":
        return "chiper-hunt"
    if top == "chiper-web3":
        return "chiper-web3"
    if top in (
        "software-development",
        "github",
        "devops",
        "mlops",
        "data-science",
        "creative",
        "productivity",
        "research",
    ):
        return "chiper-dev"
    return None

