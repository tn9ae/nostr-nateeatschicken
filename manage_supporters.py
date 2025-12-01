#!/usr/bin/env python3
import os
import sys
from typing import List

SUPPORTERS_PATH = "/opt/nostr/relay/supporters.txt"


def read_lines() -> List[str]:
    """Read all lines from supporters.txt, or return an empty list."""
    if not os.path.exists(SUPPORTERS_PATH):
        return []
    with open(SUPPORTERS_PATH, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def write_lines(lines: List[str]) -> None:
    """Write all lines back atomically to supporters.txt."""
    tmp_path = SUPPORTERS_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    os.replace(tmp_path, SUPPORTERS_PATH)


def add_supporter(hexpub: str) -> None:
    hexpub = hexpub.strip()
    if not hexpub:
        print("Empty hexpub, nothing to add.", file=sys.stderr)
        sys.exit(1)

    lines = read_lines()

    # Preserve comments
    existing = {line for line in lines if not line.startswith("#")}
    if hexpub in existing:
        print(f"Supporter already present: {hexpub}")
        return

    lines.append(hexpub)
    write_lines(lines)
    print(f"Added supporter: {hexpub}")


def remove_supporter(hexpub: str) -> None:
    hexpub = hexpub.strip()
    if not hexpub:
        print("Empty hexpub, nothing to remove.", file=sys.stderr)
        sys.exit(1)

    lines = read_lines()
    new_lines = []
    removed = False

    for line in lines:
        if not line.startswith("#") and line.strip() == hexpub:
            removed = True
            continue
        new_lines.append(line)

    if not removed:
        print(f"Supporter not found: {hexpub}", file=sys.stderr)
        sys.exit(1)

    write_lines(new_lines)
    print(f"Removed supporter: {hexpub}")


def list_supporters() -> None:
    lines = read_lines()
    for line in lines:
        print(line)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: manage_supporters.py [add|remove|list] [hexpub]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        if len(sys.argv) != 3:
            print("Usage: manage_supporters.py add <hexpub>", file=sys.stderr)
            sys.exit(1)
        add_supporter(sys.argv[2])
    elif cmd == "remove":
        if len(sys.argv) != 3:
            print("Usage: manage_supporters.py remove <hexpub>", file=sys.stderr)
            sys.exit(1)
        remove_supporter(sys.argv[2])
    elif cmd == "list":
        list_supporters()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
