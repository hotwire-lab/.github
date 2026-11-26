#!/usr/bin/env python3
"""Compile every HotWire ESP32 sketch and refresh public/firmware bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

JOBS = [
    # app, sketch folder, board suffix, fqbn, PSRAM
    ("logic-analyzer", "HotWire_XIAO_ESP32", "S3", "esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,CDCOnBoot=default", False),
    ("logic-analyzer", "HotWire_XIAO_ESP32", "C6", "esp32:esp32:XIAO_ESP32C6:CDCOnBoot=cdc", False),
    ("oscilloscope", "HotWire_Scope_XIAO_ESP32S3", "S3", "esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,CDCOnBoot=default,PSRAM=opi", False),
    ("oscilloscope", "HotWire_Scope_XIAO_ESP32C6", "C6", "esp32:esp32:XIAO_ESP32C6:CDCOnBoot=cdc", False),
    ("serial-terminal", "HotWire_UART_XIAO_ESP32S3", "S3", "esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,CDCOnBoot=default", False),
    ("serial-terminal", "HotWire_UART_XIAO_ESP32C6", "C6", "esp32:esp32:XIAO_ESP32C6:CDCOnBoot=cdc", False),
    ("signal-generator", "HotWire_SigGen_XIAO_ESP32S3", "S3", "esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,CDCOnBoot=default", False),
    ("signal-generator", "HotWire_SigGen_XIAO_ESP32C6", "C6", "esp32:esp32:XIAO_ESP32C6:CDCOnBoot=cdc", False),
    ("software-defined-radio", "HotWire_SDR_XIAO_ESP32S3", "S3", "esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,CDCOnBoot=default,PSRAM=opi", False),
    ("software-defined-radio", "HotWire_SDR_XIAO_ESP32C6", "C6", "esp32:esp32:XIAO_ESP32C6:CDCOnBoot=cdc", False),
]


def find_cli(explicit: str | None) -> str:
    if explicit:
        return explicit
    default = Path(
        r"C:\Users\Kari\AppData\Local\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
    )
    if default.is_file():
        return str(default)
    found = shutil.which("arduino-cli")
    if found:
        return found
    raise SystemExit("arduino-cli not found; pass --arduino-cli")


def compile_job(cli: str, app_dir: Path, sketch: str, suffix: str, fqbn: str) -> None:
    src = app_dir / "firmware" / sketch
    out = src / "build" if suffix == "C6" and app_dir.name != "logic-analyzer" else src / f"build_{suffix.lower()}"
    out.mkdir(parents=True, exist_ok=True)
    print(f"[{app_dir.name}] compiling {sketch} ({suffix})...")
    subprocess.run(
        [cli, "compile", "--fqbn", fqbn, "--output-dir", str(out), str(src)],
        check=True,
    )
    dest = app_dir / "public" / "firmware"
    dest.mkdir(parents=True, exist_ok=True)
    stem = f"{sketch}.ino"
    target_prefix = sketch if app_dir.name != "logic-analyzer" else f"HotWire_XIAO_ESP32{suffix}"
    for ext in (".bin", ".bootloader.bin", ".partitions.bin"):
        source = out / f"{stem}{ext}"
        if not source.is_file():
            raise SystemExit(f"missing build output {source}")
        shutil.copy2(source, dest / f"{target_prefix}.ino{ext}")
    print(f"[{app_dir.name}] copied {target_prefix}.ino.*")


def regenerate_manifest(app_dir: Path) -> None:
    ver_re = re.compile(r'#define\s+HOTWIRE_FW_VERSION\s+"([^"]+)"')
    sketches = []
    for ino in sorted((app_dir / "firmware").rglob("*.ino")):
        match = ver_re.search(ino.read_text(encoding="utf-8"))
        sketches.append({
            "sketch": str(ino.relative_to(app_dir)).replace("\\", "/"),
            "version": match.group(1) if match else None,
        })
    binaries = []
    for binary in sorted((app_dir / "public" / "firmware").glob("*.bin")):
        data = binary.read_bytes()
        embedded = re.findall(rb'"firmware":"([^"]+)"', data)
        binaries.append({
            "file": binary.name,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "embedded_firmware": [v.decode("utf-8", "replace") for v in embedded],
        })
    (app_dir / "firmware" / "manifest.json").write_text(
        json.dumps({"tool": app_dir.name, "caps_schema": 2, "sketches": sketches, "binaries": binaries}, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--arduino-cli", default=None)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    cli = find_cli(args.arduino_cli)
    for app, sketch, suffix, fqbn, _psram in JOBS:
        compile_job(cli, root / app, sketch, suffix, fqbn)
    for app in sorted({job[0] for job in JOBS}):
        regenerate_manifest(root / app)
        print(f"[{app}] firmware/manifest.json regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
