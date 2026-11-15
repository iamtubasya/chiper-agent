#!/usr/bin/env bash
# program-scope-intake.sh — Step 0 of the recon pipeline.
# Fetch a target's /.well-known/security.txt, follow the Policy: link, and dump
# the program page as plain text so you can extract scope + exclusions.
#
# Usage:   bash program-scope-intake.sh <domain>        # e.g. example.com
# Output:  stdout (security.txt + stripped policy page). Redirect to scope.md.
set -u
d="${1:?usage: program-scope-intake.sh <domain>}"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

for u in "https://$d/.well-known/security.txt" "https://www.$d/.well-known/security.txt" "https://$d/security.txt"; do
  body=$(curl -sSL -m 20 -A "$UA" -w $'\n@@CODE=%{http_code}' "$u")
  code=$(printf '%s' "$body" | sed -n 's/.*@@CODE=//p' | tail -1)
  stxt=$(printf '%s' "$body" | sed 's/@@CODE=.*//')
  [ "$code" = "200" ] || continue
  case "$stxt" in *Contact:*|*Policy:*|*Expires:*) ;; *) continue ;; esac

  echo "=== security.txt ($u) ==="
  printf '%s\n' "$stxt"
  pol=$(printf '%s' "$stxt" | sed -n 's/^Policy:[[:space:]]*//p' | head -1)
  if [ -n "${pol:-}" ]; then
    echo
    echo "=== Policy page: $pol ==="
    curl -sSL -m 25 -A "$UA" "$pol" \
      | sed -e 's/<script[^>]*>.*<\/script>//g' -e 's/<style[^>]*>.*<\/style>//g' -e 's/<[^>]*>/ /g' \
      | tr -s ' \t\r\n' ' ' | fold -s -w 120 | head -400
  fi
  exit 0
done
echo "no security.txt found for $d" >&2
exit 1
