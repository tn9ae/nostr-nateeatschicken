#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path
from typing import List


FILE_PATH = Path("/opt/nostr/relay/supporters.txt")
PUBKEY_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def ensure_parent_dir() -> None:
    FILE_PATH.parent.mkdir(parents=True, exist_ok=True)


def validate_pubkey(pubkey: str) -> str:
    if not PUBKEY_RE.fullmatch(pubkey or ""):
        print("Error: pubkey must be exactly 64 hexadecimal characters.", file=sys.stderr)
        sys.exit(1)
    return pubkey


def read_lines() -> List[str]:
    if not FILE_PATH.exists():
        return []
    with FILE_PATH.open("r", encoding="utf-8") as f:
        return f.readlines()


def filtered_pubkeys(lines: List[str]) -> List[str]:
    keys = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        keys.append(stripped)
    return keys


def write_lines(lines: List[str]) -> None:
    ensure_parent_dir()
    with FILE_PATH.open("w", encoding="utf-8") as f:
        f.writelines(lines)


def add_pubkey(pubkey: str) -> None:
    pubkey_valid = validate_pubkey(pubkey)
    lines = read_lines()
    existing_lower = {k.lower() for k in filtered_pubkeys(lines)}
    if pubkey_valid.lower() in existing_lower:
        print("Pubkey already present; nothing to add.")
        return

    ensure_parent_dir()
    newline_prefix = ""
    if FILE_PATH.exists():
        content = FILE_PATH.read_text(encoding="utf-8")
        if content and not content.endswith("\n"):
            newline_prefix = "\n"

    with FILE_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{newline_prefix}{pubkey_valid}\n")

    print(f"Added pubkey {pubkey_valid}")


def remove_pubkey(pubkey: str) -> None:
    pubkey_valid = validate_pubkey(pubkey)
    lines = read_lines()
    target = pubkey_valid.lower()
    kept: List[str] = []
    found = False

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and stripped.lower() == target:
            found = True
            continue
        kept.append(line)

    if not found:
        print("Pubkey not found; nothing removed.")
        return

    write_lines(kept)
    print(f"Removed pubkey {pubkey_valid}")


def list_pubkeys() -> None:
    lines = read_lines()
    for key in filtered_pubkeys(lines):
        print(key)


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description="Manage /opt/nostr/relay/supporters.txt entries.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a supporter pubkey.")
    add_parser.add_argument("--pubkey", required=True, help="64-character hex public key to add.")
    add_parser.set_defaults(func=lambda args: add_pubkey(args.pubkey))

    remove_parser = subparsers.add_parser("remove", help="Remove a supporter pubkey.")
    remove_parser.add_argument("--pubkey", required=True, help="64-character hex public key to remove.")
    remove_parser.set_defaults(func=lambda args: remove_pubkey(args.pubkey))

    list_parser = subparsers.add_parser("list", help="List supporter pubkeys.")
    list_parser.set_defaults(func=lambda args: list_pubkeys())

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
