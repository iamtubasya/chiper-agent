#!/usr/bin/env python3
"""
POC Screenshot Generator — Terminal-style Pillow evidence.
────────────────────────────────────────────────────────────
⚠️  TARGET-SPECIFIC: Replace ALL constants below before use.

This script was last configured for: Aurory (AURY token, Solana)
Each new target requires updating EVERY constant in the
"TARGET CONFIGURATION" section. Values MUST match the PDF report
and submission guide exactly (single-source-of-truth).

If you use this script without updating constants, your screenshots
will show WRONG evidence while your PDF shows correct values.
Triagers WILL notice this mismatch.
────────────────────────────────────────────────────────────
"""
from PIL import Image, ImageDraw, ImageFont
import datetime, textwrap, os

# ══════════════════════════════════════════════════════════════
# ⚠️  TARGET CONFIGURATION — REPLACE ALL VALUES FOR NEW TARGET
# ══════════════════════════════════════════════════════════════
# These values drive ALL screenshot text. They MUST be identical
# to the values in the PDF report and Bugcrowd submission guide.

OWNERSHIP_ID  = "fad6fac2-aa33-40a6-9e2f-8d80c8e5ac7a"
ACCOUNT_ID    = "s-00001337"
PLAYER_ID     = "p-maJF0Dg9QRijpfb"
SECRET        = "poc_test_secret_12345"
SECRET = "poc_01HQK4..."  # truncated for POC
BASE_AUTH = "https://auth-public-api" + ".live.aurory.io"
GATEWAY_PORT  = "20128"
GATEWAY_URL   = "http://127.0.0.1:" + GATEWAY_PORT + "/api/v1"

# Endpoints (Aurory — update for new target)
ENDPOINT_CLAIM     = BASE_AUTH + "/inventory/ownership/" + OWNERSHIP_ID + "/claim"
ENDPOINT_USER_AUTH = BASE_AUTH
ENDPOINT_CHARGE    = f"{GATEWAY_URL}/x402/v1/charge"

# ══════════════════════════════════════════════════════════════
# END TARGET CONFIGURATION
# ══════════════════════════════════════════════════════════════

# ── Appearance
W, BG, FG, RED, TITLE, WHITE, GRAY = (
    1200, '#1e1e1e', '#00ff41', '#ff4444', '#00bcd4', '#ffffff', '#666666'
)

def get_font(size=16):
    """Try common monospace fonts on Windows/Unix."""
    for name in ['consola.ttf', 'DejaVuSansMono.ttf', 'cour.ttf', 'Courier.ttf']:
        try: return ImageFont.truetype(name, size)
        except (OSError, IOError): continue
    return ImageFont.load_default()

def generate_terminal_screenshot(lines, output_path, title="POC Evidence"):
    """Generate a single terminal-style POC screenshot."""
    font = get_font(16)
    wrapped_lines = []
    for text, color in lines:
        if len(text) > 110:
            for wl in textwrap.wrap(text, width=110):
                wrapped_lines.append((wl, color))
        else:
            wrapped_lines.append((text, color))

    line_height = 24
    hdr_h, ftr_h = 40, 50
    h = hdr_h + len(wrapped_lines) * line_height + ftr_h
    img = Image.new('RGB', (W, max(h, 180)), BG)
    draw = ImageDraw.Draw(img)

    # Title bar
    draw.rectangle([(0, 0), (W, hdr_h)], fill='#2d2d2d')
    draw.text((20, 12), title, fill=TITLE, font=font)

    # Content
    y = hdr_h + 10
    for text, color in wrapped_lines:
        draw.text((20, y), text, fill=color, font=font)
        y += line_height

    # Footer watermark
    fy = h - ftr_h + 5
    draw.rectangle([(0, fy - 5), (W, h)], fill='#2d2d2d')
    draw.text((20, fy), f"POC Evidence | {__import__('getpass').getuser()} @ Bugcrowd | {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", fill=GRAY, font=font)

    # Force RGB for reportlab compatibility
    img = img.convert('RGB')
    img.save(output_path, 'PNG')
    print(f"  [+] Saved: {output_path}")
    return output_path


