#!/usr/bin/env bash
# Run an ARM (armel/armhf) firmware binary under qemu-user.
# Usage: ./scripts/run.armel.sh <image_id>   (see chiper-firmware-reverse)
set -euo pipefail

IMAGE_ID="${1:-}"
if [[ -z "$IMAGE_ID" ]]; then
  echo "usage: $0 <image_id> [args...]" >&2
  exit 2
fi

shift || true
ROOT="${FIRMWARE_ROOT:-./extracted/$IMAGE_ID}"
BINARIES=()

if [[ -d "$ROOT" ]]; then
  while IFS= read -r candidate; do
    BINARIES+=("$candidate")
  done < <(find "$ROOT" -maxdepth 3 -type f -perm -u+x \
            -exec file -b --mime-type {} \; 2>/dev/null | paste -d' ' - <(find "$ROOT" -maxdepth 3 -type f -perm -u+x) | \
            awk '/application\/x-executable|application\/x-pie-executable/ {print $NF}' || true)
fi

if [[ ${#BINARIES[@]} -eq 0 ]]; then
  echo "no executables found under $ROOT" >&2
  exit 1
fi

QEMU=""
for candidate in qemu-arm-static qemu-arm; do
  if command -v "$candidate" >/dev/null 2>&1; then
    QEMU="$candidate"
    break
  fi
done
if [[ -z "$QEMU" ]]; then
  echo "qemu-arm not found: sudo apt-get install -y qemu-user-static" >&2
  exit 1
fi

TARGET="${BINARIES[0]}"
echo "running: $QEMU -L ${SYSROOT:-$ROOT} $TARGET $*"
exec "$QEMU" -L "${SYSROOT:-$ROOT}" "$TARGET" "$@"
