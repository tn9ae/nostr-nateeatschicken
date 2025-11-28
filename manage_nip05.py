#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path


FILE_PATH = Path("/opt/nostr/site/.well-known/nostr.json")
PUBKEY_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def ensure_parent_dir() -> None:
    FILE_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_data() -> dict:
    if FILE_PATH.exists():
        with FILE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"names": {}}


def save_data(data: dict) -> None:
    ensure_parent_dir()
    with FILE_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


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


def add_handle(handle: str, pubkey: str) -> None:
    handle_norm = normalize_handle(handle)
    validate_pubkey(pubkey)
    data = load_data()
    names = data.setdefault("names", {})
    names[handle_norm] = pubkey
    save_data(data)
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


def list_handles() -> None:
    data = load_data()
    for handle, pubkey in sorted(data.get("names", {}).items()):
        print(f"{handle} {pubkey}")


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description="Manage /opt/nostr/site/.well-known/nostr.json NIP-05 mappings.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add or update a handle mapping.")
    add_parser.add_argument("--name", required=True, help="Handle to add (will be lowercased).")
    add_parser.add_argument("--pubkey", required=True, help="64-character hex public key.")
    add_parser.set_defaults(func=lambda args: add_handle(args.name, args.pubkey))

    remove_parser = subparsers.add_parser("remove", help="Remove a handle mapping.")
    remove_parser.add_argument("--name", required=True, help="Handle to remove (case-insensitive).")
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
