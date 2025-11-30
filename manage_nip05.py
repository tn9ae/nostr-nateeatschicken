#!/usr/bin/env python3
import argparse
import json
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional


LIVE_NIP05_PATH = "/opt/nostr/proxy/site/.well-known/nostr.json"
LIVE_NIP05 = Path(LIVE_NIP05_PATH)
PUBKEY_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def print_json_path() -> None:
    print(f"Using NIP-05 file: {LIVE_NIP05_PATH}")


def ensure_parent_dir() -> None:
    LIVE_NIP05.parent.mkdir(parents=True, exist_ok=True)


def load_data() -> dict:
    print_json_path()
    try:
        content = LIVE_NIP05.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"names": {}}

    if not content.strip():
        return {"names": {}}

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        logging.warning("Invalid JSON at %s; reinitializing empty mapping: %s", LIVE_NIP05_PATH, exc)
        return {"names": {}}

    if not isinstance(data, dict):
        logging.warning("Unexpected data structure at %s; reinitializing empty mapping.", LIVE_NIP05_PATH)
        return {"names": {}}

    names = data.get("names")
    if not isinstance(names, dict):
        data["names"] = {}

    return data


def save_data(data: dict) -> None:
    print_json_path()
    ensure_parent_dir()
    tmp_file: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=LIVE_NIP05.parent, delete=False
        ) as tmp:
            json.dump(data, tmp, indent=2, sort_keys=True)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_file = Path(tmp.name)
        os.replace(tmp_file, LIVE_NIP05)
    except Exception:
        logging.exception("Failed to write NIP-05 data to %s", LIVE_NIP05_PATH)
        raise
    finally:
        if tmp_file and tmp_file.exists():
            tmp_file.unlink(missing_ok=True)


def normalize_handle(name: str) -> str:
    handle = (name or "").strip().lower()
    if not handle:
        print("Error: handle must be non-empty.", file=sys.stderr)
        sys.exit(1)
    return handle


def validate_pubkey(pubkey: str) -> None:
    if not PUBKEY_RE.fullmatch(pubkey or ""):
        print("Error: pubkey must be exactly 64 hexadecimal characters.", file=sys.stderr)
        sys.exit(1)


def claim_handle(handle: str, pubkey: str) -> None:
    handle_norm = normalize_handle(handle)
    validate_pubkey(pubkey)
    data = load_data()
    names = data.setdefault("names", {})
    names[handle_norm] = pubkey
    save_data(data)
    logging.info("Updated live NIP-05 %s: %s -> %s", LIVE_NIP05_PATH, handle_norm, pubkey)
    print(f"Stored handle '{handle_norm}' -> {pubkey}")


def remove_handle(handle: str) -> None:
    handle_norm = normalize_handle(handle)
    data = load_data()
    names = data.setdefault("names", {})
    if handle_norm in names:
        del names[handle_norm]
        save_data(data)
        print(f"Removed handle '{handle_norm}'")
    else:
        print(f"Handle '{handle_norm}' not found; nothing to remove.")


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description="Manage NIP-05 nostr.json mappings.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    claim_parser = subparsers.add_parser("claim", help="Create or update a handle mapping.")
    claim_parser.add_argument("handle", help="Handle to claim (will be lowercased).")
    claim_parser.add_argument("pubkey", help="64-character hex public key.")
    claim_parser.set_defaults(func=lambda args: claim_handle(args.handle, args.pubkey))

    remove_parser = subparsers.add_parser("remove", help="Remove a handle mapping.")
    remove_parser.add_argument("handle", help="Handle to remove (case-insensitive).")
    remove_parser.set_defaults(func=lambda args: remove_handle(args.handle))

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
