#!/usr/bin/env python3
"""Cross-repository consistency checks for the HotWire Lab suite."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

SLUGS = {
    "LogicAnalyzer": "logic",
    "Oscilloscope": "scope",
    "Sdr": "sdr",
    "SerialTerminal": "serial",
    "SignalGenerator": "siggen",
}

APPS = {
    "logic-analyzer": ("LogicAnalyzer", "HotWire Logic"),
    "oscilloscope": ("Oscilloscope", "HotWire Scope"),
    "software-defined-radio": ("Sdr", "HotWire SDR"),
    "serial-terminal": ("SerialTerminal", "HotWire Serial"),
    "signal-generator": ("SignalGenerator", "HotWire Gen"),
}
CORE = "hotwire-core"
SITE = "hotwire-lab.github.io"

MIN_VERSION_RE = re.compile(
    r"ToolId::(?P<tool>LogicAnalyzer|Oscilloscope|Sdr|SerialTerminal|SignalGenerator)"
    r"\s*=>\s*FirmwareVersion::new\((?P<major>\d+),\s*(?P<minor>\d+),\s*(?P<patch>\d+)\)"
)
FW_VERSION_RE = re.compile(r'#define\s+HOTWIRE_FW_VERSION\s+"([^"]+)"')
README_MIN_RE = re.compile(r"\[Live\]\([^)]+\)\)\s*—\s*`v(\d+\.\d+\.\d+)\+`")


def parse_version(raw: str) -> tuple[int, int, int] | None:
    core = raw.strip().lstrip("vV").split("-")[0].split("+")[0]
    parts = core.split(".")
    if len(parts) < 2:
        return None
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    except ValueError:
        return None


def cargo_package_version(path: Path) -> str:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return data["package"]["version"]


def core_tag_pin(path: Path) -> str | None:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    dep = data.get("dependencies", {}).get("hotwire-core")
    if isinstance(dep, dict):
        return dep.get("tag")
    return None


def main(root: Path) -> int:
    errors: list[str] = []
    notes: list[str] = []

    core_toml = root / CORE / "Cargo.toml"
    core_version = cargo_package_version(core_toml)
    expected_tag = f"v{core_version}"

    handshake = (root / CORE / "src" / "protocol" / "handshake.rs").read_text(encoding="utf-8")
    min_versions: dict[str, tuple[int, int, int]] = {}
    for match in MIN_VERSION_RE.finditer(handshake):
        min_versions[match.group("tool")] = (
            int(match.group("major")),
            int(match.group("minor")),
            int(match.group("patch")),
        )
    if not min_versions:
        errors.append("could not parse ToolId::min_firmware_version arms")

    for app, (tool, short_name) in APPS.items():
        app_dir = root / app
        if not app_dir.is_dir():
            errors.append(f"{app}: missing repository directory")
            continue

        # Core tag pin + lockfile.
        tag = core_tag_pin(app_dir / "Cargo.toml")
        if tag != expected_tag:
            errors.append(f"{app}: hotwire-core tag is {tag!r}, expected {expected_tag!r}")
        lock = (app_dir / "Cargo.lock").read_text(encoding="utf-8")
        lock_match = re.search(r'name = "hotwire-core"\r?\nversion = "([^"]+)"', lock)
        if not lock_match or lock_match.group(1) != core_version:
            errors.append(f"{app}: Cargo.lock hotwire-core version does not match {core_version}")

        # Firmware source version vs core minimum.
        source_versions = []
        for ino in sorted((app_dir / "firmware").rglob("*.ino")):
            source_versions.extend(FW_VERSION_RE.findall(ino.read_text(encoding="utf-8")))
        if not source_versions:
            errors.append(f"{app}: no HOTWIRE_FW_VERSION in firmware sketches")
        else:
            semvers = [parse_version(v) for v in source_versions]
            minimum = min_versions.get(tool)
            if minimum and all(v is not None and v < minimum for v in semvers):
                errors.append(
                    f"{app}: firmware versions {source_versions} are below core minimum {minimum}"
                )

        # Bundled binaries.
        verify_script = app_dir / "scripts" / "verify_firmware.py"
        if not verify_script.is_file():
            errors.append(f"{app}: missing scripts/verify_firmware.py")
        else:
            result = subprocess.run(
                [sys.executable, str(verify_script)],
                cwd=app_dir,
                text=True,
                capture_output=True,
            )
            if result.returncode != 0:
                errors.append(f"{app}: firmware verification failed\n{result.stderr.strip()}")
            else:
                notes.append(f"{app}: {result.stdout.strip()}")

        # Repository hygiene.
        for name in (".gitattributes", ".editorconfig"):
            if not (app_dir / name).is_file():
                errors.append(f"{app}: missing {name}")

        # Release profile.
        cargo_text = (app_dir / "Cargo.toml").read_text(encoding="utf-8")
        release = cargo_text.split("[profile.release]", 1)
        if len(release) != 2:
            errors.append(f"{app}: missing [profile.release]")
        else:
            for key in ("opt-level", "lto", "codegen-units", "panic", "strip"):
                if f"{key}" not in release[1]:
                    errors.append(f"{app}: [profile.release] missing {key}")

        # Workflow must use the shared reusable workflow.
        workflow = (app_dir / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        if "hotwire-lab/.github/.github/workflows/pwa-deploy.yml@main" not in workflow:
            errors.append(f"{app}: deploy.yml does not use the shared pwa-deploy workflow")

        # Bundled firmware schema/tool markers.
        for binary in sorted((app_dir / "public" / "firmware").glob("*.ino.bin")):
            data = binary.read_bytes()
            if b'"schema":2' not in data:
                errors.append(f"{app}: {binary.name} does not embed caps schema 2")
            tool_marker = f'"tool":"{SLUGS[tool]}"'.encode()
            if tool_marker not in data:
                errors.append(f"{app}: {binary.name} does not embed {tool_marker!r}")

        # PWA manifest.
        manifest_path = app_dir / "public" / "manifest.webmanifest"
        if not manifest_path.is_file():
            errors.append(f"{app}: missing public/manifest.webmanifest")
        else:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("short_name") != short_name:
                errors.append(
                    f"{app}: manifest short_name is {manifest.get('short_name')!r}, expected {short_name!r}"
                )
            if manifest.get("theme_color") != "#0b0e12":
                errors.append(f"{app}: manifest theme_color is not #0b0e12")
            icons = manifest.get("icons", [])
            sizes = {icon.get("sizes") for icon in icons}
            for size in ("192x192", "512x512"):
                if size not in sizes:
                    errors.append(f"{app}: manifest missing {size} icon")
            if not any(icon.get("purpose") == "maskable" or "maskable" in str(icon.get("purpose")) for icon in icons):
                errors.append(f"{app}: manifest has no maskable icon")

        # Self-hosted fonts and vendored flasher assets.
        for font in (
            "ibm-plex-sans-latin-400-normal.woff2",
            "ibm-plex-sans-latin-600-normal.woff2",
            "ibm-plex-mono-latin-400-normal.woff2",
            "ibm-plex-mono-latin-500-normal.woff2",
        ):
            if not (app_dir / "public" / "fonts" / font).is_file():
                errors.append(f"{app}: missing public/fonts/{font}")
        if not (app_dir / "public" / "vendor" / "esptool-js.bundle.js").is_file():
            errors.append(f"{app}: missing public/vendor/esptool-js.bundle.js")
        for icon in ("icon-180.png", "icon-192.png", "icon-512.png"):
            if not (app_dir / "public" / icon).is_file():
                errors.append(f"{app}: missing public/{icon}")

        # SEO/social head tags.
        index = (app_dir / "index.html").read_text(encoding="utf-8")
        for needle in (
            'rel="canonical"',
            'property="og:image"',
            'name="twitter:card"',
            'application/ld+json',
        ):
            if needle not in index:
                errors.append(f"{app}: index.html missing {needle}")

        if "fonts.googleapis.com" in index or "fonts.gstatic.com" in index:
            errors.append(f"{app}: index.html still references Google Fonts")
        if 'rel="preload" href="./fonts/' not in index:
            errors.append(f"{app}: index.html missing local font preload")
        sw = (app_dir / "public" / "sw.js").read_text(encoding="utf-8")
        if "./fonts/ibm-plex-sans-latin-400-normal.woff2" not in sw:
            errors.append(f"{app}: sw.js does not precache local fonts")

        # Docs mention the full five-tool switcher.
        readme = (app_dir / "README.md").read_text(encoding="utf-8")
        if "Gen" not in readme and "Signal Generator" not in readme:
            errors.append(f"{app}: README does not mention the Signal Generator tool")

        # Bootloader magic must be used everywhere.
        for rs in (app_dir / "src").rglob("*.rs"):
            text = rs.read_text(encoding="utf-8")
            if "build_bootloader_cmd_zero" in text:
                errors.append(f"{app}: {rs.relative_to(app_dir)} still uses build_bootloader_cmd_zero")

    # Shared firmware header must be byte-identical in every sketch folder.
    header_hashes: dict[str, list[str]] = {}
    for app in APPS:
        for header in (root / app / "firmware").rglob("hotwire_protocol.h"):
            digest = __import__("hashlib").sha256(header.read_bytes()).hexdigest()
            header_hashes.setdefault(digest, []).append(str(header.relative_to(root)))
    if len(header_hashes) > 1:
        errors.append(f"firmware hotwire_protocol.h files differ: {header_hashes}")
    if not header_hashes:
        errors.append("no firmware hotwire_protocol.h files found")

    # Core docs must list the current minimum versions.
    core_readme = (root / CORE / "README.md").read_text(encoding="utf-8")
    for tool, version in min_versions.items():
        rendered = ".".join(str(part) for part in version)
        if f"`v{rendered}+`" not in core_readme:
            errors.append(f"{CORE}/README.md does not mention v{rendered}+ for {tool}")

    # Landing page firmware minimum labels.
    site_data = (root / SITE / "src" / "data" / "tools.ts").read_text(encoding="utf-8")
    for tool, version in min_versions.items():
        rendered = ".".join(str(part) for part in version)
        if tool != "SerialTerminal" and f"v{rendered}+" not in site_data:
            errors.append(f"{SITE}: tools.ts does not mention v{rendered}+ for {tool}")

    if notes:
        for note in notes:
            print(f"OK: {note}")
    if errors:
        print("\nSuite consistency check failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"\nSuite consistency check passed (core {expected_tag}, {len(APPS)} apps).")
    return 0


if __name__ == "__main__":
    workspace = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    raise SystemExit(main(workspace))