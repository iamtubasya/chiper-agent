#!/usr/bin/env bash
# ============================================================================
# Pre-commit hook: Reject stale "hermes" branding in staged files.
#
# Install:
#   cp scripts/hooks/pre-commit-branding-check.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# Or via core.hooksPath:
#   git config core.hooksPath scripts/hooks
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Patterns to search for (case-sensitive)
PATTERNS=("hermes" "Hermes" "HERMES")

# Directories to exclude from scanning
EXCLUDE_DIRS=(
    "node_modules"
    "vendor"
    ".git"
    "__pycache__"
    ".venv"
    "venv"
    "dist"
    "build"
    ".cache"
)

# Files to exclude
EXCLUDE_FILES=(
    "package-lock.json"
    "pnpm-lock.yaml"
    "bun.lock"
    "Cargo.lock"
    "uv.lock"
)

# Build exclude args for grep
EXCLUDE_ARGS=""
for dir in "${EXCLUDE_DIRS[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude-dir=$dir"
done
for file in "${EXCLUDE_FILES[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude=$file"
done

# Allowed exceptions (intentional references)
# These are checked as exact line matches
ALLOWED_EXCEPTIONS=(
    "Perbedaan dengan Hermes Agent"
    "Hermes Agent | Chiper"
    "hermes Agent | Chiper"
    "| Command | \`hermes\`"
    "| Data Dir | \`~/.hermes\`"
    "| Code Dir | \`/usr/local/lib/hermes-agent\`"
    "Original: \[Hermes Agent\]"
    "Chiper/hermes-agent"
    "wikipedia.org/wiki/Hermes"
    "hermes-parser"
    "hermes-estree"
    "@hermes/ink"
)

# Get staged files (only added/modified content)
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

VIOLATIONS=""
VIOLATION_COUNT=0

for file in $STAGED_FILES; do
    # Skip if file doesn't exist (deleted)
    [ -f "$file" ] || continue

    # Skip binary files
    if file --mime-encoding "$file" 2>/dev/null | grep -q "binary"; then
        continue
    fi

    # Skip excluded files
    skip=false
    for exc in "${EXCLUDE_FILES[@]}"; do
        if [[ "$file" == *"$exc" ]]; then
            skip=true
            break
        fi
    done
    $skip && continue

    # Scan staged content (not working tree)
    staged_content=$(git show ":$file" 2>/dev/null || true)
    if [ -z "$staged_content" ]; then
        continue
    fi

    while IFS= read -r line; do
        # Check if line contains any pattern
        for pattern in "${PATTERNS[@]}"; do
            if echo "$line" | grep -q "$pattern"; then
                # Check if it's an allowed exception
                is_exception=false
                for exception in "${ALLOWED_EXCEPTIONS[@]}"; do
                    if echo "$line" | grep -q "$exception"; then
                        is_exception=true
                        break
                    fi
                done

                if ! $is_exception; then
                    VIOLATIONS="${VIOLATIONS}${RED}✗${NC} ${file}: ${line}\n"
                    VIOLATION_COUNT=$((VIOLATION_COUNT + 1))
                fi
                break
            fi
        done
    done <<< "$staged_content"
done

if [ "$VIOLATION_COUNT" -gt 0 ]; then
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  BRANDING VIOLATION: 'hermes' found in staged files${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "$VIOLATIONS"
    echo -e "${YELLOW}Found ${VIOLATION_COUNT} violation(s).${NC}"
    echo ""
    echo -e "Replace 'hermes' with 'chiper' before committing."
    echo -e "If this is an intentional reference (e.g. upstream comparison),"
    echo -e "add it to the ALLOWED_EXCEPTIONS list in this hook."
    echo ""
    exit 1
fi

exit 0
