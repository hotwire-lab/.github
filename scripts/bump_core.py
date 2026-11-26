#!/usr/bin/env python3
"""Bump the hotwire-core git tag in every HotWire app and refresh lockfiles."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

APPS = [
    "logic-analyzer",
    "oscilloscope",
    "software-defined-radio",
    "serial-terminal",
    "signal-generator",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True, help="Tag, e.g. v0.6.0")
    parser.add_argument("--root", default=".", help="Workspace root")
    parser.add_argument("--test", action="store_true", help="Run cargo test after updating")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    tag = args.version.strip()
    if not tag.startswith("v"):
        tag = f"v{tag}"

    for app in APPS:
        app_dir = root / app
        cargo_toml = app_dir / "Cargo.toml"
        if not cargo_toml.is_file():
            print(f"ERROR: missing {cargo_toml}", file=sys.stderr)
            return 1
        text = cargo_toml.read_text(encoding="utf-8")
        updated, count = re.subn(
            r'(hotwire-core\s*=\s*\{[^}]*tag\s*=\s*")[^"]+(")',
            lambda m: m.group(1) + tag + m.group(2),
            text,
        )
        if count == 0:
            print(f"ERROR: hotwire-core tag not found in {cargo_toml}", file=sys.stderr)
            return 1
        cargo_toml.write_text(updated, encoding="utf-8")
        print(f"{app}: pinned hotwire-core {tag}")

        subprocess.run(["cargo", "update", "-p", "hotwire-core"], cwd=app_dir, check=True)
        if args.test:
            subprocess.run(["cargo", "test"], cwd=app_dir, check=True)
            subprocess.run(
                ["cargo", "clippy", "--all-targets", "--", "-D", "warnings"],
                cwd=app_dir,
                check=True,
            )

    print("Done. Remove local .cargo/config.toml patches before committing if present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
