#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$HOME/nostr-project"
LIVE_RELAY_DIR="/opt/nostr/relay"
CONTAINER_NAME="nostr-relay-1"
SITE_SRC="$REPO_DIR/site"
SITE_DST="/opt/nostr/site"

echo "=== Deploy started at $(date) ==="

echo "[1/5] Fetching latest code from origin/main..."
cd "$REPO_DIR"
git fetch origin
git reset --hard origin/main

echo "[2/6] Backing up live relay directory at $LIVE_RELAY_DIR ..."
sudo mkdir -p /opt/nostr/relay-backups
sudo cp -a "$LIVE_RELAY_DIR" "/opt/nostr/relay-backups/$(date +%F-%H%M)"

echo "Syncing static site to $SITE_DST ..."
sudo mkdir -p "$SITE_DST"
sudo rsync -av --delete "$SITE_SRC/" "$SITE_DST/"

echo "[3/6] Copying relay configs and scripts into $LIVE_RELAY_DIR ..."
sudo cp "$REPO_DIR/relay/config.toml" \
        "$REPO_DIR/relay/config-open.toml" \
        "$REPO_DIR/relay/config-locked.toml" \
        "$REPO_DIR/relay/relay_open.sh" \
        "$REPO_DIR/relay/relay_lockdown.sh" \
        "$REPO_DIR/relay/supporters.txt" \
        "$LIVE_RELAY_DIR/"

echo "[4/6] Ensuring relay scripts are executable..."
sudo chmod +x "$LIVE_RELAY_DIR/relay_open.sh" "$LIVE_RELAY_DIR/relay_lockdown.sh"

echo "[5/6] Restarting relay container: $CONTAINER_NAME ..."
sudo docker restart "$CONTAINER_NAME"

echo "[6/6] Deploy complete at $(date)"
