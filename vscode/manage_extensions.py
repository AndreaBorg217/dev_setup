#!/usr/bin/env python3
import argparse
import json
import logging
import re
import subprocess
from pathlib import Path

EXTENSIONS_JSON = Path(__file__).parent / "extensions.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("manage_extensions")


def parse_extensions(path):
    lines = []
    for line in path.read_text().splitlines():
        lines.append(line.split("//")[0])
    content = re.sub(r",\s*([}\]])", r"\1", "\n".join(lines))
    recs = json.loads(content)["recommendations"]
    log.info("parsed %d extensions from %s", len(recs), path.name)
    return recs


def get_installed():
    result = subprocess.run(
        ["code", "--list-extensions"], capture_output=True, text=True, check=True
    )
    return {e.lower() for e in result.stdout.strip().splitlines() if e}


def list_installed():
    result = subprocess.run(
        ["code", "--list-extensions", "--show-versions"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [e for e in result.stdout.strip().splitlines() if e]


def print_installed():
    installed = list_installed()
    log.info("%d extensions installed", len(installed))
    for ext in installed:
        print(ext)


def install(extensions):
    installed = get_installed()
    missing = [e for e in extensions if e.lower() not in installed]
    log.info(
        "%d/%d already installed, installing %d",
        len(extensions) - len(missing),
        len(extensions),
        len(missing),
    )
    for ext in missing:
        log.info("installing: %s", ext)
        subprocess.run(["code", "--install-extension", ext], check=True)
    log.info("install done")


def uninstall_all():
    remaining = get_installed()
    log.info("uninstalling %d extensions", len(remaining))
    while remaining:
        for ext in sorted(remaining):
            log.info("uninstalling: %s", ext)
            result = subprocess.run(
                ["code", "--uninstall-extension", ext], capture_output=True, text=True
            )
            if result.returncode != 0:
                message = (result.stderr or result.stdout).strip()
                log.warning("uninstall failed for %s: %s", ext, message)
        still_installed = get_installed() & remaining
        if still_installed == remaining:
            log.warning("could not uninstall: %s", sorted(still_installed))
            break
        remaining = still_installed
    log.info("uninstall done")
    print_installed()


def main():
    parser = argparse.ArgumentParser(
        description="Manage VSCode extensions from extensions.json"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--install", action="store_true", help="Install missing extensions"
    )
    group.add_argument(
        "--uninstall", action="store_true", help="Uninstall all extensions"
    )
    group.add_argument(
        "--reinstall",
        action="store_true",
        help="Uninstall all, then install from extensions.json",
    )
    group.add_argument("--list", action="store_true", help="List installed extensions")
    args = parser.parse_args()

    if args.install:
        install(parse_extensions(EXTENSIONS_JSON))
    elif args.uninstall:
        uninstall_all()
    elif args.reinstall:
        uninstall_all()
        install(parse_extensions(EXTENSIONS_JSON))
    elif args.list:
        print_installed()


if __name__ == "__main__":
    main()