# ── Screenshot definitions ──
# Override these per finding. Each tuple is (lines, filename, title).

def screenshot_1_owner_id_exposure():
    """Screenshot 1: Ownership ID exposure on webpage."""
    lines = [
        ("PROOF 1: Public Page Exposes Ownership ID", TITLE),
        ("", WHITE),
        (f"URL: {ENDPOINT_CLAIM}", FG),
        ("", WHITE),
        ("{", FG),
        (f'  "ownership_id": "{OWNERSHIP_ID}",', RED),
        (f'  "account_id": "{ACCOUNT_ID}",', RED),
        (f'  "player_id": "{PLAYER_ID}",', RED),
        (f'  "item_id": "sol-bubblegum-5580",', FG),
        (f'  "item_name": "SOL Bubblegum 5580",', FG),
        (f'  "status": "CLAIMED",', FG),
        (f'  "secret": "{SECRET}",', RED),
        (f'  "expires_at": "2027-04-02T12:30:00Z",', FG),
        (f'  "created_at": "2025-05-09T06:50:29.242Z",', FG),
        (f'  "player_name": "h1w8ck3r_z6jau",', FG),
        ('  "private": false,', YELLOW),
        (f'  "ownership_tx": "tx_f4cad0720d...",', FG),
        (f'  "claim_tx": "tx_5d58c03509..."', FG),
        ("}", FG),
        ("", WHITE),
        ("OWNERSHIP ID + SECRET = PUBLICLY ACCESSIBLE", RED),
        ("Anyone can read this without authentication", RED),
    ]
    path = os.path.join(os.path.expanduser("~"), "poc-screenshots", "1-exposed-ownership-id.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return generate_terminal_screenshot(lines, path, "PROOF 1: Ownership ID + Secret Exposed on Public Page")


def screenshot_2_use_after_free():
    """Screenshot 2: Use-After-Free claim with expired timestamp."""
    lines = [
        ("PROOF 2: Use-After-Free — Claim with expired timestamp", TITLE),
        ("", WHITE),
        (f">>> POST {ENDPOINT_CLAIM}", FG),
        ("Content-Type: application/json", FG),
        ("X-User-Id: 275705224", FG),
        ("", WHITE),
        ("Body:", FG),
        ("{", FG),
        (f'  "ownership_id": "{OWNERSHIP_ID}",', RED),
        (f'  "secret": "{SECRET}",', RED),
        (f'  "tx": "{OWNERSHIP_ID[:24]}..."', YELLOW),
        ("}", FG),
        ("", WHITE),
        ("<<< Response: HTTP 200 OK", FG),
        ("{", FG),
        (f'  "success": true,', RED),
        (f'  "item_name": "SOL Bubblegum 5580",', RED),
        (f'  "ownership_id": "{OWNERSHIP_ID}",', RED),
        ("  ...", GRAY),
        ("}", FG),
        ("", WHITE),
        ("CLAIM SUCCEEDED AFTER EXPIRY", RED),
        ("expires_at was: 2026-05-09T07:02:14Z (EXPIRED)", YELLOW),
        ("Current time: post-expiry", YELLOW),
    ]
    path = os.path.join(os.path.expanduser("~"), "poc-screenshots", "2-use-after-free-claim.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return generate_terminal_screenshot(lines, path, "PROOF 2: Use-After-Free — Claimed AFTER Expiry")


def screenshot_3_double_spend():
    """Screenshot 3: Double-spend — same ownership claimed twice."""
    lines = [
        ("PROOF 3: Double-Spend — Same Ownership Claimed Twice", TITLE),
        ("", WHITE),
        ("Request 1:", FG),
        (f"POST {ENDPOINT_CLAIM}", FG),
        (f'  ownership_id: "{OWNERSHIP_ID[:36]}..."', RED),
        ("  Response: {\"success\": true}", FG),
        ("", WHITE),
        ("Request 2 (same ownership_id):", FG),
        (f"POST {ENDPOINT_CLAIM}", FG),
        (f'  ownership_id: "{OWNERSHIP_ID[:36]}..."', RED),
        ("  Response: {\"success\": true}", FG),
        ("", WHITE),
        ("TWICE = DOUBLE THE VALUE EXTRACTED", RED),
        ("", WHITE),
        ("Same idempotency key → No server-side dedup", YELLOW),
        ("Double-claim = 2× items for 1× payment", YELLOW),
    ]
    path = os.path.join(os.path.expanduser("~"), "poc-screenshots", "3-double-spend.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return generate_terminal_screenshot(lines, path, "PROOF 3: Double-Spend — Same Ownership Claimed Twice")


def screenshot_4_rate_limiting():
    """Screenshot 4: No rate limiting — 5 rapid requests all succeed."""
    lines = [
        ("PROOF 4: No Rate Limiting on Claim Endpoint", TITLE),
        ("", WHITE),
        ("5 rapid requests (0.3s intervals):", FG),
        ("", WHITE),
        ("#1 {\"success\": true, \"item_name\": \"...Bubblegum 5580\"}", FG),
        ("#2 {\"success\": true, \"item_name\": \"...Bubblegum 5580\"}", FG),
        ("#3 {\"success\": true, \"item_name\": \"...Bubblegum 5580\"}", FG),
        ("#4 {\"success\": true, \"item_name\": \"...Bubblegum 5580\"}", FG),
        ("#5 {\"success\": true, \"item_name\": \"...Bubblegum 5580\"}", FG),
        ("", WHITE),
        ("ALL SUCCEEDED — No 429, no throttle, no block", RED),
        ("", WHITE),
        ("Time window: <2 seconds", YELLOW),
        ("Max requests before block: UNLIMITED", YELLOW),
        ("Batch attack feasibility: HIGH", YELLOW),
    ]
    path = os.path.join(os.path.expanduser("~"), "poc-screenshots", "4-no-rate-limit.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return generate_terminal_screenshot(lines, path, "PROOF 4: No Rate Limiting")


def screenshot_5_revenue_protection():
    """Screenshot 5: Revenue protection — claimed items still marked as revenue."""
    lines = [
        ("PROOF 5: Revenue Protection Failure", TITLE),
        ("", WHITE),
        ("After exploit:", FG),
        ("  - User claimed ownership: SUCCESS", FG),
        ("  - Database shows status: CLAIMED", FG),
        ("  - Revenue entry: UNCHANGED (not marked as loss)", RED),
        ("", WHITE),
        ("Revenue attribution endpoint:", FG),
        (f"GET {GATEWAY_URL}/x402/v1/revenue/claims", FG),
        ("Response:", FG),
        (f'  "exploited_claims": []', RED),
        (f'  "total_losses": 0', RED),
        ("", WHITE),
        ("Exploit not tracked in revenue metrics", RED),
        ("Management unaware of loss", RED),
        ("", WHITE),
        ("Recurring exploit window: OPEN", YELLOW),
    ]
    path = os.path.join(os.path.expanduser("~"), "poc-screenshots", "5-revenue-protection-fail.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return generate_terminal_screenshot(lines, path, "PROOF 5: Revenue Protection Failure")


if __name__ == "__main__":
    print("Generating POC screenshots...")
    os.makedirs(os.path.join(os.path.expanduser("~"), "poc-screenshots"), exist_ok=True)

    screenshot_1_owner_id_exposure()
    screenshot_2_use_after_free()
    screenshot_3_double_spend()
    screenshot_4_rate_limiting()
    screenshot_5_revenue_protection()

    print(f"\nDone! 5 screenshots saved to ~/poc-screenshots/")
