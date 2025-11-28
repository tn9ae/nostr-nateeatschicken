#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path


NOSTR_JSON_PATH = Path(__file__).resolve().parent / "site" / ".well-known" / "nostr.json"
PUBKEY_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def load_data() -> dict:
    if NOSTR_JSON_PATH.exists():
        with NOSTR_JSON_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"names": {}}


def write_data(data: dict) -> None:
    NOSTR_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = NOSTR_JSON_PATH.with_name(NOSTR_JSON_PATH.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp_path, NOSTR_JSON_PATH)


def ensure_valid_pubkey(pubkey: str) -> None:
    if not PUBKEY_RE.fullmatch(pubkey):
        print("Error: pubkey must be exactly 64 hexadecimal characters.", file=sys.stderr)
        sys.exit(1)


def add_handle(handle: str, pubkey: str) -> None:
    ensure_valid_pubkey(pubkey)
    data = load_data()
    names = data.setdefault("names", {})
    handle_lower = handle.lower()
    names[handle_lower] = pubkey
    write_data(data)
    print(f"Stored handle '{handle_lower}' -> {pubkey}")


def remove_handle(handle: str) -> None:
    data = load_data()
    names = data.setdefault("names", {})
    handle_lower = handle.lower()
    if handle_lower in names:
        del names[handle_lower]
        write_data(data)
        print(f"Removed handle '{handle_lower}'")
    else:
        print(f"Handle '{handle_lower}' not found; nothing removed.")


def list_handles() -> None:
    data = load_data()
    for handle, pubkey in sorted(data.get("names", {}).items()):
        print(f"{handle} {pubkey}")


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description="Manage NIP-05 nostr.json entries.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add or update a handle mapping.")
    add_parser.add_argument("--name", required=True, help="Handle to add (will be lowercased).")
    add_parser.add_argument("--pubkey", required=True, help="Hex public key to associate.")
    add_parser.set_defaults(func=lambda args: add_handle(args.name, args.pubkey))

    remove_parser = subparsers.add_parser("remove", help="Remove a handle mapping.")
    remove_parser.add_argument("--name", required=True, help="Handle to remove.")
    remove_parser.set_defaults(func=lambda args: remove_handle(args.name))

    list_parser = subparsers.add_parser("list", help="List all handle mappings.")
    list_parser.set_defaults(func=lambda args: list_handles())

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
