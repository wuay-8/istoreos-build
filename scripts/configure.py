#!/usr/bin/env python3
"""Merge the official installed package set with explicit custom selections."""
import re
import sys
from pathlib import Path


def read_config(text):
    values = {}
    for line in text.splitlines():
        match = re.fullmatch(r"(CONFIG_\w[\w-]*)=(.*)", line)
        disabled = re.fullmatch(r"# (CONFIG_\w[\w-]*) is not set", line)
        if match:
            values[match[1]] = match[2]
        elif disabled:
            values[disabled[1]] = "n"
    return values


def main():
    base, custom, destination = map(Path, sys.argv[1:])
    values = read_config(base.read_text())
    # Official SDK/feed packages marked m are not needed in a firmware-only build.
    values = {key: ("n" if value == "m" else value) for key, value in values.items()}
    values.update(read_config(custom.read_text()))
    destination.write_text("".join(
        f"# {key} is not set\n" if value == "n" else f"{key}={value}\n"
        for key, value in values.items()
    ))


if __name__ == "__main__":
    main()
