#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$HOME/nostr-project"
LIVE_RELAY_DIR="/opt/nostr/relay"
CONTAINER_NAME="nostr_relay" # Change this to the real name from `docker ps` on the server.

echo "=== Deploy started at $(date) ==="

echo "[1/5] Fetching latest code from origin/main..."
cd "$REPO_DIR"
git fetch origin
git reset --hard origin/main

echo "[2/5] Backing up live relay directory at $LIVE_RELAY_DIR ..."
sudo mkdir -p /opt/nostr/relay-backups
sudo cp -a "$LIVE_RELAY_DIR" "/opt/nostr/relay-backups/$(date +%F-%H%M)"

echo "[3/5] Copying relay configs and scripts into $LIVE_RELAY_DIR ..."
sudo cp "$REPO_DIR/relay/config.toml" \
        "$REPO_DIR/relay/config-open.toml" \
        "$REPO_DIR/relay/config-locked.toml" \
        "$REPO_DIR/relay/relay_open.sh" \
        "$REPO_DIR/relay/relay_lockdown.sh" \
        "$REPO_DIR/relay/supporters.txt" \
        "$LIVE_RELAY_DIR/"

echo "[4/5] Ensuring relay scripts are executable..."
sudo chmod +x "$LIVE_RELAY_DIR/relay_open.sh" "$LIVE_RELAY_DIR/relay_lockdown.sh"

echo "[5/5] Restarting relay container: $CONTAINER_NAME ..."
sudo docker restart "$CONTAINER_NAME"

echo "=== Deploy complete at $(date) ==="
