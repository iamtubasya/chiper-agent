#!/usr/bin/env python3
"""
Branding Lint Rule — Scan repository for stale "hermes" references.

Usage:
    python3 scripts/branding-lint.py              # Scan entire repo
    python3 scripts/branding-lint.py --staged      # Scan only staged files
    python3 scripts/branding-lint.py --fix         # Interactive fix mode
    python3 scripts/branding-lint.py --ci          # CI mode (exit 1 on violations)

Exit codes:
    0 — Clean (no violations)
    1 — Violations found
    2 — Error
"""

import os
import re
import sys
import subprocess
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent

# Patterns to detect (case-insensitive for scanning, case-sensitive for reporting)
PATTERNS = [
    re.compile(r'\bhermes\b', re.IGNORECASE),
    re.compile(r'HERMES_[A-Z_]+'),  # ENV vars
]

# Directories to skip
SKIP_DIRS = {
    'node_modules', 'vendor', '.git', '__pycache__',
    '.venv', 'venv', 'dist', 'build', '.cache',
}

# Files to skip (these tools intentionally reference "hermes" for detection)
SKIP_FILES = {
    'package-lock.json', 'pnpm-lock.yaml', 'bun.lock',
    'Cargo.lock', 'uv.lock',
}

# Files that are part of the branding check tooling itself
# (they naturally contain "hermes" in detection patterns/messages)
SKIP_PATHS = {
    'scripts/branding-lint.py',
    'scripts/hooks/pre-commit-branding-check.sh',
    '.github/workflows/branding-check.yml',
}

# Allowed exceptions — regex patterns for lines that are intentionally about upstream
ALLOWED_EXCEPTIONS = [
    r'Perbedaan dengan Hermes Agent',
    r'Hermes Agent \| Chiper',
    r'hermes Agent \| Chiper',
    r'\| Command \| `hermes`',
    r'\| Data Dir \| `~/.hermes`',
    r'\| Code Dir \| `/usr/local/lib/hermes-agent`',
    r'Original:.*Hermes Agent',
    r'Chiper/hermes-agent',
    r'wikipedia\.org/wiki/Hermes',
    r'hermes-parser',
    r'hermes-estree',
    r'@hermes/ink',
]

# File extensions to scan
SCAN_EXTENSIONS = {
    '.py', '.ts', '.tsx', '.js', '.mjs', '.cjs', '.jsx',
    '.json', '.yaml', '.yml', '.toml', '.cfg', '.ini',
    '.md', '.mdx', '.txt', '.rst',
    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.cmd', '.bat',
    '.go', '.rs', '.java', '.kt', '.swift',
    '.css', '.scss', '.less', '.html', '.htm', '.svg', '.xml',
    '.nix', '.rb', '.lua', '.r',
    '.dockerignore', '.gitignore', '.envrc', '.manifest',
    '.jsonl', '.service', '.tmpl',
}

# Special filenames (no extension)
SCAN_FILENAMES = {
    'Dockerfile', 'Makefile', 'NOTICE', 'LICENSE',
}


def is_allowed_exception(line: str) -> bool:
    """Check if a line matches an allowed exception pattern."""
    for pattern in ALLOWED_EXCEPTIONS:
        if re.search(pattern, line):
            return True
    return False


def get_staged_files() -> list:
    """Get list of staged files from git."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR'],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        return [f for f in result.stdout.strip().split('\n') if f]
    except Exception:
        return []


def get_staged_content(filepath: str) -> str:
    """Get staged content of a file."""
    try:
        result = subprocess.run(
            ['git', 'show', f':{filepath}'],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        return result.stdout
    except Exception:
        return ''


def scan_file(filepath: Path, staged_only: bool = False) -> list:
    """Scan a single file for branding violations."""
    violations = []
    short = filepath.relative_to(REPO_ROOT)

    # Get content
    if staged_only:
        content = get_staged_content(str(short))
        if not content:
            return []
    else:
        try:
            # Skip binary files
            with open(filepath, 'rb') as f:
                raw = f.read(8192)
                if b'\x00' in raw:
                    return []
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return []

    for i, line in enumerate(content.split('\n'), 1):
        for pattern in PATTERNS:
            if pattern.search(line):
                if not is_allowed_exception(line):
                    violations.append({
                        'file': str(short),
                        'line': i,
                        'text': line.strip()[:120],
                        'pattern': pattern.pattern,
                    })
                break  # Only report first pattern match per line

    return violations


def scan_repository(staged_only: bool = False) -> list:
    """Scan the entire repository."""
    violations = []

    if staged_only:
        files = [REPO_ROOT / f for f in get_staged_files() if (REPO_ROOT / f).is_file()]
    else:
        files = []
        for root, dirs, filenames in os.walk(REPO_ROOT):
            # Skip directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for fname in filenames:
                if fname in SKIP_FILES:
                    continue

                filepath = Path(root) / fname

                # Check extension or special filename
                ext = filepath.suffix
                if ext not in SCAN_EXTENSIONS and fname not in SCAN_FILENAMES:
                    continue

                files.append(filepath)

    for filepath in files:
        # Skip branding check tooling itself
        rel = str(filepath.relative_to(REPO_ROOT))
        if rel in SKIP_PATHS:
            continue
        violations.extend(scan_file(filepath, staged_only))

    return violations


def print_report(violations: list, ci_mode: bool = False):
    """Print the violation report."""
    if not violations:
        if ci_mode:
            print("✅ BRANDING CHECK PASSED — no 'hermes' references found")
        else:
            print("✅ Clean — no branding violations found")
        return

    print()
    print("=" * 60)
    print("  BRANDING VIOLATION: 'hermes' found in source files")
    print("=" * 60)
    print()

    # Group by file
    by_file = {}
    for v in violations:
        by_file.setdefault(v['file'], []).append(v)

    for filepath in sorted(by_file.keys()):
        print(f"  📄 {filepath}")
        for v in by_file[filepath]:
            print(f"     L{v['line']}: {v['text']}")
        print()

    print(f"  Total: {len(violations)} violation(s) in {len(by_file)} file(s)")
    print()
    print("  Replace 'hermes' with 'chiper' before committing.")
    print("  If intentional, add to ALLOWED_EXCEPTIONS in scripts/branding-lint.py")
    print()


def main():
    ci_mode = '--ci' in sys.argv
    staged_only = '--staged' in sys.argv
    fix_mode = '--fix' in sys.argv

    if fix_mode:
        print("Fix mode not implemented — please replace manually.")
        sys.exit(2)

    violations = scan_repository(staged_only)
    print_report(violations, ci_mode)

    if violations:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
