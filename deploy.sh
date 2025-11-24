#!/usr/bin/env bash
set -euo pipefail

# Paths and settings (edit as needed)
REPO_DIR="$HOME/nostr-project"
LIVE_RELAY_DIR="/opt/nostr/relay"
BACKUP_DIR="/opt/nostr/relay-backups"
CONTAINER_NAME="nostr_relay" # TODO: set this to the actual relay container name from `docker ps`

echo "==> Syncing repo to origin/main"
cd "$REPO_DIR"
git fetch origin
git reset --hard origin/main

echo "==> Backing up live relay directory"
mkdir -p "$BACKUP_DIR"
timestamp="$(date +%Y%m%d%H%M%S)"
if [ -d "$LIVE_RELAY_DIR" ]; then
  cp -a "$LIVE_RELAY_DIR" "${BACKUP_DIR}/relay-backup-${timestamp}"
  echo "Backup created at ${BACKUP_DIR}/relay-backup-${timestamp}"
else
  echo "Warning: live relay directory not found at $LIVE_RELAY_DIR; skipping backup" >&2
fi

echo "==> Deploying relay configs and scripts"
files=(
  config.toml
  config-open.toml
  config-locked.toml
  relay_open.sh
  relay_lockdown.sh
  supporters.txt
)
for file in "${files[@]}"; do
  cp "$REPO_DIR/relay/$file" "$LIVE_RELAY_DIR/$file"
done

echo "==> Ensuring relay scripts are executable"
chmod +x "$LIVE_RELAY_DIR/relay_open.sh" "$LIVE_RELAY_DIR/relay_lockdown.sh"

echo "==> Restarting relay container: $CONTAINER_NAME"
sudo docker restart "$CONTAINER_NAME"

echo "Deploy complete."
