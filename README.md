README.md
## 1. High-level overview

This project runs on **Contabo** and powers:

- A **NIP-05 handle service** on  
  `name@nostr.nateeatschicken.xyz`
- A **Nostr relay** (`wss://nostr.nateeatschicken.xyz`) with:
  - Free tier for everyone
  - Planned “power user” tier with better guarantees
- Future **automation**:
  - Ko-fi webhook to auto-create NIP-05 handles
  - Optional relay “power user” upgrades
  - Optional notifications (e.g. Nostr DM, logs)

The main idea: users can support `nateeatschicken` and get:

- A verified Nostr handle on the `nostr.nateeatschicken.xyz` domain  
- Preferential access to the relay if spam/abuse means the relay has to tighten rules

---

## 2. Domains & URLs

- **Frontend / Dev UI (Codex, etc.):**  
  `https://dev.nostr.nateeatschicken.xyz`  
- **Production Nostr subdomain:**  
  `https://nostr.nateeatschicken.xyz`
- **NIP-05 endpoint (Nostr identity lookup):**  
  `https://nostr.nateeatschicken.xyz/.well-known/nostr.json`
- **Relay URL:**  
  `wss://nostr.nateeatschicken.xyz`

---

## 3. Current components (implemented)

### 3.1 Web server / reverse proxy

- Frontend is handled by **Caddy running in Docker**.
- The Caddy container typically:
  - Serves static files from a host directory mapped to `/srv`
  - Reverse proxies to the Nostr relay container and any webhook apps

Assumptions for Codex (verify via `docker-compose.yml` or container inspect):

- Web root (host): `/opt/nostr/site`
- Caddyfile (host): `/opt/nostr/Caddyfile`
- Caddy container: `nostr_caddy_1` (or similar)

### 3.2 NIP-05 – `nostr.json`

NIP-05 is how a human-readable handle (like `nate@nostr.nateeatschicken.xyz`) is mapped to a Nostr pubkey.

Implementation so far:

- Web root has:

  ```text
  /opt/nostr/site/.well-known/nostr.json
Example content:

{
  "names": {
    "nate": "b12b6d90b7ba7b6d4432b272b10a4983d22ebdae5defd9aacfe54d158a0fdd0d"
  }
}

This maps:

nate@nostr.nateeatschicken.xyz → Nate’s hex pubkey

npub (for reference):
npub1ky4kmy9hhfak63pjkfetzzjfs0fza0dwthhan2k0u4x3tzs0m5xsh9mgd2

There is or will be a helper script to update this file:

Host path: /opt/nostr/manage_nip05.py

It should:

Load the JSON

Insert/update a names[handle] = hex_pubkey

Write the file safely (temp file + atomic replace)

Codex should treat this script as the source of truth for modifying nostr.json.

3.3 Nostr relay (nostr-rs-relay)

The relay is expected to be nostr-rs-relay inside Docker.

Assumptions for Codex (verify):

Relay container: nostr_relay (or similar)

Host config: /opt/nostr/relay/config.toml

Host data dir: /opt/nostr/relay/data

Base config needs to include:

[info] relay_url = "wss://nostr.nateeatschicken.xyz/"

Sane [limits]:

messages_per_sec

subscriptions_per_min

max_event_bytes etc.

[verified_users] configured with:

Initially mode = "passive" (check NIP-05 but do not block)

[pay_to_relay] currently disabled.

A supporter list file is planned:

/opt/nostr/relay/supporters.txt

Format: one hex pubkey per line, comments allowed with #.

4. Planned but NOT implemented yet (important for Codex)
4.1 Relay: free vs power-user + spam/security (Step 4)

This is the main missing piece.

Desired behaviour:

Normal (open) mode:

Anyone can publish to the relay (within rate limits).

NIP-05 is checked but not enforced.

Supports a free tier and makes discovery easy.

Lockdown (spam wave / abuse) mode:

Only users with valid name@nostr.nateeatschicken.xyz NIP-05 (and possibly a whitelist) get full persistence.

Other events can be rejected or not stored.

Power users / supporters should keep working without friction.

Expected implementation:

Two config variants on host:

/opt/nostr/relay/config-open.toml

/opt/nostr/relay/config-locked.toml

A “live” config:

/opt/nostr/relay/config.toml (symlink or copy of one of the above)

Two helper scripts:

/opt/nostr/relay/relay_open.sh

/opt/nostr/relay/relay_lockdown.sh

These scripts should:

Copy the appropriate TOML into config.toml.

Restart the relay container (e.g. docker restart nostr_relay).

config-open.toml expectations:

[verified_users] mode = "passive"

Reasonable but not extreme rate limits.

config-locked.toml expectations:

[verified_users] mode = "enabled"

domain_whitelist = ["nostr.nateeatschicken.xyz"]

Optional pubkey_whitelist using values from supporters.txt.

Possibly slightly tighter rate limits to reduce abuse.

Codex’s job here: create these configs + scripts, making sure they match the actual container names and paths in the repo.

4.2 Ko-fi + automation

Longer-term goals:

A small Flask or similar app on host:

Receives Ko-fi webhooks at /kofi-webhook via Caddy reverse proxy.

Logs all payment events.

For specific products (“NIP-05 handle”, “Relay power user”):

Parses buyer’s requested handle + npub.

Converts npub → hex pubkey.

Calls manage_nip05.py handle hex_pubkey.

Appends hex pubkey to /opt/nostr/relay/supporters.txt.

Optionally triggers a relay reload if needed.

Later: optional Nostr DM notification to Nate’s npub when provisioning succeeds.

The Ko-fi automation is not required yet for basic functionality, but Codex should be aware of this future integration so it keeps paths and structure clean.

5. Security & anti-spam expectations

Codex should ensure:

Rate limiting is enabled:

messages_per_sec

subscriptions_per_min

max_event_bytes not too large (e.g. 64KB).

Relay is not logging or exposing sensitive keys (only pubkeys).

NIP-05 enforcement (config-locked) is correctly wired to the nostr.nateeatschicken.xyz domain.

Helper scripts fail fast / exit on errors.

It’s safe to run scripts multiple times.

Future optional ideas (not required yet):

Fail2ban or similar watching reverse proxy logs.

Event kind allowlists/blacklists if a specific spam pattern emerges.

6. What Codex should do first

Given this README, Codex should:

Verify assumptions:

Confirm file paths for:

Caddyfile

Web root

Relay config.toml

Any existing scripts in /opt/nostr or equivalent.

Update this README if paths are different.

Implement Step 4 (relay open/lockdown):

Add config-open.toml and config-locked.toml under /opt/nostr/relay/ (or repo equivalents).

Add relay_open.sh and relay_lockdown.sh.

Make sure they use the correct Docker container name.

Ensure they are executable and robust.

Wire everything into version control:

Make sure all relevant files are under Git:

README.md

Caddyfile (or config)

Relay configs

Helper scripts

Ko-fi webhook skeleton (if present)

Prepare for automation:

If a Ko-fi webhook app exists in the repo:

Document its structure and endpoints.

Add TODO blocks for npub → hex conversion and handle parsing.

Codex should treat this README as the single source of context for the Nostr stack and keep it updated as changes are made.
