#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path


SUPPORTERS_PATH = Path(__file__).resolve().parent / "relay" / "supporters.txt"
PUBKEY_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def print_usage() -> None:
    prog = Path(sys.argv[0]).name
    msg = (
        "Usage:\n"
        f"  python3 {prog} add <hex_pubkey>\n"
        f"  python3 {prog} remove <hex_pubkey>\n"
        f"  python3 {prog} list"
    )
    print(msg, file=sys.stderr)


def ensure_valid_pubkey(pubkey: str) -> None:
    if not PUBKEY_RE.fullmatch(pubkey):
        print("Error: pubkey must be exactly 64 hexadecimal characters.", file=sys.stderr)
        sys.exit(1)


def load_lines() -> list[str]:
    if not SUPPORTERS_PATH.exists():
        return []
    with SUPPORTERS_PATH.open("r", encoding="utf-8") as f:
        return f.readlines()


def existing_pubkeys(lines: list[str]) -> list[str]:
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
    current_keys_lower = {k.lower() for k in existing_pubkeys(lines)}
    if pubkey.lower() in current_keys_lower:
        print("Pubkey already present; nothing to add.")
        return

    SUPPORTERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SUPPORTERS_PATH.exists():
        current_content = SUPPORTERS_PATH.read_text(encoding="utf-8")
        newline_prefix = "" if current_content.endswith("\n") or current_content == "" else "\n"
    else:
        newline_prefix = ""

    with SUPPORTERS_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{newline_prefix}{pubkey}\n")


def remove_pubkey(pubkey: str) -> None:
    ensure_valid_pubkey(pubkey)
    lines = load_lines()
    target = pubkey.lower()
    kept: list[str] = []
    found = False

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and stripped.lower() == target:
            found = True
            continue
        kept.append(line)

    if not found:
        print("Pubkey not found; nothing to remove.")
        return

    write_lines_atomic(kept)


def list_pubkeys() -> None:
    lines = load_lines()
    for key in existing_pubkeys(lines):
        print(key)


def main() -> None:
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "add":
        if len(sys.argv) != 3:
            print_usage()
            sys.exit(1)
        add_pubkey(sys.argv[2])
    elif command == "remove":
        if len(sys.argv) != 3:
            print_usage()
            sys.exit(1)
        remove_pubkey(sys.argv[2])
    elif command == "list":
        if len(sys.argv) != 2:
            print_usage()
            sys.exit(1)
        list_pubkeys()
    else:
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
