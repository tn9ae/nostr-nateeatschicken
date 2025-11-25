README.md
## 1. High-level overview

This project runs on **Contabo** and powers:

- A **NIP-05 handle service** on `name@nostr.nateeatschicken.xyz`
- A **Nostr relay** (`wss://nostr.nateeatschicken.xyz`) with:
  - Free tier for everyone
  - Planned “power user” tier with better guarantees
- Future **automation**:
  - Ko-fi webhook to auto-create NIP-05 handles
  - Optional relay “power user” upgrades
  - Optional notifications (e.g. Nostr DM, logs)

The main idea: supporters of `nateeatschicken` get:

- A verified Nostr handle on the `nostr.nateeatschicken.xyz` domain
- Preferential access to the relay if spam/abuse requires tighter rules

---

## 2. Domains & URLs

- **Frontend / Dev UI (Codex, etc.):** `https://dev.nostr.nateeatschicken.xyz`
- **Production Nostr subdomain:** `https://nostr.nateeatschicken.xyz`
- **NIP-05 endpoint (Nostr identity lookup):** `https://nostr.nateeatschicken.xyz/.well-known/nostr.json`
- **Relay URL:** `wss://nostr.nateeatschicken.xyz`

---

## 3. Current components (implemented)

### 3.1 Repo layout (actual paths)

- Relay active config: `relay/config.toml` (copied from the mode-specific configs)
- Relay config variants: `relay/config-open.toml`, `relay/config-locked.toml`
- Relay data dir: `relay/db/` (`nostr.db`, `nostr.db-shm`, `nostr.db-wal`)
- Supporter list: `relay/supporters.txt`
- Helper scripts: `relay/relay_open.sh`, `relay/relay_lockdown.sh`
- NIP-05 file: `site/.well-known/nostr.json`
- Caddy/Docker definitions: not tracked in this repo (expected to exist on the host)

### 3.2 Web server / reverse proxy

- Caddy runs in Docker, serves static files, and reverse proxies to the relay container.
- Caddyfile/container name are not in this repo; map the host volume for the web root to `site/` and proxy to the relay container port.

### 3.3 NIP-05 – `nostr.json`

NIP-05 maps a handle (like `nate@nostr.nateeatschicken.xyz`) to a Nostr pubkey.

- File: `site/.well-known/nostr.json`
- Example content:

  ```json
  {
    "names": {
      "nate": "b12b6d90b7ba7b6d4432b272b10a4983d22ebdae5defd9aacfe54d158a0fdd0d"
    }
  }
  ```

- Helper script to edit this file (e.g., `manage_nip05.py`) is not yet present; when editing manually, write atomically.

### Managing NIP-05 handles

- File location: `site/.well-known/nostr.json`
- Example commands (run from the repo root):

  ```bash
  python3 manage_nip05.py add nate b12b6d90b7ba7b6d4432b272b10a4983d22ebdae5defd9aacfe54d158a0fdd0d
  python3 manage_nip05.py remove nate
  python3 manage_nip05.py list
  ```

- Full NIP-05 identifier format: `handle@nostr.nateeatschicken.xyz` (use the handle from the script with the fixed domain).

### Managing relay supporters

- File: `relay/supporters.txt` (used to populate the whitelist in lockdown mode).
- Example commands (run from the repo root):

  ```bash
  python3 manage_supporters.py add b12b6d90b7ba7b6d4432b272b10a4983d22ebdae5defd9aacfe54d158a0fdd0d
  python3 manage_supporters.py remove b12b6d90b7ba7b6d4432b272b10a4983d22ebdae5defd9aacfe54d158a0fdd0d
  python3 manage_supporters.py list
  ```

- After changing supporters, run `./deploy.sh` on the server to push the updates live.

### 3.4 Nostr relay (nostr-rs-relay)

- Active config: `relay/config.toml`
- Relay URL: `wss://nostr.nateeatschicken.xyz/`
- Defaults: `[verified_users]` mode = `passive`, domain whitelist includes `nostr.nateeatschicken.xyz`
- Limits (active config and open config): `messages_per_sec = 10`, `subscriptions_per_min = 60`, `max_event_bytes = 65536`
- Data files: `relay/db/nostr.db*`
- Container name is not documented here; scripts leave restart to the operator.

---

## 4. Relay: free vs power-user + spam/security (Step 4 implemented)

- `relay/config-open.toml`: open tier; `verified_users.mode = "passive"` with the rate limits above.
- `relay/config-locked.toml`: lockdown; `verified_users.mode = "enabled"`, `domain_whitelist = ["nostr.nateeatschicken.xyz"]`, and a `pubkey_whitelist` placeholder that can be populated from `supporters.txt`.
- `relay/supporters.txt`: one hex pubkey per line; lines starting with `#` are comments and are ignored. Used to build the whitelist in lockdown mode.
- `relay/relay_open.sh`: copies `config-open.toml` over `config.toml`. Does not restart Docker.
- `relay/relay_lockdown.sh`: rebuilds `pubkey_whitelist` from `supporters.txt`, then copies the locked config over `config.toml`. Does not restart Docker.

Usage (run from repo root or inside `relay/`):

```bash
./relay/relay_open.sh
./relay/relay_lockdown.sh
# then restart the relay container on the host, e.g.:
# docker restart <relay-container-name>
```

`relay/config.toml` is the live config consumed by the relay container (copy or symlink it into place as needed on the host).

---

## 5. Ko-fi + automation (future)

- Small Flask (or similar) app exposed at `/kofi-webhook` via Caddy.
- Log all payment events.
- For products like “NIP-05 handle” or “Relay power user”:
  - Parse buyer’s requested handle + npub.
  - Convert npub → hex pubkey.
  - Update `site/.well-known/nostr.json` (via a helper script) with `names[handle] = hex`.
  - Append the hex pubkey to `relay/supporters.txt`.
  - Optionally trigger a relay reload if needed.
- Future: optional Nostr DM notification to Nate’s npub when provisioning succeeds.

---

## 6. Security & anti-spam expectations

- Rate limiting enabled: `messages_per_sec`, `subscriptions_per_min`, `max_event_bytes` (~64KB).
- `relay_url` and `domain_whitelist` use `nostr.nateeatschicken.xyz`.
- NIP-05 enforcement is only enabled in lockdown mode.
- Helper scripts fail fast (`set -euo pipefail`) and are safe to re-run.
- Future ideas: Fail2ban watching reverse proxy logs; event kind allowlists/blacklists if spam patterns emerge.

---

## 7. What Codex should do first

- Verify host Caddy/Caddyfile paths and container names; align with the repo-relative paths above.
- Use `relay_open.sh` / `relay_lockdown.sh` to switch modes, then restart the relay container manually on the host.
- Keep this README updated as paths or configs change; ensure future automation reuses `relay/supporters.txt` and `site/.well-known/nostr.json`.

## 8. Ko-fi webhook skeleton

- Placeholder app lives at `kofi-webhook/app.py`.
- Run locally:

  ```bash
  cd kofi-webhook
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  python3 app.py
  ```

- Current behaviour: listens on `0.0.0.0:5000`, checks `X-Ko-Fi-Token` against `KOFI_WEBHOOK_TOKEN` (if set), logs payloads, and returns `ok`.
- Future behaviour: parse Ko-fi payloads for specific products/tier names, call `manage_nip05.py` to add handles, and call `manage_supporters.py add <pubkey>` to whitelist paying users.
