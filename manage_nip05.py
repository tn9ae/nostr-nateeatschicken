#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path


NOSTR_JSON_PATH = Path(__file__).resolve().parent / "site" / ".well-known" / "nostr.json"
PUBKEY_RE = re.compile(r"^[0-9a-fA-F]{64}$")


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


def print_usage() -> None:
    prog = Path(sys.argv[0]).name
    usage = (
        f"Usage:\n"
        f"  python3 {prog} add <handle> <hex_pubkey>\n"
        f"  python3 {prog} remove <handle>\n"
        f"  python3 {prog} list"
    )
    print(usage, file=sys.stderr)


def ensure_valid_pubkey(pubkey: str) -> None:
    if not PUBKEY_RE.fullmatch(pubkey):
        print("Error: pubkey must be exactly 64 hexadecimal characters.", file=sys.stderr)
        sys.exit(1)


def add_handle(handle: str, pubkey: str) -> None:
    ensure_valid_pubkey(pubkey)
    data = load_data()
    data.setdefault("names", {})
    data["names"][handle] = pubkey
    write_data(data)


def remove_handle(handle: str) -> None:
    data = load_data()
    if "names" in data and handle in data["names"]:
        del data["names"][handle]
        write_data(data)
    else:
        print(f"Handle '{handle}' not found; nothing to remove.")


def list_handles() -> None:
    data = load_data()
    for handle, pubkey in sorted(data.get("names", {}).items()):
        print(f"{handle} {pubkey}")


def main() -> None:
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "add":
        if len(sys.argv) != 4:
            print_usage()
            sys.exit(1)
        handle, pubkey = sys.argv[2], sys.argv[3]
        add_handle(handle, pubkey)
    elif command == "remove":
        if len(sys.argv) != 3:
            print_usage()
            sys.exit(1)
        handle = sys.argv[2]
        remove_handle(handle)
    elif command == "list":
        if len(sys.argv) != 2:
            print_usage()
            sys.exit(1)
        list_handles()
    else:
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
