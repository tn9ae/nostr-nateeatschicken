#!/usr/bin/env python3
import argparse
import os
import re
import sys
from pathlib import Path


SUPPORTERS_PATH = Path(__file__).resolve().parent / "relay" / "supporters.txt"
PUBKEY_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def ensure_valid_pubkey(pubkey: str) -> None:
    if not PUBKEY_RE.fullmatch(pubkey):
        print("Error: pubkey must be exactly 64 hexadecimal characters.", file=sys.stderr)
        sys.exit(1)


def load_lines() -> list[str]:
    if not SUPPORTERS_PATH.exists():
        return []
    with SUPPORTERS_PATH.open("r", encoding="utf-8") as f:
        return f.readlines()


def filtered_pubkeys(lines: list[str]) -> list[str]:
    keys = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        keys.append(stripped)
    return keys


def write_lines_atomic(lines: list[str]) -> None:
    SUPPORTERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = SUPPORTERS_PATH.with_name(SUPPORTERS_PATH.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        f.writelines(lines)
    os.replace(tmp_path, SUPPORTERS_PATH)


def add_pubkey(pubkey: str) -> None:
    ensure_valid_pubkey(pubkey)
    lines = load_lines()
    existing = filtered_pubkeys(lines)
    if pubkey in existing:
        print("Pubkey already present; nothing added.")
        return

    SUPPORTERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    newline_prefix = ""
    if SUPPORTERS_PATH.exists():
        current_content = SUPPORTERS_PATH.read_text(encoding="utf-8")
        newline_prefix = "" if current_content.endswith("\n") or current_content == "" else "\n"

    with SUPPORTERS_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{newline_prefix}{pubkey}\n")

    print(f"Added pubkey {pubkey}")


def remove_pubkey(pubkey: str) -> None:
    ensure_valid_pubkey(pubkey)
    lines = load_lines()
    kept: list[str] = []
    found = False

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and stripped == pubkey:
            found = True
            continue
        kept.append(line)

    if not found:
        print("Pubkey not found; nothing removed.")
        return

    write_lines_atomic(kept)
    print(f"Removed pubkey {pubkey}")


def list_pubkeys() -> None:
    lines = load_lines()
    for key in filtered_pubkeys(lines):
        print(key)


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description="Manage relay/supporters.txt entries.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a supporter pubkey.")
    add_parser.add_argument("--pubkey", required=True, help="Hex public key to add.")
    add_parser.set_defaults(func=lambda args: add_pubkey(args.pubkey))

    remove_parser = subparsers.add_parser("remove", help="Remove a supporter pubkey.")
    remove_parser.add_argument("--pubkey", required=True, help="Hex public key to remove.")
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
