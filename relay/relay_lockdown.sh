#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCKED="$SCRIPT_DIR/config-locked.toml"
DEST="$SCRIPT_DIR/config.toml"
SUPPORTERS="$SCRIPT_DIR/supporters.txt"

if [ ! -f "$LOCKED" ]; then
  echo "Missing lockdown config at $LOCKED" >&2
  exit 1
fi

tmpfile="$(mktemp)"
trap 'rm -f "$tmpfile"' EXIT

supporters=()
if [ -f "$SUPPORTERS" ]; then
  mapfile -t supporters < <(grep -Ev '^\s*(#|$)' "$SUPPORTERS" || true)
fi

if [ "${#supporters[@]}" -gt 0 ]; then
  whitelist=$(printf '"%s", ' "${supporters[@]}")
  whitelist=${whitelist%, }

  if ! grep -q '^pubkey_whitelist' "$LOCKED"; then
    echo "Expected pubkey_whitelist placeholder in $LOCKED" >&2
    exit 1
  fi

  sed "s|^pubkey_whitelist = .*|pubkey_whitelist = [${whitelist}]|" "$LOCKED" > "$tmpfile"
else
  cp "$LOCKED" "$tmpfile"
fi

cp "$tmpfile" "$DEST"

echo "Config switched to LOCKDOWN mode (copied config-locked.toml -> config.toml). pubkey_whitelist entries: ${#supporters[@]}."
echo "Now restart the relay container on the host."
