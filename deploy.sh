#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$HOME/nostr-project"
LIVE_RELAY_DIR="/opt/nostr/relay"
CONTAINER_NAME="nostr_relay" # Change this to the real container name from `docker ps`.

BACKUP_DIR="/opt/nostr/relay-backups"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
BACKUP_DEST="${BACKUP_DIR}/relay-${TIMESTAMP}"

echo "Fetching latest code from origin/main..."
cd "$REPO_DIR"
git fetch origin
git reset --hard origin/main

echo "Backing up live relay directory..."
mkdir -p "$BACKUP_DIR"
cp -a "$LIVE_RELAY_DIR" "$BACKUP_DEST"

echo "Copying configs and scripts to live relay dir..."
for file in \
  config.toml \
  config-open.toml \
  config-locked.toml \
  relay_open.sh \
  relay_lockdown.sh \
  supporters.txt
do
  cp "$REPO_DIR/relay/$file" "$LIVE_RELAY_DIR/$file"
done

echo "Setting execute permissions on relay scripts..."
chmod +x "$LIVE_RELAY_DIR/relay_open.sh" "$LIVE_RELAY_DIR/relay_lockdown.sh"

echo "Restarting relay container..."
sudo docker restart "$CONTAINER_NAME"

echo "Deploy complete."
