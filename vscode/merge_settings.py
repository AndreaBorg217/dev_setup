#!/usr/bin/env python3
import json
import logging
import re
from pathlib import Path

BASE = Path(__file__).parent / "settings.json"
LOCAL = Path(__file__).parent / "settings.local.json"
DEST = Path.home() / "Library/Application Support/Code/User/settings.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("merge_settings")


def load_jsonc(path):
    lines = [line.split("//")[0] for line in path.read_text().splitlines()]
    return json.loads(re.sub(r",\s*([}\]])", r"\1", "\n".join(lines)))


def deep_merge(base, override):
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        else:
            if k in result and result[k] != v:
                log.info("override: %s = %r (was %r)", k, v, result[k])
            elif k not in result:
                log.info("add: %s = %r", k, v)
            result[k] = v
    return result


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)

    if not LOCAL.exists():
        if DEST.is_symlink() and DEST.resolve() == BASE.resolve():
            log.info("settings symlink is current")
            print("changed=false")
            return

        log.info("no local overrides, symlinking base -> %s", DEST)
        temporary = DEST.with_name(f".{DEST.name}.tmp")
        if temporary.is_symlink() or temporary.exists():
            temporary.unlink()
        temporary.symlink_to(BASE)
        temporary.replace(DEST)
        print("changed=true")
        return

    log.info("base: %s", BASE)
    settings = load_jsonc(BASE)
    log.info("loaded %d base keys", len(settings))
    log.info("merging local overrides: %s", LOCAL)
    settings = deep_merge(settings, load_jsonc(LOCAL))

    content = json.dumps(settings, indent=4) + "\n"
    if not DEST.is_symlink() and DEST.exists() and DEST.read_text() == content:
        log.info("merged settings are current")
        print("changed=false")
        return

    temporary = DEST.with_name(f".{DEST.name}.tmp")
    if temporary.is_symlink() or temporary.exists():
        temporary.unlink()
    temporary.write_text(content)
    temporary.replace(DEST)
    log.info("wrote %d keys -> %s", len(settings), DEST)
    print("changed=true")


if __name__ == "__main__":
    main()
