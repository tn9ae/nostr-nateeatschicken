#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/config-open.toml"
DEST="$SCRIPT_DIR/config.toml"

if [ ! -f "$SRC" ]; then
  echo "Missing open config at $SRC" >&2
  exit 1
fi

cp "$SRC" "$DEST"

echo "Config switched to OPEN mode (copied config-open.toml -> config.toml). Now restart the relay container on the host."
