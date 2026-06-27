#!/usr/bin/env python3
import json
import re
import logging
from pathlib import Path

REPO_USER_DIR = Path(__file__).parent / "Library/Application Support/Code/User"
BASE = REPO_USER_DIR / "settings.json"
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
    # Clear whatever is there (symlink or generated file) so we can switch modes freely.
    if DEST.is_symlink() or DEST.exists():
        DEST.unlink()

    # No local overrides -> nothing to merge, symlink the base so edits are live.
    if not LOCAL.exists():
        log.info("no local overrides, symlinking base -> %s", DEST)
        DEST.symlink_to(BASE)
        return

    log.info("base: %s", BASE)
    settings = load_jsonc(BASE)
    log.info("loaded %d base keys", len(settings))
    log.info("merging local overrides: %s", LOCAL)
    settings = deep_merge(settings, load_jsonc(LOCAL))

    DEST.write_text(json.dumps(settings, indent=4) + "\n")
    log.info("wrote %d keys -> %s", len(settings), DEST)


if __name__ == "__main__":
    main()
